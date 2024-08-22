#!/usr/bin/env python

from pathlib import Path

from openspeleo_lib.types import Survey

if __name__ == "__main__":
    # shot = Shot(name="AAAA")
    # shot = Shot()
    # print(shot.model_dump_json(indent=1))
    # print("# -------------------------------------------------------------- #")
    # section = Section(name="ZA", shots=[shot])
    # print(section.model_dump_json(indent=1))
    # print("# -------------------------------------------------------------- #")
    # survey_f = Survey(name="Mayan Blue", sections=[section])
    # print(survey_f.model_dump_json(indent=1))
    # print("# -------------------------------------------------------------- #")
    # print(survey_f.shots)

    print(f"{'#' * 80}")

    # file = Path("tests/artifacts/fulford.dat")
    # survey = Survey.from_compass_file(filepath=file)
    # print(survey.model_dump_json(indent=1))

    filepath = Path("tests/artifacts/survey.tml")

    from ariane_lib.parser import ArianeParser

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: `{filepath}`")

    survey_data = ArianeParser(filepath).data

    import json

    with open("data.json", "w") as convert_file:
        convert_file.write(json.dumps(survey_data, indent=4))

    survey = Survey.from_ariane(survey_data)
    # survey_data_round = survey.to_ariane()
    # # survey = Survey.from_ariane_file(filepath=file)
    # # print(survey.model_dump_json(indent=1))
    # from pprint import pprint

    # from deepdiff import DeepDiff

    # diff = DeepDiff(survey_data, survey_data_round, verbose_level=2)
    # pprint(diff, indent=2)

    survey.to_ariane_file("survey.xml")
