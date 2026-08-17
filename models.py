"""Data objects shared by the UI and Maya integration layers."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AnimationFile:
    path: str
    enabled: bool = True
    status: str = "Pending"


@dataclass
class Segment:
    name: str
    source_file: str
    anim_source: str
    clip_id: int
    clip_node: str
    start: float
    end: float
    duration: float
    maya_duration: float
    gap_after: int
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def valid(self):
        return not self.errors


@dataclass
class ImportFailure:
    source_file: str
    stage: str
    message: str


@dataclass
class BatchResult:
    segments: List[Segment] = field(default_factory=list)
    failures: List[ImportFailure] = field(default_factory=list)
    stopped_early: bool = False
    playback_start: Optional[float] = None
    playback_end: Optional[float] = None
