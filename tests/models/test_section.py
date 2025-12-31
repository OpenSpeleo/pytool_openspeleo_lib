from __future__ import annotations

import datetime
import sys
import uuid

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.enums import ArianeProfileType
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.models import Section
from openspeleo_lib.models import Shot


def test_valid_section():
    """
    Test creating a valid Section instance.
    """
    shot = Shot(
        id_stop=1,
        name="TEST_SHOT",
        azimuth=45.0,
        closure_to_id=-1,
        color="#FFFFFF",
        comment="Test comment",
        depth=100.0,
        depth_start=10.0,
        excluded=False,
        id_start=2,
        inclination=5.0,
        latitude=40.7128,
        length=50.0,
        locked=True,
        longitude=-74.0060,
        profiletype=ArianeProfileType.BISECTION,
        shot_type=ArianeShotType.REAL,
        shape=None,
        left=0.0,
        right=0.0,
        up=0.0,
        down=0.0,
    )
    section = Section(
        id=uuid.uuid4(),
        name="Test Section",
        date=datetime.datetime.now(
            tz=datetime.UTC if sys.version_info >= (3, 11) else datetime.timezone.utc
        ).date(),
        explorers=["Explorer1", "Explorer2"],
        surveyors=["Surveyor1", "Surveyor2"],
        shots=[shot],
        comment="Test comment",
        compass_format="DDDDUDLRLADN",
        correction=[0.1, 0.2],
        correction2=[0.3, 0.4],
        declination=0.0,
    )
    assert section.name == "Test Section"
    assert (
        section.date
        == datetime.datetime.now(
            tz=datetime.UTC if sys.version_info >= (3, 11) else datetime.timezone.utc
        ).date()
    )
    assert section.explorers == ["Explorer1", "Explorer2"]
    assert section.surveyors == ["Surveyor1", "Surveyor2"]
    assert section.shots == [shot]
    assert section.comment == "Test comment"
    assert section.compass_format == "DDDDUDLRLADN"
    assert section.correction == [0.1, 0.2]
    assert section.correction2 == [0.3, 0.4]
    assert section.declination == 0.0


def test_invalid_section():
    """
    Test creating an invalid Section instance.
    """
    with pytest.raises(ValidationError):
        Section(
            id=1,  # Should be a UUID
            name="invalid name",  # Should match the pattern
            date="invalid",  # Should be a date
            explorers="invalid",  # Should be a list of strings
            surveyors="invalid",  # Should be a list of strings
            shots="invalid",  # Should be a list of Shot instances
            comment=123,  # Should be a string
            compass_format=123,  # Should be a string
            correction="invalid",  # Should be a list of floats
            correction2="invalid",  # Should be a list of floats
            declination="invalid",  # Should be a float
        )


@given(
    section_id=st.uuids(version=4),
    name=st.text(
        alphabet=" a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
        max_size=OSPL_SECTIONNAME_MAX_LENGTH,
    ),
    date=st.dates(),
    explorers=st.lists(st.text()),
    surveyors=st.lists(st.text()),
    shots=st.lists(
        st.builds(
            Shot,
            id_stop=st.integers(min_value=0),
            name=st.text(
                alphabet="a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
                max_size=OSPL_SHOTNAME_MAX_LENGTH,
            ),
            azimuth=st.floats(min_value=0.0, max_value=360.0, exclude_max=True),
            closure_to_id=st.integers(),
            color=st.from_regex(r"^#(?:[0-9a-fA-F]{3}){1,2}$"),
            comment=st.one_of(st.none(), st.text()),
            depth=st.floats(min_value=0.0),
            depth_start=st.floats(),
            excluded=st.booleans(),
            id_start=st.integers(),
            inclination=st.floats(),
            latitude=st.floats(min_value=-90.0, max_value=90.0),
            length=st.floats(min_value=0.0),
            locked=st.booleans(),
            longitude=st.floats(min_value=-180.0, max_value=180.0),
            profiletype=st.sampled_from(ArianeProfileType),
            shot_type=st.sampled_from(ArianeShotType),
            shape=st.one_of(
                st.none(),
                st.dictionaries(
                    keys=st.text(), values=st.one_of(st.integers(), st.text())
                ),
            ),
            left=st.floats(min_value=0.0),
            right=st.floats(min_value=0.0),
            up=st.floats(min_value=0.0),
            down=st.floats(min_value=0.0),
        )
    ),
    comment=st.text(),
    compass_format=st.text(),
    correction=st.lists(st.floats()),
    correction2=st.lists(st.floats()),
    declination=st.floats(),
)
def test_fuzzy_section(
    section_id,
    name,
    date,
    explorers,
    surveyors,
    shots,
    comment,
    compass_format,
    correction,
    correction2,
    declination,
):
    """
    Fuzzy testing for Section class using Hypothesis.
    """
    section = Section(
        id=section_id,
        name=name,
        date=date,
        explorers=explorers,
        surveyors=surveyors,
        shots=shots,
        comment=comment,
        compass_format=compass_format,
        correction=correction,
        correction2=correction2,
        declination=declination,
    )
    assert isinstance(section, Section)


if __name__ == "__main__":
    pytest.main()
