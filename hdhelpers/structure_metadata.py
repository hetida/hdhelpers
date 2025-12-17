"""Model to represent metadata defined in https://fuseki.atlassian.net/wiki/spaces/DSB/pages/4954849313/Metadaten-Konventionen"""

import logging
from collections import defaultdict
from typing import Literal


from pydantic import BaseModel, Field, computed_field

logger = logging.getLogger(__name__)


class Value(BaseModel):
    name: str | None = Field(default=None)
    value_data_type: str | None = Field(default=None)
    unit: str | None = Field(default=None)
    display_name: str | None = Field(default=None)
    short_display_name: str | None = Field(default=None)
    description: str | None = Field(default=None)


class Metric(BaseModel):
    name: str | None = Field(default=None)
    external_id: str | None = Field(default=None)
    channel_id: str | None = Field(default=None)
    display_name: str | None = Field(default=None)
    short_display_name: str | None = Field(default=None)
    description: str | None = Field(default=None)


class StructuredMetadata(BaseModel):
    metric: Metric = Field(default=Metric())
    value_dimensions: dict[str, Value] = Field(default=defaultdict(lambda: None))
    inherited: dict = Field(default=defaultdict(lambda: None))
    hierarchy: dict = Field(default=defaultdict(lambda: None))

    def _get_value_dims(self) -> list[str]:
        value_dims = []
        for key in self.value_dimensions.keys():
            value_dims.append(key)
        return value_dims

    def _get_from_metric(self, key: str) -> str | None:
        entry_from_metric = None
        try:
            metric = self.metric
            entry_from_metric = getattr(metric, key)
        except AttributeError:
            logger.info("Metadata not in standard format, returning None")

        return entry_from_metric

    def _get_from_value(self, key: str) -> dict[str, str]:
        value_names = defaultdict(lambda: None)
        for dim in self._get_value_dims():
            value_names[dim] = self._get_from_value_single(key)
        return value_names

    def _get_from_value_single(self, key: str, dim: str = "value") -> str | None:
        entry_from_value = None
        try:
            value = self.value_dimensions.get(dim)
            entry_from_value = getattr(value, key)
        except AttributeError:
            logger.info("Metadata not in standard format, returning None")

        return entry_from_value

    def get_metric_name(self) -> str | None:
        return self._get_from_metric("name")

    def get_metric_display_name(self) -> str | None:
        return self._get_from_metric("display_name")

    def get_metric_short_display_name(self) -> str | None:
        return self._get_from_metric("short_display_name")

    def get_value_name(self) -> dict[str, str | None]:
        return self._get_from_value("name")

    def get_value_display_name(self) -> dict[str, str | None]:
        return self._get_from_value("display_name")

    def get_value_short_display_name(self) -> dict[str, str | None]:
        return self._get_from_value("short_display_name")

    def get_value_unit(self) -> dict[str, str | None]:
        return self._get_from_value("unit")


class DatasetMetadata(BaseModel):
    ref_interval_start_timestamp: str | None = Field(default=None)
    ref_interval_end_timestamp: str | None = Field(default=None)
    ref_interval_type: Literal["left_closed", "right_open", "right_closed", "left_open", "closed", "open"] | None = Field(default=None)
    ref_metric: str | None = Field(default=None)
    ref_data_frequency: str | None = Field(default=None)
    ref_data_frequency_offset: str | None = Field(default=None)
    invalidation_interval_start: str | None = Field(default=None)
    invalidation_interval_end: str | None = Field(default=None)
    invalidation_interval_type: str | None = Field(default=None)
    invalidate_dataset: str | None = Field(default=None)
    delete_invalidated: str | None = Field(default=None)
    only_invalidate: bool | None = Field(default=False)
    ref_dataset_discrete: str | None = Field(default=None)
    invalidation_timestamp: str | None = Field(default=None)
    new_data_invalidation_date: str | None = Field(default=None)

    def get_requested_interval_start(self) -> str | None:
        return self.ref_interval_start_timestamp

    def get_requested_interval_end(self) -> str | None:
        return self.ref_interval_end_timestamp




class SeriesMetadata(BaseModel):
    dataset_metadata: DatasetMetadata = Field(default=DatasetMetadata())
    by_metric: dict[str, StructuredMetadata] = Field(default=defaultdict(lambda: StructuredMetadata()))
    METRIC_KEY: str = "series"
    VALUE_KEY:str = "value"

    @computed_field
    @property
    def metric(self) -> StructuredMetadata:
        return self.by_metric[self.METRIC_KEY]

    def get_unit(self) -> str | None:
        return self.metric.get_value_unit()[self.VALUE_KEY]

    def get_name(self) -> str | None:
        name = self.metric.get_metric_name()
        if not name:
            name = self.metric.get_value_name()[self.VALUE_KEY]
        return name

    def get_display_name(self) -> str | None:
        name = self.metric.get_metric_display_name()
        if not name:
            name = self.metric.get_value_display_name()[self.VALUE_KEY]
        if not name:
            name = self.get_name()
        return name

    def get_short_display_name(self) -> str | None:
        name = self.metric.get_metric_short_display_name()
        if not name:
            name = self.metric.get_value_short_display_name()[self.VALUE_KEY]
        if not name:
            name = self.get_display_name()
        if not name:
            name = self.get_name()
        return name

    def get_start(self) -> str:
        return self.dataset_metadata.get_requested_interval_start()

    def get_end(self) -> str:
        return self.dataset_metadata.get_requested_interval_end()


class MTSMetadata(BaseModel):
    dataset_metadata: DatasetMetadata = Field(default=DatasetMetadata())
    by_metric: dict[str, StructuredMetadata] = Field(default=defaultdict(lambda: StructuredMetadata()))

    def get_unit(self) -> dict[str, str | None]:
        return {key: value.get_value_unit()["value"] for key, value in self.by_metric.items()}

    def get_start(self) -> str:
        return self.dataset_metadata.get_requested_interval_start()

    def get_end(self) -> str:
        return self.dataset_metadata.get_requested_interval_end()
