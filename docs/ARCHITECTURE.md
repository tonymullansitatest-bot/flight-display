# Portable Flight Display – Architecture

**Status:** MVP implementation baseline  
**Target:** Windows/Linux desktop and Raspberry Pi 4  
**Primary display:** PySide6 desktop / HUB75 RGB 64x32 LED matrix  
**Location:** USB GPS receiver via GPSD, with manual fallback  
**Flight source:** Local RTL-SDR/readsb receiver (with optional FlightAware/community providers)

## 1. Goals

1. Show current aircraft positions within a configurable distance of the observer.
2. Identify overhead candidates using distance, altitude and position freshness.
3. Share all domain and processing logic across desktop and Raspberry Pi deployments.
4. Continue in mock/manual mode when API credentials or GPS hardware are absent.
5. Keep API credentials out of source code and logs.

## 2. Non-goals

- Certified aviation situational awareness or collision avoidance.
- Guaranteed identification of every aircraft.
- Guaranteed exact height above ground or true vertical separation.
- Offline live tracking without a receiver/data feed.
- Route enrichment for every aircraft in the first release.

## 3. Component view

```mermaid
flowchart TB
  CFG[Config + Environment] --> APP[Application / Polling]
  GPS[USB GPS via GPSD] --> LOC[Location Provider]
  MAN[Manual Location] --> LOC
  APP --> LOC
  APP --> FLS[Flight Service]
  SDR[1090 MHz Antenna] --> RTL[RTL-SDR USB]
  RTL --> READSB[readsb Decoder]
  READSB --> JSON[/run/readsb/aircraft.json]
  JSON --> LOCAL[LocalAdsbProvider]
  FLS --> LOCAL
  FLS --> FA[FlightAware Provider]
  FLS --> COMMUNITY[Airplanes.live / adsb.lol]
  FLS --> MOCK[Mock Provider]
  LOCAL --> PROC[Flight Processor]
  FA --> PROC
  COMMUNITY --> PROC
  MOCK --> PROC
  LOC --> PROC
  PROC --> DET[Overhead Detector + Geo]
  DET --> REPO[SQLite Snapshot Repository]
  DET --> DISP[Display Interface]
  DISP --> QT[PySide6 Desktop]
  DISP --> LED[RGB Matrix 64x32]
  DISP --> CON[Console]
```

## 4. Runtime flow

1. Load YAML configuration and environment variables.
2. Acquire a fresh location from GPSD or the manual provider.
3. Select the configured provider. The local receiver reads `/run/readsb/aircraft.json`; FlightAware uses AeroAPI `/flights/search`; community providers use their point/radius endpoints.
4. Normalize the provider response into the common `Aircraft` domain model.
5. Apply exact Haversine distance filtering locally.
6. Mark overhead candidates based on horizontal radius, altitude limits and position age.
7. Persist a compact snapshot to SQLite.
8. Render the result through the selected display adapter.
9. Repeat at the configured interval, with errors isolated to the provider/polling cycle.

## 5. Main classes

| Class | Module | Responsibility |
|---|---|---|
| `ApplicationController` | `application.py` | Lifecycle and polling orchestration |
| `Settings` | `config.py` | Typed configuration |
| `LocationService` | `location/service.py` | Select and validate location source |
| `GpsdLocationProvider` | `location/gpsd_provider.py` | Read USB GPS through GPSD |
| `ManualLocationProvider` | `location/manual_provider.py` | Fixed configured location |
| `FlightDataProvider` | `providers/base.py` | Provider contract |
| `FlightAwareProvider` | `providers/flightaware.py` | AeroAPI `/flights/search` and optional operator enrichment |
| `AirplanesLiveProvider` | `providers/airplanes_live.py` | Airplanes.live point/radius ADS-B feed |
| `ADSBLolProvider` | `providers/adsb_lol.py` | adsb.lol point/radius ADS-B feed |
| `LocalAdsbProvider` | `providers/local_adsb.py` | Reads readsb `aircraft.json` from local filesystem |
| `ADSBPointProvider` | `providers/adsb_base.py` | Shared ADS-B response mapping, HTTP handling and unit conversion |
| `MockFlightProvider` | `providers/mock.py` | Deterministic local test data |
| `FlightService` | `flight/service.py` | Provider selection and retrieval |
| `FlightProcessor` | `flight/processor.py` | Filter, enrich and sort positions |
| `OverheadDetector` | `flight/overhead.py` | Nearby/overhead heuristic |
| `GeoCalculator` | `flight/geo.py` | Haversine, bounding box and bearing |
| `SQLiteFlightRepository` | `repository/sqlite.py` | Persist latest snapshots |
| `DisplayInterface` | `display/base.py` | Hardware-neutral rendering contract |
| `DesktopWindow` | `ui/main_window.py` | PySide6 table and status |
| `LedMatrixDisplay` | `display/led_matrix.py` | HUB75 matrix adapter |

## 6. Data contracts

`Location` contains latitude, longitude, optional altitude, timestamp and source.

`Aircraft` is provider-neutral. FlightAware may populate flight ID, ident/callsign, operator code/name,
airport codes/names/cities and estimated arrival. ADS-B community providers populate Mode-S hex,
callsign, registration, aircraft type, coordinates, barometric/geometric altitude, groundspeed,
track, squawk, category, vertical rate and position age. Fields not supplied by a provider remain
`None`; ADS-B feeds do not normally provide flight-plan origin/destination or airline names.

Unknown fields remain `None`; the UI displays `—` rather than inventing values.

## 7. FlightAware query design

The adapter uses:

- FlightAware base URL: `https://aeroapi.flightaware.com/aeroapi`
- Airplanes.live base URL: `https://api.airplanes.live/v2`
- adsb.lol base URL: `https://api.adsb.lol/v2`
- Provider selection: `mock`, `flightaware`, `airplanes_live`, `adsb_lol`, `local_adsb`
- Endpoint: `GET /flights/search`
- Authentication: `x-apikey`
- Query: `-latlong "MINLAT MINLON MAXLAT MAXLON"`
- Result limit: configurable, default one page / 15 records.
- Airport names/cities: read directly from each flight's `origin` and `destination` references.
- Operator name: optional `GET /operators/{ICAO}` lookup, cached in memory per provider session.

A geographic bounding box is a coarse pre-filter. The application applies an exact circular
Haversine filter afterward. The ADS-B point APIs receive the GPS/manual latitude, longitude and
radius converted from kilometres to integer nautical miles. The bounding box expands longitude by latitude cosine and clamps
latitude near the poles.

FlightAware's API is usage-based. Polling every 15 seconds can create material query usage;
the supplied default is 30 seconds and must be reviewed against the user's plan. Operator enrichment
adds at most one lookup per distinct ICAO operator code during a provider session. It can be disabled
with `flight_provider.enrich_operator_names: false`; airport details do not require extra lookups.

## 8. Local receiver data flow

The RTL-SDR receives 1090 MHz transmissions. `readsb` decodes Mode S / ADS-B messages and periodically writes `/run/readsb/aircraft.json`. `LocalAdsbProvider` reads this atomically replaced JSON file asynchronously via a worker thread and maps its `aircraft` array using the shared ADS-B field mapper. It does not open a TCP port or make a network request. `FlightProcessor` applies the configured application-location radius and overhead heuristic. readsb receiver coordinates are used for decoder range/statistics and are separate from the GPS/manual observer location used by PFD.

## 9. Failure and degraded operation

| Failure | Behaviour |
|---|---|
| GPSD unavailable | Use configured manual coordinates and mark location as manual-fallback |
| FlightAware timeout / 5xx | Log and keep UI alive; next poll retries |
| 401/403 | Surface credential/subscription error; no tight retry loop |
| 429 | Respect `Retry-After`; wait before next request |
| Empty result | Show no aircraft |
| Stale position | Exclude from overhead candidate; retain only if within max-age policy |
| LED unavailable | Log hardware error; core services remain testable |
| SQLite error | Log; rendering continues |

## 10. Security and privacy

- API key comes from `FLIGHTAWARE_API_KEY` environment variable.
- Never log request headers or API keys.
- Location is sensitive: GPS coordinates are not sent to third parties except as part of the
  bounding-box request to the configured flight provider.
- SQLite is local and should be protected by OS account permissions.
- Review FlightAware's terms for display, caching and redistribution rights.

## 11. Deployment profiles

### Desktop
Install `.[desktop]`; use PySide6 UI. GPSD is optional; manual location is available.

### Raspberry Pi 4
Install `.[gps,led]`; configure GPSD; run LED mode. The core package has no mandatory
Raspberry Pi imports, so Windows test runs remain possible.

## 12. Decisions / follow-up

- Confirm AeroAPI account access to flight-position search and validate field units.
- Confirm whether the 64x32 panel is HUB75 and verify exact scan rate/driver configuration.
- Confirm GPS receiver chipset and GPSD device path.
- Add track-vector closest-approach calculation after the MVP is field-tested.
