import argparse
import asyncio
import logging

from portable_flight_display.application import ApplicationController
from portable_flight_display.config import load_settings
from portable_flight_display.display.console import ConsoleDisplay
from portable_flight_display.flight.service import FlightService
from portable_flight_display.location.service import LocationService


def main():
    parser = argparse.ArgumentParser(description="Portable Flight Display")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--display", choices=["desktop", "led", "console"])
    parser.add_argument("--mock", action="store_true", help="Force mock flight data")
    args = parser.parse_args()

    settings = load_settings(args.config)
    logging.basicConfig(
        level=getattr(logging, str(settings.application.get("log_level", "INFO")).upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    display_type = args.display or settings.display.type

    if display_type == "desktop":
        try:
            from portable_flight_display.ui.main_window import run_desktop
        except ImportError as exc:
            raise SystemExit('Desktop mode requires PySide6: pip install -e ".[desktop]"') from exc
        raise SystemExit(run_desktop(settings, args.mock))

    if display_type == "console":
        async def run_console():
            location_service = LocationService(settings.location)
            service = FlightService(settings, location_service, args.mock)
            display = ConsoleDisplay()
            display.initialise()
            try:
                while True:
                    try:
                        display.render(await service.refresh())
                    except Exception:
                        logging.exception("Flight refresh failed")
                    await asyncio.sleep(settings.polling.interval_seconds)
            finally:
                display.shutdown()
                await service.close()
        asyncio.run(run_console())
    else:
        asyncio.run(ApplicationController(settings, display_type, args.mock).run())


if __name__ == "__main__":
    main()
