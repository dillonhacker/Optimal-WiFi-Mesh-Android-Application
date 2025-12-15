# Wifi-Mesh Optimzer
 Author: Dillon Hacker

## Pre-Requisetes:
1. Ubuntu 24.04.3 LTS
    1. The OS was installed on a MacOS (MacBook Pro M4) using VMware Fusion as the virtualization software.
2. Alfa USB Network Adapter (AWUS036ACM)
    1. This is 802.11ac compatible with both dual band support (2.4 GHz and 5GHz)
3. Ubiquiti U7 XGS Access points off of a Ubiquiti XGS Switch. From a PFsense Firewall (bare-bones on a N100 mini PC). Any wireless router should appear, but this is the equipment I used.
4. Other requirements have been included in the `requirements.txt` and `install.sh` files. 

## How to Run:
1. First, run `install.sh`which should install the requirements for this project.
2. Verify that rust has created an executable file **VERIFY** 
3. You should have entered a Python venv, so you can know rust `python3 ./main.py` if you are in the same directory as the `main.py`
4. A GUI should show up where you can now enter your `House Name` and enter the number of floors your house has.
5. You are next prompted to enter the number of rooms for each floor and have the option to name them. Hit the finish button to move to the next step. 
6. You will now see `Floor: Floor 1` and `Room: "Room_Name"`. You can hit the `Run Scan` button and results should populate the table below. You should do this step for each room as you move around the house, selecting the corresponding room/floor you are currently in.
7. Once all the floors and corresponding rooms have been scanned, you can go to the results tab near the top of the window to see all the information gathered about your house. This includes all the access points your WiFi driver can detect. 
8. You also have the option to view a summary which can provide recommendations on whether your AP is on the best channel already or if their is a better option due to congestion of a frequency range. 
9. You can also save your data as a `.json` file that can be uploaded again to view previous results. 

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
 
