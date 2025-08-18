# test_declination.py
import datetime

import pytest
from pydantic import ValidationError

from openspeleo_lib.geo_utils import GeoLocation
from openspeleo_lib.geo_utils import decimal_year
from openspeleo_lib.geo_utils import get_declination


@pytest.mark.parametrize(
    ("dt", "expected_result"),
    [
        (datetime.datetime(2025, 1, 1), 2025.0),  # Start of year
        (datetime.datetime(2025, 12, 31), 2025.99),  # End of the year
        (datetime.datetime(2025, 7, 2), 2025.5),  # non-leap year
        (datetime.datetime(2024, 7, 2), 2024.503),  # leap year
    ],
)
def test_start_of_year(dt: datetime.datetime, expected_result: float):
    result = decimal_year(dt)
    assert result == pytest.approx(expected_result, rel=1e-5)


class TestGeoLocation:
    def test_valid_coordinates(self):
        lat, long = (45.0, -120.0)
        loc = GeoLocation(latitude=lat, longitude=long)
        assert loc.latitude == lat
        assert loc.longitude == long

    @pytest.mark.parametrize("latitude", [91, -91])
    def test_invalid_latitude(self, latitude: float):
        with pytest.raises(ValidationError):
            # latitude out of range [-90, 90]
            GeoLocation(latitude=latitude, longitude=0.0)

    @pytest.mark.parametrize("longitude", [181, -181])
    def test_invalid_longitude(self, longitude: float):
        with pytest.raises(ValidationError):
            # longitude out of range [-180, 180]
            GeoLocation(latitude=0.0, longitude=longitude)


LOC_MX = GeoLocation(latitude=20.6296, longitude=-87.0739)  # Playa Del Carmen, QROO, MX
LOC_US = GeoLocation(latitude=29.8269, longitude=-82.5968)  # High Springs, FL, USA
LOC_FR = GeoLocation(latitude=44.2712, longitude=1.451100)  # Émergence du Ressel, FR
LOC_NZ = GeoLocation(latitude=-41.220, longitude=172.7619)  # Pearse Resurgence, NZ


@pytest.mark.parametrize(
    ("dt", "location", "expected_result"),
    [
        (datetime.datetime(2025, 1, 1), LOC_MX, -2.42),
        (datetime.datetime(1990, 7, 1), LOC_MX, 1.65),
        (datetime.datetime(2025, 1, 1), LOC_US, -6.25),
        (datetime.datetime(1990, 7, 1), LOC_US, -2.88),
        (datetime.datetime(2025, 1, 1), LOC_FR, 1.67),
        (datetime.datetime(1990, 7, 1), LOC_FR, -2.88),
        (datetime.datetime(2025, 1, 1), LOC_NZ, 22.83),
        (datetime.datetime(1990, 7, 1), LOC_NZ, 21.44),
    ],
)
def test_declination_calls_pyigrf(
    dt: datetime.datetime, location: GeoLocation, expected_result: float
):
    declination = get_declination(location, dt)
    assert declination == pytest.approx(expected_result, rel=5e-3)
