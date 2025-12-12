// backend/src/lib_rust.rs
//
// Target crate versions:
//   neli = 0.4.4
//   nl80211 = 0.0.2
//
// Notes:
// - In neli 0.4.4, NlPayload is in neli::nl (NOT neli::nlmsg).
// - Genlmsghdr::new(...) returns Self (no Result) in 0.4.4.
// - Interface index from nl80211::InterfaceInfo is Option<Vec<u8>>.
// - We only need ONE valid ifindex to trigger scan; results include all BSS.
// - BSS parsing handles common attribute IDs and uses fallbacks for SSID/signal.

use anyhow::{bail, Context, Result};
use nl80211::{Socket, Nl80211Attr as Attr, Nl80211Cmd as Cmd, NL_80211_GENL_VERSION};

use neli::consts::nl::{NlmF, Nlmsg};
use neli::genl::Genlmsghdr;
use neli::nl::{NlPayload, Nlmsghdr};
use neli::nlattr::Nlattr;

use std::collections::HashMap;
use std::fmt::Write as _;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Default)]
pub struct BssRow {
    pub ssid: Option<String>,
    pub bssid: Option<String>,
    pub freq_mhz: Option<u32>,
    pub signal_dbm: Option<f32>,
    pub channel: Option<u32>,
}

/// Scan all visible BSS entries.
///
/// We pick the first interface with a usable index only to issue TRIGGER_SCAN.
/// The subsequent GET_SCAN dump returns all BSS known to the phy.
pub fn scan_all_ssids() -> Result<Vec<BssRow>> {
    let mut sock = Socket::connect()?;
    let ifaces = sock.get_interfaces_info()?;

    // Find ANY iface with a non-empty index to drive the scan request.
    let iface = ifaces
        .into_iter()
        .find(|i| i.index.as_ref().map(|v| !v.is_empty()).unwrap_or(false))
        .context("no Wi-Fi interface with usable index bytes")?;

    let index_bytes = iface
        .index
        .as_ref()
        .context("interface index missing")?;
    let ifindex = le_u32(index_bytes)?;

    trigger_scan(&mut sock, ifindex)?;
    wait_scan_done(&mut sock, Duration::from_secs(4))?;
    dump_scan_results(&mut sock, ifindex)
}

fn trigger_scan(sock: &mut Socket, ifindex: u32) -> Result<()> {
    let mut attrs: Vec<Nlattr<Attr, Vec<u8>>> = Vec::new();

    // NL80211_ATTR_IFINDEX
    attrs.push(Nlattr::new(
        None,
        Attr::AttrIfindex,
        ifindex.to_le_bytes().to_vec(),
    )?);

    // NL80211_ATTR_SCAN_SSIDS (wildcard => all SSIDs)
    attrs.push(Nlattr::new(None, Attr::AttrScanSsids, Vec::<u8>::new())?);

    let genlhdr = Genlmsghdr::new(Cmd::CmdTriggerScan, NL_80211_GENL_VERSION, attrs);
    let nlhdr = Nlmsghdr::new(
        None,
        sock.family_id,
        vec![NlmF::Request],
        None,
        None,
        genlhdr,
    );

    sock.sock.send_nl(nlhdr)?;
    Ok(())
}

fn wait_scan_done(sock: &mut Socket, timeout: Duration) -> Result<()> {
    let start = Instant::now();
    let mut iter = sock.sock.iter::<Nlmsg, Genlmsghdr<Cmd, Attr>>();

    while start.elapsed() < timeout {
        if let Some(Ok(msg)) = iter.next() {
            if let NlPayload::Payload(genl) = msg.nl_payload {
                match genl.cmd {
                    Cmd::CmdNewScanResults => return Ok(()),
                    Cmd::CmdScanAborted => bail!("scan aborted"),
                    _ => {}
                }
            }
        } else {
            std::thread::sleep(Duration::from_millis(20));
        }
    }

    bail!("scan timeout");
}

fn dump_scan_results(sock: &mut Socket, ifindex: u32) -> Result<Vec<BssRow>> {
    let mut attrs: Vec<Nlattr<Attr, Vec<u8>>> = Vec::new();

    attrs.push(Nlattr::new(
        None,
        Attr::AttrIfindex,
        ifindex.to_le_bytes().to_vec(),
    )?);

    let genlhdr = Genlmsghdr::new(Cmd::CmdGetScan, NL_80211_GENL_VERSION, attrs);
    let nlhdr = Nlmsghdr::new(
        None,
        sock.family_id,
        vec![NlmF::Request, NlmF::Dump],
        None,
        None,
        genlhdr,
    );

    sock.sock.send_nl(nlhdr)?;

    let mut iter = sock.sock.iter::<Nlmsg, Genlmsghdr<Cmd, Attr>>();
    let mut out: Vec<BssRow> = Vec::new();

    while let Some(Ok(msg)) = iter.next() {
        match msg.nl_type {
            Nlmsg::Error => bail!("GET_SCAN: netlink error"),
            Nlmsg::Done => break,
            _ => {
                if let NlPayload::Payload(genl) = msg.nl_payload {
                    for a in &genl.attrs {
                        if a.nla_type == Attr::AttrBss {
                            if let Some(row) = parse_bss(&a.payload) {
                                out.push(row);
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(out)
}

/// Parse a nested NL80211_ATTR_BSS blob.
///
/// Common nl80211_bss attr IDs:
///  1 = NL80211_BSS_BSSID
///  2 = NL80211_BSS_FREQUENCY (u32 MHz)
///  7 = NL80211_BSS_SIGNAL_UNSPEC (u8-ish)
///  8 = NL80211_BSS_INFORMATION_ELEMENTS (IEs; SSID is IE id=0)
/// 10 = NL80211_BSS_SIGNAL_MBM (i32 mBm)
/// 31 = NL80211_BSS_SSID (some drivers)
fn parse_bss(nested: &[u8]) -> Option<BssRow> {
    let mut rem = nested;
    let mut row = BssRow::default();

    while rem.len() >= 4 {
        let len = u16::from_le_bytes([rem[0], rem[1]]) as usize;
        if len < 4 || len > rem.len() {
            break;
        }

        let attr_type = u16::from_le_bytes([rem[2], rem[3]]);
        let payload = &rem[4..len];

        match attr_type {
            // BSSID
            1 => {
                if payload.len() >= 6 {
                    row.bssid = Some(format_mac(&payload[0..6]));
                }
            }

            // FREQUENCY MHz
            2 => {
                if payload.len() >= 4 {
                    if let Ok(f) = le_u32(payload) {
                        row.freq_mhz = Some(f);
                        row.channel = freq_to_channel(f);
                    }
                }
            }

            // INFORMATION_ELEMENTS => SSID from IE id=0
            8 => {
                if row.ssid.is_none() {
                    if let Some(ssid) = parse_ssid_ie(payload) {
                        row.ssid = Some(ssid);
                    }
                }
            }

            // SIGNAL_MBM => i32 mBm (divide by 100)
            10 => {
                if payload.len() >= 4 {
                    if let Ok(mbm_u32) = le_u32(payload) {
                        let mbm_i32 = mbm_u32 as i32;
                        row.signal_dbm = Some(mbm_i32 as f32 / 100.0);
                    }
                }
            }

            // SIGNAL_UNSPEC fallback
            7 => {
                if row.signal_dbm.is_none() && !payload.is_empty() {
                    let p = payload[0] as f32; // 0..100-ish
                    row.signal_dbm = Some(p - 100.0); // rough dBm-ish mapping
                }
            }

            // Direct SSID fallback (driver-specific)
            31 => {
                if row.ssid.is_none() && !payload.is_empty() {
                    row.ssid = Some(String::from_utf8_lossy(payload).to_string());
                }
            }

            _ => {}
        }

        // netlink alignment to 4 bytes
        let pad = ((len + 3) & !3) - len;
        let adv = len + pad;
        if adv > rem.len() {
            break;
        }
        rem = &rem[adv..];
    }

    Some(row)
}

fn parse_ssid_ie(mut ies: &[u8]) -> Option<String> {
    while ies.len() >= 2 {
        let id = ies[0];
        let len = ies[1] as usize;
        ies = &ies[2..];

        if len > ies.len() {
            break;
        }

        let val = &ies[..len];
        ies = &ies[len..];

        if id == 0 {
            return Some(String::from_utf8_lossy(val).to_string());
        }
    }
    None
}

fn le_u32(b: &[u8]) -> Result<u32> {
    if b.len() < 4 {
        bail!("not enough bytes");
    }
    let mut tmp = [0u8; 4];
    tmp.copy_from_slice(&b[..4]);
    Ok(u32::from_le_bytes(tmp))
}

fn format_mac(bytes: &[u8]) -> String {
    let mut s = String::new();
    for (i, b) in bytes.iter().take(6).enumerate() {
        if i > 0 {
            let _ = write!(s, ":");
        }
        let _ = write!(s, "{:02x}", b);
    }
    s
}

fn freq_to_channel(f: u32) -> Option<u32> {
    match f {
        2412..=2484 => Some((f - 2407) / 5),
        5180..=5885 => Some((f - 5000) / 5),
        5955..=7115 => Some((f - 5950) / 5),
        _ => None,
    }
}

/// Public API: used by lib.rs PyO3 wrapper
pub fn compute_best_channel_internal() -> Result<u32> {
    let rows = scan_all_ssids()?;
    Ok(best_channel_from_rows(&rows))
}

/// Heuristic best-channel pick using only current scan:
/// - Compute interference weight per observed channel
/// - Stronger APs contribute more weight
/// - Return channel with lowest weight
/// - If nothing observed, fall back to channel 1
fn best_channel_from_rows(rows: &[BssRow]) -> u32 {
    let mut weight: HashMap<u32, f32> = HashMap::new();

    for r in rows {
        let ch = match r.channel {
            Some(c) if c > 0 => c,
            _ => continue,
        };

        let w = r.signal_dbm.unwrap_or(-80.0) + 100.0;
        *weight.entry(ch).or_insert(0.0) += w;
    }

    if weight.is_empty() {
        return 1;
    }

    let mut best = (1u32, f32::INFINITY);
    for (&ch, &w) in &weight {
        if w < best.1 {
            best = (ch, w);
        }
    }

    best.0
}
