"""Artifact reference and storage primitives."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass
class ArtifactRef:
    uri: str


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._payloads: dict[str, Any] = {}
        self._next_number = 1

    def put(self, payload: Any, kind: str = "artifact") -> ArtifactRef:
        ref = ArtifactRef(uri=self._next_uri(kind))
        self._payloads[ref.uri] = deepcopy(payload)
        return ref

    def get(self, ref: ArtifactRef) -> Any:
        if ref.uri not in self._payloads:
            raise KeyError(f"Unknown artifact: {ref.uri}")
        return deepcopy(self._payloads[ref.uri])

    def _next_uri(self, kind: str) -> str:
        uri = f"memory://{kind}/{self._next_number}"
        self._next_number += 1
        return uri
