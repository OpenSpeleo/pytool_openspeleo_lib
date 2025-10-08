from __future__ import annotations

import unittest

import pytest

from openspeleo_lib.utils import str2bool


class TestStr2Bool(unittest.TestCase):
    def test_true_values(self):
        true_values = [
            "true",
            "True",
            "TRUE",
            "t",
            "T",
            "yes",
            "Yes",
            "y",
            "Y",
            "1",
            "on",
            "On",
            "ON",
        ]
        for val in true_values:
            if not str2bool(val):
                raise AssertionError(f"{val} should be interpreted as True.")

    def test_false_values(self):
        false_values = [
            "false",
            "False",
            "FALSE",
            "f",
            "F",
            "no",
            "No",
            "n",
            "N",
            "0",
            "off",
            "Off",
            "OFF",
        ]
        for val in false_values:
            if str2bool(val):
                raise AssertionError(f"{val} should be interpreted as False.")

    def test_stripped_values(self):
        if not str2bool("  true  "):
            raise AssertionError("'  true  ' should be interpreted as True.")
        if str2bool("  false  "):
            raise AssertionError("'  false  ' should be interpreted as False.")
        if not str2bool("\nYes\n"):
            raise AssertionError("'\\nYes\\n' should be interpreted as True.")
        if str2bool("\tNo\t"):
            raise AssertionError("'\\tNo\\t' should be interpreted as False.")

    def test_invalid_values(self):
        invalid_values = ["maybe", "2", "", "random", None]
        for val in invalid_values:
            with pytest.raises(ValueError):  # noqa: PT011
                str2bool(val)

    def test_non_string_and_non_int(self):
        try:
            str2bool([])
        except ValueError:
            pass
        else:
            raise AssertionError("List input should raise a ValueError.")

        try:
            str2bool({})
        except ValueError:
            pass
        else:
            raise AssertionError("Dict input should raise a ValueError.")


if __name__ == "__main__":
    unittest.main()
