import re


def camel2snakecase(value: str) -> str:
    # Breaks before sequences of uppercase letters (but not for acronyms) or digits
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=\D)(?=\d)", "_", value).lower()


def snake2camelcase(value: str) -> str:
    first, *others = value.split("_")
    return "".join([first.lower(), *map(str.title, others)])


def str2bool(value: str) -> bool:
    """
    Convert a string or integer value to a boolean.
    Accepts common string representations and integers.
    Returns True or False based on the input.
    Raises ValueError if the input cannot be converted to a boolean.
    """

    if isinstance(value, str):
        value = value.strip().lower()

        if value in {"true", "t", "yes", "y", "1", "on"}:
            return True

        if value in {"false", "f", "no", "n", "0", "off"}:
            return False

    raise ValueError(f"Cannot convert {value!r} to boolean")


def remove_none_values(d):
    """
    Recursively remove None values from a dictionary.

    Args:
        d (dict): The dictionary to clean.

    Returns:
        dict: The cleaned dictionary with no None values.
    """
    if isinstance(d, dict):
        for k, v in list(d.items()):
            if isinstance(v, (dict, tuple, list)):
                remove_none_values(v)
            if v is None:
                del d[k]

    elif isinstance(d, (list, tuple)):
        values = []
        for i in d:
            if i is None:
                continue
            if isinstance(i, (dict, tuple, list)):
                values.append(remove_none_values(i))
            else:
                values.append(i)

    return d


def apply_key_mapping(data: dict | list | tuple, mapping: dict) -> dict | list:
    if not isinstance(data, (tuple, dict, list)):
        raise TypeError(f"Unexpected type received: {type(data)}")

    if isinstance(data, dict):
        rslt = {}
        for key, val in data.items():
            key = mapping.get(key, key)  # noqa: PLW2901

            if isinstance(val, (dict, list, tuple)):
                rslt[key] = apply_key_mapping(val, mapping)
            else:
                rslt[key] = val

    else:
        rslt = []
        for val in data:
            if isinstance(val, (dict, list, tuple)):
                rslt.append(apply_key_mapping(val, mapping))
            else:
                rslt.append(val)

    return rslt
