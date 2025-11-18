import pytest
from pydantic import ValidationError

from hdhelpers.structure_metadata import MTSMetadata, SeriesMetadata


def test_init_series_metadata():
    metadata_for_series = {
        "dataset_metadata": {
            "ref_interval_start_timestamp": "2025-11-05T13:28:00Z",
            "ref_interval_end_timestamp": "2025-11-05T13:28:00Z",
            "ref_interval_type": "closed",
            "ref_metric": "Wasserstand Ruhr Meschede",
            "ref_data_frequency": None,
            "ref_data_frequency_offset": None,
            "invalidation_interval_start": None,
            "invalidation_interval_end": None,
            "invalidation_interval_type": None,
            "invalidate_dataset": None,
            "delete_invalidated": None,
            "only_invalidate": None,
            "ref_dataset_discrete": None,
            "invalidation_timestamp": None,
            "new_data_invalidation_date": None,
        },
        "single_metric_metadata": {
            "structured_metadata": {
                "metric": {
                    "name": "Wasserstand Ruhr Meschede",
                    "display_name": None,
                    "short_display_name": None,
                    "description": None,
                    "unit": "m³/s",
                    "value_data_type": None,
                    "external_id": "wasserstand.ruhr.meschede2",
                    "channel_id": "303fc49a-b515-4fbc-b4fd-70594f053f58",
                },
                "inherited": {
                    "Stationsname": "Meschede (Ruhr)",
                    "Latitude": 51.347759,
                    "Longitude": 8.280575,
                },
                "value_dimensions": {
                    "value": {
                        "name": "Wasserstand Ruhr Meschede",
                        "display_name": None,
                        "short_display_name": None,
                        "description": None,
                        "unit": "m³/s",
                        "value_data_type": "float",
                    }
                },
            }
        },
    }

    try:
        SeriesMetadata(**metadata_for_series)
    except ValidationError:
        pytest.fail("Unexpected MyError when initializing series metadata")


def test_init_mts_metadata():
    metadata_for_mts = {
        "dataset_metadata": {
            "ref_interval_start_timestamp": "2025-11-05T13:28:00Z",
            "ref_interval_end_timestamp": "2025-11-05T13:28:00Z",
            "ref_interval_type": "closed",
            "ref_metric": "Wasserstand Ruhr Meschede",
            "ref_data_frequency": None,
            "ref_data_frequency_offset": None,
            "invalidation_interval_start": None,
            "invalidation_interval_end": None,
            "invalidation_interval_type": None,
            "invalidate_dataset": None,
            "delete_invalidated": None,
            "only_invalidate": None,
            "ref_dataset_discrete": None,
            "invalidation_timestamp": None,
            "new_data_invalidation_date": None,
        },
        "by_metric": {
            "key1": {
                "structured_metadata": {
                    "metric": {
                        "name": "Wasserstand Ruhr Meschede",
                        "display_name": None,
                        "short_display_name": None,
                        "description": None,
                        "unit": "m³/s",
                        "value_data_type": None,
                        "external_id": "wasserstand.ruhr.meschede2",
                        "channel_id": "303fc49a-b515-4fbc-b4fd-70594f053f58",
                    },
                    "inherited": {
                        "Stationsname": "Meschede (Ruhr)",
                        "Latitude": 51.347759,
                        "Longitude": 8.280575,
                    },
                    "value_dimensions": {
                        "value": {
                            "name": "Wasserstand Ruhr Meschede",
                            "display_name": None,
                            "short_display_name": None,
                            "description": None,
                            "unit": "m³/s",
                            "value_data_type": "float",
                        }
                    },
                }
            },
            "key2": {
                "structured_metadata": {
                    "metric": {
                        "name": "Wasserstand Ruhr Meschede",
                        "display_name": None,
                        "short_display_name": None,
                        "description": None,
                        "unit": "m³/s",
                        "value_data_type": None,
                        "external_id": "wasserstand.ruhr.meschede2",
                        "channel_id": "303fc49a-b515-4fbc-b4fd-70594f053f58",
                    },
                    "inherited": {
                        "Stationsname": "Meschede (Ruhr)",
                        "Latitude": 51.347759,
                        "Longitude": 8.280575,
                    },
                    "value_dimensions": {
                        "value": {
                            "name": "Wasserstand Ruhr Meschede",
                            "display_name": None,
                            "short_display_name": None,
                            "description": None,
                            "unit": "m³/s",
                            "value_data_type": "float",
                        }
                    },
                }
            },
        },
    }

    try:
        MTSMetadata(**metadata_for_mts)
    except ValidationError:
        pytest.fail("Unexpected Error when initializing mts metadata")
