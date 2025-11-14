import json
import pytest

@pytest.fixture(scope="session")
def series_attrs():
    with open('tests/data/series_attrs.json', 'r') as file:
        data = json.load(file)
    return data
