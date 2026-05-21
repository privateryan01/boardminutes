from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import Attachment, Meeting

DEFAULT_MEETING_URL = "https://ccsd.community.diligentoneplatform.com/Portal/MeetingInformation.aspx?Org=Cal&Id=1678"
ALLOWED_MEETING_HOSTS = frozenset({"ccsd.community.diligentoneplatform.com"})
MAX_JSON_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024

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
        self.source_url = validate_meeting_url(source_url)
        self.base_url = _base_url(self.source_url)
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
        return self._get_json(url)

    def get_meeting_data(self, meeting_id: int | None = None) -> dict:
        meeting_id = meeting_id or meeting_id_from_url(self.source_url)
        url = urljoin(self.base_url, f"/Services/MeetingsService.svc/meetings/{meeting_id}/meetingData")
        return self._get_json(url)

    def list_meetings(self, from_date: str, to_date: str, load_all: bool = True) -> list[dict]:
        query = urlencode({"from": from_date, "to": to_date, "loadall": str(load_all).lower()})
        url = urljoin(self.base_url, f"/Services/MeetingsService.svc/meetings?{query}")
        meetings = self._get_json(url)
        if not isinstance(meetings, list):
            raise ValueError("Meeting list endpoint did not return a list.")
        return meetings

    def download_document(self, document_url: str) -> bytes:
        validated_url = validate_document_url(document_url, self.base_url)
        return self._get_bytes(validated_url, MAX_DOCUMENT_BYTES)

    def _get_json(self, url: str) -> dict | list:
        return json.loads(self._get_bytes(url, MAX_JSON_BYTES).decode("utf-8"))

    def _get_bytes(self, url: str, max_bytes: int) -> bytes:
        response = self.session.get(url, timeout=self.timeout, stream=True)
        response.raise_for_status()
        return _read_limited_response(response, max_bytes)


def meeting_id_from_url(url: str) -> int:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "Id" not in query:
        raise ValueError(f"Meeting URL is missing Id query parameter: {url}")
    return int(query["Id"][0])


def validate_meeting_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("Meeting URL must use https.")
    if parsed.username or parsed.password:
        raise ValueError("Meeting URL must not contain credentials.")
    if _effective_port(parsed) != 443:
        raise ValueError("Meeting URL must use the standard https port.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_MEETING_HOSTS:
        raise ValueError("Meeting URL must use the official CCSD Diligent board website.")
    if parsed.path.lower() != "/portal/meetinginformation.aspx":
        raise ValueError("Meeting URL must point to a Diligent meeting information page.")
    meeting_id_from_url(url)
    return url


def validate_document_url(document_url: str, base_url: str) -> str:
    parsed_url = urlparse(document_url)
    parsed_base = urlparse(base_url)
    if parsed_url.username or parsed_url.password:
        raise ValueError("Document URL must not contain credentials.")
    if parsed_url.scheme.lower() != parsed_base.scheme.lower():
        raise ValueError("Document URL must use the same scheme as the meeting website.")
    if (parsed_url.hostname or "").lower().rstrip(".") != (parsed_base.hostname or "").lower().rstrip("."):
        raise ValueError("Document URL must stay on the official meeting website.")
    if _effective_port(parsed_url) != _effective_port(parsed_base):
        raise ValueError("Document URL must use the same port as the meeting website.")
    if not re.search(r"/document/[^/?#]+", parsed_url.path):
        raise ValueError("Document URL must point to a Diligent document.")
    return document_url


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

        document_url = _same_origin_document_url(base_url, href)
        if not document_url:
            continue

        attachments.append(
            Attachment(
                item_number=item_number,
                item_title=item_title,
                attachment_name=attachment_name,
                document_id=document_id,
                document_url=document_url,
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


def _same_origin_document_url(base_url: str, href: str) -> str:
    document_url = urljoin(base_url, href)
    try:
        return validate_document_url(document_url, base_url)
    except ValueError:
        return ""


def _effective_port(parsed) -> int:
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("URL port is invalid.") from exc
    if port:
        return port
    if parsed.scheme.lower() == "https":
        return 443
    if parsed.scheme.lower() == "http":
        return 80
    return 0


def _read_limited_response(response: requests.Response, max_bytes: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            expected_length = int(content_length)
        except ValueError:
            expected_length = 0
        if expected_length > max_bytes:
            raise ValueError("Response is too large.")

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("Response is too large.")
        chunks.append(chunk)
    return b"".join(chunks)


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
