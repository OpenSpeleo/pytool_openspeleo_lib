import unittest
from uuid import UUID

import pytest
from parameterized import parameterized
from pydantic import ValidationError

from openspeleo_lib.generators import UniqueNameGenerator
from openspeleo_lib.models import Survey
from openspeleo_lib.models import SurveyShot


class TestSurvey(unittest.TestCase):
    def test_survey_creation_with_valid_data(self):
        data = {
            "cave_name": "DEMO",
            "first_start_absolute_elevation": "123.45",
            "unit": "m",
            "use_magnetic_azimuth": "true",
            "carto_ellipse": "SomeValue",
            "carto_line": "SomeValue",
            "carto_linked_surface": "SomeValue",
            "carto_overlay": "SomeValue",
            "carto_page": "SomeValue",
            "carto_rectangle": "SomeValue",
            "carto_selection": "SomeValue",
            "carto_spline": "SomeValue",
            "constraints": "SomeValue",
            "list_annotation": "SomeValue",
        }

        survey = Survey(**data)

        assert survey.speleodb_id is not None
        assert isinstance(survey.speleodb_id, UUID)
        assert survey.cave_name == "DEMO"
        assert survey.first_start_absolute_elevation == 123.45
        assert survey.unit == "m"
        assert survey.use_magnetic_azimuth is True

        # Check optional fields
        assert survey.carto_ellipse == "SomeValue"
        assert survey.carto_line == "SomeValue"
        assert survey.carto_linked_surface == "SomeValue"
        assert survey.carto_overlay == "SomeValue"
        assert survey.carto_page == "SomeValue"
        assert survey.carto_rectangle == "SomeValue"
        assert survey.carto_selection == "SomeValue"
        assert survey.carto_spline == "SomeValue"
        assert survey.constraints == "SomeValue"
        assert survey.list_annotation == "SomeValue"

    def test_survey_creation_with_default_values(self):
        data = {"cave_name": "DEMO"}

        survey = Survey(**data)

        assert survey.speleodb_id is not None
        assert isinstance(survey.speleodb_id, UUID)
        assert survey.cave_name == "DEMO"
        assert survey.first_start_absolute_elevation == 0.0
        assert survey.unit == "m"
        assert survey.use_magnetic_azimuth is True

        # Check optional fields
        assert survey.carto_ellipse is None
        assert survey.carto_line is None
        assert survey.carto_linked_surface is None
        assert survey.carto_overlay is None
        assert survey.carto_page is None
        assert survey.carto_rectangle is None
        assert survey.carto_selection is None
        assert survey.carto_spline is None
        assert survey.constraints is None
        assert survey.list_annotation is None

    def test_invalid_float_conversion(self):
        data = {
            "cave_name": "DEMO",
            "first_start_absolute_elevation": "invalid_float",
            "unit": "m",
            "use_magnetic_azimuth": "true",
        }

        with pytest.raises(ValidationError, match="Input should be a valid number"):
            Survey(**data)

    def test_invalid_boolean_conversion(self):
        data = {
            "cave_name": "DEMO",
            "first_start_absolute_elevation": "0.0",
            "unit": "m",
            "use_magnetic_azimuth": "abc",
        }

        with pytest.raises(ValidationError, match="Input should be a valid boolean"):
            Survey(**data)

    def test_missing_required_field(self):
        data = {
            "first_start_absolute_elevation": "0.0",
            "unit": "m",
            "use_magnetic_azimuth": "true",
        }

        with pytest.raises(ValidationError, match="Field required"):
            Survey(**data)

    def test_extra_fields(self):
        data = {
            "cave_name": "DEMO",
            "first_start_absolute_elevation": "0.0",
            "unit": "m",
            "use_magnetic_azimuth": "true",
            "extra_field": "unexpected",
        }

        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            Survey(**data)

    def test_invalid_shot_collection(self):
        data = {
            "cave_name": "DEMO",
            "first_start_absolute_elevation": "123.45",
            "unit": "m",
            "use_magnetic_azimuth": "true",
            "data": "invalid_data",
        }

        with pytest.raises(ValidationError, match="Input should be a valid"):
            Survey(**data)


class TestSurveyShot(unittest.TestCase):
    def setUp(self) -> None:
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001
        self.data = {
            "azimuth": "0.0",
            "closure_to_id": "-1",
            "color": "0x00000000",
            "comment": "CLOSURE",
            "date": "2024-04-07",
            "depth": "0.0",
            "depth_in": "0.0",
            "down": "0.0",
            "excluded": "false",
            "explorer": "<Explorer>Snoopy</Surveyor>",
            "from_id": "8",
            "id": "78",
            "inclination": "0.0",
            "latitude": "0.0",
            "left": "0.0",
            "length": "0.0",
            "locked": "false",
            "longitude": "0.0",
            "name_compass": "ABCD",
            "profiletype": "VERTICAL",
            "right": "0.0",
            "section": "Main Line",
            "shape": None,
            "type": "REAL",
            "up": "0.0",
        }

    def test_invalid_date_conversion_with_time(self):
        self.data["date"] = "2024-04-07 11:05"

        with pytest.raises(
            ValidationError, match="Datetimes provided to dates should have zero time"
        ):
            SurveyShot(**self.data)

    @parameterized.expand(["24-04-2024", "2024-24-04"])
    def test_invalid_date_format(self, date_val: str):
        self.data["date"] = date_val

        with pytest.raises(
            ValidationError, match="Input should be a valid date or datetime"
        ):
            SurveyShot(**self.data)


if __name__ == "__main__":
    unittest.main()
