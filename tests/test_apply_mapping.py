import unittest

import pytest

from openspeleo_lib.utils import apply_key_mapping


class TestApplyKeyMapping(unittest.TestCase):

    def test_dict_with_key_mapping(self):
        data = {
            "Azimut": "0.0",
            "Depth": "10.0",
            "Explorer": "Ariane"
        }
        mapping = {"Azimut": "Bearing", "Explorer": "Diver"}
        expected_output = {
            "Bearing": "0.0",
            "Depth": "10.0",
            "Diver": "Ariane"
        }
        assert apply_key_mapping(data, mapping) == expected_output

    def test_nested_dict_with_key_mapping(self):
        data = {
            "Shape": {
                "RadiusCollection": {
                    "RadiusVector": [
                        {"angle": "0.0", "length": "0.0"},
                        {"angle": "90.0", "length": "0.0"},
                    ]
                },
                "profileAzimut": "0.0"
            },
            "Azimut": "180.0"
        }
        mapping = {"Azimut": "Bearing", "profileAzimut": "profileBearing"}
        expected_output = {
            "Shape": {
                "RadiusCollection": {
                    "RadiusVector": [
                        {"angle": "0.0", "length": "0.0"},
                        {"angle": "90.0", "length": "0.0"},
                    ]
                },
                "profileBearing": "0.0"
            },
            "Bearing": "180.0"
        }
        assert apply_key_mapping(data, mapping) == expected_output

    def test_list_with_nested_dict_and_key_mapping(self):
        data = [
            {"Azimut": "0.0", "Depth": "10.0"},
            {"Azimut": "90.0", "Depth": "20.0"}
        ]
        mapping = {"Azimut": "Bearing"}
        expected_output = [
            {"Bearing": "0.0", "Depth": "10.0"},
            {"Bearing": "90.0", "Depth": "20.0"}
        ]
        assert apply_key_mapping(data, mapping) == expected_output

    def test_tuple_with_nested_dict_and_key_mapping(self):
        data = (
            {"Azimut": "0.0", "Depth": "10.0"},
            {"Azimut": "90.0", "Depth": "20.0"}
        )
        mapping = {"Azimut": "Bearing"}
        expected_output = [
            {"Bearing": "0.0", "Depth": "10.0"},
            {"Bearing": "90.0", "Depth": "20.0"}
        ]
        assert apply_key_mapping(data, mapping) == expected_output

    def test_no_key_mapping(self):
        data = {"Azimut": "0.0", "Depth": "10.0"}
        mapping = {}
        assert apply_key_mapping(data, mapping) == data

    def test_no_match_key_mapping(self):
        data = {"Azimut": "0.0", "Depth": "10.0"}
        mapping = {"NonexistentKey": "NewKey"}
        assert apply_key_mapping(data, mapping) == data

    def test_type_error_on_invalid_input(self):
        data = "Invalid data type"
        mapping = {}
        with pytest.raises(TypeError, match="Unexpected type received: <class 'str'>"):
            apply_key_mapping(data, mapping)

    def test_key_replacement_with_non_string_keys(self):
        data = {1: "one", 2: "two", 3: {"Length": "10.0"}}
        mapping = {1: "one", 2: "two", "Length": "Norm"}
        expected_output = {"one": "one", "two": "two", 3: {"Norm": "10.0"}}
        assert apply_key_mapping(data, mapping) == expected_output


if __name__ == "__main__":
    unittest.main()
