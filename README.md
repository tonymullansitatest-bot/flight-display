# Portable Flight Display

A Python MVP for discovering aircraft near a GPS/manual location and displaying them on a
PySide6 desktop UI or a 64x32 RGB LED matrix attached to a Raspberry Pi 4.

## What is included

- Shared domain models, geospatial calculations and overhead candidate detection.
- Flight provider interface with a deterministic mock provider, FlightAware AeroAPI v4 adapter,
  Airplanes.live, adsb.lol and local readsb adapters.
- Selectable community ADS-B feeds plus a fully local RTL-SDR/readsb receiver provider.
- Geographic airborne-flight search using AeroAPI `GET /flights/search` and its simplified `-latlong` query syntax.
- GPSD and manual location providers.
- SQLite snapshot persistence.
- Console, PySide6 desktop and RGB matrix display adapters.
- Configuration, logging, unit tests and Raspberry Pi systemd example.

## Important FlightAware integration note

AeroAPI is query/usage based. This project uses `GET /flights/search` with a latitude/longitude
bounding-box query. The provider returns airborne flights within that box; the application then
performs exact Haversine radius filtering locally. API access, endpoint access, query syntax, field
availability, retention and price depend on the AeroAPI subscription and current FlightAware
contract. Verify the query against your account before enabling unattended polling. The supplied
configuration defaults to `local_adsb` for the Raspberry Pi receiver build; select a network provider explicitly on a development PC.

Official references:
- https://www.flightaware.com/commercial/aeroapi/
- https://www.flightaware.com/commercial/aeroapi/explorer/
- https://www.flightaware.com/commercial/aeroapi/faq.rvt

The FlightAware API adapter sends `x-apikey` and uses `/flights/search` with the simplified query form
`-latlong "MINLAT MINLON MAXLAT MAXLON"`. The response contains `flights[]`; each flight can
include a nested `last_position`, origin/destination airport references, ident variants and
aircraft type. Airport references include a code, common name and city; the desktop table displays
these together. `/flights/search` does not provide a documented operator display name, so the adapter
uses the ICAO flight ident prefix to request `GET /operators/{id}`. Operator names are cached in
memory for the provider session and looked up once per distinct code. Set
`flight_provider.enrich_operator_names: false` to avoid those optional additional API requests.
AeroAPI's `last_position.altitude` is expressed in hundreds of feet, so the adapter converts it to
feet for the internal model. The adapter rejects flights without a current `last_position`, then the
local processor performs exact radius and freshness checks.

## Requirements

- Python 3.11+
- Desktop: Windows 10/11 or Linux with PySide6 support
- Pi: Raspberry Pi 4, Raspberry Pi OS 64-bit, network access
- Optional GPS: `gpsd` and a USB GPS receiver
- Optional LED: compatible HUB75 64x32 panel, appropriate driver/interface and separate power supply

## Install – Windows desktop

```powershell
py -3.12 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[desktop,dev]"
Copy-Item .env.example .env
```

The supplied YAML selects `local_adsb`, which expects readsb to create `/run/readsb/aircraft.json` on the Raspberry Pi. On Windows, use `PFD_PROVIDER=mock` for a no-network demonstration, or select `airplanes_live`, `adsb_lol` or `flightaware` to use a network provider. For AeroAPI, populate `FLIGHTAWARE_API_KEY`; for adsb.lol, `ADSB_LOL_API_KEY` is optional.

Run:

```powershell
pfd --config config/config.yaml --display desktop
# or
python -m portable_flight_display.main --config config/config.yaml --display console
```

## Install – Raspberry Pi 4

For the complete RTL-SDR Blog V4 bill of materials, wiring, V4 driver notes, readsb installation, and receiver verification, follow [docs/ADS-B_RECEIVER_BUILD.md](docs/ADS-B_RECEIVER_BUILD.md). The readsb installer is also available as `deployment/raspberry-pi/install-readsb.sh`.

Install Raspberry Pi OS 64-bit, connect the Pi to the network, then:

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential git gpsd gpsd-clients
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[gps,dev]"
# Install Pillow for LED rendering; install the rgbmatrix Python binding from the upstream driver repository.
```

For GPSD, configure `/etc/default/gpsd` for your USB receiver and verify with:

```bash
cgps -s
```

The Python GPS provider connects to the local GPSD daemon. If GPSD or the optional Python binding
is unavailable, switch to `location.provider: manual` until it is configured.

For a HUB75 matrix, install Pillow and the Python `rgbmatrix` binding built from the upstream driver repository. Verify panel scan pattern, GPIO mapping, power budget and compatibility with
the Raspberry Pi 4 before wiring. Never power a matrix panel from the Pi 5V pin. Use a suitable
regulated external supply, common ground and the correct interface/level shifting. The
`rgbmatrix` Python binding may need to be built from the upstream driver for your OS/Pi image;
follow https://github.com/hzeller/rpi-rgb-led-matrix.

Run LED mode:

```bash
sudo .venv/bin/pfd --config config/config.yaml --display led
```

## Configuration

Edit `config/config.yaml`. Use `location.provider: manual` to set fixed coordinates, or `gpsd`
for GPSD. The supplied Dublin coordinates are examples only. The location is not automatically
derived from the host operating system.

Select a provider in `config/config.yaml` or override it with `PFD_PROVIDER`:

```bash
# Local receiver (Raspberry Pi only; readsb must be running)
export PFD_PROVIDER=local_adsb

# Free community feed
export PFD_PROVIDER=airplanes_live

# Alternative community feed; key is optional
export PFD_PROVIDER=adsb_lol
export ADSB_LOL_API_KEY="..."  # optional

# Paid FlightAware AeroAPI
export PFD_PROVIDER=flightaware
export FLIGHTAWARE_API_KEY="..."
```

### Local RTL-SDR / readsb provider

Set `flight_provider.provider: local_adsb`. The provider reads the local readsb file at `flight_provider.local_adsb_aircraft_json_path` (default `/run/readsb/aircraft.json`). readsb writes this JSON file periodically; its `aircraft` array is mapped into the common `Aircraft` model. This is a direct local file read: it needs no API key, internet connection, or exposed network port. The application applies its existing Haversine radius and overhead processing after loading the current readsb aircraft list. The default polling interval for the local receiver is five seconds.

### Community ADS-B providers

Both community providers use a radius query centred on the current GPS/manual location. The
application converts the configured radius from kilometres to nautical miles, then applies its
own exact Haversine radius filter. They return live ADS-B observations, not FlightAware-style
flight plans: origin/destination airports, airline names and scheduled/estimated times are not
normally included. Callsign, Mode-S hex, registration, aircraft type, position, barometric/geometric
altitude, speed, track, squawk and vertical rate are mapped when available.

- Airplanes.live: `GET /v2/point/{lat}/{lon}/{radius_nm}`. Public access currently does not require
  a feeder; documented limit is 1 request/second. Non-commercial use; no SLA or uptime guarantee.
  API guide: https://airplanes.live/api-guide/
- adsb.lol: `GET /v2/lat/{lat}/lon/{lon}/dist/{radius_nm}`. Official documentation currently
  lists 500 requests/day without a key, 1,000/day for a free adhoc key and 7,200/day for feeder
  access; quotas and policies can change. Data is ODbL 1.0; review attribution/share-alike
  obligations. API docs: https://www.adsb.lol/docs/open-data/api

The community-provider poll interval should remain within the provider limits; the local readsb provider can use a shorter five-second polling interval. HTTP 429 responses are surfaced with any `Retry-After`
header; the application does not automatically hammer the service with retries.

Do not commit `.env`, API keys, GPS logs or local database files.

## Overhead semantics

`nearby` means within the configured horizontal radius. `overhead candidate` means within the
smaller horizontal radius, inside configured altitude limits, and with a sufficiently fresh
position. This is a practical display heuristic, not a certified line-of-sight or exact
overflight determination. Aircraft altitude is pressure/barometric altitude as supplied by the
provider, not necessarily height above the observer. A true vertical separation calculation
requires compatible aircraft and observer altitude references.

## Tests

```bash
pytest
```

Tests use mock data and do not require a FlightAware key, GPS receiver, GUI or LED panel.

## CLI options

```text
pfd --config config/config.yaml --display desktop|led|console --mock
```

`--mock` forces the mock provider regardless of the configured live provider.

## MVP limitations / next steps

- No map view or route enrichment in this MVP.
- Local ADS-B reception requires a compatible SDR, antenna, readsb installation and radio coverage.
- AeroAPI search results are subject to subscription permissions, API limits and coverage.
- Community ADS-B feeds are best-effort, coverage-dependent, and do not supply flight-plan metadata.
- Some fields (registration, operator name, textual route, ETA) may be absent from `/flights/search`
  results. The UI must tolerate missing data; add targeted enrichment only after measuring its
  per-query cost.
- LED driver initialization is hardware-dependent and must be tested with the exact panel.
- Add position history and vector-based closest-approach prediction in a later iteration.
