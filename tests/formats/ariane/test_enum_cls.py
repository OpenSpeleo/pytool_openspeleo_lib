import unittest

import pytest

from openspeleo_lib.formats.ariane.enums_cls import ArianeFileType
from openspeleo_lib.formats.ariane.enums_cls import ProfileType
from openspeleo_lib.formats.ariane.enums_cls import ShotType
from openspeleo_lib.formats.ariane.enums_cls import UnitType


class TestArianeFileType(unittest.TestCase):

    def test_ariane_file_type_tml(self):
        assert ArianeFileType.from_str("TML") == ArianeFileType.TML
        assert ArianeFileType.TML.value == 0

    def test_ariane_file_type_tmlu(self):
        assert ArianeFileType.from_str("TMLU") == ArianeFileType.TMLU
        assert ArianeFileType.TMLU.value == 1

    def test_ariane_file_type_invalid(self):
        with pytest.raises(ValueError, match="Unknown value"):
            ArianeFileType.from_str("INVALID")

class TestUnitType(unittest.TestCase):

    def test_unit_type_metric(self):
        assert UnitType.from_str("M") == UnitType.METRIC
        assert UnitType.from_str("METRIC") == UnitType.METRIC
        assert UnitType.METRIC.value == 0

    def test_unit_type_imperial(self):
        assert UnitType.from_str("FT") == UnitType.IMPERIAL
        assert UnitType.from_str("IMPERIAL") == UnitType.IMPERIAL
        assert UnitType.IMPERIAL.value == 1

    def test_unit_type_invalid(self):
        with pytest.raises(ValueError, match="Unknown value"):
            UnitType.from_str("INVALID")


class TestProfileType(unittest.TestCase):

    def test_profile_type_vertical(self):
        assert ProfileType.from_str("VERTICAL") == ProfileType.VERTICAL
        assert ProfileType.VERTICAL.value == 0

    def test_profile_type_invalid(self):
        with pytest.raises(ValueError, match="Unknown value"):
            ProfileType.from_str("INVALID")


class TestShotType(unittest.TestCase):

    def test_shot_type_real(self):
        assert ShotType.from_str("REAL") == ShotType.REAL
        assert ShotType.REAL.value == 1

    def test_shot_type_virtual(self):
        assert ShotType.from_str("VIRTUAL") == ShotType.VIRTUAL
        assert ShotType.VIRTUAL.value == 2

    def test_shot_type_start(self):
        assert ShotType.from_str("START") == ShotType.START
        assert ShotType.START.value == 3

    def test_shot_type_closure(self):
        assert ShotType.from_str("CLOSURE") == ShotType.CLOSURE
        assert ShotType.CLOSURE.value == 4

    def test_shot_type_invalid(self):
        with pytest.raises(ValueError, match="Unknown value"):
            ShotType.from_str("INVALID")


if __name__ == "__main__":
    unittest.main()
