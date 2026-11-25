from portable_flight_display.flight.geo import GeoCalculator


def test_same_point_is_zero():
    assert GeoCalculator.distance_km(53.3, -6.2, 53.3, -6.2) == 0


def test_dublin_to_london_distance_is_reasonable():
    distance = GeoCalculator.distance_km(53.3498, -6.2603, 51.5072, -0.1276)
    assert 460 < distance < 480


def test_bearing_is_north():
    assert 0 <= GeoCalculator.bearing_deg(0, 0, 1, 0) <= 1


def test_bounding_box_is_ordered():
    min_lat, min_lon, max_lat, max_lon = GeoCalculator.bounding_box(53.3, -6.2, 20)
    assert min_lat < 53.3 < max_lat
    assert min_lon < -6.2 < max_lon
