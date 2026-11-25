from math import asin, atan2, cos, degrees, radians, sin, sqrt


class GeoCalculator:
    EARTH_RADIUS_KM = 6371.0088

    @classmethod
    def distance_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        p1, p2 = radians(lat1), radians(lat2)
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
        return 2 * cls.EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))

    @staticmethod
    def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        p1, p2 = radians(lat1), radians(lat2)
        dl = radians(lon2 - lon1)
        y = sin(dl) * cos(p2)
        x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl)
        return (degrees(atan2(y, x)) + 360) % 360

    @staticmethod
    def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
        """Return min_lat, min_lon, max_lat, max_lon around a centre point."""
        lat_delta = radius_km / 111.045
        cos_lat = max(0.01, abs(cos(radians(lat))))
        lon_delta = min(180.0, radius_km / (111.045 * cos_lat))
        return (
            max(-90.0, lat - lat_delta),
            max(-180.0, lon - lon_delta),
            min(90.0, lat + lat_delta),
            min(180.0, lon + lon_delta),
        )
