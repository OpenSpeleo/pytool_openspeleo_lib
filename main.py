#!/usr/bin/env python

from pathlib import Path

from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.models import Survey

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

    print(f"{'#' * 80}")  # noqa: T201

    # file = Path("tests/artifacts/fulford.dat")
    # survey = Survey.from_compass_file(filepath=file)
    # print(survey.model_dump_json(indent=1))

    filepath = Path("tests/artifacts/hand_survey.tml")

    DEBUG = False

    survey: Survey = ArianeInterface.from_file(filepath)

    ArianeInterface.to_file(survey=survey, filepath="survey.tml")
