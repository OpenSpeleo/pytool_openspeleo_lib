
import json
import unittest

import pytest
from parameterized import parameterized
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import model_validator

from openspeleo_lib.constants import COMPASS_MAX_NAME_LENGTH
from openspeleo_lib.formats.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.generators import UniqueIDGenerator
from openspeleo_lib.generators import UniqueNameGenerator
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

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_validate_unique_with_duplicates(self):
        _ = SubModel(id=1, name_compass="test1")

        with pytest.raises(ValidationError, match="has already been registred"):
            _ = SubModel(id=1, name_compass="test1")


class TestBaseMixin(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_name_default_generation(self):
        model = SubModel(id=1)
        assert len(model.name_compass) == 6
        assert all(
            char.upper() in UniqueNameGenerator.VOCAB
            for char in model.name_compass
        )

    def test_name_validator_accept_valid_name(self):
        model = SubModel(id=1, name_compass="valid_name-1")
        assert model.name_compass == "valid_name-1"

    def test_name_validator_reject_invalid_name(self):
        with pytest.raises(
            ValidationError,
            match=r"The character `\^` is not allowed as `name`."
        ):
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

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #

    def test_from_ariane_dict_basic(self):
        ariane_data = {
            "id": 1,
            "name_compass": "Test"
        }
        model = SubModel.from_ariane_dict(ariane_data)

        # Validate that the model was created correctly from Ariane data
        assert model.id == 1
        assert model.name_compass == "Test"

    def test_model_valide(self):
        data = {"id": 1, "name_compass": "Test", "ExtraField": None}
        model = SubModel.model_validate(data)

        assert hasattr(model, "name_compass")
        assert not hasattr(model, "extra_field")

    def test_validate_unique_raises_error(self):

        model1 = SubModel(id=1, name_compass="Test1")
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001
        model2 = SubModel(id=2, name_compass="Test1")

        with pytest.raises(
            ValidationError,
            match="Duplicate value found for `name_compass`"
        ):
            ContainerModel(items=[model1, model2])


class TestBaseMixinToJson(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_to_json_basic(self):
        model = SubModel(id=1, name_compass="Test")
        json_output = model.to_json()

        # Expected JSON string
        expected_json = json.dumps({
            "id": 1,
            "name_compass": "Test"
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_nested(self):
        nested_model = SubModel(id=2, name_compass="Nested")
        model = NestedModel(name="hello", nested=nested_model)

        json_output = model.to_json()

        # Expected JSON string
        expected_json = json.dumps({
            "name": "hello",
            "nested": {
                "id": 2,
                "name_compass": "Nested"
            }
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_empty_fields(self):
        model = SubModel(id=3, name_compass="")
        json_output = model.to_json()

        # Expected JSON string
        expected_json = json.dumps({
            "id": 3,
            "name_compass": model.name_compass,
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_with_special_characters(self):
        model = SubModel(id=4, name_compass="NameWith!Mark")
        json_output = model.to_json()

        # Expected JSON string with escaped quotes
        expected_json = json.dumps({
            "id": 4,
            "name_compass": "NameWith!Mark"
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_sort_keys(self):
        model = SubModel(id=5, name_compass="Zebra")
        json_output = model.to_json()

        # Expected JSON string with sorted keys
        expected_json = json.dumps({
            "id": 5,
            "name_compass": "Zebra"
        }, indent=4, sort_keys=True)

        assert json.loads(json_output) == json.loads(expected_json)

    def test_to_ariane_dict_basic(self):
        model = SubModel(id=1, name_compass="Test")
        ariane_dict = model.to_ariane_dict()

        # Expected dictionary after key mapping
        expected_dict = apply_key_mapping(model.model_dump(), mapping=ARIANE_MAPPING)

        assert ariane_dict == expected_dict

    def test_to_json_with_nested_none(self):
        model = SubModel(id=1, name_compass="Test")
        model_json = model.to_json()

        # Verify that no `None` values are included in the JSON output
        assert '"None"' not in model_json


class TestBaseMixinDebugMode(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_from_ariane_dict_with_debug(self):
        ariane_data = {"id": 1, "name_compass": "Test"}
        model = SubModel.from_ariane_dict(ariane_data, debug=True)
        assert model.id == 1
        assert model.name_compass == "Test", f"{model.name_compass}"

    def test_to_ariane_dict_with_debug(self):
        model = SubModel(id=1, name_compass="Test")
        ariane_dict = model.to_ariane_dict(debug=True)
        expected_dict = apply_key_mapping(model.model_dump(), mapping=ARIANE_MAPPING)
        assert ariane_dict == expected_dict


class TestAutoIdModelMixin(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueIDGenerator._used_values.clear()  # noqa: SLF001

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
        _ = AutoIdModel(id="123")

        with pytest.raises(ValidationError, match="has already been registred"):
            AutoIdModel(id="123")

    def test_validate_unique_id_invalid_type(self):
        with pytest.raises(
            ValidationError,
            match=r"invalid literal for int\(\) with base 10"
        ):
            AutoIdModel(id="invalid_id")


class TestNameIdModelMixin(unittest.TestCase):

    def setUp(self) -> None:
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_name_generation_with_default_factory(self):
        model = NameIdModel()
        assert len(model.name_compass) == 6
        assert all(
            char.upper() in UniqueNameGenerator.VOCAB
            for char in model.name_compass
        )

    def test_name_validation_rejects_long_names(self):
        long_name = "A" * (COMPASS_MAX_NAME_LENGTH + 1)

        with pytest.raises(ValidationError, match=f"Name {long_name} is too long"):
            NameIdModel(name_compass=long_name)

    def test_name_registration_with_retries(self):
        name = "TestName"
        UniqueNameGenerator.register(value=name)

        # Creating model with the same name should trigger retries
        with pytest.raises(
            ValidationError,
            match=f"Value `{name}` has already been registred."
        ):
            _ = NameIdModel(name_compass=name)


if __name__ == "__main__":
    unittest.main()
