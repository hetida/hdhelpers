"""Metadata of the conventions attached to pandas objects as model

The runtime of the hetida designer parses the metadata of each workflow input once and attaches
the model under attrs["hd_metadata"] (META_KEY), in place of the keys of the conventions
("dataset_metadata", "metrics", "value_dimensions_shared"). Other keys of attrs stay as they are.

pandas deep-copies attrs for (almost) every object derived from another one. The models are
immutable and return themselves when copied, so that all derived objects share the model
instead of copying the metadata.

Component code reads the metadata via read_metadata and attaches a changed version (see the
with_* methods of the models) to its own result via set_metadata. Everything serializing attrs
to JSON needs attrs_to_json, since the model is no JSON value.
"""

from collections.abc import Mapping
from typing import Any, Literal, overload

import pandas as pd
from pydantic import ValidationError

from hdhelpers.metadata.conventions import (
    METADATA_MODELS,
    MetadataConventionError,
    MetadataConventionIssue,
    MetadataIssueSeverity,
    MultiTSFrameMetadata,
    SeriesMetadata,
    SingleTSFrameMetadata,
    TimeseriesDataType,
    _TimeseriesMetadataBase,
    check_metadata_conventions,
)

META_KEY = "hd_metadata"

# the top-level keys of attrs which belong to the conventions, i.e. the fields of the models
CONVENTION_KEYS = frozenset(
    field for model in METADATA_MODELS.values() for field in model.model_fields
)

AnyMetadata = SeriesMetadata | SingleTSFrameMetadata | MultiTSFrameMetadata


def infer_data_type(obj: pd.Series | pd.DataFrame) -> TimeseriesDataType:
    """SERIES for a Series, MULTITSFRAME for a frame with a "metric" column, else SINGLETSFRAME"""
    if isinstance(obj, pd.Series):
        return "SERIES"
    return "MULTITSFRAME" if "metric" in obj.columns else "SINGLETSFRAME"


def _convention_attrs(attrs: Mapping[Any, Any]) -> dict[str, Any]:
    return {key: value for key, value in attrs.items() if key in CONVENTION_KEYS}


def attach_metadata(
    obj: pd.Series | pd.DataFrame, data_type: TimeseriesDataType | None = None
) -> AnyMetadata | None:
    """Parse metadata in attrs and attach the resulting immutable model.

    Replace convention fields with attrs["hd_metadata"]; preserve other attrs. An already
    attached model is returned unchanged.

    Args:
        obj: Series or DataFrame to update in place.
        data_type:
            Convention for raw attrs, or None to infer it; see
            :ref:`metadata-type-selection`. Used only when no model is attached.

    Returns:
        SeriesMetadata | SingleTSFrameMetadata | MultiTSFrameMetadata | None:
            Attached model, or None for absent/invalid metadata. Failure leaves attrs
            unchanged.

    Code example:

    Using :ref:`metadata-example-data`, attach a model while preserving unrelated attrs:

    .. doctest:: metadata.attach_metadata

        >>> data = series.copy()
        >>> data.attrs["source"] = "example"
        >>> meta = md.attach_metadata(data)
        >>> meta.unit()
        'm'
        >>> sorted(data.attrs)
        ['hd_metadata', 'source']
        >>> md.read_metadata(data) is meta
        True
        >>> md.attach_metadata(data) is meta
        True
        >>> md.attach_metadata(pd.Series([1.0])) is None
        True
    """
    attached = obj.attrs.get(META_KEY)
    if isinstance(attached, _TimeseriesMetadataBase):
        return attached  # type: ignore[return-value]
    convention_attrs = _convention_attrs(obj.attrs)
    if len(convention_attrs) == 0:
        return None
    model = METADATA_MODELS[data_type or infer_data_type(obj)]
    try:
        meta = model.model_validate(convention_attrs)
    except ValidationError:
        return None
    obj.attrs = {key: value for key, value in obj.attrs.items() if key not in CONVENTION_KEYS} | {
        META_KEY: meta
    }
    return meta  # type: ignore[return-value]


@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: Literal["SERIES"], *, required: Literal[True]
) -> SeriesMetadata: ...
@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: Literal["SERIES"], *, required: bool = False
) -> SeriesMetadata | None: ...
@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: Literal["SINGLETSFRAME"], *, required: Literal[True]
) -> SingleTSFrameMetadata: ...
@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: Literal["SINGLETSFRAME"], *, required: bool = False
) -> SingleTSFrameMetadata | None: ...
@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: Literal["MULTITSFRAME"], *, required: Literal[True]
) -> MultiTSFrameMetadata: ...
@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: Literal["MULTITSFRAME"], *, required: bool = False
) -> MultiTSFrameMetadata | None: ...
@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: None = None, *, required: Literal[True]
) -> AnyMetadata: ...
@overload
def read_metadata(
    obj: pd.Series | pd.DataFrame, data_type: None = None, *, required: bool = False
) -> AnyMetadata | None: ...
def read_metadata(
    obj: pd.Series | pd.DataFrame,
    data_type: TimeseriesDataType | None = None,
    *,
    required: bool = False,
) -> AnyMetadata | None:
    """Read metadata as a model without changing the input.

    Reuse an attached model; otherwise parse convention fields in attrs.

    Args:
        obj: Series or DataFrame to read.
        data_type:
            Expected convention. None keeps an attached model's type or infers it for raw
            attrs; see :ref:`metadata-type-selection`.
        required:
            If True, raise on missing, invalid or wrong-type metadata instead of returning
            None.

    Returns:
        SeriesMetadata | SingleTSFrameMetadata | MultiTSFrameMetadata | None:
            Attached or newly parsed model; None for missing, invalid or wrong-type
            metadata.

    Raises:
        MetadataConventionError: Metadata cannot be returned and required=True.

    Code example:

    Using :ref:`metadata-example-data`, read a model without changing the original attrs:

    .. doctest:: metadata.read_metadata

        >>> meta = md.read_metadata(series, required=True)
        >>> meta.unit()
        'm'
        >>> "hd_metadata" in series.attrs
        False
        >>> missing = pd.Series([1.0])
        >>> md.read_metadata(missing) is None
        True
        >>> try:
        ...     md.read_metadata(missing, required=True)
        ... except md.MetadataConventionError as error:
        ...     print(error.issues[0].message)
        No metadata in attrs.
    """
    attached = obj.attrs.get(META_KEY)
    if isinstance(attached, _TimeseriesMetadataBase):
        if data_type is None or attached._data_type == data_type:
            return attached  # type: ignore[return-value]
        _no_metadata(
            required,
            f"The attached metadata is {attached._data_type} metadata, not {data_type} metadata.",
        )
        return None

    convention_attrs = _convention_attrs(obj.attrs)
    if len(convention_attrs) == 0:
        _no_metadata(required, "No metadata in attrs.")
        return None
    data_type = data_type or infer_data_type(obj)
    try:
        return METADATA_MODELS[data_type].model_validate(convention_attrs)  # type: ignore[return-value]
    except ValidationError as e:
        if not required:
            return None
        issues = [
            issue
            for issue in check_metadata_conventions(convention_attrs, data_type)
            if issue.severity == MetadataIssueSeverity.ERROR
        ]
        raise MetadataConventionError(issues) from e


def _no_metadata(required: bool, message: str) -> None:
    """None, or with required raise a MetadataConventionError"""
    if required:
        raise MetadataConventionError(
            [
                MetadataConventionIssue(
                    severity=MetadataIssueSeverity.ERROR, location="", message=message
                )
            ]
        )


def set_metadata(obj: pd.Series | pd.DataFrame, meta: AnyMetadata) -> None:
    """Attach the supplied metadata model to a result object.

    Store it under attrs["hd_metadata"], replacing convention fields and preserving
    unrelated attrs.

    Args:
        obj: Result Series or DataFrame created by your component; updated in place.
        meta: Validated metadata model; shared without copying or revalidation.

    Returns:
        None: Updates obj in place.

    Code example:

    Convert the metre values from :ref:`metadata-example-data` to centimetres and set matching
    metadata on the result. The original metadata stays unchanged:

    .. doctest:: metadata.set_metadata

        >>> meta = md.read_metadata(series, required=True)
        >>> result = series * 100
        >>> changed = meta.with_value_dimension(None, "value", unit="cm")
        >>> md.set_metadata(result, changed)
        >>> md.get_series_unit(result), md.get_series_unit(series)
        ('cm', 'm')
        >>> md.read_metadata(result) is changed
        True
    """
    obj.attrs = {key: value for key, value in obj.attrs.items() if key not in CONVENTION_KEYS} | {
        META_KEY: meta
    }


def attrs_to_json(attrs: Mapping[Any, Any]) -> dict[Any, Any]:
    """Replace attached metadata with its JSON fields in a new attrs dictionary.

    Keep unrelated attrs as-is. Omit optional metadata fields set to None or their defaults.

    Args:
        attrs: Pandas attrs mapping; left unchanged.

    Returns:
        dict[Any, Any]:
            Dictionary for json.dumps or export. Unrelated attrs must also be
            JSON-compatible.

    Code example:

    Using :ref:`metadata-example-data`, convert attached models to JSON-compatible dictionaries.
    This function returns a dictionary; json.dumps produces the JSON string:

    .. doctest:: metadata.attrs_to_json

        >>> import json
        >>> data = series.copy()
        >>> _ = md.attach_metadata(data)
        >>> attrs = md.attrs_to_json(data.attrs)
        >>> isinstance(attrs, dict), "hd_metadata" in attrs
        (True, False)
        >>> encoded = json.dumps(attrs)
        >>> json.loads(encoded)["metrics"][0]["value_dimensions"][0]["unit"]
        'm'
        >>> export = data.copy()
        >>> export.attrs = md.attrs_to_json(export.attrs)
        >>> "hd_metadata" in data.attrs, "hd_metadata" in export.attrs
        (True, False)

    The export copy can now be written with ``export.to_frame().to_parquet("series.parquet")``
    if a pandas Parquet engine is installed. The original keeps its attached model.
    """
    attached = attrs.get(META_KEY)
    if not isinstance(attached, _TimeseriesMetadataBase):
        return dict(attrs)
    rest = {key: value for key, value in attrs.items() if key != META_KEY}
    return rest | attached.model_dump(mode="json")
