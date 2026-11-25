# Portable Flight Display – Local ADS-B Receiver Build

This guide builds a self-contained 1090 MHz ADS-B receiver on the same Raspberry Pi 4 that runs Portable Flight Display. The selected receiver is an RTL-SDR Blog V4 with an indoor antenna. `readsb` decodes the radio messages and writes `/run/readsb/aircraft.json`; the Python `LocalAdsbProvider` reads that file directly. No local HTTP listener, internet flight API, API key, or GPIO wiring is required.

## 1. Hardware bill of materials

| Item | Requirement / recommendation | Notes |
|---|---|---|
| Raspberry Pi 4 Model B | Existing board, preferably 2 GB RAM or higher | Runs Raspberry Pi OS 64-bit, readsb and PFD |
| Pi power supply | Official-quality 5.1 V / 3 A USB-C supply | Avoid marginal phone chargers, especially with SDR and display peripherals attached |
| microSD card | 32 GB or larger, reputable A1/A2 card | Raspberry Pi OS and logs; use a high-endurance card if the Pi runs continuously |
| RTL-SDR Blog V4 | USB RTL2832U/R820T2 receiver | V4 needs updated RTL-SDR drivers; stock Debian/Raspberry Pi OS drivers may not work correctly |
| 1090 MHz antenna | Indoor antenna explicitly tuned for 1090 MHz | Prefer a dedicated ADS-B antenna over a generic wideband whip |
| RF adapter / coax | SMA-compatible cable or adapter matching both antenna and dongle | Check connector gender before ordering; keep the cable short and low-loss |
| USB extension | Short, shielded USB extension (about 0.3–1 m) | Lets you move the dongle away from Pi/USB noise and position the antenna more freely |
| Case and cooling | Pi 4 case with suitable ventilation / heatsinks | Useful for continuous operation |
| Optional 1090 MHz filter | Inline 1090 MHz band-pass filter | Consider only if nearby RF transmitters cause overload or interference |
| Optional powered LNA | 1090 MHz LNA designed for ADS-B | Not needed for first indoor test; requires correct power/bias-tee arrangement |

Do not enable the RTL-SDR V4 bias tee for a passive antenna. Only enable it when the attached active antenna/LNA explicitly requires bias-tee power and its voltage/current requirements are compatible. The V4 guide warns against powering a DC-short passive antenna through the bias tee.

## 2. RF and USB connections

There are no GPIO connections and no soldering for this build. The signal/power path is:

```text
1090 MHz indoor antenna -- SMA/coax --> RTL-SDR Blog V4 -- USB --> Raspberry Pi 4
                                                              ^
                                                       USB-C 5.1 V / 3 A PSU
```

A simple quarter-wave 1090 MHz whip has a radiator length of approximately 69 mm; use an antenna designed for 1090 MHz and follow its mounting/ground-plane instructions.

1. Connect the 1090 MHz antenna to the RTL-SDR's SMA input, directly or through the correctly matched coax/adapter.
2. Connect the RTL-SDR USB plug to a Raspberry Pi USB port. Start with a USB 2.0 port and/or the short extension; USB 3 devices and cables can generate RF noise.
3. Place the antenna vertically, as high as practical, close to a window with the clearest view of the sky.
4. Keep the antenna away from Wi-Fi access points, monitors, USB 3 storage, switching power supplies and metal obstructions.
5. If using an inline filter, place it between antenna and SDR. Add an LNA only after establishing a baseline; more gain is not always better.
6. Power the Pi from its USB-C supply. Connect Ethernet or Wi-Fi for administration and optional enrichment, but the ADS-B reception and PFD local provider do not need internet access once installed.

Indoor reception varies significantly. Reinforced concrete, foil-backed insulation and metallised / low-E glazing can attenuate 1090 MHz signals. If the first test shows poor reception, move the antenna before buying an amplifier.

## 3. Install Raspberry Pi OS

1. Use Raspberry Pi Imager to install **Raspberry Pi OS Lite (64-bit)** or Raspberry Pi OS 64-bit with desktop if you intend to run the PySide6 desktop locally.
2. Configure hostname, user, Wi-Fi and SSH in Imager.
3. Boot the Pi, connect over SSH, and update it:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

After reboot, reconnect over SSH.

## 4. Install readsb and tar1090

The readsb project's maintained installer installs the decoder and its supporting tar1090 web map. Review the installer and its effects before running it. The installer documentation notes that it can remove other ADS-B decoders because only one decoder can own the SDR device.

```bash
sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
sudo reboot
```

The installer documentation is at <https://github.com/wiedehopf/adsb-scripts/wiki/Automatic-installation-for-readsb>.

### RTL-SDR Blog V4 driver requirement

The V4 requires updated drivers. The readsb installer documentation specifically calls out the extra V4 driver installation. Follow the V4-specific Debian instructions at <https://www.rtl-sdr.com/V4/>. The documented source-build procedure is:

```bash
sudo apt update
sudo apt install -y libusb-1.0-0-dev git cmake pkg-config build-essential
cd ~
git clone https://github.com/osmocom/rtl-sdr.git
cd rtl-sdr
mkdir -p build
cd build
cmake .. -DINSTALL_UDEV_RULES=ON
make -j"$(nproc)"
sudo make install
sudo cp ../rtl-sdr.rules /etc/udev/rules.d/
sudo ldconfig
```

The RTL-SDR V4 guide also documents blacklisting the kernel DVB driver if it claims the receiver:

```bash
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-dvb_usb_rtl28xxu.conf
sudo reboot
```

Do not blindly purge existing SDR libraries on a Pi that already runs other SDR applications or feeders. Check the current setup first; replacing system libraries can affect those applications.

## 5. Configure readsb

Check that the decoder is running:

```bash
sudo systemctl status readsb --no-pager
sudo journalctl -u readsb -n 50 --no-pager
```

Set the receiver's approximate fixed antenna location (latitude first, longitude second). This is readsb's receiver location for its range/statistics calculations; PFD continues to use its own configured GPS/manual location for aircraft distance and overhead detection.

```bash
sudo readsb-set-location 53.34980 -6.26030
sudo readsb-gain auto
```

Replace the example coordinates with the actual antenna location. Do not use the Dublin example if your receiver is elsewhere.

The readsb JSON writer normally stores aircraft data under `/run/readsb/aircraft.json` and refreshes the file periodically (typically once per second). Verify:

```bash
ls -l /run/readsb/aircraft.json
python3 -m json.tool /run/readsb/aircraft.json | head -60
```

The JSON object has an `aircraft` array. Each entry may include `hex`, `flight`, `lat`, `lon`, `alt_baro`, `alt_geom`, `gs`, `track`, `baro_rate`, `squawk`, `seen_pos`, `r` and `t`. Missing fields are normal. The aircraft database fields `r` (registration) and `t` (type) are only available when readsb is configured with a compatible aircraft database file.

Optional local map: open `http://<raspberry-pi-hostname-or-ip>/tar1090` from a device on your home network. This is a useful independent check that the receiver is decoding aircraft.

## 6. Configure Portable Flight Display

In `config/config.yaml`:

```yaml
flight_provider:
  provider: local_adsb
  local_adsb_aircraft_json_path: /run/readsb/aircraft.json

polling:
  interval_seconds: 5
```

The local provider reads the JSON file directly. It does not need an HTTP API port or a cloud API key. A five-second application polling interval is a reasonable starting point; readsb itself refreshes the file more frequently.

On the Pi, install the project and dependencies in the project virtual environment, including the desktop extra if required:

```bash
cd ~/portable-flight-display
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[desktop,gps]'
pfd --config config/config.yaml --display desktop
```

If the PFD service runs as a non-root user, confirm that it can read `/run/readsb/aircraft.json`. The file is normally world-readable, but verify the actual permissions on your installation. Do not run the GUI as root to work around a permissions issue.

## 7. Verification checklist

- [ ] `lsusb` lists the RTL-SDR device.
- [ ] `sudo systemctl is-active readsb` reports `active`.
- [ ] `/run/readsb/aircraft.json` exists and its `now` value advances.
- [ ] `aircraft` is a JSON array (it can legitimately be empty if reception is poor or no aircraft are in range).
- [ ] tar1090 shows aircraft when traffic and reception conditions allow.
- [ ] PFD starts with `provider: local_adsb` and reports `Local ADS-B (readsb)`.
- [ ] Aircraft positions become visible in PFD; distance and overhead-candidate calculations are still performed by the existing Python processor.

## 8. Troubleshooting

| Symptom | Checks |
|---|---|
| `aircraft.json` missing | `sudo systemctl status readsb`; `sudo journalctl -u readsb -n 100`; verify readsb's `--write-json` setting and output directory |
| No aircraft | Check antenna connection/orientation/window location; allow time for traffic; check `readsb` logs and tar1090; confirm antenna is 1090 MHz |
| RTL-SDR V4 detected but no usable messages | Install the updated V4-compatible driver; stock drivers can produce no signals or corrupted/wrong-frequency data |
| `Kernel driver is active` / device busy | Ensure only one decoder uses the SDR; inspect other feeder/decoder services; follow the readsb installer troubleshooting notes |
| Many distant aircraft but few nearby | Indoor antenna placement, building attenuation and line-of-sight may be limiting reception |
| Unstable reception / USB errors | Try a short USB extension, another USB port, a stable Pi power supply, and move SDR away from USB 3 and switching-power noise |
| Registration/type blank | Expected unless the readsb aircraft database (`--db-file`) is installed and current; callsign/position can still work without it |

## 9. Limitations and safety

- The receiver hears compatible transmissions within radio line-of-sight; it cannot guarantee every aircraft is detected.
- Position, callsign and other fields are broadcast only when available and may be missing or stale.
- ADS-B altitude is generally barometric or geometric altitude, not a direct measurement of height above the observer.
- This is an enthusiast situational-awareness display, not certified aviation equipment and not a substitute for official aviation information.
- Follow local radio-monitoring laws and the software/hardware licences. Receiving ADS-B does not grant permission to transmit or rebroadcast other data.

## References

- RTL-SDR Blog V4 driver guide: <https://www.rtl-sdr.com/V4/>
- readsb project: <https://github.com/wiedehopf/readsb>
- readsb JSON format and `aircraft.json`: <https://github.com/wiedehopf/readsb/blob/dev/README-json.md>
- readsb automatic installation: <https://github.com/wiedehopf/adsb-scripts/wiki/Automatic-installation-for-readsb>
- tar1090: <https://github.com/wiedehopf/tar1090>
