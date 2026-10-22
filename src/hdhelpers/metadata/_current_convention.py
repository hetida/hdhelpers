"""Extraction of metadata following the current metadata convention

The metadata is gathered in a single pass in plain Python: the object of each metric with its
value dimensions by column, and the value dimensions shared by all metrics
("value_dimensions_shared"). The fallback chains are resolved on these objects, applying the
spec of the requested information only to the objects of the levels actually needed. Field
names and dotted paths of them are looked up without glom, since evaluating glom specs costs a
lot of time per object, which adds up for frames with many metrics.

Entries not adhering to the conventions are skipped: metrics which are no objects or whose
field named by the metric key is no string, and value dimensions which are no objects or whose
column is no string. "value_dimensions" and "value_dimensions_shared" which are no lists count
as empty, a metric key which is no string as missing, i.e. the default "id" is used.

Older metadata structures are handled by the glom specs in _specs.
"""

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from glom import Coalesce, Spec, glom

from hdhelpers.metadata._specs import INHERITED

Getter = Callable[[Any], Any]

_MISSING = object()
_DEFAULT_COALESCE_SKIP = Coalesce("any").skip


@dataclass(frozen=True)
class GatheredMetric:
    metric: dict
    value_dimensions: dict[str, dict]  # by column


@dataclass(frozen=True)
class GatheredMetadata:
    metrics: dict[str, GatheredMetric]  # by value of the field named by the metric key
    value_dimensions_shared: dict[str, dict]  # by column


def follows_current_convention(attrs: Any) -> bool:
    """Whether metadata follows the current metadata convention, i.e. has a list of metrics"""
    return isinstance(attrs, dict) and isinstance(attrs.get("metrics"), list)


def _metric_key(attrs: dict) -> str:
    dataset_metadata = attrs.get("dataset_metadata")
    metric_key = dataset_metadata.get("metric_key") if isinstance(dataset_metadata, dict) else None
    return metric_key if isinstance(metric_key, str) else "id"


def _by_column(value_dimensions: Any) -> dict[str, dict]:
    """Value dimension objects by column, the last one winning, skipping malformed ones"""
    if not isinstance(value_dimensions, list):
        return {}
    return {
        value_dimension["column"]: value_dimension
        for value_dimension in value_dimensions
        if isinstance(value_dimension, dict) and isinstance(value_dimension.get("column"), str)
    }


def gather(attrs: Any) -> GatheredMetadata | None:
    """Gather the objects of all levels, None if not following the current convention"""
    if not follows_current_convention(attrs):
        return None

    metric_key = _metric_key(attrs)
    return GatheredMetadata(
        metrics={
            metric[metric_key]: GatheredMetric(metric, _by_column(metric.get("value_dimensions")))
            for metric in attrs["metrics"]
            if isinstance(metric, dict) and isinstance(metric.get(metric_key), str)
        },
        value_dimensions_shared=_by_column(attrs.get("value_dimensions_shared")),
    )


def _simple_path(spec: Any) -> tuple[str, ...] | None:
    """The keys a spec looks up one after another, if it is just a path of dict keys

    glom splits string paths at dots, and only interprets stars besides.
    """
    if isinstance(spec, str) and "*" not in spec and "\\" not in spec:
        return tuple(spec.split("."))
    if (
        isinstance(spec, Coalesce)
        and len(spec.subspecs) == 1
        and spec.default is None
        and spec.skip is _DEFAULT_COALESCE_SKIP
    ):
        return _simple_path(spec.subspecs[0])
    return None


def getter(spec: str | Spec) -> Getter:
    """Apply spec as Coalesce(spec, default=None), without glom for paths of dict keys"""
    generic_spec = Coalesce(spec, default=None)

    def generic(obj: Any) -> Any:
        return glom(obj, generic_spec)

    path = _simple_path(spec)
    if path is None:
        return generic

    def by_path(obj: Any) -> Any:
        # glom accesses keys of dicts via item access only, so a missing key yields None.
        # Other targets, e.g. lists accessed via indices, are left to glom.
        target = obj
        for key in path:
            if type(target) is not dict:
                return generic(obj)
            if key not in target:
                return None
            target = target[key]
        return target

    return by_path


def _inherited_info(metric: dict, get: Getter) -> Any:
    # the spec is not applied if the metric does not provide inherited properties at all
    return get(metric[INHERITED]) if INHERITED in metric else None


def value_dimension_info(
    gathered: GatheredMetadata, specs: Sequence[str | Spec], include_inherited: bool
) -> defaultdict[str, defaultdict[str, Any]]:
    """Information per value dimension per metric, falling back to further specs

    The value dimensions of a metric are its own ones, "value" and the shared ones. For each
    of them, the first information which is not None is used: Each spec is applied on

    1. the value dimension itself,
    2. only for the value dimension "value": the metric,
    3. "value_dimensions_shared"

    before the next spec is tried. If include_inherited, the properties the metric inherits
    are used as last resort for the value dimension "value", again trying each spec in turn.
    """
    getters = [getter(spec) for spec in specs]
    shared_info_cache: list[dict[str, Any]] = [{} for _ in getters]

    def shared_info(index: int, column: str) -> Any:
        cache = shared_info_cache[index]
        if column not in cache:
            shared = gathered.value_dimensions_shared.get(column)
            cache[column] = None if shared is None else getters[index](shared)
        return cache[column]

    result: defaultdict[str, defaultdict[str, Any]] = defaultdict(lambda: defaultdict(lambda: None))
    for metric, gathered_metric in gathered.metrics.items():
        info_by_column: defaultdict[str, Any] = defaultdict(lambda: None)
        columns = dict.fromkeys(
            [*gathered.value_dimensions_shared, "value", *gathered_metric.value_dimensions]
        )
        for column in columns:
            value_dimension = gathered_metric.value_dimensions.get(column)
            info = None
            for index, get in enumerate(getters):
                info = get(value_dimension) if value_dimension is not None else None
                if info is None and column == "value":
                    info = get(gathered_metric.metric)
                if info is None:
                    info = shared_info(index, column)
                if info is not None:
                    break
            if info is None and include_inherited and column == "value":
                for get in getters:
                    info = _inherited_info(gathered_metric.metric, get)
                    if info is not None:
                        break
            info_by_column[column] = info
        result[metric] = info_by_column
    return result


def metric_info(
    gathered: GatheredMetadata, spec: str | Spec, include_inherited: bool
) -> dict[str, Any]:
    """Information per metric, the first one which is not None of

    1. the metric itself,
    2. its value dimension "value",
    3. the value dimension "value" in "value_dimensions_shared",
    4. if include_inherited, the properties the metric inherits.
    """
    get = getter(spec)
    shared = gathered.value_dimensions_shared.get("value")
    shared_info: Any = _MISSING

    result: dict[str, Any] = {}
    for metric, gathered_metric in gathered.metrics.items():
        info = get(gathered_metric.metric)
        if info is None:
            value_dimension = gathered_metric.value_dimensions.get("value")
            info = get(value_dimension) if value_dimension is not None else None
        if info is None and shared is not None:
            if shared_info is _MISSING:
                shared_info = get(shared)
            info = shared_info
        if info is None and include_inherited:
            info = _inherited_info(gathered_metric.metric, get)
        result[metric] = info
    return result
