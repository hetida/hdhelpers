import logging
from functools import singledispatch

import pandas as pd
import pytz

import hdhelpers

logger = logging.getLogger("hdhelpers")


@singledispatch
def _convert_to_optional_timezone(object_to_convert, to_timezone: str | None):
    """Convert object_to_convert to to_timezone if not None,
    or to its own timezone if aware
    or to UTC otherwise"""
    raise NotImplementedError(
        f"Not implemented for object_to_convert of type {type(object_to_convert).__name__}"
    )


@_convert_to_optional_timezone.register(pd.Timestamp | pd.DatetimeIndex)
def _[T: (pd.Timestamp, pd.DatetimeIndex)](object_to_convert: T, to_timezone: str | None) -> T:
    if to_timezone is None:
        if object_to_convert.tz is None:
            return object_to_convert.tz_localize("UTC")
        return object_to_convert
    if object_to_convert.tz is None:
        return object_to_convert.tz_localize(to_timezone)
    return object_to_convert.tz_convert(to_timezone)


@_convert_to_optional_timezone.register
def _(object_to_convert: pd.Series, to_timezone: str | None) -> pd.Series:
    if to_timezone is None:
        if object_to_convert.dt.tz is None:
            return object_to_convert.dt.tz_localize("UTC")
        return object_to_convert
    if object_to_convert.dt.tz is None:
        return object_to_convert.dt.tz_localize(to_timezone)
    return object_to_convert.dt.tz_convert(to_timezone)


def modify_timezone[T: (pd.Timestamp, pd.Series, pd.DataFrame)](  # noqa: PLR0912
    object_to_convert: T,
    to_timezone: str | None = None,
    column_names: list[str] | None = None,
    convert_index: bool = True,
) -> T:
    """Converts time information of pandas objects to a certain timezone

    This function is applicable to index and/or columns of pd.Series or pd.DataFrame as well as for single pd.Timestamp objects.

    Args:
        object_to_convert (pd.Timestamp | pd.Series | pd.DataFrame): Timestamp, Series or DataFrame where timezone is modified
        to_timezone (str | None): Timezone to convert to, e.g. for German time use "Europe/Berlin". See possible timezone strings in pandas' `tz_convert` method or pytz all_timezones list. If to_timezone is not defined, the global timezone from plot_target_settings is used. .
        column_names (str | None): List of column_names to modify. For pd.Series the default behaviour is modifying the index and for pd.DataFrame the default behaviour is modifying the column "timestamp". This option is not applicable in case object_to_convert is a pd.Timestamp.
        convert_index (bool | None): Boolean that controls whether the index of pd.Dataframe or pd.Series should be transformed. Note that for a pd.Series setting this option to true results in the same output as using `column_names=None`. This option is not applicable in case `object_to_convert` is a pd.Timestamp.
    Returns:
        pd.Timestamp | pd.Series | pd.DataFrame:
            Returns the modified timezone object.

    Raises:
        TypeError: If `object_to_convert` is not a pd.Series, pd.Timestamp, pd.DataFrame.

    Code example:

    .. doctest::

        >>> from hdhelpers.helpers import modify_timezone
        >>> modified_timezone = modify_timezone(pd.to_datetime("2025-01-01T01:00:00+05:00"), to_timezone="Europe/Berlin")
        >>> int(modified_timezone.utcoffset().total_seconds())
        3600
    """

    if not isinstance(object_to_convert, pd.Timestamp | pd.Series | pd.DataFrame):
        raise TypeError(
            f"object_to_convert is {type(object_to_convert)} not pd.Series | pd.DataFrame"
        )
    if column_names is None:
        column_names = []

    try:
        if to_timezone is None:
            plot_target_settings = hdhelpers.plot_target_settings.get_plot_target_settings()
            if plot_target_settings.plot_target_timezone is not None:
                to_timezone = plot_target_settings.plot_target_timezone

        if isinstance(object_to_convert, pd.Timestamp):
            return _convert_to_optional_timezone(object_to_convert, to_timezone)

        if isinstance(object_to_convert, pd.Series):
            new_object = object_to_convert.to_frame(name=object_to_convert.name)
        else:
            new_object = object_to_convert.copy(deep=True)

        if len(column_names) == 0:
            if isinstance(object_to_convert, pd.Series):
                new_object.index = _convert_to_optional_timezone(
                    pd.to_datetime(new_object.index), to_timezone
                )
                msg = f"Converted index to datetime starting with {object_to_convert.index[0]}"
                logger.debug(msg=msg)
            elif isinstance(new_object, pd.DataFrame) and "timestamp" in new_object.columns:
                new_object["timestamp"] = _convert_to_optional_timezone(
                    pd.to_datetime(new_object["timestamp"]), to_timezone
                )
                msg = f"""Converted column "timestamp" to datetime starting with
                {object_to_convert["timestamp"][0]}"""
                logger.debug(msg=msg)

        if len(column_names) > 0:
            for column in column_names:
                new_object[column] = _convert_to_optional_timezone(
                    pd.to_datetime(new_object[column]), to_timezone
                )

        if convert_index:
            new_object.index = _convert_to_optional_timezone(
                pd.to_datetime(new_object.index), to_timezone
            )

        if not isinstance(object_to_convert, pd.Series):
            new_object.attrs = object_to_convert.attrs
            return new_object

        series_object = pd.Series(
            new_object[object_to_convert.name],
            index=new_object.index,
            name=object_to_convert.name,
        )
        series_object.attrs = object_to_convert.attrs

        return series_object

    except pytz.exceptions.UnknownTimeZoneError as exc:
        possible_timezone = pytz.all_timezones
        raise ValueError(f"""Timezone not known, please choose from {possible_timezone}""") from exc
    except (AttributeError, pytz.exceptions.NonExistentTimeError) as exc:
        raise TypeError("Entries to convert do not contain valid timestamps") from exc
    except KeyError as exc:
        exc.add_note(f"At least one column name of {column_names} not in object_to_convert")
        raise
