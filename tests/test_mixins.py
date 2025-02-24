import json
import unittest

import orjson
import pytest
from parameterized import parameterized
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import model_validator

from openspeleo_lib.constants import OSPL_DEFAULT_NAME_LENGTH
from openspeleo_lib.constants import OSPL_MAX_NAME_LENGTH
from openspeleo_lib.generators import UniqueValueGenerator
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.mixins import AutoIdModelMixin
from openspeleo_lib.mixins import BaseMixin
from openspeleo_lib.mixins import NameIdModelMixin
from openspeleo_lib.utils import apply_key_mapping


# Sample model using the mixins
class SubModel(BaseMixin, NameIdModelMixin, BaseModel):
    id: int


# Another model to test uniqueness in lists
class ContainerModel(BaseMixin, BaseModel):
    items: list[SubModel]

    @model_validator(mode="before")
    @classmethod
    def check_unique_items(cls, values):
        values["items"] = cls.validate_unique("name_compass", values.get("items", []))
        return values


class NestedModel(BaseMixin, BaseModel):
    name: str
    nested: SubModel


# Model with auto-generated `id`
class AutoIdModel(BaseMixin, AutoIdModelMixin, BaseModel):
    pass


# Model with auto-generated `name_compass`
class NameIdModel(BaseMixin, NameIdModelMixin, BaseModel):
    pass


class TestUniqueSubFieldMixin(unittest.TestCase):
    def test_validate_unique_with_duplicates(self):
        with UniqueValueGenerator.activate_uniqueness():
            _ = SubModel(id=1, name_compass="test1")

            with pytest.raises(ValidationError, match="has already been registered"):
                _ = SubModel(id=1, name_compass="test1")

    def test_validate_unique_with_duplicates_with_ctx_not_activated(self):
        _ = SubModel(id=1, name_compass="test1")
        _ = SubModel(id=1, name_compass="test1")


class TestBaseMixin(unittest.TestCase):
    def test_name_default_generation(self):
        model = NameIdModel(id=1)
        assert len(model.name_compass) == OSPL_DEFAULT_NAME_LENGTH
        assert all(
            char.upper() in UniqueValueGenerator.VOCAB for char in model.name_compass
        )

    def test_id_default_generation(self):
        model = AutoIdModel()
        assert model.id > 0

    def test_name_validator_accept_valid_name(self):
        model = SubModel(id=1, name_compass="valid_name-1")
        assert model.name_compass == "VALID_NAME-1"

    def test_name_validator_reject_invalid_name(self):
        with pytest.raises(ValidationError, match="String should match pattern."):
            SubModel(id=1, name_compass="invalid_name^")

    def test_container_model_with_unique_items(self):
        # Test ContainerModel with unique items
        items = [
            SubModel(id=1, name_compass="test1"),
            SubModel(id=2, name_compass="test2"),
            SubModel(id=3, name_compass="test3"),
        ]

        _ = ContainerModel(items=items)

    def test_container_model_with_duplicate_items(self):
        # Test ContainerModel with duplicate items
        item = SubModel(id=1, name_compass="test1")

        with pytest.raises(ValidationError, match="Duplicate value found"):
            ContainerModel(items=[item, item, item])

    #     # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #

    def test_submodel_from_dict(self):
        ariane_data = {"id": 1, "name_compass": "TEST"}
        model = SubModel(**ariane_data)

        # Validate that the model was created correctly from Ariane data
        assert model.id == 1
        assert model.name_compass == "TEST"

    def test_model_valide(self):
        data = {"id": 1, "name_compass": "TEST", "ExtraField": None}
        model = SubModel.model_validate(data)

        assert hasattr(model, "name_compass")
        assert not hasattr(model, "extra_field")

    def test_validate_unique_raises_error(self):
        model1 = SubModel(id=1, name_compass="Test1")
        model2 = SubModel(id=2, name_compass="Test1")

        with pytest.raises(
            ValidationError, match="Duplicate value found for `name_compass`"
        ):
            ContainerModel(items=[model1, model2])


class TestBaseMixinExport(unittest.TestCase):
    def test_to_json_basic(self):
        model = SubModel(id=1, name_compass="Test")
        json_output = model.to_json()

        # Expected JSON string
        expected_json = orjson.dumps(
            {"id": 1, "name_compass": "TEST"},
            None,
            option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
        ).decode("utf-8")

        assert json_output == expected_json

    def test_to_json_nested(self):
        nested_model = SubModel(id=2, name_compass="Nested")
        model = NestedModel(name="hello", nested=nested_model)

        json_output = model.to_json()

        # Expected JSON string
        expected_json = orjson.dumps(
            {"name": "hello", "nested": {"id": 2, "name_compass": "NESTED"}},
            None,
            option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
        ).decode("utf-8")

        assert json_output == expected_json

    def test_to_json_empty_fields(self):
        model = SubModel(id=3, name_compass="")
        json_output = model.to_json()

        # Expected JSON string
        expected_json = orjson.dumps(
            {
                "id": 3,
                "name_compass": model.name_compass.upper(),
            },
            None,
            option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
        ).decode("utf-8")

        assert json_output == expected_json

    def test_to_json_with_special_characters(self):
        model = SubModel(id=4, name_compass="NameWith!Mark")
        json_output = model.to_json()

        # Expected JSON string with escaped quotes
        expected_json = orjson.dumps(
            {"id": 4, "name_compass": "NAMEWITH!MARK"},
            None,
            option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
        ).decode("utf-8")

        assert json_output == expected_json

    def test_to_json_sort_keys(self):
        model = SubModel(id=5, name_compass="Zebra")
        json_output = model.to_json()

        # Expected JSON string with sorted keys
        expected_json = orjson.dumps(
            {"id": 5, "name_compass": "ZEBRA"},
            None,
            option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
        ).decode("utf-8")

        assert json.loads(json_output) == json.loads(expected_json)

    def test_submodel_to_dict(self):
        model = SubModel(id=1, name_compass="Test")
        transformed_dict = apply_key_mapping(model.model_dump(), mapping=ARIANE_MAPPING)
        assert transformed_dict == {"Name": "TEST", "ID": 1}


class TestAutoIdModelMixin(unittest.TestCase):
    def test_auto_id_generation(self):
        model = AutoIdModel()
        assert isinstance(model.id, int)
        assert model.id == 1

    def test_validate_unique_id_from_string(self):
        model = AutoIdModel(id="123")
        assert model.id == 123

    def test_validate_unique_id_from_int(self):
        model = AutoIdModel(id=123)
        assert model.id == 123

    @parameterized.expand([None, ""])
    def test_validate_no_id(self, id_value):
        model = AutoIdModel(id=id_value)
        assert model.id == 1

    def test_unique_id_clash(self):
        with UniqueValueGenerator.activate_uniqueness():
            _ = AutoIdModel(id="123")

            with pytest.raises(ValidationError, match="has already been registered"):
                AutoIdModel(id="123")

    def test_unique_id_no_clash(self):
        _ = AutoIdModel(id="123")
        _ = AutoIdModel(id="123")

    def test_validate_unique_id_invalid_type(self):
        with pytest.raises(
            ValidationError,
            match="should be a valid integer, unable to parse string as an integer",
        ):
            AutoIdModel(id="invalid_id")


class TestNameIdModelMixin(unittest.TestCase):
    def test_name_generation_with_default_factory(self):
        model = NameIdModel()
        assert len(model.name_compass) == OSPL_DEFAULT_NAME_LENGTH
        assert all(
            char.upper() in UniqueValueGenerator.VOCAB for char in model.name_compass
        )

    def test_name_validation_rejects_long_names(self):
        long_name = "A" * (OSPL_MAX_NAME_LENGTH + 1)

        with pytest.raises(ValidationError, match="String should match pattern"):
            NameIdModel(name_compass=long_name)

    def test_name_registration_with_retries(self):
        name = "TestName"

        # Creating model with the same name should trigger retries
        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=str, value=name.upper())
            with pytest.raises(ValidationError, match="has already been registered."):
                _ = NameIdModel(name_compass=name)


if __name__ == "__main__":
    unittest.main()
