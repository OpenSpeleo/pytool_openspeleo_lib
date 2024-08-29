import unittest
from datetime import date

import pytest

from openspeleo_lib.formats.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.generators import UniqueNameGenerator
from openspeleo_lib.models import SurveyShot
from openspeleo_lib.utils import apply_key_mapping


def shot_from_dict(data: dict) -> SurveyShot:
    data = apply_key_mapping(data, ARIANE_MAPPING.inverse)
    return SurveyShot(**data)


class TestCaveDataModel(unittest.TestCase):

    def setUp(self):
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

        self.valid_data = {
            "Azimut": "0.0",
            "ClosureToID": "-1",
            "Color": "0x00ffffff",
            "Comment": "Lead on the right side.",
            "Date": "2024-04-22",
            "Depth": "0.0",
            "DepthIn": "0.0",
            "Down": "0.0",
            "Excluded": "false",
            "Explorer": "Ariane",
            "FromID": "-1",
            "ID": "0",
            "Inclination": "0.0",
            "Latitude": "0.0",
            "Left": "0.0",
            "Length": "0.0",
            "Locked": "true",
            "Longitude": "0.0",
            "Name": "ABC",
            "Profiletype": "VERTICAL",
            "Right": "0.0",
            "Section": "Start",
            "Shape": {
                "RadiusCollection": {
                    "RadiusVector": [
                        {
                            "TensionCorridor": "1.0",
                            "TensionProfile": "1.0",
                            "angle": "0.0",
                            "length": "0.0"
                        },
                        {
                            "TensionCorridor": "1.0",
                            "TensionProfile": "1.0",
                            "angle": "180.0",
                            "length": "0.0"
                        },
                        {
                            "TensionCorridor": "1.0",
                            "TensionProfile": "1.0",
                            "angle": "90.0",
                            "length": "0.0"
                        },
                        {
                            "TensionCorridor": "1.0",
                            "TensionProfile": "1.0",
                            "angle": "270.0",
                            "length": "0.0"
                        }
                    ]
                },
                "hasProfileAzimut": "false",
                "hasProfileTilt": "false",
                "profileAzimut": "0.0",
                "profileTilt": "0.0"
            },
            "Type": "START",
            "Up": "0.0"
        }

    def test_create_cave_data_model(self):
        cave_data = shot_from_dict(self.valid_data)
        assert cave_data.azimuth == 0.0
        assert cave_data.closure_to_id == -1
        assert cave_data.color == "0x00ffffff"
        assert cave_data.date == date(2024, 4, 22)
        assert cave_data.depth == 0.0
        assert not cave_data.excluded
        assert cave_data.explorer == "Ariane"
        assert not cave_data.shape.has_profile_azimuth
        assert cave_data.shape.radius_collection.radius_vector[0].tension_corridor == \
            1.0

    def test_invalid_data(self):
        invalid_data = self.valid_data.copy()
        invalid_data["Azimut"] = "not_a_float"
        with pytest.raises(
            ValueError,
            match="Input should be a valid number, unable to parse string as a number"
        ):
            shot_from_dict(invalid_data)

    def test_optional_fields(self):
        partial_data = self.valid_data.copy()
        partial_data["Comment"] = None
        partial_data["Name"] = None
        cave_data = shot_from_dict(partial_data)
        assert cave_data.comment is None
        assert cave_data.name_compass is not None


if __name__ == "__main__":
    unittest.main()
