from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import School

SUFFIX_EXPANSIONS = {
    " ES": " ELEMENTARY SCHOOL",
    " MS": " MIDDLE SCHOOL",
    " JHS": " JUNIOR HIGH SCHOOL",
    " HS": " HIGH SCHOOL",
    " CTA": " CAREER TECHNICAL ACADEMY",
}


def normalize_name(value: str) -> str:
    text = value.upper()
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def alias_variants(alias: str) -> set[str]:
    normalized = normalize_name(alias)
    variants = {normalized}
    for short, expanded in SUFFIX_EXPANSIONS.items():
        short_norm = normalize_name(short)
        expanded_norm = normalize_name(expanded)
        if normalized.endswith(short_norm):
            variants.add(normalized[: -len(short_norm)].rstrip() + expanded_norm)
        if normalized.endswith(expanded_norm):
            variants.add(normalized[: -len(expanded_norm)].rstrip() + short_norm)
    return {variant.strip() for variant in variants if variant.strip()}


def load_schools(path: Path) -> list[School]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        schools: list[School] = []
        for row in reader:
            aliases = [row["display_name"], *row["aliases"].split(";")]
            schools.append(
                School(
                    school_id=row["school_id"].strip(),
                    cluster=row["cluster"].strip(),
                    display_name=row["display_name"].strip(),
                    aliases=tuple(dict.fromkeys(alias.strip() for alias in aliases if alias.strip())),
                    source_image=row["source_image"].strip(),
                )
            )
    return schools


def save_schools(path: Path, schools: list[School]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["school_id", "cluster", "display_name", "aliases", "source_image"])
        writer.writeheader()
        for school in sorted(schools, key=lambda item: (*cluster_sort_key(item.cluster), item.display_name.lower())):
            writer.writerow(
                {
                    "school_id": school.school_id,
                    "cluster": school.cluster,
                    "display_name": school.display_name,
                    "aliases": ";".join(school.aliases),
                    "source_image": school.source_image,
                }
            )


def cluster_sort_key(cluster: str) -> tuple[int, int, str]:
    text = str(cluster or "").strip()
    match = re.search(r"\b(?:cluster\s*)?(\d+)\b", text, re.I)
    if match:
        return (0, int(match.group(1)), text.lower())
    return (1, 0, text.lower())


def school_id_from_name(display_name: str, existing_ids: set[str] | None = None) -> str:
    existing_ids = existing_ids or set()
    base = normalize_name(display_name).lower().replace(" ", "_")
    base = re.sub(r"[^a-z0-9_]+", "", base).strip("_") or "school"
    candidate = base
    index = 2
    while candidate in existing_ids:
        candidate = f"{base}_{index}"
        index += 1
    return candidate


def compiled_school_aliases(schools: list[School]) -> list[tuple[School, str, str]]:
    compiled: list[tuple[School, str, str]] = []
    for school in schools:
        for alias in school.aliases:
            for variant in alias_variants(alias):
                if _skip_bare_alias(alias, variant):
                    continue
                compiled.append((school, alias, variant))
    compiled.sort(key=lambda item: len(item[2]), reverse=True)
    return compiled


def _skip_bare_alias(alias: str, normalized_variant: str) -> bool:
    if len(normalized_variant.split()) != 1:
        return False
    stripped = alias.strip()
    if stripped.isupper() and len(stripped) >= 4:
        return False
    return True
