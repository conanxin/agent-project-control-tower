/**
 * filters.ts — generic client-side search / filter / sort for the dashboard.
 *
 * Each page marks its list of items with a `data-` attribute set on a
 * container element. The `applyFilterBar` function reads the form's
 * state, queries the items, and toggles their `hidden` attribute.
 *
 * Conventions:
 *   data-container="items"           - the <ul>/<div> that wraps items
 *   data-item="project" / "agent" /
 *                "timeline" / "phase" - per-item marker
 *   data-search-target="..."        - per-item field names to match against
 *                                     (e.g. "name,id,repo,summary")
 *   data-filter-key="status"        - filter dropdown name -> data-key=value
 *   data-filter-key="health"        - same
 *   data-filter-key="agent"         - same
 *   data-filter-key="project"       - same
 *   data-filter-key="event_type"    - same
 *   data-sort-key="updated" /       - sort dropdown name -> ordering rule
 *                  "health" /
 *                  "name"
 *   data-count-target="..."         - element to display "N matching"
 *
 * No dependencies, no framework.
 */

type FilterForm = HTMLFormElement;

function $(sel: string, root: ParentNode = document) {
  return root.querySelector(sel) as HTMLElement | null;
}

function getFormFromContainer(container: HTMLElement): FilterForm | null {
  return container.parentElement?.querySelector(
    "form[data-filter-form]"
  ) as FilterForm | null;
}

function valuesOf(form: FilterForm): Record<string, string> {
  const fd = new FormData(form);
  const out: Record<string, string> = {};
  for (const [k, v] of fd.entries()) {
    out[k] = String(v).trim();
  }
  return out;
}

function matches(item: HTMLElement, filters: Record<string, string>): boolean {
  // 1. Free-text search
  const search = (filters.q ?? "").toLowerCase();
  if (search) {
    const targets = (item.dataset.searchTarget ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    let hay = "";
    for (const f of targets) {
      const v = item.dataset[f.toLowerCase()] ?? "";
      hay += " " + v;
    }
    // Also fall back to the rendered text content (works for everything).
    hay += " " + (item.textContent ?? "");
    if (!hay.toLowerCase().includes(search)) return false;
  }

  // 2. Dropdown filters
  for (const [k, v] of Object.entries(filters)) {
    if (!v) continue;
    if (k === "q") continue;
    if (k === "sort") continue;
    const itemVal = item.dataset[k] ?? "";
    if (itemVal !== v) return false;
  }
  return true;
}

const HEALTH_ORDER: Record<string, number> = {
  red: 0, yellow: 1, green: 2, gray: 3,
};

function compareItems(a: HTMLElement, b: HTMLElement, sortKey: string): number {
  switch (sortKey) {
    case "updated": {
      const ax = Date.parse(a.dataset.updatedAt ?? "") || 0;
      const bx = Date.parse(b.dataset.updatedAt ?? "") || 0;
      return bx - ax;
    }
    case "health": {
      const ax = HEALTH_ORDER[a.dataset.health ?? "gray"] ?? 99;
      const bx = HEALTH_ORDER[b.dataset.health ?? "gray"] ?? 99;
      return ax - bx;
    }
    case "name": {
      return (a.dataset.name ?? "").localeCompare(b.dataset.name ?? "");
    }
    case "newest": {
      const ax = Date.parse(a.dataset.createdAt ?? "") || 0;
      const bx = Date.parse(b.dataset.createdAt ?? "") || 0;
      return bx - ax;
    }
    case "oldest": {
      const ax = Date.parse(a.dataset.createdAt ?? "") || 0;
      const bx = Date.parse(b.dataset.createdAt ?? "") || 0;
      return ax - bx;
    }
    default:
      return 0;
  }
}

function applyToContainer(container: HTMLElement) {
  const form = getFormFromContainer(container);
  if (!form) return;
  const filters = valuesOf(form);
  const items = Array.from(
    container.querySelectorAll<HTMLElement>("[data-item]")
  );
  let visible = 0;
  for (const it of items) {
    if (matches(it, filters)) {
      it.hidden = false;
      visible++;
    } else {
      it.hidden = true;
    }
  }

  // Sort
  const sortKey = filters.sort ?? "";
  if (sortKey) {
    items.sort((a, b) => compareItems(a, b, sortKey));
    for (const it of items) container.appendChild(it);
  }

  // Empty state
  const emptyEl = container.parentElement?.querySelector<HTMLElement>(
    "[data-empty-state]"
  );
  if (emptyEl) {
    emptyEl.hidden = visible > 0;
  }

  // Count badge
  const countTarget = container.parentElement?.querySelector<HTMLElement>(
    "[data-count-target]"
  );
  if (countTarget) {
    countTarget.textContent = `${visible} matching`;
  }
}

function applyAll() {
  const containers = document.querySelectorAll<HTMLElement>(
    "[data-container='items']"
  );
  for (const c of containers) applyToContainer(c);
}

function clearForm(form: FilterForm) {
  form.reset();
  applyAll();
}

function init() {
  // Wire all forms with data-filter-form attribute
  const forms = document.querySelectorAll<FilterForm>("form[data-filter-form]");
  for (const form of forms) {
    if (form.dataset.bound) continue;
    form.dataset.bound = "1";
    form.addEventListener("input", () => applyAll());
    form.addEventListener("change", () => applyAll());
    const clear = form.querySelector<HTMLButtonElement>(
      "button[data-filter-clear]"
    );
    if (clear) {
      clear.addEventListener("click", (e) => {
        e.preventDefault();
        clearForm(form);
      });
    }
  }
  // Run once to apply any pre-populated values
  applyAll();
}

// Expose for inline debugging if needed
if (typeof window !== "undefined") {
  (window as unknown as { towerFilters: object }).towerFilters = {
    applyAll,
  };
}

// Re-init on Astro view transitions, which swap the DOM but keep scripts.
if (typeof document !== "undefined") {
  document.addEventListener("astro:page-load", init);
  if (document.readyState !== "loading") {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
}
