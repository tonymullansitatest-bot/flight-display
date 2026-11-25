import asyncio
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout,
)
from portable_flight_display.core.models import FlightSnapshot
from portable_flight_display.flight.service import FlightService
from portable_flight_display.location.service import LocationService
from portable_flight_display.config import Settings


class RefreshWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, service: FlightService):
        super().__init__()
        self.service = service

    def run(self):
        try:
            snapshot = asyncio.run(self.service.refresh())
            self.completed.emit(snapshot)
        except Exception as exc:
            self.failed.emit(str(exc))


class DesktopWindow(QMainWindow):
    def __init__(self, settings: Settings, force_mock: bool = False):
        super().__init__()
        self.settings = settings
        self.location_service = LocationService(settings.location)
        self.service = FlightService(settings, self.location_service, force_mock)
        self.worker = None
        self.setWindowTitle("Portable Flight Display")
        self.resize(1050, 600)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.status = QLabel("Starting flight monitor…")
        layout.addWidget(self.status)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Status", "Flight", "Airline / Operator", "Aircraft", "Origin", "Destination",
            "Distance km", "Altitude ft", "Speed kt", "Heading", "Position UTC",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh now")
        self.refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(settings.polling.interval_seconds * 1000)
        self.refresh()

    def refresh(self):
        if self.worker and self.worker.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.status.setText("Refreshing aircraft positions…")
        self.worker = RefreshWorker(self.service)
        self.worker.completed.connect(self.show_snapshot)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.worker.start()

    def show_snapshot(self, snapshot: FlightSnapshot):
        self.table.setRowCount(len(snapshot.aircraft))
        for row, aircraft in enumerate(snapshot.aircraft):
            values = [
                "OVERHEAD" if aircraft.is_overhead_candidate else "NEARBY",
                aircraft.ident or aircraft.flight_id,
                aircraft.airline or aircraft.operator_code or "—",
                aircraft.aircraft_type or "—",
                self._airport_label(aircraft.origin, aircraft.origin_name, aircraft.origin_city),
                self._airport_label(aircraft.destination, aircraft.destination_name, aircraft.destination_city),
                f"{aircraft.distance_km:.2f}" if aircraft.distance_km is not None else "—",
                str(aircraft.altitude_ft) if aircraft.altitude_ft is not None else "—",
                str(aircraft.groundspeed_kts) if aircraft.groundspeed_kts is not None else "—",
                f"{aircraft.heading_deg:.0f}°" if aircraft.heading_deg is not None else "—",
                f"{aircraft.position_timestamp:%H:%M:%S}" if aircraft.position_timestamp else "—",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.status.setText(
            f"{snapshot.status_message} | {snapshot.provider_name} | "
            f"{snapshot.fetched_at:%H:%M:%S UTC} | "
            f"GPS: {snapshot.location.source}"
        )

    @staticmethod
    def _airport_label(code: str | None, name: str | None, city: str | None) -> str:
        parts = [part for part in (code, name, city) if part]
        return " — ".join(parts) if parts else "—"

    def show_error(self, message: str):
        self.status.setText(f"Refresh failed: {message}")

    def closeEvent(self, event):
        self.timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.wait(3000)
        asyncio.run(self.service.close())
        event.accept()


def run_desktop(settings: Settings, force_mock: bool = False):
    app = QApplication.instance() or QApplication([])
    window = DesktopWindow(settings, force_mock)
    window.show()
    return app.exec()
