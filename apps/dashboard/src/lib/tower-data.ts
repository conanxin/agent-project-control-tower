/**
 * tower-data.ts — load and type generated/index.json at build time.
 *
 * The data file lives at the repo root (../../generated/index.json),
 * produced by `python scripts/tower.py build`. We import it as a JSON
 * module so Astro can statically pre-render every page.
 *
 * Convention: when a value is missing, fall back to a safe default so
 * pages never crash on an empty seed.
 */
import data from "../../../../generated/index.json";

export type Health = "green" | "yellow" | "red" | "gray";

export type EventType =
  | "AGENT_REGISTERED"
  | "PROJECT_REGISTERED"
  | "PHASE_REPORT"
  | "REVIEW_REPORT"
  | "HANDOFF"
  | "RELEASE"
  | "FAILURE"
  | "BLOCK"
  | "UNBLOCK"
  | "ARCHIVE";

export type Status =
  | "ACTIVE"
  | "PASS"
  | "FAIL"
  | "PARTIAL"
  | "BLOCKED"
  | "PAUSED"
  | "RELEASED"
  | "ARCHIVED";

export interface Project {
  project_id: string;
  name: string;
  repo: string | null;
  location: string;
  category: string;
  current_status: Status;
  current_health: Health;
  current_phase_id: string | null;
  current_phase_name: string | null;
  last_agent_id: string | null;
  last_event_at: string | null;
  last_event_type: EventType | null;
  last_summary: string | null;
  next: string | null;
  event_count: number;
}

export interface Agent {
  agent_id: string;
  name: string;
  machine: string;
  role: string;
  last_event_at: string | null;
  last_project_id: string | null;
  last_event_type: EventType | null;
  event_count: number;
}

export interface TimelineEntry {
  event_id: string | null;
  event_type: EventType;
  project_id: string | null;
  agent_id: string | null;
  phase_id: string | null;
  phase_name: string | null;
  status: Status;
  health?: Health;
  summary: string | null;
  next: string | null;
  created_at: string;
}

export interface TowerData {
  schema_version: string;
  source: string;
  generated_at: string;
  summary: {
    project_count: number;
    agent_count: number;
    event_count: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
    blocked_count: number;
  };
  projects: Project[];
  agents: Agent[];
  timeline: TimelineEntry[];
}

const raw = data as unknown as TowerData;
export const tower: TowerData = {
  schema_version: raw.schema_version ?? "unknown",
  source: raw.source ?? "data",
  generated_at: raw.generated_at ?? "",
  summary: {
    project_count: raw.summary?.project_count ?? 0,
    agent_count: raw.summary?.agent_count ?? 0,
    event_count: raw.summary?.event_count ?? 0,
    green_count: raw.summary?.green_count ?? 0,
    yellow_count: raw.summary?.yellow_count ?? 0,
    red_count: raw.summary?.red_count ?? 0,
    blocked_count: raw.summary?.blocked_count ?? 0,
  },
  projects: raw.projects ?? [],
  agents: raw.agents ?? [],
  timeline: raw.timeline ?? [],
};

export function getProject(id: string): Project | undefined {
  return tower.projects.find((p) => p.project_id === id);
}

export function getAgent(id: string): Agent | undefined {
  // Safe: if id is null/undefined, .find still walks the array.
  return tower.agents.find((a) => a.agent_id === id);
}

export function projectTimeline(projectId: string): TimelineEntry[] {
  return tower.timeline.filter((t) => t.project_id === projectId);
}

export function agentTimeline(agentId: string): TimelineEntry[] {
  return tower.timeline.filter((t) => t.agent_id === agentId);
}

/* ---------- ACT-3B derived helpers (pure, deterministic) ---------- */

/** Distinct values, sorted ascending. Safe on empty arrays. */
export function distinctProjects(): Project[] {
  return tower.projects;
}
export function distinctAgents(): Agent[] {
  return tower.agents;
}

/** Project ids touched by a given agent (ordered by last_event_at desc). */
export function projectsByAgent(agentId: string): Project[] {
  const seen = new Set<string>();
  const out: Project[] = [];
  for (const t of tower.timeline) {
    if (t.agent_id !== agentId) continue;
    if (!t.project_id || seen.has(t.project_id)) continue;
    seen.add(t.project_id);
    const p = tower.projects.find((x) => x.project_id === t.project_id);
    if (p) out.push(p);
  }
  return out;
}

/** Group a timeline by phase_id. Phases appear in first-seen order. */
export function groupByPhase(entries: TimelineEntry[]): Array<{
  phase_id: string | null;
  phase_name: string | null;
  events: TimelineEntry[];
}> {
  const map = new Map<string, { phase_id: string | null; phase_name: string | null; events: TimelineEntry[] }>();
  for (const t of entries) {
    const key = t.phase_id ?? "(no phase)";
    if (!map.has(key)) {
      map.set(key, { phase_id: t.phase_id, phase_name: t.phase_name, events: [] });
    }
    map.get(key)!.events.push(t);
  }
  return Array.from(map.values());
}

/** Counts of timeline entries grouped by event_type. */
export function countByEventType(entries: TimelineEntry[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const t of entries) {
    out[t.event_type] = (out[t.event_type] ?? 0) + 1;
  }
  return out;
}
