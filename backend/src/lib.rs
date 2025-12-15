// src/lib.rs
//
// PyO3 wrapper for the wifi_backend module.
// Exports to Python:
//   - scan() -> list[dict]
//   - compute_channels() -> dict[channel -> count]
//   - compute_best_channel() -> int
//   - connected_bssid() -> str | None

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

mod lib_rust;
use lib_rust::{
    compute_best_channel_internal,
    compute_channels_internal,
    format_mac,
    get_connected_bssid,
    scan_all_bss,
};

fn map_pyerr<T>(res: anyhow::Result<T>) -> PyResult<T> {
    res.map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

/// Python: scan() -> List[Dict]
/// Each dict: {ssid, bssid, freq_mhz, signal_dbm, channel}
#[pyfunction]
fn scan(py: Python<'_>) -> PyResult<PyObject> {
    let rows = map_pyerr(scan_all_bss())?;

    let list = PyList::empty_bound(py);

    for r in rows {
        let d = PyDict::new_bound(py);

        if let Some(ref ssid) = r.ssid {
            d.set_item("ssid", ssid)?;
        }
        if let Some(ref mac) = r.bssid {
            d.set_item("bssid", format_mac(mac))?;
        }
        if let Some(freq) = r.freq_mhz {
            d.set_item("freq_mhz", freq)?;
        }
        if let Some(sig) = r.signal_dbm {
            d.set_item("signal_dbm", sig)?;
        }
        if let Some(ch) = r.channel {
            d.set_item("channel", ch)?;
        }

        list.append(d)?;
    }

    Ok(list.into_py(py))
}

/// Python: compute_channels() -> Dict[int, int]
#[pyfunction]
fn compute_channels(py: Python<'_>) -> PyResult<PyObject> {
    let map = map_pyerr(compute_channels_internal())?;

    let d = PyDict::new_bound(py);
    for (ch, count) in map {
        d.set_item(ch, count)?;
    }

    Ok(d.into_py(py))
}

/// Python: compute_best_channel() -> int
#[pyfunction]
fn compute_best_channel() -> PyResult<u32> {
    map_pyerr(compute_best_channel_internal())
}

/// Python: connected_bssid() -> str | None
#[pyfunction]
fn connected_bssid(py: Python<'_>) -> PyResult<PyObject> {
    let maybe = map_pyerr(get_connected_bssid())?;
    let obj = match maybe {
        Some(mac) => format_mac(&mac).into_py(py),
        None => py.None(),
    };
    Ok(obj)
}

/// Module init. Name *must* be wifi_backend to match Cargo.toml [lib].name.
#[pymodule]
fn wifi_backend(_py: Python<'_>, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan, m)?)?;
    m.add_function(wrap_pyfunction!(compute_channels, m)?)?;
    m.add_function(wrap_pyfunction!(compute_best_channel, m)?)?;
    m.add_function(wrap_pyfunction!(connected_bssid, m)?)?;
    Ok(())
}
