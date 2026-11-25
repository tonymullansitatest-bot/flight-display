from portable_flight_display.config import DisplaySettings
from portable_flight_display.display.console import ConsoleDisplay
from portable_flight_display.display.led_matrix import LedMatrixDisplay


def create_display(settings: DisplaySettings, display_type: str | None = None):
    selected = (display_type or settings.type).lower()
    if selected == "console":
        return ConsoleDisplay()
    if selected == "led":
        return LedMatrixDisplay(
            rows=settings.led_rows, cols=settings.led_cols,
            chain_length=settings.led_chain_length,
            parallel=settings.led_parallel, brightness=settings.led_brightness, font_path=settings.led_font_path,
        )
    if selected == "desktop":
        from portable_flight_display.ui.main_window import run_desktop
        return run_desktop
    raise ValueError(f"Unknown display type: {selected}")
