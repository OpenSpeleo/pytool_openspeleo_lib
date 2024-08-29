import unittest

from openspeleo_lib.models import RadiusCollection
from openspeleo_lib.models import RadiusVector


class TestSurvey(unittest.TestCase):

    def test_radius_collection_default(self):
        radius_collect = RadiusCollection()
        assert radius_collect.radius_vector == []

    def test_radius_collection_from_radius_vector(self):
        data = {
            "tension_corridor": 1.0,
            "tension_profile": 1.0,
            "angle": 1.0,
            "norm": 1.0
        }
        vector = RadiusVector(**data)

        radius_collect = RadiusCollection(radius_vector=data)
        assert radius_collect.radius_vector == [vector]

        radius_collect = RadiusCollection(radius_vector=[vector])
        assert radius_collect.radius_vector == [vector]


if __name__ == "__main__":
    unittest.main()

