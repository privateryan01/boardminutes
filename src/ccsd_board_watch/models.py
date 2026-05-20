from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class School:
    school_id: str
    cluster: str
    display_name: str
    aliases: tuple[str, ...]
    source_image: str


@dataclass(frozen=True)
class Attachment:
    item_number: str
    item_title: str
    attachment_name: str
    document_id: str
    document_url: str
    movement_type: str


@dataclass(frozen=True)
class Meeting:
    meeting_id: int
    meeting_name: str
    meeting_date: str
    source_url: str
    meeting_type: str = ""


@dataclass
class Finding:
    finding_id: str
    meeting_id: int
    meeting_name: str
    meeting_date: str
    board_meeting_url: str
    item_number: str
    item_title: str
    movement_type: str
    school_id: str
    school_name: str
    cluster: str
    matched_alias: str
    person_name: str
    effective_date: str
    reason: str
    attachment_name: str
    source_url: str
    context: str
    matched_line_number: int = 0
    context_line_start: int = 0
    context_line_end: int = 0
    source_pdf_path: str = ""
    source_text_path: str = ""
    confidence: str = "medium"
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
