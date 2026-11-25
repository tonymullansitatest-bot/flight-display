from portable_flight_display.core.models import FlightSnapshot
from portable_flight_display.display.base import DisplayInterface


class ConsoleDisplay(DisplayInterface):
    def initialise(self) -> None:
        pass

    def render(self, snapshot: FlightSnapshot) -> None:
        print("\\n" + "=" * 76)
        print(f"PORTABLE FLIGHT DISPLAY | {snapshot.provider_name} | {snapshot.fetched_at:%H:%M:%S} UTC")
        print(f"Location: {snapshot.location.latitude:.5f}, {snapshot.location.longitude:.5f} ({snapshot.location.source})")
        print(snapshot.status_message)
        if not snapshot.aircraft:
            print("No aircraft in range.")
        for item in snapshot.aircraft:
            marker = "OVERHEAD CANDIDATE" if item.is_overhead_candidate else "NEARBY"
            print(
                f"{marker:18} {item.ident or item.flight_id:12} "
                f"{item.distance_km:>6.2f} km  "
                f"{item.altitude_ft if item.altitude_ft is not None else '—':>7} ft  "
                f"{item.groundspeed_kts if item.groundspeed_kts is not None else '—':>5} kt  "
                f"{item.bearing_deg if item.bearing_deg is not None else '—'}°"
            )

    def shutdown(self) -> None:
        pass
