# Class and Function Catalogue

| Class / function | Purpose |
|---|---|
| `ApplicationController.run()` | Starts display and repeats refresh cycles |
| `load_settings(path)` | Loads YAML and `.env` settings |
| `LocationService.get_current_location()` | Reads configured GPS/manual location |
| `GpsdLocationProvider.get_location()` | Reads GPS fix asynchronously |
| `ManualLocationProvider.get_location()` | Returns configured fixed coordinates |
| `FlightDataProvider.get_aircraft_nearby()` | Provider contract |
| `FlightAwareProvider.get_aircraft_nearby()` | Queries AeroAPI `/flights/search` |
| `FlightAwareProvider._to_aircraft()` | Maps flight, airport and operator-code fields to domain model |
| `FlightAwareProvider._enrich_operator_names()` | Resolves and session-caches airline/operator names |
| `AirplanesLiveProvider.get_aircraft_nearby()` | Queries Airplanes.live by GPS point and radius |
| `ADSBLolProvider.get_aircraft_nearby()` | Queries adsb.lol by GPS point and radius |
| `LocalAdsbProvider.get_aircraft_nearby()` | Reads local readsb aircraft JSON from disk |
| `LocalAdsbProvider._decode()` | Maps readsb `aircraft` array into common aircraft models |
| `ADSBPointProvider.map_aircraft()` | Maps ADS-B fields, timestamps, altitude and vertical rate |
| `MockFlightProvider.get_aircraft_nearby()` | Supplies local demonstration aircraft |
| `GeoCalculator.distance_km()` | Haversine distance |
| `GeoCalculator.bearing_deg()` | Initial compass bearing |
| `GeoCalculator.bounding_box()` | Bounding box for API pre-filter |
| `OverheadDetector.is_fresh()` | Rejects old position reports |
| `OverheadDetector.is_overhead_candidate()` | Applies overhead heuristic |
| `FlightProcessor.process()` | Filters, calculates and sorts aircraft |
| `FlightService.refresh()` | Coordinates location, provider, processor and repository |
| `SQLiteFlightRepository.save()` | Persists snapshot |
| `DisplayInterface.render()` | Display adapter contract |
| `ConsoleDisplay.render()` | Text output |
| `LedMatrixDisplay.render()` | HUB75 matrix output |
| `DesktopWindow.refresh()` | Runs refresh in worker thread |
| `DesktopWindow.show_snapshot()` | Renders flight table |
