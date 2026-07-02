"""Artifact reference and storage primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ArtifactRef:
    uri: str
