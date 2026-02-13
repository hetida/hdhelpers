from hdhelpers.metadata import (
    get_display_names,
    get_measurements,
    get_metric_info,
    get_series_display_name,
    get_series_measurement,
    get_series_name,
    get_series_short_display_name,
    get_series_unit,
    get_units,
)

def test_get_units_mts_old_format(empty_mts_with_old_attr):
    units_by_metric_by_value_dimension = get_units(empty_mts_with_old_attr)

    # get values
    assert units_by_metric_by_value_dimension["test_channel"]["value"] == "l/min"
    assert units_by_metric_by_value_dimension["some_other_metric"]["value"] == "l"

    # ensure that default dict is used in case of missing entry
    assert units_by_metric_by_value_dimension["SOME"]["SOME"] is None # is a default dict


def test_get_units_mts_new_format_1(empty_mts_with_attr):

    measurements_by_metric_by_value_dimension = get_measurements(empty_mts_with_attr)

    assert measurements_by_metric_by_value_dimension["first"]["temp"] == "temperature"
    assert measurements_by_metric_by_value_dimension["first"]["value"] is None
    assert measurements_by_metric_by_value_dimension["first"]["pressure"] == "pressure"
    assert measurements_by_metric_by_value_dimension["first"]["NOT OCCURING"] is None
    assert measurements_by_metric_by_value_dimension["NOT OCCURING"]["value"] is None

    assert measurements_by_metric_by_value_dimension["second"]["temp"] == "temperature"

    assert measurements_by_metric_by_value_dimension["third"]["value"] == "height"
    assert measurements_by_metric_by_value_dimension["third"]["pressure"] == "pressure"


def test_get_units_mts_new_format_2(empty_mts_with_attr):

    units_by_metric_by_value_dimension = get_units(empty_mts_with_attr)

    assert units_by_metric_by_value_dimension["first"]["temp"] == "C"
    assert units_by_metric_by_value_dimension["first"]["value"] == "m"
    assert units_by_metric_by_value_dimension["first"]["NOT OCCURING"] is None
    assert units_by_metric_by_value_dimension["NOT OCCURING"]["value"] is None

    assert units_by_metric_by_value_dimension["second"]["temp"] == "C"
    assert units_by_metric_by_value_dimension["second"]["value"] is None

    assert units_by_metric_by_value_dimension["third"]["pressure"] == "bar"
    assert units_by_metric_by_value_dimension["third"]["value"] is None

    assert units_by_metric_by_value_dimension["fourth"]["pressure"] == "Pa"
    assert units_by_metric_by_value_dimension["fourth"]["value"] == "l"

    assert units_by_metric_by_value_dimension["fifth"]["pressure"] == "bar"
    assert units_by_metric_by_value_dimension["fifth"]["value"] == "m^3"


def test_get_units_mts_new_format_3(empty_mts_with_attr):

    empty_mts_with_attr.attrs["dataset_metadata"]["metric_key"] = ("external_id")
    units_by_metric_by_value_dimension = get_units(empty_mts_with_attr)

    assert units_by_metric_by_value_dimension["external_first"]["temp"] == "C"
    assert units_by_metric_by_value_dimension["external_first"]["value"] == "m"
    assert units_by_metric_by_value_dimension["external_first"]["NOT OCCURING"] is None
    assert units_by_metric_by_value_dimension["NOT OCCURING"]["value"] is None

    assert units_by_metric_by_value_dimension["external_second"]["temp"] == "C"
    assert units_by_metric_by_value_dimension["external_second"]["value"] is None

    assert units_by_metric_by_value_dimension["external_third"]["pressure"] == "bar"
    assert units_by_metric_by_value_dimension["external_third"]["value"] is None

    assert units_by_metric_by_value_dimension["external_fourth"]["pressure"] == "Pa"
    assert units_by_metric_by_value_dimension["external_fourth"]["value"] == "l"

    assert units_by_metric_by_value_dimension["external_fifth"]["pressure"] == "bar"
    assert units_by_metric_by_value_dimension["external_fifth"]["value"] == "m^3"


def test_get_multitsframe_display_names_from_metadata_with_value_dimensions(empty_mts_with_attr):

    display_names_by_metric_by_value_dimension = get_display_names(empty_mts_with_attr)

    assert display_names_by_metric_by_value_dimension["first"]["temp"] is None
    assert display_names_by_metric_by_value_dimension["first"]["value"] == "first display name"
    assert (
        display_names_by_metric_by_value_dimension["first"]["pressure"]
        == "shared value_dimension pressure name"
    )

    assert display_names_by_metric_by_value_dimension["first"]["NOT OCCURING"] is None
    assert display_names_by_metric_by_value_dimension["NOT OCCURING"]["value"] is None

    assert display_names_by_metric_by_value_dimension["second"]["value"] == "second name"
    assert display_names_by_metric_by_value_dimension["second"]["temp"] is None

    assert display_names_by_metric_by_value_dimension["third"]["pressure"] == "thirds's pressure"
    assert display_names_by_metric_by_value_dimension["third"]["temp"] is None


def test_get_metric_info(empty_mts_with_attr):

    external_ids_by_metric = get_metric_info(empty_mts_with_attr, "external_id")

    assert external_ids_by_metric["UNKNOWN"] is None
    assert external_ids_by_metric["first"] == "external_first"
    assert external_ids_by_metric["second"] == "external_second"


def test_series_unit(empty_series_with_attr):
    assert get_series_unit(empty_series_with_attr) == "m"

    assert get_series_name(empty_series_with_attr) == "first name"
    assert get_series_display_name(empty_series_with_attr) == "first name"
    assert get_series_short_display_name(empty_series_with_attr) == "first name"

    assert get_series_measurement(empty_series_with_attr) is None


def test_series_unit_old(empty_series_with_old_attr):

    assert get_series_unit(empty_series_with_old_attr) == "C°"

    assert get_series_name(empty_series_with_old_attr) == "Muster Channel"
    assert get_series_display_name(empty_series_with_old_attr) == "Muster Channel"
    assert get_series_short_display_name(empty_series_with_old_attr) == "muster"

    assert get_series_measurement(empty_series_with_old_attr) is None
