import tempfile
import unittest

import pytest

from openspeleo_lib.interfaces.base import BaseInterface


class TestBaseInterface(unittest.TestCase):
    def test_instantiation_abc_class(self):
        with pytest.raises(TypeError):
            BaseInterface(survey=None)

    def test_to_file_not_implemented(self):
        class DemoInterface(BaseInterface):
            pass

        with pytest.raises(TypeError):
            DemoInterface(survey=None)

    def test_from_file_not_implemented(self):
        with tempfile.NamedTemporaryFile() as tmp_f, pytest.raises(NotImplementedError):
            BaseInterface.from_file(filepath=tmp_f.name)

    def test_instanciation(self):
        with pytest.raises(TypeError):
            BaseInterface()


if __name__ == "__main__":
    unittest.main()
