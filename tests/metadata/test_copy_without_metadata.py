import pandas as pd
import pytest

from hdhelpers.metadata import copy_without_metadata


class NotCopyable:
    """Metadata which fails if it is copied"""

    def __deepcopy__(self, memo):
        raise AssertionError("The metadata was copied")


@pytest.mark.parametrize(
    "data",
    [
        pd.DataFrame({"metric": ["a", "b"], "value": [1.0, 2.0]}),
        pd.Series([1.0, 2.0], index=pd.date_range("2026-01-01", periods=2, tz="UTC"), name="a"),
    ],
)
def test_copy_without_metadata(data):
    metadata = {"metrics": [{"id": "a"}], "not copyable": NotCopyable()}
    data.attrs = metadata

    copy = copy_without_metadata(data)

    assert copy.attrs == {}
    assert data.attrs == metadata
    # comparing the data creates objects from it, which would copy its metadata
    data.attrs = {}
    pd.testing.assert_index_equal(copy.index, data.index)
    if isinstance(data, pd.Series):
        assert copy.name == data.name
        pd.testing.assert_series_equal(copy, data, check_flags=False)
    else:
        pd.testing.assert_frame_equal(copy, data, check_flags=False)


def test_changing_the_copy_does_not_change_the_data():
    data = pd.DataFrame({"value": [1.0, 2.0]})
    data.attrs = {"metrics": []}

    copy = copy_without_metadata(data)
    copy.loc[0, "value"] = -1.0

    assert data.loc[0, "value"] == 1.0


def test_copy_without_metadata_requires_series_or_dataframe():
    with pytest.raises(TypeError):
        copy_without_metadata([1.0, 2.0])
