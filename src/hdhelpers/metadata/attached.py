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
    """SERIES for a Series, MULTITSFRAME for a DataFrame with a "metric" column, else SINGLETSFRAME"""
    if isinstance(obj, pd.Series):
        return "SERIES"
    return "MULTITSFRAME" if "metric" in obj.columns else "SINGLETSFRAME"


def _convention_attrs(attrs: Mapping[Any, Any]) -> dict[str, Any]:
    return {key: value for key, value in attrs.items() if key in CONVENTION_KEYS}


def attach_metadata(
    obj: pd.Series | pd.DataFrame, data_type: TimeseriesDataType | None = None
) -> AnyMetadata | None:
    """Parse the metadata in obj.attrs and attach the model in place of the convention keys

    For the runtime, once per workflow input. Returns the attached model, None if attrs do not
    contain valid metadata of the data type, which then stay untouched. The data type is
    inferred from obj if not given, see infer_data_type. Metadata which is already attached
    stays as it is.
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
    """The metadata of obj as model of the conventions

    Returns the attached model. It may belong to another data type than obj, e.g. the metadata
    of a SINGLETSFRAME on a Series taken from it, unless data_type requests a specific one.
    Without attached metadata, the convention keys of attrs are parsed, as data_type or as the
    type inferred from obj (see infer_data_type), without attaching the model.

    Returns None if there is no valid metadata of the data type. With required=True, raises a
    MetadataConventionError with the issues found instead.
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
    return None


def set_metadata(obj: pd.Series | pd.DataFrame, meta: AnyMetadata) -> None:
    """Attach meta to obj, e.g. a changed version to the result of a component

    Replaces attached metadata and convention keys in obj.attrs. Only set metadata on objects
    you created: The runtime passes the same input object to all components using it.
    """
    obj.attrs = {key: value for key, value in obj.attrs.items() if key not in CONVENTION_KEYS} | {
        META_KEY: meta
    }


def attrs_to_json(attrs: Mapping[Any, Any]) -> dict[Any, Any]:
    """attrs with the attached model as convention keys, e.g. for json.dumps or to_parquet

    Optional fields which are null or have their default value are left out.
    """
    attached = attrs.get(META_KEY)
    if not isinstance(attached, _TimeseriesMetadataBase):
        return dict(attrs)
    rest = {key: value for key, value in attrs.items() if key != META_KEY}
    return rest | attached.model_dump(mode="json")
