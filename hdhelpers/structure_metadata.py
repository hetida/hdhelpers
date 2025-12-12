"""Model to represent metadata defined in https://fuseki.atlassian.net/wiki/spaces/DSB/pages/4954849313/Metadaten-Konventionen"""

import logging
from typing import Literal
from abc import abstractmethod

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Value(BaseModel):
    name: str
    value_data_type: str
    unit: str
    display_name: str | None = Field(default=None)
    short_display_name: str | None = Field(default=None)
    description: str | None = Field(default=None)


class Metric(BaseModel):
    name: str
    external_id: str
    channel_id: str
    display_name: str | None = Field(default=None)
    short_display_name: str | None = Field(default=None)
    description: str | None = Field(default=None)


class StructuredMetadata(BaseModel):
    metric: Metric
    value_dimensions: dict[str, Value]
    inherited: dict = Field(default={})
    hierarchy: dict = Field(default={})


class SingleMetricMetadata(BaseModel):
    structured_metadata: StructuredMetadata

    def _get_from_value(self, key: str) -> dict[str, str | None]:
        entry_from_value = None
        try:
            value = self.structured_metadata.value_dimensions.get("value")
            entry_from_value = getattr(value, key)
        except AttributeError:
            logger.info("No unit found in metadata.")

        return {"value": entry_from_value}

    def get_display_name(self) -> dict[str, str | None]:
        return self._get_from_value("short_display_name")

    def get_name(self) -> dict[str, str | None]:
        return self._get_from_value("name")

    def get_unit(self) -> dict[str, str | None]:
        return self._get_from_value("unit")


class DatasetMetadata(BaseModel):
    ref_interval_start_timestamp: str
    ref_interval_end_timestamp: str
    ref_interval_type: Literal[
        "left_closed", "right_open", "right_closed", "left_open", "closed", "open"
    ]
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

    def get_requested_interval_start(self) -> str:
        return self.ref_interval_start_timestamp

    def get_requested_interval_end(self) -> str:
        return self.ref_interval_end_timestamp



class MetaDataInterface(BaseModel):

    @abstractmethod
    def get_unit(self) -> dict[str, str | None]:
        raise NotImplementedError

    @abstractmethod
    def get_display_name(self) -> dict[str, str | None]:
        raise NotImplementedError

    @abstractmethod
    def get_name(self) -> dict[str, str | None]:
        raise NotImplementedError

    @abstractmethod
    def get_start(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_end(self) -> str:
        raise NotImplementedError


class SeriesMetadata(MetaDataInterface):
    dataset_metadata: DatasetMetadata
    single_metric_metadata: SingleMetricMetadata

    def get_unit(self) -> dict[str, str | None]:
        return self.single_metric_metadata.get_unit()

    def get_name(self) -> dict[str, str | None]:
        return self.single_metric_metadata.get_name()

    def get_display_name(self) -> dict[str, str | None]:
        return self.single_metric_metadata.get_display_name()

    def get_start(self) -> str:
        return self.dataset_metadata.get_requested_interval_start()

    def get_end(self) -> str:
        return self.dataset_metadata.get_requested_interval_end()


class MTSMetadata(MetaDataInterface):
    dataset_metadata: DatasetMetadata
    by_metric: dict[str, SingleMetricMetadata]

    def get_unit(self) -> dict[str, str | None]:
        return {key: value.get_unit()["value"] for key, value in self.by_metric.items()}

    def get_name(self) -> dict[str, str | None]:
        return {key: value.get_name()["value"] for key, value in self.by_metric.items()}

    def get_display_name(self) -> dict[str, str | None]:
        return {key: value.get_display_name()["value"] for key, value in self.by_metric.items()}

    def get_start(self) -> str:
        return self.dataset_metadata.get_requested_interval_start()

    def get_end(self) -> str:
        return self.dataset_metadata.get_requested_interval_end()
