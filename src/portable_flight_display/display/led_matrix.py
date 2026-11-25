from portable_flight_display.core.models import FlightSnapshot
from portable_flight_display.display.base import DisplayInterface


class LedMatrixDisplay(DisplayInterface):
    """Optional HUB75 RGB matrix display using the upstream rgbmatrix graphics API."""

    def __init__(self, rows=32, cols=64, chain_length=1, parallel=1,
                 brightness=45, font_path="fonts/5x8.bdf"):
        self.rows, self.cols = rows, cols
        self.chain_length, self.parallel = chain_length, parallel
        self.brightness = brightness
        self.font_path = font_path
        self.matrix = None
        self.canvas = None
        self.graphics = None
        self.font = None

    def initialise(self) -> None:
        try:
            from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
        except ImportError as exc:
            raise RuntimeError(
                "LED mode requires the rgbmatrix Python binding built from "
                "https://github.com/hzeller/rpi-rgb-led-matrix"
            ) from exc
        options = RGBMatrixOptions()
        options.rows = self.rows
        options.cols = self.cols
        options.chain_length = self.chain_length
        options.parallel = self.parallel
        options.brightness = self.brightness
        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.graphics = graphics
        self.font = graphics.Font()
        try:
            self.font.LoadFont(self.font_path)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to load LED font '{self.font_path}'. Set display.led_font_path "
                "to the installed 5x8.bdf font from the rgbmatrix repository."
            ) from exc

    def render(self, snapshot: FlightSnapshot) -> None:
        if self.matrix is None or self.graphics is None:
            raise RuntimeError("LED matrix has not been initialised")
        self.canvas.Clear()
        white = self.graphics.Color(255, 255, 255)
        cyan = self.graphics.Color(0, 180, 255)
        green = self.graphics.Color(0, 255, 80)
        yellow = self.graphics.Color(255, 220, 0)
        self.graphics.DrawText(self.canvas, self.font, 1, 7, cyan, "FLIGHT DISPLAY")
        if not snapshot.aircraft:
            self.graphics.DrawText(self.canvas, self.font, 1, 19, white, "NO AIRCRAFT")
        else:
            first = snapshot.aircraft[0]
            colour = green if first.is_overhead_candidate else yellow
            ident = (first.ident or first.flight_id)[:10]
            altitude = f"{first.altitude_ft // 100}FL" if first.altitude_ft is not None else "ALT --"
            distance = f"{first.distance_km:.1f}KM" if first.distance_km is not None else "--KM"
            self.graphics.DrawText(self.canvas, self.font, 1, 18, colour, ident)
            self.graphics.DrawText(self.canvas, self.font, 1, 29, white, f"{altitude} {distance}")
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def shutdown(self) -> None:
        if self.matrix is not None:
            self.matrix.Clear()
            self.matrix = None
