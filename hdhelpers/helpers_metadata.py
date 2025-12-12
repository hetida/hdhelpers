import logging

import pandas as pd
from pydantic import ValidationError

from hdhelpers.structure_metadata import MTSMetadata, SeriesMetadata

logger = logging.getLogger("hdhelpers")


def _load_mts(timeseries_object: pd.DataFrame | pd.Series) -> MTSMetadata | SeriesMetadata:
    try:
        return SeriesMetadata(**timeseries_object.attrs) # type: ignore[misc]
    except ValidationError:
        try:
            logger.debug("object does not correspond to series metadata, trying mts-metadata")
            return MTSMetadata(**timeseries_object.attrs) # type: ignore[misc]
        except ValidationError as exc2:
            logger.debug("object does not correspond to trying mts-metadata")
            raise ValidationError("Metadata does not follow convention") from exc2



def get_unit(timeseries_object: pd.DataFrame | pd.Series) -> dict[str, str | None]:
    metadata = _load_mts(timeseries_object)
    return metadata.get_unit()


def get_name(timeseries_object: pd.DataFrame | pd.Series) -> dict[str, str | None]:
    metadata = _load_mts(timeseries_object)
    return metadata.get_name()


def get_display_name(timeseries_object: pd.DataFrame | pd.Series) -> dict[str, str | None]:
    metadata = _load_mts(timeseries_object)
    return metadata.get_display_name()


def get_start(timeseries_object: pd.DataFrame | pd.Series) -> str:
    metadata = _load_mts(timeseries_object)
    return metadata.get_start()


def get_end(timeseries_object: pd.DataFrame | pd.Series) -> str:
    metadata = _load_mts(timeseries_object)
    return metadata.get_end()
