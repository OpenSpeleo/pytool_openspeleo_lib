"""Exact export regressions; normal test runs never regenerate golden assets."""

import pytest

from tests.export_goldens import ARTIFACTS
from tests.export_goldens import EXPORTS
from tests.export_goldens import FIXTURES
from tests.export_goldens import golden_name
from tests.export_goldens import read_source
from tests.export_goldens import write_export


@pytest.fixture(scope="module", params=FIXTURES, ids=[prefix for _, prefix in FIXTURES])
def source_case(request):
    filename, prefix = request.param
    original_bytes = (ARTIFACTS / filename).read_bytes()
    source = read_source(filename)
    original_model = source.model_dump_json()
    yield source, prefix
    assert source.model_dump_json() == original_model
    assert (ARTIFACTS / filename).read_bytes() == original_bytes


@pytest.mark.parametrize(
    "export",
    EXPORTS,
    ids=[export if isinstance(export, str) else export.name for export in EXPORTS],
)
def test_export_matches_golden(source_case, export, tmp_path):
    source, prefix = source_case
    name = golden_name(prefix, export)
    target = tmp_path / name
    write_export(source, export, target)
    expected = (ARTIFACTS / name).read_bytes()
    actual = target.read_bytes()
    if actual != expected:
        pytest.fail(f"{name}: export differs from its checked-in golden")
