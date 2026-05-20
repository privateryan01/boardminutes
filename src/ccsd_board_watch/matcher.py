from __future__ import annotations

import hashlib
import re

from .models import Attachment, Finding, Meeting, School
from .schools import compiled_school_aliases, normalize_name

DATE_PATTERN = re.compile(r"\b(?:\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}|TBD)\b", re.I)
HEADER_HINTS = {
    "name",
    "school and assignment",
    "location and assignment",
    "effective date",
    "hire date",
    "reason",
    "information",
    "promotions",
    "transfers",
    "reassignments",
    "page",
}
ROLE_WORDS = {
    "assistant",
    "associate",
    "principal",
    "teacher",
    "coordinator",
    "manager",
    "director",
    "specialist",
    "strategist",
    "counselor",
    "nurse",
    "psychologist",
    "facilitator",
    "administrator",
    "clerk",
    "secretary",
}
REASON_PATTERNS = [
    "Retirement",
    "Disability Retirement",
    "Death",
    "Relocation",
    "Accepted Position in Other District",
    "Accepted Position",
    "Accepted Other Position/Leaving Profession",
    "Accepted Other Position",
    "Return to School",
    "Medical",
    "Leaving Profession",
    "Dissatisfied with District",
    "Not Offered Contract",
    "Personal/Family Reasons",
    "No Reason Given",
    "Board/Admin Action",
    "No Contract/Mutual Resign",
    "No Contract",
    "Mutual Resignation",
]


def find_school_personnel_matches(text: str, attachment: Attachment, meeting: Meeting, schools: list[School]) -> list[Finding]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    normalized_lines = [normalize_name(line) for line in lines]
    aliases = compiled_school_aliases(schools)
    findings: list[Finding] = []
    seen: set[str] = set()

    for index, normalized in enumerate(normalized_lines):
        if not normalized:
            continue
        for school, alias, normalized_alias in aliases:
            if not _contains_alias(normalized, normalized_alias):
                continue

            start = max(0, index - 3)
            end = min(len(lines), index + 4)
            context_lines = lines[start:end]
            context = "\n".join(context_lines)
            person = extract_person_name(lines, index, alias)
            effective_date = extract_effective_date_for_match(lines, index, context)
            reason = extract_reason_for_match(lines, index, context)
            confidence, flags = _confidence_for(person, effective_date, attachment.movement_type)
            fingerprint_parts = [
                meeting.meeting_id,
                attachment.document_id,
                school.school_id,
                attachment.movement_type,
                person,
                effective_date,
            ]
            if not person:
                fingerprint_parts.append(context)
            fingerprint = _fingerprint(*fingerprint_parts)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)

            findings.append(
                Finding(
                    finding_id=fingerprint,
                    meeting_id=meeting.meeting_id,
                    meeting_name=meeting.meeting_name,
                    meeting_date=meeting.meeting_date,
                    board_meeting_url=meeting.source_url,
                    item_number=attachment.item_number,
                    item_title=attachment.item_title,
                    movement_type=attachment.movement_type,
                    school_id=school.school_id,
                    school_name=school.display_name,
                    cluster=school.cluster,
                    matched_alias=alias,
                    person_name=person,
                    effective_date=effective_date,
                    reason=reason,
                    attachment_name=attachment.attachment_name,
                    source_url=attachment.document_url,
                    context=context,
                    matched_line_number=index + 1,
                    context_line_start=start + 1,
                    context_line_end=end,
                    confidence=confidence,
                    flags=flags,
                )
            )
    return findings


def extract_person_name(lines: list[str], index: int, alias: str) -> str:
    current = lines[index]
    inline = _person_from_line_prefix(current, alias)
    if inline:
        return inline

    for candidate in reversed(lines[max(0, index - 3) : index]):
        candidate = candidate.strip()
        if _looks_like_header(candidate) or DATE_PATTERN.fullmatch(candidate):
            continue
        person = _leading_person_name(candidate)
        if person:
            return person
    return ""


def extract_effective_date(context: str) -> str:
    matches = DATE_PATTERN.findall(context)
    if not matches:
        return ""
    return matches[-1]


def extract_effective_date_for_match(lines: list[str], index: int, context: str) -> str:
    candidates = [lines[index]]
    candidates.extend(reversed(lines[max(0, index - 2) : index]))
    candidates.extend(lines[index + 1 : min(len(lines), index + 3)])
    for candidate in candidates:
        date = extract_effective_date(candidate)
        if date:
            return date
    return extract_effective_date(context)


def extract_reason(context: str) -> str:
    normalized = re.sub(r"\s+", " ", context)
    matches = [
        (normalized.lower().find(reason.lower()), reason)
        for reason in REASON_PATTERNS
        if normalized.lower().find(reason.lower()) >= 0
    ]
    if not matches:
        return ""
    return sorted(matches, key=lambda item: item[0])[0][1]


def extract_reason_for_match(lines: list[str], index: int, context: str) -> str:
    candidates = [lines[index]]
    candidates.extend(lines[index + 1 : min(len(lines), index + 3)])
    candidates.extend(reversed(lines[max(0, index - 2) : index]))
    for candidate in candidates:
        reason = extract_reason(candidate)
        if reason:
            return reason
    return extract_reason(context)


def _contains_alias(normalized_line: str, normalized_alias: str) -> bool:
    if len(normalized_alias) < 4:
        return False
    return re.search(rf"(^|\s){re.escape(normalized_alias)}($|\s)", normalized_line) is not None


def _person_from_line_prefix(line: str, alias: str) -> str:
    normalized_line, mapping = _normalize_with_mapping(line)
    best_position: int | None = None
    for variant in [normalize_name(alias), *sorted(_alias_text_variants(alias), key=len, reverse=True)]:
        pos = normalized_line.find(variant)
        if pos >= 0:
            best_position = pos if best_position is None else min(best_position, pos)
    if best_position is None or best_position == 0:
        return ""

    prefix_words = normalized_line[:best_position].strip().split()
    if len(prefix_words) < 2:
        return ""

    original_cut = mapping[best_position] if best_position < len(mapping) else len(line)
    original_words = re.sub(r"\s+", " ", line[:original_cut]).split()
    name_words: list[str] = []
    for word in original_words:
        cleaned = re.sub(r"[^A-Za-z'.-]", "", word)
        if not cleaned:
            continue
        if cleaned.lower() in ROLE_WORDS:
            break
        name_words.append(cleaned)
        if len(name_words) >= 5:
            break
    return _clean_person(" ".join(name_words))


def _normalize_with_mapping(value: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    mapping: list[int] = []
    pending_space = False
    for index, char in enumerate(value.upper()):
        if char.isalnum():
            if pending_space and chars:
                chars.append(" ")
                mapping.append(index)
            chars.append(char)
            mapping.append(index)
            pending_space = False
        else:
            pending_space = True
    return "".join(chars).strip(), mapping[: len(chars)]


def _leading_person_name(line: str) -> str:
    words = re.sub(r"\s+", " ", line).split()
    name_words: list[str] = []
    for word in words:
        cleaned = re.sub(r"[^A-Za-z'.-]", "", word)
        if not cleaned:
            continue
        if cleaned.lower() in ROLE_WORDS:
            break
        if cleaned.lower() in HEADER_HINTS:
            return ""
        name_words.append(cleaned)
        if len(name_words) >= 5:
            break
    return _clean_person(" ".join(name_words))


def _looks_like_header(line: str) -> bool:
    normalized = normalize_name(line).lower()
    if len(normalized.split()) <= 1 and normalized in HEADER_HINTS:
        return True
    return any(hint in normalized for hint in HEADER_HINTS)


def _clean_person(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" ,-")
    words = value.split()
    if len(words) < 2:
        return ""
    if _looks_like_school_or_org(value):
        return ""
    if any(word.lower() in HEADER_HINTS for word in words):
        return ""
    return value


def _looks_like_school_or_org(value: str) -> bool:
    normalized_words = normalize_name(value).split()
    if not normalized_words:
        return False
    school_suffixes = {"ES", "MS", "JHS", "HS", "SCHOOL", "ACADEMY", "CENTER", "UNIT", "DEPARTMENT"}
    return normalized_words[-1] in school_suffixes


def _alias_text_variants(alias: str) -> set[str]:
    normalized = normalize_name(alias)
    variants = {normalized}
    replacements = {
        " ES": " ELEMENTARY SCHOOL",
        " MS": " MIDDLE SCHOOL",
        " JHS": " JUNIOR HIGH SCHOOL",
        " HS": " HIGH SCHOOL",
    }
    for old, new in replacements.items():
        old_norm = normalize_name(old)
        new_norm = normalize_name(new)
        if normalized.endswith(old_norm):
            variants.add(normalized[: -len(old_norm)].rstrip() + new_norm)
    return variants


def _confidence_for(person: str, effective_date: str, movement_type: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    if not person:
        flags.append("person_not_parsed")
    if movement_type in {"separation", "promotion_transfer", "new_hire"} and not effective_date:
        flags.append("effective_date_not_parsed")
    if not flags:
        return "high", flags
    if person:
        return "medium", flags
    return "low", flags


def _fingerprint(*parts: object) -> str:
    digest = hashlib.sha1()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
