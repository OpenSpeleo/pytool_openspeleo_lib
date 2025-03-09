import unittest

from parameterized import parameterized

from openspeleo_lib.xml_utils import deserialize_xmlfield_to_dict
from openspeleo_lib.xml_utils import serialize_dict_to_xmlfield

TEST_DATA = [
    (
        "<Explorer>DiveTeam</Explorer><Surveyor>Diver1, Diver2</Surveyor>",
        {"Explorer": "DiveTeam", "Surveyor": "Diver1, Diver2"},
    ),
    (
        "<Explorer>DiveTeam</Explorer>",
        {"Explorer": "DiveTeam"},
    ),
    ("<Surveyor>Diver1, Diver2</Surveyor>", {"Surveyor": "Diver1, Diver2"}),
    ("Ariane", "Ariane"),
    ("", None),
]


class TestCaseConversion(unittest.TestCase):
    @parameterized.expand(TEST_DATA)
    def test_deserialize_xmlfield_to_dict(
        self, xml_field: str | None, expected_output: dict | str | None
    ):
        assert deserialize_xmlfield_to_dict(xml_field) == expected_output

    @parameterized.expand(TEST_DATA)
    def test_serialize_dict_to_xmlfield(
        self, expected_output: str | None, ospl_field: dict | str | None
    ):
        assert serialize_dict_to_xmlfield(ospl_field) == expected_output


if __name__ == "__main__":
    unittest.main()
