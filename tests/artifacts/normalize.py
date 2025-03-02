import zipfile  # noqa: INP001
from pathlib import Path

import xmltodict
from defusedxml.minidom import parseString
from dicttoxml2 import dicttoxml

if __name__ == "__main__":
    for ariane_f in [
        "test_simple.mini.tml",
        "test_simple.tml",
        "test_with_walls.tml",
        "test_large.tml",
    ]:
        ariane_f = Path(ariane_f)  # noqa: PLW2901
        print(f"Processing: `{ariane_f}` ...")  # noqa: T201
        with zipfile.ZipFile(ariane_f, "r") as zf:
            data = xmltodict.parse(zf.open("Data.xml").read())["CaveFile"]

        # Process and clean the data
        for shot in data["Data"]["SurveyData"]:
            shot["Azimut"] = str(abs(float(shot["Azimut"])) % 360)

        # Export the processed data back to an XML file
        xml_str = dicttoxml(
            data, custom_root="CaveFile", attr_type=False, fold_list=False
        )

        xml_prettyfied = (
            parseString(xml_str)
            .toprettyxml(indent=" " * 4, encoding="utf-8", standalone=True)
            .decode("utf-8")
        )

        with zipfile.ZipFile(ariane_f, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Data.xml", xml_prettyfied)
