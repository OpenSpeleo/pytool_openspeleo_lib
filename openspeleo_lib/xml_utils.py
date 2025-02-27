from lxml import etree

# ===================== FROM XML TO DICT ===================== #


def xml_to_dict(xml_data: str) -> dict:
    root = etree.fromstring(xml_data)  # noqa: S320
    return _etree_to_dict(root)


def _etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = {}
        for dc in map(_etree_to_dict, children):
            for k, v in dc.items():
                if k in dd:
                    if not isinstance(dd[k], list):
                        dd[k] = [dd[k]]
                    dd[k].append(v)
                else:
                    dd[k] = v
        d = {t.tag: dd}
    if t.attrib:
        d[t.tag].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]["#text"] = text
        else:
            d[t.tag] = text
    return d


# ===================== FROM DICT TO XML ===================== #


def dict_to_xml(data: dict, root_tag="CaveFile") -> str:
    if not isinstance(data, dict):
        raise TypeError(f"Expected a dictionary, received: `{type(data)}`")

    root = etree.Element(root_tag)
    _dict_to_etree(data, root)

    xml_declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    xml_str = etree.tostring(root, pretty_print=True, encoding="unicode")

    return xml_declaration + xml_str


def _dict_to_etree(d, root):
    for key, value in d.items():
        if isinstance(value, dict):
            sub_element = etree.SubElement(root, key)
            _dict_to_etree(value, sub_element)

        elif isinstance(value, list):
            for item in value:
                sub_element = etree.SubElement(root, key)
                _dict_to_etree(item, sub_element)

        else:
            sub_element = etree.SubElement(root, key)
            if value is not None:
                sub_element.text = str(value)
