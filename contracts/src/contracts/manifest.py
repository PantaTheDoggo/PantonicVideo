from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RequiredService(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    min_version: str


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    contracts_min_version: str
    author: str
    description: str
    entry_point: str
    required_services: list[RequiredService]
    inputs: list[str]
    outputs: list[str]
    permissions: list[str]
