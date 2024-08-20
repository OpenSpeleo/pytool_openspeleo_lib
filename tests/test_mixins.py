
import json
import unittest

import pytest
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import model_validator

from openspeleo_lib.mixins import BaseMixin
from openspeleo_lib.mixins import UniqueSubFieldMixin
from openspeleo_lib.utils import UniqueNameGenerator


# Sample model using the mixins
class SubModel(UniqueSubFieldMixin, BaseMixin, BaseModel):
    id: int

# Another model to test uniqueness in lists
class ContainerModel(UniqueSubFieldMixin, BaseModel):
    items: list[SubModel]

    @model_validator(mode="before")
    @classmethod
    def check_unique_items(cls, values):
        values["items"] = cls.validate_unique("name", values.get("items", []))
        return values


class NestedModel(BaseMixin, BaseModel):
    nested: SubModel


class TestUniqueSubFieldMixin(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_names.clear()  # noqa: SLF001

    def test_validate_unique_no_duplicates(self):
        for idx in range(3):
            _ = SubModel(id=1, name=f"test{idx}")

    def test_validate_unique_with_duplicates(self):
        _ = SubModel(id=1, name="test1")
        with pytest.raises(ValidationError) as exc_info:
            _ = SubModel(id=1, name="test1")
        assert "has already been allocated" in str(exc_info.value)


class TestBaseMixin(unittest.TestCase):

    def test_name_default_generation(self):
        model = SubModel(id=1)
        assert len(model.name) == 6  # noqa: PLR2004
        assert all(char.upper() in UniqueNameGenerator.VOCAB for char in model.name)

    def test_name_validator_accept_valid_name(self):
        model = SubModel(id=1, name="valid_name-1")
        assert model.name == "valid_name-1"

    def test_name_validator_reject_invalid_name(self):
        with pytest.raises(ValidationError) as exc_info:
            SubModel(id=1, name="invalid_name^")
        assert "The character `^` is not allowed as `name`." in str(exc_info.value)

    # def test_enforce_snake_and_remove_none(self):

    #     class TestModel(BaseMixin, BaseModel):
    #         id: int
    #         some_field: str | None = None
    #         another_field: str

    #     model = TestModel(ID=1, SomeField=None, AnotherField="test")
    #     model_dict = model.model_dump()

    #     assert "id" in model_dict
    #     assert "ID" not in model_dict
    #     assert model_dict["id"] == 1

    #     assert "some_field" in model_dict
    #     assert "SomeField" not in model_dict
    #     assert model_dict["some_field"] is None

    #     assert "another_field" in model_dict
    #     assert "AnotherField" not in model_dict
    #     assert model_dict["another_field"] == "test"


class TestIntegration(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_names.clear()  # noqa: SLF001

    def test_container_model_with_unique_items(self):
        # Test ContainerModel with unique items
        items = [
            SubModel(id=1, name="test1"),
            SubModel(id=2, name="test2"),
            SubModel(id=3, name="test3"),
        ]

        _ = ContainerModel(items=items)

    def test_container_model_with_duplicate_items(self):
        # Test ContainerModel with duplicate items
        item = SubModel(id=1, name="test1")

        with pytest.raises(ValidationError) as exc_info:
            ContainerModel(items=[item, item, item])
        assert "Duplicate value found" in str(exc_info.value)


class TestBaseMixinToJson(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_names.clear()  # noqa: SLF001

    def test_to_json_basic(self):
        model = SubModel(id=1, name="Test")
        json_output = model.to_json()

        # Expected JSON string
        expected_json = json.dumps({
            "id": 1,
            "name": "Test"
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_nested(self):
        nested_model = SubModel(id=2, name="Nested")
        model = NestedModel(name="hello", nested=nested_model)

        json_output = model.to_json()

        # Expected JSON string
        expected_json = json.dumps({
            "name": "hello",
            "nested": {
                "id": 2,
                "name": "Nested"
            }
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_empty_fields(self):
        model = SubModel(id=3, name="")
        json_output = model.to_json()

        # Expected JSON string
        expected_json = json.dumps({
            "id": 3,
            "name": model.name,
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_with_special_characters(self):
        model = SubModel(id=4, name="NameWith!Mark")
        json_output = model.to_json()

        # Expected JSON string with escaped quotes
        expected_json = json.dumps({
            "id": 4,
            "name": "NameWith!Mark"
        }, indent=4, sort_keys=True)

        assert json_output == expected_json

    def test_to_json_sort_keys(self):
        model = SubModel(id=5, name="Zebra")
        json_output = model.to_json()

        # Expected JSON string with sorted keys
        expected_json = json.dumps({
            "id": 5,
            "name": "Zebra"
        }, indent=4, sort_keys=True)

        assert json.loads(json_output) == json.loads(expected_json)


if __name__ == "__main__":
    unittest.main()
