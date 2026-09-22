from __future__ import annotations

from typing import Annotated
from typing import get_args
from typing import get_origin

from pydantic import BaseModel
from pydantic import create_model
from pydantic.fields import Field


def aliased_model(
    base: type[BaseModel], alias_set: dict, name_suffix: str
) -> type[BaseModel]:
    # Resolve forward references before copying their Field attributes.
    base.model_rebuild()
    fields = {}

    for name, field in base.model_fields.items():
        alias = alias_set.get(base, {}).get(name)

        field_data = field.asdict()
        ann = field_data["annotation"]

        # Preserve nested models
        origin = get_origin(ann)
        if origin is list:
            (inner,) = get_args(ann)
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                inner = aliased_model(inner, alias_set, name_suffix)
                ann = list[inner]

        # Reconstruct the complete field, including constraints and exclusions.
        # __base__ preserves model/field validators and serializers.
        attributes = field_data["attributes"]
        if alias:
            attributes.update(
                alias=alias, validation_alias=alias, serialization_alias=alias
            )
        fields[name] = (
            Annotated[ann, *field_data["metadata"]] if field_data["metadata"] else ann,
            Field(**attributes),
        )

    return create_model(
        f"{base.__name__}{name_suffix}",
        __base__=base,
        __module__=base.__module__,
        **fields,
    )
