// Exposes:
//   - scan_all_bss() -> Result<Vec<BssRow>>
//   - get_connected_bssid() -> Result<Option<[u8; 6]>>
//   - compute_channels_internal() -> Result<HashMap<u32, u32>>
//   - compute_best_channel_internal() -> Result<u32>
//
// Uses a fresh neli-wifi Socket on each call, so every room scan is new.

use anyhow::{anyhow, Result};
use neli_wifi::{Bss, Socket, Station};
use std::collections::HashMap;
use std::fmt::Write as _;


// Struct that will hold information collected from each BSS
#[derive(Debug, Clone)]
pub struct BssRow {
    pub ssid: Option<String>,
    pub bssid: Option<[u8; 6]>,
    pub freq_mhz: Option<u32>,
    pub signal_dbm: Option<f32>,
    pub channel: Option<u32>,
}

// Converts a u8 array to 
fn vec_to_mac(v: &[u8]) -> Option<[u8; 6]> {
    if v.len() < 6 {
        return None;
    }
    let mut out = [0u8; 6];
    out.copy_from_slice(&v[..6]);
    Some(out)
}

pub fn format_mac(bytes: &[u8; 6]) -> String {
    let mut s = String::with_capacity(17);
    for (i, b) in bytes.iter().enumerate() {
        if i > 0 {
            let _ = write!(s, ":");
        }
        let _ = write!(s, "{:02x}", b);
    }
    s
}

//Collect information for each SSID scann.
fn parse_ssid_ie(mut ies: &[u8]) -> Option<String> {
    // IEs are TLVs: [id, len, value...]
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
            // SSID; may be empty for hidden
            return Some(String::from_utf8_lossy(val).to_string());
        }
    }
    None
}

// Channel mapping, only goes to channel 165 before returning 0 as the channel since we are only looking at < 5G
fn freq_to_channel(freq: &u32) -> u32 {
    match *freq {
        2412 => 1,
        2417 => 2,
        2422 => 3,
        2427 => 4,
        2432 => 5,
        2437 => 6,
        2442 => 7,
        2447 => 8,
        2452 => 9,
        2457 => 10,
        2462 => 11,
        2467 => 12,
        2472 => 13,
        2482 => 14,
        5180 => 36,
        5200 => 40,
        5220 => 44,
        5240 => 48,
        5260 => 52,
        5280 => 56,
        5300 => 60,
        5320 => 64,
        5500 => 100,
        5520 => 104,
        5540 => 108,
        5560 => 112,
        5580 => 116,
        5600 => 120,
        5620 => 124,
        5640 => 128,
        5660 => 132,
        5680 => 136,
        5700 => 140,
        5745 => 149,
        5765 => 153,
        5785 => 157,
        5805 => 161,
        5825 => 165,
        5845 => 169,
        5865 => 173,
        5885 => 177,
        _ => 0,
    }
}

// Check which frequency we are on and correlate it to the correct band. 
fn freq_band(freq_mhz: u32) -> u8 {
    // 1 = 2.4 GHz, 2 = 5 GHz, 3 = All others
    match freq_mhz {
        2401..=2495 => 1,
        5150..=5895 => 2,
        _ => 3,
    }
}

/// Heuristic: two BSSIDs are likely from the same device if
/// bytes 1..=4 match Only first & last differ with my Ubiquiti routers.
fn same_device(a: &[u8; 6], b: &[u8; 6]) -> bool {
    a[1] == b[1] && a[2] == b[2] && a[3] == b[3] && a[4] == b[4]
}

/// -------------------- Public internal APIs --------------------

/// Fresh scan of all BSSs visible from the Wi-Fi interface.
pub fn scan_all_bss() -> Result<Vec<BssRow>> {
    //Connect a socket
    let mut sock = Socket::connect()?;

    //Gather interface information from socket
    let iface = sock
        .get_interfaces_info()?
        .into_iter()
        .next()
        .ok_or_else(|| anyhow!("no Wi-Fi interface found"))?;

    let ifindex = iface
        .index
        .ok_or_else(|| anyhow!("Wi-Fi interface index missing"))?;

    // neli-wifi returns Vec<Bss> here
    //Gather BSS info
    let bsses: Vec<Bss> = sock.get_bss_info(ifindex)?;

    let mut out = Vec::new();
    //Iterate through in information collected from the BSS
    for b in bsses {
        let ssid = b
            .information_elements
            .as_deref()
            .and_then(parse_ssid_ie);
        //Collect BSSID
        let bssid = b.bssid.as_deref().and_then(vec_to_mac);
        //Collect Freq (in MHz)
        let freq_mhz = b.frequency;
        //Determine the channel being used used
        let channel = freq_mhz.and_then(|f| {
            let ch = freq_to_channel(&f);
            if ch == 0 { None } else { Some(ch) }
        });

        // BSS signal is in mBm (1/100 dBm)
        let signal_dbm = b.signal.map(|mbm| (mbm as f32) / 100.0);
        //Store all the collected information in a Vec that will be returned.
        out.push(BssRow {
            ssid,
            bssid,
            freq_mhz,
            signal_dbm,
            channel,
        });
    }

    Ok(out)
}

// Currently connected AP's BSSID (if any), as raw bytes.
pub fn get_connected_bssid() -> Result<Option<[u8; 6]>> {
    let mut sock = Socket::connect()?;

    let iface = sock
        .get_interfaces_info()?
        .into_iter()
        .next()
        .ok_or_else(|| anyhow!("no Wi-Fi interface found"))?;

    let ifindex = iface
        .index
        .ok_or_else(|| anyhow!("Wi-Fi interface index missing"))?;

    // For neli-wifi 0.5.x this returns a single Station
    let st: Station = sock.get_station_info(ifindex)?;
    //Translate the bytes collected to a readable MAC
    if let Some(ref v) = st.bssid {
        if let Some(mac) = vec_to_mac(v) {
            return Ok(Some(mac));
        }
    }

    Ok(None)
}

/// Simple channel count: how many APs per channel.
pub fn compute_channels_internal() -> Result<HashMap<u32, u32>> {
    let rows = scan_all_bss()?;
    let mut counts: HashMap<u32, u32> = HashMap::new();

    for r in rows {
        if let Some(ch) = r.channel {
            if ch > 0 {
                *counts.entry(ch).or_insert(0) += 1;
            }
        }
    }

    Ok(counts)
}

/// Smart "best channel" computation:
///
/// - Uses connected BSSID if available
/// - Only compares channels in the same band (2.4 vs 5GHz)
/// - Ignores APs weaker than THRESH_DBM
/// - Ignores your own AP and "same device" BSSIDs as interference
/// - Prefers to stay on current channel if its interference is close
///   to the best option.
pub fn compute_best_channel_internal() -> Result<u32> {
    //DBM threshold 
    const THRESH_DBM: f32 = -80.0;
    const MARGIN: f32 = 10.0; // how much worse than best before we recommend moving

    //Collect all BSS
    let rows = scan_all_bss()?;
    //What is the BSSID we are on?
    let connected = get_connected_bssid()?;

    // Figure out which channel and band we're actually on (if connected).
    let mut current_ch: Option<u32> = None;
    let mut current_band: Option<u8> = None;

    if let Some(ref cmac) = connected {
        for r in &rows {
            if let Some(ref rbssid) = r.bssid {
                if rbssid == cmac {
                    if let (Some(ch), Some(freq)) = (r.channel, r.freq_mhz) {
                        current_ch = Some(ch);
                        current_band = Some(freq_band(freq));
                    }
                    break;
                }
            }
        }
    }

    // Build interference weights per (band, channel) from other visible APs.
    let mut weight: HashMap<(u8, u32), f32> = HashMap::new();

    for r in &rows {
        let ch = match r.channel {
            Some(c) if c > 0 => c,
            _ => continue,
        };
        let freq = match r.freq_mhz {
            Some(f) => f,
            None => continue,
        };
        let band = freq_band(freq);
        let sig = r.signal_dbm.unwrap_or(-90.0);
        if sig < THRESH_DBM {
            continue; // too weak, ignore
        }

        // Skip our own device BSSIDs as interference
        if let (Some(ref cmac), Some(ref rbssid)) = (&connected, &r.bssid) {
            if rbssid == cmac || same_device(cmac, rbssid) {
                continue;
            }
        }

        // Stronger AP signal can have more interference if they are near the channel we are on
        let w = (sig + 100.0).max(0.0);
        *weight.entry((band, ch)).or_insert(0.0) += w;
    }

    // If we're connected and know our channel+band, try to stay put if it's good.
    if let (Some(cur_ch), Some(cur_band)) = (current_ch, current_band) {
        // Find the best (lowest weight) channel in *this band*.
        let mut best_opt: Option<(u32, f32)> = None;

        for (&(band, ch), &w) in &weight {
            if band != cur_band {
                continue;
            }
            match best_opt {
                None => best_opt = Some((ch, w)),
                Some((_, bw)) if w < bw => best_opt = Some((ch, w)),
                _ => {}
            }
        }

        // Interference on our current channel (0.0 if nobody above threshold)
        let cur_w = *weight.get(&(cur_band, cur_ch)).unwrap_or(&0.0);

        if let Some((best_ch, best_w)) = best_opt {
            // If our current channel is within MARGIN of the best, stay.
            if cur_w <= best_w + MARGIN {
                return Ok(cur_ch);
            } else {
                return Ok(best_ch);
            }
        } else {
            // No neighbors above threshold in our band -> our channel is clean.
            return Ok(cur_ch);
        }
    }

    // If we don't know what we're connected to, pick global argmin across bands.
    if weight.is_empty() {
        // No interference seen at all
        return Ok(1);
    }

    let mut best: Option<(u32, f32)> = None;
    for (&(_band, ch), &w) in &weight {
        match best {
            None => best = Some((ch, w)),
            Some((_, bw)) if w < bw => best = Some((ch, w)),
            _ => {}
        }
    }

    Ok(best.unwrap().0)
}
