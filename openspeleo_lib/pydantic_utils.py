from __future__ import annotations

from typing import Annotated
from typing import get_args
from typing import get_origin

from pydantic import BaseModel
from pydantic.fields import Field


def aliased_model(
    base: type[BaseModel], alias_set: dict, name_suffix: str
) -> type[BaseModel]:
    annotations = {}
    namespace = {}

    for name, field in base.model_fields.items():
        alias = alias_set.get(base, {}).get(name)

        ann = field.annotation

        # Preserve nested models
        origin = get_origin(ann)
        if origin is list:
            (inner,) = get_args(ann)
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                inner = aliased_model(inner, alias_set, name_suffix)
                ann = list[inner]

        # Injecting the alias
        if alias:
            ann = Annotated[ann, Field(alias=alias)]

        annotations[name] = ann

        # Conserving the default value of the Field
        if field.default_factory is not None:
            namespace[name] = Field(default_factory=field.default_factory)
        else:
            namespace[name] = field.default

    namespace.update(
        {
            "__annotations__": annotations,
            "__module__": base.__module__,
        }
    )
    return type(f"{base.__name__}{name_suffix}", (base,), namespace)
