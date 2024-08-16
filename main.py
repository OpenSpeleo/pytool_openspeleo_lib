#!/usr/bin/env python

import json
import unittest
from pathlib import Path

from compass_lib.parser import CompassParser

from openspeleo_lib.types import Section
from openspeleo_lib.types import Shot
from openspeleo_lib.types import Survey

if __name__ == "__main__":
    shot = Shot(name="AAAA")
    shot = Shot()
    print(shot.model_dump_json(indent=1))
    print("# -------------------------------------------------------------- #")
    section = Section(name="ZA", shots=[shot])
    print(section.model_dump_json(indent=1))
    print("# -------------------------------------------------------------- #")
    survey_f = Survey(name="Mayan Blue", sections=[section])
    print(survey_f.model_dump_json(indent=1))
    print("# -------------------------------------------------------------- #")
    print(survey_f.shots)

    print(f"{'#' * 80}")

    file = Path("tests/artifacts/fulford.dat")
    survey = Survey.from_compass_file(filepath=file)
    print(survey.model_dump_json(indent=1))

    file = Path("tests/artifacts/test_simple.tml")
    survey = Survey.from_ariane_file(filepath=file)
    print(survey.model_dump_json(indent=1))
