const DATA_URL = "data/board-data.json";
const SCHOOL_STORAGE_KEY = "ccsd-board-watch-schools-v1";
const SCHOOL_VERSION_STORAGE_KEY = "ccsd-board-watch-schools-version-v1";
const DEFAULT_SCHOOL_SET_VERSION = "cluster-1-40-v3";
const FILTER_STORAGE_KEY = "ccsd-board-watch-filters-v1";
const SNAPSHOT_STORAGE_KEY = "ccsd-board-watch-finding-snapshot-v1";
const FINDING_CACHE_STORAGE_KEY = "ccsd-board-watch-finding-cache-v1";
const FINDING_CACHE_VERSION = "findings-v2";
const LEGACY_DEFAULT_SOURCE_IMAGES = new Set([
  "henderson cluster.png",
  "North east vegas cluster.png",
  "southeast vegas cluster.png",
  "southwest vegas cluster.png",
]);
const CLUSTER_DEFAULT_SOURCE_IMAGES = new Set([
  "clusters 1-10.png",
  "clusters 11-20.png",
  "clusters 21-30.png",
  "clusters 31-40.png",
]);

const DATE_PATTERN = /\b(?:\d{1,2}\/\d{1,2}\/+\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}|TBD)\b/ig;
const HEADER_HINTS = new Set([
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
]);
const ROLE_WORDS = new Set([
  "accountant",
  "administrative",
  "assistant",
  "associate",
  "aide",
  "bus",
  "campus",
  "cashier",
  "clerical",
  "custodian",
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
  "driver",
  "emergency",
  "financial",
  "food",
  "general",
  "human",
  "instructional",
  "learning",
  "maintenance",
  "mechanic",
  "office",
  "officer",
  "para-professional",
  "paraprofessional",
  "police",
  "receptionist",
  "registrar",
  "resources",
  "returning",
  "safety",
  "school",
  "security",
  "service",
  "special",
  "student",
  "success",
  "technician",
  "technical",
  "training",
  "transportation",
  "warehouse",
]);
const REASON_RULES = [
  [/\bdisability\s+retirement\b/i, "Disability Retirement"],
  [/\bnormal\s+retirement\b/i, "Retirement"],
  [/\bretirement\b/i, "Retirement"],
  [/\bdeath\b/i, "Death"],
  [/\brelocation\b/i, "Relocation"],
  [/\baccept(?:ed)?\s+pos(?:ition)?(?:\s+[a-z]+){0,4}\s+in\s+(?:an?\s+)?other\s+district\b/i, "Accepted Position in Other District"],
  [/\baccept(?:ed)?\s+other\s+pos(?:ition)?\s*\/?\s*leave\s+prof+e?s+s?ion\b/i, "Accepted Other Position/Leaving Profession"],
  [/\baccepted\s+other\s+position\s*\/\s*leaving\s+profession\b/i, "Accepted Other Position/Leaving Profession"],
  [/\baccepted\s+other\s+position\b/i, "Accepted Other Position"],
  [/\baccepted\s+position\b/i, "Accepted Position"],
  [/\bno\s*\/?\s*negative\s+response(?:\s+[a-z]+){0,5}\s+to\s+declaration\s+of\s+intent\b/i, "No/Negative Response to Declaration of Intent"],
  [/\bfailure\s+to\s+license\b/i, "Failure to License"],
  [/\breturn\s+to\s+licensed\s+status\b/i, "Return to Licensed Status"],
  [/\breturn\s+to\s+school\b/i, "Return to School"],
  [/\bmedical(?:\s+reasons?)?\b/i, "Medical"],
  [/\bleaving\s+profession\b/i, "Leaving Profession"],
  [/\bdiss?atisfied\s+(?:w\/|with\s+)(?:the\s+)?district\b/i, "Dissatisfied with District"],
  [/\bdiss?atisfied\s+(?:w\/|with\s+)(?:the\s+)?community\b/i, "Dissatisfied with Community"],
  [/\bnot\s+offered\s+contract\b/i, "Not Offered Contract"],
  [/\bpersonal\s*\/\s*family\s+reasons?\b/i, "Personal/Family Reasons"],
  [/\bno\s+reason\s+given\b/i, "No Reason Given"],
  [/\bboard\s*\/\s*admin\s+action\b/i, "Board/Admin Action"],
  [/\bno\s+contract\s*\/\s*mutual\s+resign(?:ation)?\b/i, "No Contract/Mutual Resign"],
  [/\bmutual\s+resignation\b/i, "Mutual Resignation"],
  [/\bend\s+of\s+contract\b/i, "End of Contract"],
  [/\bvocational\s*\/\s*rehab\s*\/\s*training\b/i, "Vocational/Rehab/Training"],
  [/\bjob\s+abandonment\b/i, "Job Abandonment"],
  [/\bbroke\s+contract\b/i, "Broke Contract"],
  [/\bresignation\b/i, "Resignation"],
  [/\bno\s+contract\b/i, "No Contract"],
  [/\bpersonal\b/i, "Personal"],
];
const EMPLOYMENT_MOVEMENT_TYPES = new Set([
  "new_hire",
  "promotion_transfer",
  "separation",
]);
const TYPE_FILTER_ORDER = [
  "new_hire",
  "promotion_transfer",
  "retirement",
  "relocation",
  "separation",
];
const TYPE_FILTER_LABELS = {
  relocation: "Relocation",
  retirement: "Retirement",
  separation: "Other Separation",
};
const ORGANIZATION_WORDS = new Set([
  "agency",
  "association",
  "bank",
  "brothers",
  "center",
  "clinic",
  "college",
  "company",
  "consulting",
  "corp",
  "corporation",
  "department",
  "district",
  "foundation",
  "fundraising",
  "group",
  "hospital",
  "inc",
  "llc",
  "lp",
  "marketing",
  "office",
  "program",
  "resort",
  "services",
  "systems",
  "technologies",
  "university",
]);
const LOCATION_HISTORY_PATTERN = /\b[A-Z][A-Za-z'.-]*(?:\s+[A-Z][A-Za-z'.-]*)*,\s*[A-Z]{2}\s*\([^)]*(?:\d{4}|present|current|remote)[^)]*\)/i;
const RESUME_SECTION_PATTERN = /\b(experience|education|employment history|professional experience|work history)\b/i;
const SPLIT_NAME_BLOCK_WORDS = new Set([
  "art",
  "dance",
  "early",
  "education",
  "english",
  "explorations",
  "fifth",
  "first",
  "fourth",
  "grade",
  "history",
  "kindergarten",
  "language",
  "math",
  "music",
  "orchestra",
  "physical",
  "reading",
  "school",
  "science",
  "second",
  "special",
  "star",
  "strings",
  "study",
  "third",
]);
const NON_PERSON_NAME_PATTERN = /\b(?:and|as|at|present|current|remote|report|information|discussion|status|position|licensed|declaration|intent|division|unit|management|advocate|ledger|construction|education|institute|career|pbs|ccsd)\b/i;
const SCHOOL_SUFFIXES = new Set(["ES", "MS", "JHS", "HS", "CTA"]);
const SCHOOL_DESCRIPTOR_WORDS = new Set(["SCHOOL", "ACADEMY", "CENTER"]);
const NAME_PARTICLES = new Set(["da", "de", "del", "della", "der", "di", "du", "la", "le", "van", "von", "y"]);

const state = {
  data: null,
  schools: [],
  findings: [],
  filteredFindings: [],
  newFindingIds: new Set(),
  filters: defaultFilters(),
};

document.addEventListener("DOMContentLoaded", init);
window.addEventListener("hashchange", route);

async function init() {
  state.filters = loadSavedFilters();
  bindControls();
  try {
    const response = await fetch(DATA_URL, { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`Data request failed: ${response.status}`);
    }
    state.data = await response.json();
    state.schools = loadSavedSchools(state.data.schools || []);
    recomputeFindings();
    renderAll();
    setStatus("", "", true);
    route();
  } catch (error) {
    setStatus("Unable to load board data", error.message || String(error), false);
  }
}

function bindControls() {
  document.getElementById("yearFilter").addEventListener("change", (event) => {
    state.filters.year = event.target.value;
    persistFilters();
  });
  document.getElementById("clusterFilter").addEventListener("change", (event) => {
    state.filters.cluster = event.target.value;
    persistFilters();
  });
  document.getElementById("typeFilter").addEventListener("change", (event) => {
    state.filters.type = event.target.value;
    persistFilters();
  });
  document.getElementById("employmentDateAscending").addEventListener("click", () => {
    setEmploymentDateSort("ascending");
  });
  document.getElementById("employmentDateDescending").addEventListener("click", () => {
    setEmploymentDateSort("descending");
  });
  document.getElementById("searchFilter").addEventListener("input", (event) => {
    state.filters.search = event.target.value.trim().toLowerCase();
    persistFilters();
  });
  document.getElementById("newOnlyFilter").addEventListener("change", (event) => {
    state.filters.newOnly = event.target.checked;
    persistFilters();
  });

  document.getElementById("addSchoolForm").addEventListener("submit", addSchool);
  document.getElementById("resetSchoolsButton").addEventListener("click", resetSchools);
  document.getElementById("exportSchoolsButton").addEventListener("click", exportSchools);
  document.getElementById("importSchoolsButton").addEventListener("click", () => {
    document.getElementById("importSchoolsInput").click();
  });
  document.getElementById("importSchoolsInput").addEventListener("change", importSchools);
  document.getElementById("schoolGrid").addEventListener("submit", saveSchool);
  document.getElementById("schoolGrid").addEventListener("click", deleteSchool);
}

function defaultFilters() {
  return {
    year: "all",
    cluster: "all",
    type: "all",
    employmentDateSort: "default",
    search: "",
    newOnly: false,
  };
}

function loadSavedFilters() {
  const fallback = defaultFilters();
  try {
    const saved = JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY) || "null");
    if (!saved || typeof saved !== "object") return fallback;
    return {
      year: String(saved.year || fallback.year),
      cluster: String(saved.cluster || fallback.cluster),
      type: String(saved.type || fallback.type),
      employmentDateSort: ["ascending", "descending"].includes(saved.employmentDateSort) ? saved.employmentDateSort : fallback.employmentDateSort,
      search: String(saved.search || fallback.search).trim().toLowerCase(),
      newOnly: Boolean(saved.newOnly),
    };
  } catch {
    return fallback;
  }
}

function persistFilters() {
  saveJsonToStorage(FILTER_STORAGE_KEY, state.filters);
  renderDashboard();
}

function loadSavedSchools(defaultSchools) {
  const fallback = normalizeSchools(defaultSchools);
  try {
    const saved = JSON.parse(localStorage.getItem(SCHOOL_STORAGE_KEY) || "null");
    if (Array.isArray(saved) && saved.length) {
      const normalized = normalizeSchools(saved);
      const savedVersion = localStorage.getItem(SCHOOL_VERSION_STORAGE_KEY) || "";
      if (savedVersion === DEFAULT_SCHOOL_SET_VERSION || !isBundledDefaultSchoolSet(normalized)) {
        return normalized;
      }
    }
  } catch {
    return fallback;
  }
  return fallback;
}

function saveSchoolsToStorage() {
  saveJsonToStorage(SCHOOL_STORAGE_KEY, state.schools);
  saveTextToStorage(SCHOOL_VERSION_STORAGE_KEY, DEFAULT_SCHOOL_SET_VERSION);
}

function isLegacyDefaultSchoolSet(schools) {
  return schools.length <= 40 && schools.every((school) => LEGACY_DEFAULT_SOURCE_IMAGES.has(school.source_image));
}

function isBundledDefaultSchoolSet(schools) {
  return isLegacyDefaultSchoolSet(schools) || (
    schools.length === 319 && schools.every((school) => CLUSTER_DEFAULT_SOURCE_IMAGES.has(school.source_image))
  );
}

function normalizeSchools(schools) {
  return schools.map((school, index) => {
    const displayName = String(school.display_name || school.displayName || "").trim();
    const aliases = unique([
      displayName,
      ...(Array.isArray(school.aliases) ? school.aliases : String(school.aliases || "").split(";")),
    ].map((alias) => String(alias).trim()).filter(Boolean));
    return {
      school_id: String(school.school_id || school.schoolId || schoolIdFromName(displayName || `school ${index + 1}`)).trim(),
      cluster: String(school.cluster || "Unassigned").trim(),
      display_name: displayName || `School ${index + 1}`,
      aliases,
      source_image: String(school.source_image || ""),
    };
  });
}

function recomputeFindings() {
  const cacheKey = findingCacheKey();
  const cachedFindings = loadCachedFindings(cacheKey);
  if (cachedFindings) {
    state.findings = cachedFindings;
  } else {
    state.findings = buildFindings(state.data.attachments || [], state.schools);
    saveCachedFindings(cacheKey, state.findings);
  }
  markNewFindings();
}

function buildFindings(attachments, schools) {
  const aliases = compiledSchoolAliases(schools);
  const findings = [];
  const seen = new Set();

  for (const attachment of attachments) {
    if (!EMPLOYMENT_MOVEMENT_TYPES.has(String(attachment.movement_type || ""))) continue;
    const lines = Array.isArray(attachment.lines) ? attachment.lines.map((line) => String(line).trim()).filter(Boolean) : [];
    const normalizedLines = lines.map(normalizeName);
    for (let index = 0; index < normalizedLines.length; index += 1) {
      const normalized = normalizedLines[index];
      if (!normalized) continue;
      let matches = lineSchoolMatches(normalized, aliases);
      if (!matches.length && normalizedLines[index + 1]) {
        matches = crossLineSchoolMatches(normalized, normalizedLines[index + 1], aliases);
      }
      if (!matches.length) continue;

      if (attachment.movement_type === "promotion_transfer" && matches.length >= 2) {
        const finding = buildFindingFromMatches(attachment, lines, index, matches.slice(0, 2), seen);
        if (finding) findings.push(finding);
        continue;
      }

      for (const match of matches) {
        const finding = buildFindingFromMatches(attachment, lines, index, [match], seen);
        if (finding) findings.push(finding);
      }
    }
  }

  return dedupeFindings(findings).sort(compareFindings);
}

function dedupeFindings(findings) {
  const byKey = new Map();
  for (const finding of findings) {
    const keyParts = [
      normalizeName(finding.meeting_date),
      canonicalMeetingName(finding.meeting_name),
      normalizeName(finding.item_number),
      finding.movement_type,
      normalizeName(finding.person_name),
      normalizeName(finding.effective_date),
    ];
    if (finding.movement_type !== "promotion_transfer") {
      keyParts.push([...finding.school_ids].sort().join(">"));
    }
    const key = keyParts.join("|");
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, finding);
    } else if (finding.movement_type === "promotion_transfer") {
      byKey.set(key, mergePromotionFindings(existing, finding));
    } else if (findingQuality(finding) > findingQuality(existing)) {
      byKey.set(key, finding);
    }
  }
  return [...byKey.values()];
}

function findingQuality(finding) {
  return Number(Boolean(finding.person_name)) * 4
    + Number(Boolean(finding.effective_date)) * 2
    + Number(Boolean(finding.reason)) * 2
    + Math.min(2, finding.school_ids.length) * 2
    + Number(/\brevised\b/i.test(finding.attachment_name || ""))
    + Number(/\bamended\b/i.test(finding.meeting_name || ""));
}

function canonicalMeetingName(value) {
  return normalizeName(value).replace(/\bAMENDED\b/g, "").replace(/\s+/g, " ").trim();
}

function mergePromotionFindings(first, second) {
  const preferred = findingQuality(second) > findingQuality(first) ? second : first;
  const routeSource = preferred.school_ids.length >= 2
    ? preferred.school_ids
    : [...first.school_ids, ...second.school_ids];
  const schoolById = new Map();
  for (const finding of [first, second]) {
    finding.school_ids.forEach((schoolId, index) => {
      schoolById.set(schoolId, {
        id: schoolId,
        name: finding.school_names[index] || "",
        cluster: finding.clusters[index] || finding.cluster || "",
      });
    });
  }
  const route = unique(routeSource).slice(0, 2).map((schoolId) => schoolById.get(schoolId)).filter(Boolean);
  const merged = {
    ...preferred,
    school_id: route.map((school) => school.id).join("|"),
    school_ids: route.map((school) => school.id),
    school_name: route.map((school) => school.name).join(" -> "),
    school_names: route.map((school) => school.name),
    cluster: unique(route.map((school) => school.cluster).filter(Boolean)).join(" -> "),
    clusters: unique(route.map((school) => school.cluster).filter(Boolean)),
    from_school_id: route[0]?.id || "",
    from_school_name: route[0]?.name || "",
    from_cluster: route[0]?.cluster || "",
    to_school_id: route[1]?.id || "",
    to_school_name: route[1]?.name || "",
    to_cluster: route[1]?.cluster || "",
  };
  merged.id = fingerprint([
    merged.meeting_id,
    merged.item_number,
    merged.movement_type,
    normalizeName(merged.person_name),
    merged.school_ids.join(">"),
    normalizeName(merged.effective_date),
  ]);
  return merged;
}

function buildFindingFromMatches(attachment, lines, index, matches, seen) {
  const start = Math.max(0, index - 3);
  const end = Math.min(lines.length, index + 4);
  const contextLines = lines.slice(start, end);
  const context = contextLines.join("\n");
  const primary = matches[0];
  const destination = matches[1] || null;
  const person = extractPersonName(lines, index, primary.normalizedAlias);
  const effectiveDate = extractEffectiveDateForMatch(lines, index, context);
  const reason = extractReasonForMatch(lines, index, context);
  if (shouldRejectFinding(lines, index, context, person, effectiveDate, attachment.movement_type)) return null;

  const schoolIds = matches.map((match) => match.school.school_id);
  const schoolNames = matches.map((match) => match.school.display_name);
  const clusters = unique(matches.map((match) => match.school.cluster));
  const fingerprintParts = [
    attachment.meeting_id,
    attachment.document_id,
    schoolIds.join(">"),
    attachment.movement_type,
    person,
    effectiveDate,
  ];
  const id = fingerprint(fingerprintParts);
  if (seen.has(id)) return null;
  seen.add(id);

  return {
    id,
    meeting_id: attachment.meeting_id,
    meeting_name: attachment.meeting_name,
    meeting_date: attachment.meeting_date,
    meeting_year: attachment.meeting_year,
    board_meeting_url: attachment.board_meeting_url,
    item_number: attachment.item_number,
    item_title: attachment.item_title,
    movement_type: attachment.movement_type,
    school_id: schoolIds.join("|"),
    school_ids: schoolIds,
    school_name: schoolNames.join(" -> "),
    school_names: schoolNames,
    cluster: clusters.join(" -> "),
    clusters,
    matched_alias: matches.map((match) => match.alias).join("; "),
    from_school_id: primary.school.school_id,
    from_school_name: primary.school.display_name,
    from_cluster: primary.school.cluster,
    to_school_id: destination ? destination.school.school_id : "",
    to_school_name: destination ? destination.school.display_name : "",
    to_cluster: destination ? destination.school.cluster : "",
    person_name: person,
    effective_date: effectiveDate,
    reason,
    attachment_id: attachment.attachment_id,
    attachment_name: attachment.attachment_name,
    document_url: attachment.document_url,
    context,
    matched_line_number: index + 1,
    context_line_start: start + 1,
    context_line_end: end,
  };
}

function renderAll() {
  renderRunMeta();
  renderFilterOptions();
  renderDashboard();
  renderSchools();
}

function renderRunMeta() {
  const meta = document.getElementById("runMeta");
  meta.innerHTML = `
    <span>${escapeHtml(formatGeneratedAt(state.data.generated_at))}</span>
    <strong>${state.findings.length}</strong>
    <span>recognized changes</span>
  `;
}

function renderFilterOptions() {
  const years = unique(state.findings.map((finding) => finding.meeting_year).filter(Boolean)).sort().reverse();
  const currentYear = String(state.data.current_year || "");
  const previousYear = String(state.data.previous_year || "");
  setOptions(document.getElementById("yearFilter"), [
    ["all", "All years"],
    [currentYear, `Current Year (${currentYear})`],
    [previousYear, `Previous Year (${previousYear})`],
    ...years.filter((year) => year !== currentYear && year !== previousYear).map((year) => [year, year]),
  ], state.filters.year);

  const clusters = unique(state.schools.map((school) => school.cluster).filter(Boolean)).sort(compareClusters);
  setOptions(document.getElementById("clusterFilter"), [["all", "All clusters"], ...clusters.map((cluster) => [cluster, cluster])], state.filters.cluster);

  const types = unique(state.findings.map(findingTypeFilter)).sort(compareTypeFilters);
  setOptions(document.getElementById("typeFilter"), [["all", "All types"], ...types.map((type) => [type, labelTypeFilter(type)])], state.filters.type);

  document.getElementById("searchFilter").value = state.filters.search;
  document.getElementById("newOnlyFilter").checked = state.filters.newOnly;
}

function renderDashboard() {
  state.filteredFindings = applyFilters(state.findings);
  sortFindingsForDisplay(state.filteredFindings);
  renderMetrics();
  renderBars("typeBars", countByTypeFilter(state.filteredFindings), labelTypeFilter, (a, b) => compareTypeFilters(a[0], b[0]));
  renderBars("yearBars", countBy(state.filteredFindings, "meeting_year"), (year) => labelYear(year));
  renderBars("clusterBars", countByFindingClusters(state.filteredFindings), (cluster) => cluster || "Unassigned", (a, b) => compareClusters(a[0], b[0]));
  renderEmploymentDateSort();
  renderFindingsTable();
}

function setEmploymentDateSort(direction) {
  state.filters.employmentDateSort = state.filters.employmentDateSort === direction ? "default" : direction;
  persistFilters();
}

function renderEmploymentDateSort() {
  const ascending = document.getElementById("employmentDateAscending");
  const descending = document.getElementById("employmentDateDescending");
  const activeDirection = state.filters.employmentDateSort;
  const setButtonState = (button, direction, label) => {
    const active = activeDirection === direction;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
    button.title = active ? "Return to default order" : label;
    button.setAttribute("aria-label", active ? "Return to default order" : label);
  };
  setButtonState(ascending, "ascending", "Sort employment date oldest first");
  setButtonState(descending, "descending", "Sort employment date newest first");
}

function renderMetrics() {
  const source = state.data.source || {};
  const matchedSchools = new Set(state.filteredFindings.flatMap(findingSchoolIds)).size;
  document.getElementById("metricsGrid").innerHTML = [
    metric("Meetings Scanned", source.scanned_meeting_count || 0),
    metric("Attachments", source.attachment_count || 0),
    metric("Schools Matched", matchedSchools),
    metric("New Since Last Update", state.newFindingIds.size),
    metric("Findings", state.filteredFindings.length),
  ].join("");
  document.getElementById("findingCountLabel").textContent = `${state.filteredFindings.length} findings`;
}

function renderFindingsTable() {
  const body = document.getElementById("findingsBody");
  if (!state.filteredFindings.length) {
    body.innerHTML = `<tr><td colspan="8">No recognized employment changes match the current filters.</td></tr>`;
    return;
  }
  body.innerHTML = state.filteredFindings.map((finding) => `
    <tr${finding.is_new ? ' class="row-new"' : ""}>
      <td>
        ${renderSchoolCell(finding)}
        ${finding.is_new ? '<span class="new-badge">New</span>' : ""}
      </td>
      <td>${renderClusterCell(finding)}</td>
      <td>
        <a href="${escapeAttribute(finding.board_meeting_url)}" target="_blank" rel="noreferrer">${escapeHtml(finding.meeting_date)}</a>
        <span class="subtle">${escapeHtml(finding.meeting_name)}</span>
      </td>
      <td>${findingTypeChip(finding)}</td>
      <td>
        <strong>${escapeHtml(finding.person_name || "Review needed")}</strong>
      </td>
      <td>${escapeHtml(finding.effective_date)}</td>
      <td>${escapeHtml(finding.reason)}</td>
      <td class="source-links">
        <a href="#trace/${encodeURIComponent(finding.id)}">Trace</a>
        <a href="${escapeAttribute(finding.board_meeting_url)}" target="_blank" rel="noreferrer">Board Site</a>
      </td>
    </tr>
    <tr class="context">
      <td colspan="8"><pre>${escapeHtml(finding.context)}</pre></td>
    </tr>
  `).join("");
}

function renderSchools() {
  const grid = document.getElementById("schoolGrid");
  grid.innerHTML = state.schools.map((school) => `
    <article class="school-card">
      <form data-school-id="${escapeAttribute(school.school_id)}">
        <label>
          School
          <input name="display_name" value="${escapeAttribute(school.display_name)}" required>
        </label>
        <label>
          Cluster
          <input name="cluster" value="${escapeAttribute(school.cluster)}" required>
        </label>
        <label>
          Aliases
          <textarea name="aliases">${escapeHtml(school.aliases.join("; "))}</textarea>
        </label>
        <div class="card-actions">
          <button type="submit">Save</button>
          <button type="button" class="danger-button" data-delete-school="${escapeAttribute(school.school_id)}">Delete</button>
        </div>
      </form>
    </article>
  `).join("");
}

function renderTrace(findingId) {
  const finding = state.findings.find((item) => item.id === findingId);
  if (!finding) {
    setStatus("Trace not found", "The selected finding is no longer available with the current school preferences.", false);
    location.hash = "#dashboard";
    return;
  }
  const attachment = (state.data.attachments || []).find((item) => item.attachment_id === finding.attachment_id);
  document.getElementById("traceSummary").innerHTML = `
    <div>
      <span>Board Meeting</span>
      <strong>${escapeHtml(finding.meeting_date)}</strong>
      <p>${escapeHtml(finding.meeting_name)}</p>
    </div>
    <div>
      <span>Person</span>
      <strong>${escapeHtml(finding.person_name || "Review needed")}</strong>
      <p>${escapeHtml(finding.reason || finding.effective_date || "No reason/date parsed")}</p>
    </div>
    <div>
      <span>Agenda Item</span>
      <strong>${escapeHtml(finding.item_number)}</strong>
      <p>${escapeHtml(finding.attachment_name)}</p>
    </div>
  `;
  document.getElementById("officialSourcePanel").innerHTML = `
    <div class="section-heading">
      <h2>1. Official Board Source</h2>
      ${findingTypeChip(finding)}
    </div>
    <p>This record traces back to the official CCSD/Diligent board meeting page. Open the board site to review the agenda item and linked attachment on the public source page.</p>
    <a class="official-link" href="${escapeAttribute(finding.board_meeting_url)}" target="_blank" rel="noreferrer">Open Official Board Meeting Website</a>
    <div class="trace-source-grid">
      <div>
        <span>Board Meeting</span>
        <strong>${escapeHtml(finding.meeting_date)}</strong>
        <p>${escapeHtml(finding.meeting_name)}</p>
      </div>
      <div>
        <span>Agenda Item</span>
        <strong>${escapeHtml(finding.item_number)} - ${escapeHtml(finding.item_title)}</strong>
        <p>${escapeHtml(finding.attachment_name)}</p>
      </div>
      <div>
        <span>${isTransferRoute(finding) ? "Transfer Route" : "Matched School"}</span>
        <strong>${escapeHtml(findingSchoolText(finding))}</strong>
        <p>${escapeHtml(findingClusterText(finding))}</p>
      </div>
      <div>
        <span>Person / Date</span>
        <strong>${escapeHtml(finding.person_name || "Review needed")}</strong>
        <p>${escapeHtml(finding.effective_date || finding.reason || "Review source text")}</p>
      </div>
    </div>
  `;
  const lines = attachment && Array.isArray(attachment.lines) ? attachment.lines : [];
  document.getElementById("traceLineLabel").textContent = `Line ${finding.matched_line_number}`;
  document.getElementById("sourceLines").innerHTML = lines.map((line, index) => {
    const lineNumber = index + 1;
    const highlighted = lineNumber >= finding.context_line_start && lineNumber <= finding.context_line_end;
    const target = lineNumber === finding.matched_line_number;
    return `
      <div${target ? ' id="highlight-target"' : ""} class="source-line${highlighted ? " highlighted" : ""}${target ? " target-line" : ""}">
        <span class="line-number">${lineNumber}</span>
        <code>${escapeHtml(line)}</code>
      </div>
    `;
  }).join("");
  requestAnimationFrame(() => {
    const target = document.getElementById("highlight-target");
    if (target) target.scrollIntoView({ block: "center" });
  });
}

function applyFilters(findings) {
  return findings.filter((finding) => {
    if (state.filters.year !== "all" && finding.meeting_year !== state.filters.year) return false;
    if (state.filters.cluster !== "all" && !findingClusters(finding).includes(state.filters.cluster)) return false;
    if (state.filters.type !== "all" && findingTypeFilter(finding) !== state.filters.type) return false;
    if (state.filters.newOnly && !finding.is_new) return false;
    if (state.filters.search) {
      const haystack = [
        findingSchoolText(finding),
        findingClusterText(finding),
        finding.from_school_name,
        finding.from_cluster,
        finding.to_school_name,
        finding.to_cluster,
        finding.person_name,
        finding.movement_type,
        labelMovementType(finding.movement_type),
        labelTypeFilter(findingTypeFilter(finding)),
        finding.reason,
        finding.effective_date,
        finding.meeting_name,
        finding.meeting_date,
        finding.item_title,
        finding.attachment_name,
        finding.matched_alias,
      ].join(" ").toLowerCase();
      if (!haystack.includes(state.filters.search)) return false;
    }
    return true;
  });
}

function sortFindingsForDisplay(findings) {
  const direction = state.filters.employmentDateSort;
  if (direction === "default") return;
  findings.sort((a, b) => compareEmploymentDates(a, b, direction));
}

function compareEmploymentDates(a, b, direction) {
  const dateA = dateKeyFromEmploymentDate(a.effective_date);
  const dateB = dateKeyFromEmploymentDate(b.effective_date);
  if (dateA && dateB && dateA !== dateB) {
    return direction === "ascending" ? dateA - dateB : dateB - dateA;
  }
  if (dateA && !dateB) return -1;
  if (!dateA && dateB) return 1;
  return compareFindings(a, b);
}

function markNewFindings() {
  const currentIds = state.findings.map((finding) => finding.id);
  const snapshot = loadFindingSnapshot();
  const currentSignature = schoolPreferenceSignature();
  const generatedAt = snapshotGeneratedAt();
  let newIds = new Set();
  const publishedNewIds = publishedNewFindingIds();

  if (
    snapshot &&
    snapshot.generated_at &&
    snapshot.generated_at !== generatedAt &&
    snapshot.school_signature === currentSignature &&
    Array.isArray(snapshot.finding_ids)
  ) {
    const previousIds = new Set(snapshot.finding_ids.map(String));
    newIds = new Set(currentIds.filter((id) => !previousIds.has(id)));
  }

  for (const id of publishedNewIds) {
    newIds.add(id);
  }

  if (!newIds.size && !hasPublishedNewMetadata()) {
    newIds = latestMeetingFindingIds(state.findings);
  }

  state.newFindingIds = newIds;
  state.findings.forEach((finding) => {
    finding.is_new = newIds.has(finding.id);
  });
  saveFindingSnapshot(generatedAt, currentSignature, currentIds);
}

function loadFindingSnapshot() {
  try {
    const saved = JSON.parse(localStorage.getItem(SNAPSHOT_STORAGE_KEY) || "null");
    return saved && typeof saved === "object" ? saved : null;
  } catch {
    return null;
  }
}

function saveFindingSnapshot(generatedAt, schoolSignature, findingIds) {
  saveJsonToStorage(SNAPSHOT_STORAGE_KEY, {
    generated_at: generatedAt,
    school_signature: schoolSignature,
    finding_ids: findingIds,
  });
}

function findingCacheKey() {
  const source = state.data.source || {};
  return fingerprint([
    FINDING_CACHE_VERSION,
    snapshotGeneratedAt(),
    state.data.source_run_at || "",
    source.run_label || "",
    source.attachment_count || "",
    schoolPreferenceSignature(),
  ]);
}

function loadCachedFindings(cacheKey) {
  try {
    const cached = JSON.parse(localStorage.getItem(FINDING_CACHE_STORAGE_KEY) || "null");
    if (
      cached &&
      cached.version === FINDING_CACHE_VERSION &&
      cached.cache_key === cacheKey &&
      Array.isArray(cached.findings)
    ) {
      return cached.findings;
    }
  } catch {
    return null;
  }
  return null;
}

function saveCachedFindings(cacheKey, findings) {
  try {
    localStorage.setItem(FINDING_CACHE_STORAGE_KEY, JSON.stringify({
      version: FINDING_CACHE_VERSION,
      cache_key: cacheKey,
      generated_at: snapshotGeneratedAt(),
      findings,
    }));
  } catch {
    removeFromStorage(FINDING_CACHE_STORAGE_KEY);
  }
}

function snapshotGeneratedAt() {
  const source = state.data.source || {};
  return String(state.data.generated_at || source.generated_at || source.scanned_at || "");
}

function publishedNewFindingIds() {
  const newAttachmentIds = new Set((state.data.attachments || [])
    .filter((attachment) => attachment.is_new_since_previous_export)
    .map((attachment) => String(attachment.attachment_id || "")));
  if (!newAttachmentIds.size) return new Set();
  return new Set(state.findings
    .filter((finding) => newAttachmentIds.has(String(finding.attachment_id || "")))
    .map((finding) => finding.id));
}

function hasPublishedNewMetadata() {
  const source = state.data.source || {};
  if (source.compared_to_previous_export) return true;
  return (state.data.attachments || []).some((attachment) => Object.prototype.hasOwnProperty.call(attachment, "is_new_since_previous_export"));
}

function latestMeetingFindingIds(findings) {
  let latestValue = Number.NEGATIVE_INFINITY;
  for (const finding of findings) {
    latestValue = Math.max(latestValue, meetingSortValue(finding));
  }
  if (!Number.isFinite(latestValue)) return new Set();
  return new Set(findings
    .filter((finding) => meetingSortValue(finding) === latestValue)
    .map((finding) => finding.id));
}

function meetingSortValue(finding) {
  const parsed = Date.parse(String(finding.meeting_date || ""));
  if (Number.isFinite(parsed)) return parsed;
  const year = Number.parseInt(finding.meeting_year, 10);
  const meetingId = Number.parseInt(finding.meeting_id, 10);
  return (Number.isFinite(year) ? year : 0) * 1000000 + (Number.isFinite(meetingId) ? meetingId : 0);
}

function dateKeyFromEmploymentDate(value) {
  const text = String(value || "").trim();
  if (!text || /^TBD$/i.test(text)) return null;

  let match = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/);
  if (match) {
    return dateKey(normalizeDateYear(Number(match[3])), Number(match[1]), Number(match[2]));
  }

  match = text.match(/^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$/);
  if (match) {
    const month = monthNumber(match[1]);
    if (month) return dateKey(Number(match[3]), month, Number(match[2]));
  }

  return null;
}

function normalizeDateYear(year) {
  if (year >= 100) return year;
  return year >= 70 ? 1900 + year : 2000 + year;
}

function monthNumber(value) {
  const month = String(value || "").slice(0, 3).toLowerCase();
  return {
    jan: 1,
    feb: 2,
    mar: 3,
    apr: 4,
    may: 5,
    jun: 6,
    jul: 7,
    aug: 8,
    sep: 9,
    oct: 10,
    nov: 11,
    dec: 12,
  }[month] || null;
}

function dateKey(year, month, day) {
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null;
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return year * 10000 + month * 100 + day;
}

function schoolPreferenceSignature() {
  return fingerprint(state.schools.map((school) => [
    school.school_id,
    school.cluster,
    school.display_name,
    ...(school.aliases || []),
  ].join("|")));
}

function route() {
  const hash = location.hash.replace(/^#/, "") || "dashboard";
  const [view, rawId] = hash.split("/");
  document.querySelectorAll(".view").forEach((element) => {
    element.hidden = true;
  });
  document.querySelectorAll("[data-nav]").forEach((element) => {
    element.classList.toggle("active", element.dataset.nav === view);
  });
  if (view === "schools") {
    document.getElementById("schoolsView").hidden = false;
    document.querySelector('[data-nav="schools"]').classList.add("active");
    return;
  }
  if (view === "trace" && rawId) {
    document.getElementById("traceView").hidden = false;
    renderTrace(decodeURIComponent(rawId));
    return;
  }
  document.getElementById("dashboardView").hidden = false;
  document.querySelector('[data-nav="dashboard"]').classList.add("active");
}

function addSchool(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const displayName = String(formData.get("display_name") || "").trim();
  const cluster = String(formData.get("cluster") || "").trim();
  if (!displayName || !cluster) return;
  const existingIds = new Set(state.schools.map((school) => school.school_id));
  state.schools.push({
    school_id: schoolIdFromName(displayName, existingIds),
    cluster,
    display_name: displayName,
    aliases: unique([displayName, ...splitAliases(formData.get("aliases"))]),
    source_image: "browser",
  });
  persistSchoolChanges();
  form.reset();
  location.hash = "#dashboard";
}

function saveSchool(event) {
  event.preventDefault();
  const form = event.target;
  if (!form.matches("form[data-school-id]")) return;
  const school = state.schools.find((item) => item.school_id === form.dataset.schoolId);
  if (!school) return;
  const formData = new FormData(form);
  const displayName = String(formData.get("display_name") || "").trim();
  const cluster = String(formData.get("cluster") || "").trim();
  if (!displayName || !cluster) return;
  school.display_name = displayName;
  school.cluster = cluster;
  school.aliases = unique([displayName, ...splitAliases(formData.get("aliases"))]);
  persistSchoolChanges();
}

function deleteSchool(event) {
  const button = event.target.closest("[data-delete-school]");
  if (!button) return;
  state.schools = state.schools.filter((school) => school.school_id !== button.dataset.deleteSchool);
  persistSchoolChanges();
}

function resetSchools() {
  removeFromStorage(SCHOOL_STORAGE_KEY);
  removeFromStorage(SCHOOL_VERSION_STORAGE_KEY);
  state.schools = normalizeSchools(state.data.schools || []);
  persistSchoolChanges(false);
}

function exportSchools() {
  const blob = new Blob([JSON.stringify({ schools: state.schools }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "ccsd-school-preferences.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function importSchools(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result || "{}"));
      const schools = Array.isArray(parsed) ? parsed : parsed.schools;
      if (!Array.isArray(schools) || !schools.length) throw new Error("No schools found in file.");
      state.schools = normalizeSchools(schools);
      persistSchoolChanges();
    } catch (error) {
      setStatus("Import failed", error.message || String(error), false);
    } finally {
      event.target.value = "";
    }
  };
  reader.readAsText(file);
}

function persistSchoolChanges(writeStorage = true) {
  state.schools = normalizeSchools(state.schools).sort((a, b) => compareClusters(a.cluster, b.cluster) || a.display_name.localeCompare(b.display_name));
  if (writeStorage) saveSchoolsToStorage();
  recomputeFindings();
  renderAll();
}

function setStatus(title, detail, hidden) {
  const panel = document.getElementById("statusPanel");
  panel.classList.toggle("is-hidden", Boolean(hidden));
  if (!hidden) {
    panel.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span>`;
  }
}

function saveJsonToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Managed browsers can disable storage; keep the app usable without persistence.
  }
}

function saveTextToStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Managed browsers can disable storage; keep the app usable without persistence.
  }
}

function removeFromStorage(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // Managed browsers can disable storage; keep reset usable without persistence.
  }
}

function setOptions(select, options, selectedValue) {
  const values = new Set(options.map(([value]) => String(value)));
  const finalValue = values.has(String(selectedValue)) ? String(selectedValue) : "all";
  select.innerHTML = options.map(([value, label]) => `
    <option value="${escapeAttribute(value)}"${String(value) === finalValue ? " selected" : ""}>${escapeHtml(label)}</option>
  `).join("");
  if (select.id === "yearFilter") state.filters.year = finalValue;
  if (select.id === "clusterFilter") state.filters.cluster = finalValue;
  if (select.id === "typeFilter") state.filters.type = finalValue;
}

function renderBars(elementId, counts, labeler, comparator) {
  const entries = Object.entries(counts).sort(comparator || ((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]))));
  document.getElementById(elementId).innerHTML = entries.length
    ? entries.map(([key, count]) => `<li><span>${escapeHtml(labeler(key))}</span><strong>${count}</strong></li>`).join("")
    : `<li><span>No findings</span><strong>0</strong></li>`;
}

function metric(label, value) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`;
}

function typeChip(value) {
  const type = String(value || "unknown");
  const className = type.toLowerCase().replace(/[^a-z0-9_-]+/g, "-");
  return `<span class="type-chip type-${escapeAttribute(className)}">${escapeHtml(labelMovementType(type))}</span>`;
}

function findingTypeChip(finding) {
  const type = findingTypeFilter(finding);
  const className = type.toLowerCase().replace(/[^a-z0-9_-]+/g, "-");
  return `<span class="type-chip type-${escapeAttribute(className)}">${escapeHtml(findingTypeLabel(finding))}</span>`;
}

function findingTypeLabel(finding) {
  const type = findingTypeFilter(finding);
  if (type === "retirement" || type === "relocation") return labelTypeFilter(type);
  return labelMovementType(finding.movement_type);
}

function findingTypeFilter(finding) {
  if (finding.movement_type === "separation") {
    const reason = normalizeName(finding.reason).toLowerCase();
    if (reason.includes("retirement")) return "retirement";
    if (reason === "relocation") return "relocation";
  }
  return String(finding.movement_type || "unknown");
}

function labelTypeFilter(value) {
  return TYPE_FILTER_LABELS[value] || labelMovementType(value);
}

function compareTypeFilters(a, b) {
  const indexA = TYPE_FILTER_ORDER.indexOf(String(a));
  const indexB = TYPE_FILTER_ORDER.indexOf(String(b));
  if (indexA >= 0 && indexB >= 0 && indexA !== indexB) return indexA - indexB;
  if (indexA >= 0 && indexB < 0) return -1;
  if (indexA < 0 && indexB >= 0) return 1;
  return labelTypeFilter(a).localeCompare(labelTypeFilter(b));
}

function renderSchoolCell(finding) {
  if (!isTransferRoute(finding)) return escapeHtml(finding.school_name);
  return `
    <div class="route-cell">
      <span><small>From</small>${escapeHtml(finding.from_school_name)}</span>
      <span><small>To</small>${escapeHtml(finding.to_school_name)}</span>
    </div>
  `;
}

function renderClusterCell(finding) {
  if (!isTransferRoute(finding)) return escapeHtml(finding.cluster);
  return `
    <div class="route-cell compact">
      <span><small>From</small>${escapeHtml(finding.from_cluster)}</span>
      <span><small>To</small>${escapeHtml(finding.to_cluster)}</span>
    </div>
  `;
}

function isTransferRoute(finding) {
  return finding.movement_type === "promotion_transfer" && Boolean(finding.from_school_name && finding.to_school_name);
}

function findingSchoolText(finding) {
  if (isTransferRoute(finding)) return `${finding.from_school_name} -> ${finding.to_school_name}`;
  return String(finding.school_name || "");
}

function findingClusterText(finding) {
  if (isTransferRoute(finding)) return `${finding.from_cluster} -> ${finding.to_cluster}`;
  return String(finding.cluster || "");
}

function findingSchoolIds(finding) {
  const ids = Array.isArray(finding.school_ids) ? finding.school_ids : String(finding.school_id || "").split("|");
  return unique(ids.map((id) => String(id || "").trim()).filter(Boolean));
}

function findingClusters(finding) {
  const clusters = Array.isArray(finding.clusters) ? finding.clusters : String(finding.cluster || "").split("->");
  return unique(clusters.map((cluster) => String(cluster || "").trim()).filter(Boolean));
}

function countBy(items, key) {
  return items.reduce((counts, item) => {
    const value = item[key] || "Unknown";
    counts[value] = (counts[value] || 0) + 1;
    return counts;
  }, {});
}

function countByTypeFilter(findings) {
  return findings.reduce((counts, finding) => {
    const value = findingTypeFilter(finding);
    counts[value] = (counts[value] || 0) + 1;
    return counts;
  }, {});
}

function countByFindingClusters(findings) {
  return findings.reduce((counts, finding) => {
    for (const cluster of findingClusters(finding)) {
      counts[cluster] = (counts[cluster] || 0) + 1;
    }
    return counts;
  }, {});
}

function compiledSchoolAliases(schools) {
  const compiled = [];
  for (const school of schools) {
    const aliases = unique([school.display_name, ...(school.aliases || [])]);
    for (const alias of aliases) {
      for (const variant of aliasVariants(alias)) {
        if (skipBareAlias(alias, variant)) continue;
        compiled.push({ school, alias, normalizedAlias: variant, pattern: aliasMatchPattern(variant) });
      }
    }
  }
  return compiled.sort((a, b) => b.normalizedAlias.length - a.normalizedAlias.length);
}

function lineSchoolMatches(normalizedLine, aliases) {
  const matches = [];
  for (const aliasInfo of aliases) {
    const position = aliasMatchPosition(normalizedLine, aliasInfo);
    if (position < 0 || !validAliasContext(normalizedLine, aliasInfo, position)) continue;
    matches.push({ ...aliasInfo, position });
  }
  return uniqueSchoolMatches(matches);
}

function crossLineSchoolMatches(currentLine, nextLine, aliases) {
  const combined = `${currentLine} ${nextLine}`.trim();
  const boundary = currentLine.length;
  return lineSchoolMatches(combined, aliases).filter((match) => (
    match.position < boundary && match.position + match.normalizedAlias.length > boundary
  ));
}

function uniqueSchoolMatches(matches) {
  const seen = new Set();
  const occupied = [];
  const uniqueMatches = [];
  const ordered = [...matches].sort((a, b) => b.normalizedAlias.length - a.normalizedAlias.length || a.position - b.position);
  for (const match of ordered) {
    if (seen.has(match.school.school_id)) continue;
    const interval = [match.position, match.position + match.normalizedAlias.length];
    if (occupied.some(([start, end]) => interval[0] < end && start < interval[1])) continue;
    seen.add(match.school.school_id);
    occupied.push(interval);
    uniqueMatches.push(match);
  }
  return uniqueMatches.sort((a, b) => a.position - b.position);
}

function validAliasContext(normalizedLine, aliasInfo, position) {
  const aliasWords = aliasInfo.normalizedAlias.split(" ").filter(Boolean);
  if (!aliasWords.length || SCHOOL_SUFFIXES.has(aliasWords[aliasWords.length - 1])) return true;
  if (/\bK 8$/.test(aliasInfo.normalizedAlias)) return true;
  if (aliasWords.some((word) => SCHOOL_DESCRIPTOR_WORDS.has(word))) return true;
  const lineWords = normalizedLine.split(" ").filter(Boolean);
  const startWord = normalizedLine.slice(0, position).trim().split(/\s+/).filter(Boolean).length;
  const nextWord = lineWords[startWord + aliasWords.length] || "";
  const schoolWords = normalizeName(aliasInfo.school.display_name).split(" ").filter(Boolean);
  const schoolSuffix = schoolWords[schoolWords.length - 1] || "";
  if (SCHOOL_SUFFIXES.has(nextWord)) return !SCHOOL_SUFFIXES.has(schoolSuffix) || nextWord === schoolSuffix;
  if (normalizedLine === aliasInfo.normalizedAlias) return true;
  return /\b(?:TBD|\d{1,2}\s+\d{1,2}\s+\d{2,4})\b/.test(normalizedLine);
}

function normalizeName(value) {
  return String(value || "")
    .toUpperCase()
    .replace(/&/g, " AND ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function aliasVariants(alias) {
  const normalized = normalizeName(alias);
  const variants = new Set([normalized]);
  const expansions = [
    [" ES", " ELEMENTARY SCHOOL"],
    [" MS", " MIDDLE SCHOOL"],
    [" JHS", " JUNIOR HIGH SCHOOL"],
    [" HS", " HIGH SCHOOL"],
    [" CTA", " CAREER TECHNICAL ACADEMY"],
  ];
  for (const [shortSuffix, expandedSuffix] of expansions) {
    const shortNorm = normalizeName(shortSuffix);
    const expandedNorm = normalizeName(expandedSuffix);
    if (normalized.endsWith(shortNorm)) variants.add(`${normalized.slice(0, -shortNorm.length).trim()} ${expandedNorm}`.trim());
    if (normalized.endsWith(expandedNorm)) variants.add(`${normalized.slice(0, -expandedNorm.length).trim()} ${shortNorm}`.trim());
  }
  return [...variants].filter(Boolean);
}

function skipBareAlias(alias, normalizedVariant) {
  if (normalizedVariant.split(" ").length !== 1) return false;
  const stripped = String(alias).trim();
  return !(stripped === stripped.toUpperCase() && stripped.length >= 4);
}

function containsAlias(normalizedLine, normalizedAlias) {
  return aliasMatchPosition(normalizedLine, normalizedAlias) >= 0;
}

function aliasMatchPosition(normalizedLine, aliasOrInfo) {
  const normalizedAlias = typeof aliasOrInfo === "string" ? aliasOrInfo : aliasOrInfo.normalizedAlias;
  if (normalizedAlias.length < 4) return -1;
  const pattern = typeof aliasOrInfo === "string" ? aliasMatchPattern(normalizedAlias) : aliasOrInfo.pattern;
  const match = pattern.exec(normalizedLine);
  return match ? match.index + match[1].length : -1;
}

function aliasMatchPattern(normalizedAlias) {
  return new RegExp(`(^|\\s)${escapeRegExp(normalizedAlias)}($|\\s)`);
}

function extractPersonName(lines, index, alias) {
  const currentLine = lines[index] || "";
  const nextLine = lines[index + 1] || "";
  let inline = personFromLinePrefix(currentLine, alias, nextLine);
  if (!inline && aliasSpansLines(currentLine, nextLine, alias)) {
    inline = personFromLinePrefix(`${currentLine} ${nextLine}`, alias, lines[index + 2] || "");
  }
  if (inline) return inline;
  for (let i = index - 1; i >= Math.max(0, index - 3); i -= 1) {
    const candidate = lines[i].trim();
    if (looksLikeHeader(candidate) || fullDateMatch(candidate)) continue;
    const person = leadingPersonName(candidate);
    if (person) return person;
  }
  return "";
}

function aliasSpansLines(currentLine, nextLine, alias) {
  if (!currentLine || !nextLine) return false;
  const current = normalizeName(currentLine);
  const combined = normalizeName(`${currentLine} ${nextLine}`);
  const variants = unique([normalizeName(alias), ...aliasTextVariants(alias)]);
  return variants.some((variant) => {
    const position = aliasMatchPosition(combined, variant);
    return position >= 0 && position < current.length && position + variant.length > current.length;
  });
}

function personFromLinePrefix(line, alias, nextLine = "") {
  const normalized = normalizeWithMapping(line);
  let bestPosition = null;
  const variants = [normalizeName(alias), ...aliasTextVariants(alias).sort((a, b) => b.length - a.length)];
  for (const variant of variants) {
    const position = normalized.text.indexOf(variant);
    if (position >= 0) bestPosition = bestPosition === null ? position : Math.min(bestPosition, position);
  }
  if (bestPosition === null || bestPosition === 0) return "";
  const prefixWords = normalized.text.slice(0, bestPosition).trim().split(/\s+/);
  const originalCut = normalized.mapping[bestPosition] || line.length;
  const originalWords = line.slice(0, originalCut).replace(/\s+/g, " ").split(" ");
  const nameWords = [];
  for (const word of originalWords) {
    const cleaned = word.replace(/[^A-Za-z'.-]/g, "");
    if (!cleaned) continue;
    if (ROLE_WORDS.has(cleaned.toLowerCase())) break;
    nameWords.push(cleaned);
    if (nameWords.length >= 5) break;
  }
  if (prefixWords.length < 2 && nameWords.length === 1) {
    const nextWord = firstSplitNameWord(nextLine);
    if (nextWord) return cleanPerson(`${nameWords[0]} ${nextWord}`);
  }
  return cleanPerson(nameWords.join(" "));
}

function normalizeWithMapping(value) {
  const chars = [];
  const mapping = [];
  let pendingSpace = false;
  const text = String(value || "");
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index].toUpperCase();
    if (/[A-Z0-9]/.test(char)) {
      if (pendingSpace && chars.length) {
        chars.push(" ");
        mapping.push(index);
      }
      chars.push(char);
      mapping.push(index);
      pendingSpace = false;
    } else {
      pendingSpace = true;
    }
  }
  const joined = chars.join("").trim();
  return { text: joined, mapping: mapping.slice(0, joined.length) };
}

function leadingPersonName(line) {
  const words = String(line || "").replace(/\s+/g, " ").split(" ");
  const nameWords = [];
  for (const word of words) {
    const cleaned = word.replace(/[^A-Za-z'.-]/g, "");
    if (!cleaned) continue;
    if (ROLE_WORDS.has(cleaned.toLowerCase())) break;
    if (HEADER_HINTS.has(cleaned.toLowerCase())) return "";
    nameWords.push(cleaned);
    if (nameWords.length >= 5) break;
  }
  return cleanPerson(nameWords.join(" "));
}

function cleanPerson(value) {
  const text = String(value || "").replace(/\s+/g, " ").replace(/^[\s,-]+|[\s,-]+$/g, "");
  const words = text.split(" ").filter(Boolean);
  if (words.length < 2) return "";
  if (words.some((word) => !/^(?:'?[A-Z][A-Za-z'.-]*|[A-Z]\.)$/.test(word) && !NAME_PARTICLES.has(word.toLowerCase()))) return "";
  if (NON_PERSON_NAME_PATTERN.test(text)) return "";
  if (/\b[A-Z]{2}\b/.test(text) && /\b(?:present|current|remote|19\d{2}|20\d{2})\b/i.test(text)) return "";
  if (looksLikeSchoolOrOrg(text)) return "";
  if (looksLikeOrganization(text)) return "";
  if (words.some((word) => HEADER_HINTS.has(word.toLowerCase()))) return "";
  return text;
}

function looksLikeSchoolOrOrg(value) {
  const words = normalizeName(value).split(" ").filter(Boolean);
  if (!words.length) return false;
  const schoolOrgWords = new Set(["ES", "MS", "JHS", "HS", "CTA", "SCHOOL", "ACADEMY", "CENTER", "PREP", "UNIT", "DEPARTMENT"]);
  if (schoolOrgWords.has(words[words.length - 1]) || words.some((word) => schoolOrgWords.has(word))) return true;
  return String(value).split(/\s+/).some((word) => /(?:ES|MS|JHS|HS|CTA)[A-Z][a-z]/.test(word));
}

function firstSplitNameWord(line) {
  const first = String(line || "").trim().split(/\s+/)[0] || "";
  const cleaned = first.replace(/[^A-Za-z'.-]/g, "");
  if (!cleaned) return "";
  const lower = cleaned.toLowerCase();
  if (ROLE_WORDS.has(lower) || HEADER_HINTS.has(lower) || SPLIT_NAME_BLOCK_WORDS.has(lower)) return "";
  return cleaned;
}

function shouldRejectFinding(lines, index, context, person, effectiveDate, movementType) {
  if (!EMPLOYMENT_MOVEMENT_TYPES.has(String(movementType || ""))) return true;
  if (!person || looksLikeOrganization(person)) return true;
  const currentLine = lines[index] || "";
  if (looksLikeLocationHistory(currentLine)) return true;
  if (String(movementType || "") === "new_hire" && looksLikeResumeContext(lines, index, context)) return true;
  if (String(movementType || "") === "new_hire" && !effectiveDate) return true;
  return false;
}

function looksLikeLocationHistory(value) {
  return LOCATION_HISTORY_PATTERN.test(String(value || ""));
}

function looksLikeResumeContext(lines, index, context) {
  if (RESUME_SECTION_PATTERN.test(String(context || ""))) return true;
  const windowStart = Math.max(0, index - 6);
  const nearby = lines.slice(windowStart, index + 1).join("\n");
  return RESUME_SECTION_PATTERN.test(nearby) && looksLikeLocationHistory(lines[index] || "");
}

function looksLikeOrganization(value) {
  const words = normalizeName(value).toLowerCase().split(" ").filter(Boolean);
  if (!words.length) return false;
  if (words.length > 5) return true;
  if (String(value || "").includes("&")) return true;
  return words.some((word) => ORGANIZATION_WORDS.has(word.replace(/\.$/, "")));
}

function looksLikeHeader(line) {
  const normalized = normalizeName(line).toLowerCase();
  if (normalized.split(" ").length <= 1 && HEADER_HINTS.has(normalized)) return true;
  return [...HEADER_HINTS].some((hint) => normalized.includes(hint));
}

function aliasTextVariants(alias) {
  const normalized = normalizeName(alias);
  const variants = new Set([normalized]);
  const replacements = [
    [" ES", " ELEMENTARY SCHOOL"],
    [" MS", " MIDDLE SCHOOL"],
    [" JHS", " JUNIOR HIGH SCHOOL"],
    [" HS", " HIGH SCHOOL"],
  ];
  for (const [oldValue, newValue] of replacements) {
    const oldNorm = normalizeName(oldValue);
    const newNorm = normalizeName(newValue);
    if (normalized.endsWith(oldNorm)) variants.add(`${normalized.slice(0, -oldNorm.length).trim()} ${newNorm}`.trim());
  }
  return [...variants];
}

function extractEffectiveDateForMatch(lines, index, context) {
  const candidates = [
    lines[index],
    ...lines.slice(Math.max(0, index - 2), index).reverse(),
    ...lines.slice(index + 1, Math.min(lines.length, index + 3)),
  ];
  for (const candidate of candidates) {
    const date = extractEffectiveDate(candidate);
    if (date) return date;
  }
  return extractEffectiveDate(context);
}

function extractEffectiveDate(context) {
  const matches = [...String(context || "").matchAll(DATE_PATTERN)].map((match) => match[0]);
  DATE_PATTERN.lastIndex = 0;
  return matches.length ? matches[matches.length - 1].replace(/\/+/g, "/") : "";
}

function fullDateMatch(value) {
  const text = String(value || "").trim();
  const match = text.match(DATE_PATTERN);
  DATE_PATTERN.lastIndex = 0;
  return Boolean(match && match[0] === text);
}

function extractReasonForMatch(lines, index, context) {
  const candidates = [
    lines[index],
    ...lines.slice(index + 1, Math.min(lines.length, index + 3)),
    ...lines.slice(Math.max(0, index - 2), index).reverse(),
  ];
  for (const candidate of candidates) {
    const reason = extractReason(candidate);
    if (reason) return reason;
  }
  return extractReason(context);
}

function extractReason(context) {
  const normalized = String(context || "").replace(/\s+/g, " ");
  const matches = REASON_RULES
    .map(([pattern, label]) => {
      const match = normalized.match(pattern);
      return [match ? match.index : -1, label];
    })
    .filter(([position]) => position >= 0)
    .sort((a, b) => a[0] - b[0]);
  return matches.length ? matches[0][1] : "";
}

function compareFindings(a, b) {
  const dateA = Date.parse(a.meeting_date) || 0;
  const dateB = Date.parse(b.meeting_date) || 0;
  if (dateA !== dateB) return dateB - dateA;
  return `${findingSchoolText(a)} ${a.person_name}`.localeCompare(`${findingSchoolText(b)} ${b.person_name}`);
}

function compareClusters(a, b) {
  const numberA = clusterNumber(a);
  const numberB = clusterNumber(b);
  if (numberA !== null && numberB !== null && numberA !== numberB) return numberA - numberB;
  if (numberA !== null && numberB === null) return -1;
  if (numberA === null && numberB !== null) return 1;
  return String(a || "").localeCompare(String(b || ""));
}

function clusterNumber(value) {
  const match = String(value || "").match(/\b(?:cluster\s*)?(\d+)\b/i);
  return match ? Number(match[1]) : null;
}

function labelMovementType(value) {
  return String(value || "unknown")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function labelYear(year) {
  const currentYear = String(state.data.current_year || "");
  const previousYear = String(state.data.previous_year || "");
  if (String(year) === currentYear) return `Current Year (${year})`;
  if (String(year) === previousYear) return `Previous Year (${year})`;
  return String(year || "Unknown");
}

function formatGeneratedAt(value) {
  if (!value) return "Not generated";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function schoolIdFromName(displayName, existingIds = new Set()) {
  const base = normalizeName(displayName).toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]+/g, "").replace(/^_+|_+$/g, "") || "school";
  let candidate = base;
  let index = 2;
  while (existingIds.has(candidate)) {
    candidate = `${base}_${index}`;
    index += 1;
  }
  return candidate;
}

function splitAliases(value) {
  return String(value || "")
    .split(/[;\n]/)
    .map((alias) => alias.trim())
    .filter(Boolean);
}

function unique(values) {
  return [...new Set(values.filter((value) => value !== undefined && value !== null && String(value).trim()))];
}

function fingerprint(parts) {
  const text = parts.map((part) => String(part ?? "")).join("\0");
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
