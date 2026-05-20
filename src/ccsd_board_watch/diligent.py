from __future__ import annotations

import re
from html import unescape
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import Attachment, Meeting

DEFAULT_MEETING_URL = "https://ccsd.community.diligentoneplatform.com/Portal/MeetingInformation.aspx?Org=Cal&Id=1678"

PERSONNEL_KEYWORDS = (
    "personnel",
    "promotion",
    "transfer",
    "reassignment",
    "separation",
    "staffing",
    "employment",
    "new hire",
    "teacher",
    "licensed",
    "support professional",
)


class DiligentClient:
    def __init__(self, source_url: str = DEFAULT_MEETING_URL, timeout: int = 45):
        self.source_url = source_url
        self.base_url = _base_url(source_url)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                "User-Agent": "ccsd-board-watch/0.1",
            }
        )

    def get_meeting_documents_payload(self, meeting_id: int | None = None) -> dict:
        meeting_id = meeting_id or meeting_id_from_url(self.source_url)
        url = urljoin(self.base_url, f"/Services/MeetingsService.svc/meetings/{meeting_id}/meetingDocuments")
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_meeting_data(self, meeting_id: int | None = None) -> dict:
        meeting_id = meeting_id or meeting_id_from_url(self.source_url)
        url = urljoin(self.base_url, f"/Services/MeetingsService.svc/meetings/{meeting_id}/meetingData")
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def list_meetings(self, from_date: str, to_date: str, load_all: bool = True) -> list[dict]:
        query = urlencode({"from": from_date, "to": to_date, "loadall": str(load_all).lower()})
        url = urljoin(self.base_url, f"/Services/MeetingsService.svc/meetings?{query}")
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        meetings = response.json()
        if not isinstance(meetings, list):
            raise ValueError("Meeting list endpoint did not return a list.")
        return meetings

    def download_document(self, document_url: str) -> bytes:
        response = self.session.get(document_url, timeout=self.timeout)
        response.raise_for_status()
        return response.content


def meeting_id_from_url(url: str) -> int:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "Id" not in query:
        raise ValueError(f"Meeting URL is missing Id query parameter: {url}")
    return int(query["Id"][0])


def extract_meeting(source_url: str, documents_payload: dict, meeting_data: dict) -> Meeting:
    meeting_id = int(meeting_data.get("Id") or meeting_id_from_url(source_url))
    return Meeting(
        meeting_id=meeting_id,
        meeting_name=str(meeting_data.get("Name") or "Unknown meeting"),
        meeting_date=str(documents_payload.get("MeetingDateFormatted") or ""),
        source_url=source_url,
        meeting_type=str(meeting_data.get("MeetingTypeName") or meeting_data.get("TypeId") or ""),
    )


def meeting_url(base_url: str, meeting_id: int) -> str:
    return urljoin(base_url, f"/Portal/MeetingInformation.aspx?Org=Cal&Id={meeting_id}")


def extract_agenda_html(payload: dict) -> str:
    for document in payload.get("Documents", []):
        if document.get("Type") == 1 and document.get("Html"):
            return str(document["Html"])
    for document in payload.get("Documents", []):
        if document.get("AgendaCover"):
            return str(document["AgendaCover"])
    raise ValueError("No agenda HTML found in meeting documents payload.")


def extract_personnel_attachments(agenda_html: str, base_url: str, include_all: bool = False) -> list[Attachment]:
    soup = BeautifulSoup(agenda_html, "html.parser")
    attachments: list[Attachment] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        match = re.search(r"/document/([^/?#]+)", href)
        if not match:
            continue

        attachment_name = clean_text(link.get_text(" ", strip=True))
        context_node = _agenda_item_context(link)
        context_text = clean_text(context_node.get_text(" ", strip=True) if context_node else link.parent.get_text(" ", strip=True))
        item_number = _first_match(r"\b(\d+\.\d+)\b", context_text)
        item_title = _extract_item_title(context_text, item_number, attachment_name)
        movement_type = classify_item(item_title, attachment_name)

        if not include_all and not _is_personnel_item(item_title, attachment_name):
            continue

        document_id = match.group(1)
        if document_id in seen:
            continue
        seen.add(document_id)

        attachments.append(
            Attachment(
                item_number=item_number,
                item_title=item_title,
                attachment_name=attachment_name,
                document_id=document_id,
                document_url=urljoin(base_url, href),
                movement_type=movement_type,
            )
        )
    return attachments


def classify_item(item_title: str, attachment_name: str) -> str:
    haystack = f"{item_title} {attachment_name}".lower()
    if _is_written_public_comment(attachment_name):
        return "other"
    if "nonrenewal of probationary licensed contract" in haystack:
        return "separation"
    if "promotion" in haystack or "reassignment" in haystack or ("transfer" in haystack and "personnel" in haystack):
        return "promotion_transfer"
    if "separation" in haystack and "personnel" in haystack:
        return "separation"
    if "new hire" in haystack or "new hires" in haystack:
        return "new_hire"
    if ("personnel employment" in haystack or "approval to employ" in haystack) and "personnel" in haystack:
        return "new_hire"
    if "support professional" in haystack and "staffing" in haystack:
        return "staffing_report"
    if "personnel" in haystack:
        return "personnel"
    return "other"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _base_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _is_personnel_item(item_title: str, attachment_name: str) -> bool:
    haystack = f"{item_title} {attachment_name}".lower()
    if _is_written_public_comment(attachment_name) or "budget appropriation transfer" in haystack:
        return False
    movement_type = classify_item(item_title, attachment_name)
    if movement_type in {"new_hire", "promotion_transfer", "separation", "staffing_report"}:
        return True
    return False


def _extract_item_title(context_text: str, item_number: str, attachment_name: str) -> str:
    text = context_text
    if "Subject" in text:
        text = text.split("Subject", 1)[-1]
    if "Meeting" in text:
        text = text.split("Meeting", 1)[0]
    if item_number:
        text = text.split(item_number, 1)[-1]
    if "[Contact" in text:
        text = text.split("[Contact", 1)[0]
    if attachment_name and attachment_name in text:
        text = text.split(attachment_name, 1)[0]
    return clean_text(text.strip(" -:"))


def _first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def _agenda_item_context(link):
    for parent in link.parents:
        classes = parent.get("class") or []
        if "agendaorder" in classes:
            return parent
    table = link.find_parent("table")
    if table:
        return table
    return link.parent


def _is_written_public_comment(attachment_name: str) -> bool:
    return "written public comment" in attachment_name.lower()
