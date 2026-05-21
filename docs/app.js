const DATA_URL = "data/board-data.json";
const SCHOOL_STORAGE_KEY = "ccsd-board-watch-schools-v1";
const FILTER_STORAGE_KEY = "ccsd-board-watch-filters-v1";
const SNAPSHOT_STORAGE_KEY = "ccsd-board-watch-finding-snapshot-v1";

const DATE_PATTERN = /\b(?:\d{1,2}\/\d{1,2}\/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}|TBD)\b/ig;
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
]);
const REASON_PATTERNS = [
  "Disability Retirement",
  "Accepted Position in Other District",
  "Accepted Other Position/Leaving Profession",
  "Personal/Family Reasons",
  "No Contract/Mutual Resign",
  "Board/Admin Action",
  "Accepted Other Position",
  "Accepted Position",
  "Leaving Profession",
  "Dissatisfied with District",
  "Not Offered Contract",
  "Mutual Resignation",
  "No Reason Given",
  "Return to School",
  "Retirement",
  "Relocation",
  "Medical",
  "No Contract",
  "Death",
];

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
    const response = await fetch(DATA_URL, { cache: "no-store" });
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
      return normalizeSchools(saved);
    }
  } catch {
    return fallback;
  }
  return fallback;
}

function saveSchoolsToStorage() {
  saveJsonToStorage(SCHOOL_STORAGE_KEY, state.schools);
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
  state.findings = buildFindings(state.data.attachments || [], state.schools);
  markNewFindings();
}

function buildFindings(attachments, schools) {
  const aliases = compiledSchoolAliases(schools);
  const findings = [];
  const seen = new Set();

  for (const attachment of attachments) {
    const lines = Array.isArray(attachment.lines) ? attachment.lines.map((line) => String(line).trim()).filter(Boolean) : [];
    const normalizedLines = lines.map(normalizeName);
    const matchedLineSchools = new Set();
    for (let index = 0; index < normalizedLines.length; index += 1) {
      const normalized = normalizedLines[index];
      if (!normalized) continue;
      for (const aliasInfo of aliases) {
        if (!containsAlias(normalized, aliasInfo.normalizedAlias)) continue;
        const lineSchoolKey = `${attachment.attachment_id}:${index}:${aliasInfo.school.school_id}`;
        if (matchedLineSchools.has(lineSchoolKey)) continue;
        matchedLineSchools.add(lineSchoolKey);

        const start = Math.max(0, index - 3);
        const end = Math.min(lines.length, index + 4);
        const contextLines = lines.slice(start, end);
        const context = contextLines.join("\n");
        const person = extractPersonName(lines, index, aliasInfo.normalizedAlias);
        const effectiveDate = extractEffectiveDateForMatch(lines, index, context);
        const reason = extractReasonForMatch(lines, index, context);
        const fingerprintParts = [
          attachment.meeting_id,
          attachment.document_id,
          aliasInfo.school.school_id,
          attachment.movement_type,
          person,
          effectiveDate,
        ];
        if (!person) fingerprintParts.push(context);
        const id = fingerprint(fingerprintParts);
        if (seen.has(id)) continue;
        seen.add(id);
        findings.push({
          id,
          meeting_id: attachment.meeting_id,
          meeting_name: attachment.meeting_name,
          meeting_date: attachment.meeting_date,
          meeting_year: attachment.meeting_year,
          board_meeting_url: attachment.board_meeting_url,
          item_number: attachment.item_number,
          item_title: attachment.item_title,
          movement_type: attachment.movement_type,
          school_id: aliasInfo.school.school_id,
          school_name: aliasInfo.school.display_name,
          cluster: aliasInfo.school.cluster,
          matched_alias: aliasInfo.alias,
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
        });
      }
    }
  }

  return findings.sort(compareFindings);
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

  const clusters = unique(state.schools.map((school) => school.cluster).filter(Boolean)).sort();
  setOptions(document.getElementById("clusterFilter"), [["all", "All clusters"], ...clusters.map((cluster) => [cluster, cluster])], state.filters.cluster);

  const types = unique((state.data.attachments || []).map((attachment) => attachment.movement_type).filter(Boolean)).sort();
  setOptions(document.getElementById("typeFilter"), [["all", "All types"], ...types.map((type) => [type, labelMovementType(type)])], state.filters.type);

  document.getElementById("searchFilter").value = state.filters.search;
  document.getElementById("newOnlyFilter").checked = state.filters.newOnly;
}

function renderDashboard() {
  state.filteredFindings = applyFilters(state.findings);
  renderMetrics();
  renderBars("typeBars", countBy(state.filteredFindings, "movement_type"), labelMovementType);
  renderBars("yearBars", countBy(state.filteredFindings, "meeting_year"), (year) => labelYear(year));
  renderBars("clusterBars", countBy(state.filteredFindings, "cluster"), (cluster) => cluster || "Unassigned");
  renderFindingsTable();
}

function renderMetrics() {
  const source = state.data.source || {};
  const matchedSchools = new Set(state.filteredFindings.map((finding) => finding.school_id)).size;
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
        ${escapeHtml(finding.school_name)}
        ${finding.is_new ? '<span class="new-badge">New</span>' : ""}
      </td>
      <td>${escapeHtml(finding.cluster)}</td>
      <td>
        <a href="${escapeAttribute(finding.board_meeting_url)}" target="_blank" rel="noreferrer">${escapeHtml(finding.meeting_date)}</a>
        <span class="subtle">${escapeHtml(finding.meeting_name)}</span>
      </td>
      <td>${typeChip(finding.movement_type)}</td>
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
      ${typeChip(finding.movement_type)}
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
        <span>Matched School</span>
        <strong>${escapeHtml(finding.school_name)}</strong>
        <p>${escapeHtml(finding.cluster)}</p>
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
    if (state.filters.cluster !== "all" && finding.cluster !== state.filters.cluster) return false;
    if (state.filters.type !== "all" && finding.movement_type !== state.filters.type) return false;
    if (state.filters.newOnly && !finding.is_new) return false;
    if (state.filters.search) {
      const haystack = [
        finding.school_name,
        finding.cluster,
        finding.person_name,
        finding.reason,
        finding.meeting_name,
        finding.meeting_date,
        finding.context,
      ].join(" ").toLowerCase();
      if (!haystack.includes(state.filters.search)) return false;
    }
    return true;
  });
}

function markNewFindings() {
  const currentIds = state.findings.map((finding) => finding.id);
  const snapshot = loadFindingSnapshot();
  const currentSignature = schoolPreferenceSignature();
  const generatedAt = snapshotGeneratedAt();
  let newIds = new Set();

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

function snapshotGeneratedAt() {
  const source = state.data.source || {};
  return String(state.data.generated_at || source.generated_at || source.scanned_at || "");
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
  state.schools = normalizeSchools(state.schools).sort((a, b) => `${a.cluster} ${a.display_name}`.localeCompare(`${b.cluster} ${b.display_name}`));
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

function renderBars(elementId, counts, labeler) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
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

function countBy(items, key) {
  return items.reduce((counts, item) => {
    const value = item[key] || "Unknown";
    counts[value] = (counts[value] || 0) + 1;
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
        compiled.push({ school, alias, normalizedAlias: variant });
      }
    }
  }
  return compiled.sort((a, b) => b.normalizedAlias.length - a.normalizedAlias.length);
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
  if (normalizedAlias.length < 4) return false;
  return new RegExp(`(^|\\s)${escapeRegExp(normalizedAlias)}($|\\s)`).test(normalizedLine);
}

function extractPersonName(lines, index, alias) {
  const inline = personFromLinePrefix(lines[index], alias);
  if (inline) return inline;
  for (let i = index - 1; i >= Math.max(0, index - 3); i -= 1) {
    const candidate = lines[i].trim();
    if (looksLikeHeader(candidate) || fullDateMatch(candidate)) continue;
    const person = leadingPersonName(candidate);
    if (person) return person;
  }
  return "";
}

function personFromLinePrefix(line, alias) {
  const normalized = normalizeWithMapping(line);
  let bestPosition = null;
  const variants = [normalizeName(alias), ...aliasTextVariants(alias).sort((a, b) => b.length - a.length)];
  for (const variant of variants) {
    const position = normalized.text.indexOf(variant);
    if (position >= 0) bestPosition = bestPosition === null ? position : Math.min(bestPosition, position);
  }
  if (bestPosition === null || bestPosition === 0) return "";
  const prefixWords = normalized.text.slice(0, bestPosition).trim().split(/\s+/);
  if (prefixWords.length < 2) return "";
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
  if (looksLikeSchoolOrOrg(text)) return "";
  if (words.some((word) => HEADER_HINTS.has(word.toLowerCase()))) return "";
  return text;
}

function looksLikeSchoolOrOrg(value) {
  const words = normalizeName(value).split(" ").filter(Boolean);
  if (!words.length) return false;
  return new Set(["ES", "MS", "JHS", "HS", "SCHOOL", "ACADEMY", "CENTER", "UNIT", "DEPARTMENT"]).has(words[words.length - 1]);
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
  return matches.length ? matches[matches.length - 1] : "";
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
  const normalized = String(context || "").replace(/\s+/g, " ").toLowerCase();
  const matches = REASON_PATTERNS
    .map((reason) => [normalized.indexOf(reason.toLowerCase()), reason])
    .filter(([position]) => position >= 0)
    .sort((a, b) => a[0] - b[0]);
  return matches.length ? matches[0][1] : "";
}

function compareFindings(a, b) {
  const dateA = Date.parse(a.meeting_date) || 0;
  const dateB = Date.parse(b.meeting_date) || 0;
  if (dateA !== dateB) return dateB - dateA;
  return `${a.school_name} ${a.person_name}`.localeCompare(`${b.school_name} ${b.person_name}`);
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
