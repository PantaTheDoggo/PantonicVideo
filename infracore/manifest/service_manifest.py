from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DependsOn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    min_version: str


class ServiceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    service_api_version: str
    implementation_version: str
    entry_point: str
    depends_on: list[DependsOn]
