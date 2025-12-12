# Wifi-Mesh Optimzer
 Author: Dillon Hacker

## Notes:
Formating for markdown needs to be addressed for this project. E.g. Nested list is having issues. *Use 'tab' to do the nested list.*

## Pre-Requisetes:
1. Ubuntu 24.04.3 LTS
    1. The OS was installed on a MacOS (MacBook Pro M4) using VMware Fusion as the virtualization software.
2. Alfa USB Network Adapter (AWUS036ACM)
    1. This is 802.11ac compitable with both dual band support (2.4 GHz and 5GHz)
3. Ubiquti U7 XGS Access points off of a Ubiquiti XGS Switch (**Verify**). From a PFsense Firewall (barebones on a N100 mini PC).
4. Rustup is used so the backend of the code can be written in Rust.

## Todo:
- [ ] Document!
    - [ ] Functions that have been written
    - [ ] Equipment used
- [ ] Library functions
    - [ ] Interact with WiFi
    - [ ] Get BSS/BSSID
    - [ ] Channel/Stream Info
    - [ ] Detect other SSID's 
        - [ ] Show these and what channels they are on
    - [ ] Detect overlap on channels if any
        - [ ] If no overlap, then introduce overlap with older routers
 