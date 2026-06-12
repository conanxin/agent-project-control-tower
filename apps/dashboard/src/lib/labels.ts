/**
 * labels.ts — ACT-13B unified Chinese UI labels.
 *
 * Central mapping for:
 *   - event_type → 中文 (short + long)
 *   - status     → 中文 (short + long)
 *   - health     → 中文
 *   - location   → 中文
 *   - category   → 中文 (with "uncategorized" / "local" / "public" fallback)
 *   - generic UI labels used across pages (section titles, filter bar, etc.)
 *
 * Conventions:
 *   - English technical identifiers (data/, public-data/, commit, push,
 *     agent_id, project_id, phase_id, status values like PASS / PARTIAL,
 *     health values like green / yellow) are preserved as-is per ACT-13B
 *     design: those are the "machine words" that don't translate.
 *   - User-facing chrome (section headings, filter prompts, button labels)
 *     is translated.
 *   - The original English value can always be retrieved by reversing the
 *     map; `enFor*` helpers below do this so we can render
 *     "通过 · PASS" / "本地 · local" badges when space permits.
 */

import type { EventType, Health, Status } from "./tower-data";

/* ============================================================ EVENT TYPE */
export const EVENT_TYPE_LABEL: Record<EventType, string> = {
  AGENT_REGISTERED:   "Agent 注册",
  PROJECT_REGISTERED: "项目注册",
  PHASE_REPORT:       "阶段",
  REVIEW_REPORT:      "复查",
  HANDOFF:            "交接",
  RELEASE:            "发布",
  FAILURE:            "失败",
  BLOCK:              "阻塞",
  UNBLOCK:            "解除阻塞",
  ARCHIVE:            "归档",
};

// Compact short labels — used in tight timeline rows.
export const EVENT_TYPE_SHORT: Record<EventType, string> = {
  AGENT_REGISTERED:   "AGENT",
  PROJECT_REGISTERED: "PROJ",
  PHASE_REPORT:       "阶段",
  REVIEW_REPORT:      "复查",
  HANDOFF:            "交接",
  RELEASE:            "发布",
  FAILURE:            "失败",
  BLOCK:              "阻塞",
  UNBLOCK:            "解除",
  ARCHIVE:            "归档",
};

export function eventTypeLabel(t: EventType): string {
  return EVENT_TYPE_LABEL[t] ?? t;
}

export function eventTypeShort(t: EventType): string {
  return EVENT_TYPE_SHORT[t] ?? t;
}

/* ============================================================ STATUS */
export const STATUS_LABEL: Record<Status, string> = {
  ACTIVE:   "进行中",
  PASS:     "通过",
  FAIL:     "失败",
  PARTIAL:  "部分完成",
  BLOCKED:  "阻塞",
  PAUSED:   "暂停",
  RELEASED: "已发布",
  ARCHIVED: "已归档",
};

export function statusLabel(s: Status): string {
  return STATUS_LABEL[s] ?? s;
}

/** "中文 · EN" badge — used on project / agent detail pills. */
export function statusBadge(s: Status): string {
  const cn = STATUS_LABEL[s];
  return cn && cn !== s ? `${cn} · ${s}` : s;
}

/* ============================================================ HEALTH */
export const HEALTH_LABEL: Record<Health, string> = {
  green:  "正常",
  yellow: "注意",
  red:    "异常",
  gray:   "未知",
};

export function healthLabel(h: Health): string {
  return HEALTH_LABEL[h] ?? h;
}

export function healthBadge(h: Health): string {
  const cn = HEALTH_LABEL[h];
  return cn && cn !== h ? `${cn} · ${h}` : h;
}

/* ============================================================ LOCATION */
export const LOCATION_LABEL: Record<string, string> = {
  local:   "本地",
  public:  "公开",
  private: "私有",
};

export function locationLabel(loc: string): string {
  return LOCATION_LABEL[loc] ?? loc;
}

/* ============================================================ CATEGORY */
export const CATEGORY_LABEL: Record<string, string> = {
  uncategorized: "未分类",
  translation:   "翻译",
  gallery:       "画廊",
  tool:          "工具",
  "ai-system":   "AI 系统",
};

export function categoryLabel(cat: string): string {
  return CATEGORY_LABEL[cat] ?? cat;
}

/* ============================================================ SUMMARY (homepage) */
export const SUMMARY_LABELS = {
  PROJECTS: "项目",
  AGENTS:   "Agent",
  EVENTS:   "事件",
  GREEN:    "正常",
  YELLOW:   "注意",
  RED:      "异常",
  BLOCKED:  "阻塞",
} as const;

/* ============================================================ FILTER BAR / PAGES */
export const UI = {
  navHome: "首页",
  navTimeline: "时间线",
  navHelp: "帮助",

  headerMeta: "多 Agent 项目进度控制塔 · Git 驱动 · Cloudflare Pages 部署",

  // Home
  homeTitle: "总览",
  projectsSection: "项目",
  agentsSection: "Agent",
  recentActivity: "最近活动（最新 10 条）",

  // Projects filter
  projectsSearchPlaceholder: "搜索项目名称、ID、仓库或摘要……",
  projectsHealthAll: "全部健康度",
  projectsStatusAll: "全部状态",
  projectsAgentsAll: "全部 Agent",
  projectsSortUpdated: "最近更新",
  projectsSortHealth: "健康度（异常优先）",
  projectsSortName: "名称 A–Z",
  projectsClear: "清除",
  projectsMatching: "条匹配",
  projectsEmpty: "没有匹配当前筛选条件的项目。",

  // Agents
  agentsRole: "角色",
  agentsLastProject: "最近项目",
  agentsEvents: "事件",
  agentsTotal: "总计",

  // Recent activity
  recentShown: "已显示",

  // Timeline
  timelineTitle: "所有事件（最新优先）",
  timelineTotal: "总计",
  timelineSearchPlaceholder: "搜索摘要、阶段或 Agent……",
  timelineEventTypeAll: "全部事件类型",
  timelineStatusAll: "全部状态",
  timelineProjectAll: "全部项目",
  timelineAgentAll: "全部 Agent",
  timelineSortNewest: "最新优先",
  timelineSortOldest: "最早优先",
  timelineClear: "清除",
  timelineMatching: "条匹配",
  timelineEmpty: "没有匹配当前筛选条件的事件。",

  // Project detail
  projectHeading: "项目",
  projectFieldId: "ID",
  projectFieldName: "名称",
  projectFieldRepo: "仓库",
  projectFieldLocation: "位置",
  projectFieldCategory: "分类",
  projectFieldStatus: "当前状态",
  projectFieldHealth: "健康度",
  projectFieldCurrentPhase: "当前阶段",
  projectFieldLastAgent: "最近 Agent",
  projectFieldLastEventAt: "最近事件时间",
  projectFieldEventCount: "事件数",
  projectLatestEvent: "最新事件",
  projectNoSummary: "（无摘要）",
  projectPhasePrefix: "阶段",
  projectNextActions: "下一步",
  projectNoNext: "暂无后续动作。",
  projectTimelineHeading: "时间线（按阶段分组）",
  projectTimelineCountTpl: (events: number, phases: number) =>
    `${events} 个事件 · ${phases} 个阶段`,
  projectNoEvents: "（暂无事件）",
  projectNoPhase: "（未分组）",

  // Agent detail
  agentHeading: "Agent",
  agentFieldId: "ID",
  agentFieldName: "名称",
  agentFieldMachine: "机器",
  agentFieldRole: "角色",
  agentFieldLastEventAt: "最近事件时间",
  agentFieldLastProject: "最近项目",
  agentFieldEventCount: "事件数",
  agentEventBreakdown: "事件类型分布",
  agentProjectsTouchedTpl: (n: number) => `参与项目（${n}）`,
  agentNoProjects: "（暂无项目）",
  agentActivityTimeline: "活动时间线",
  agentEventsTpl: (n: number) => `${n} 个事件`,
  agentNoEvents: "（暂无事件）",

  // Project / Agent row cards
  cardLocationPrefix: "位置",
  cardCategoryPrefix: "分类",
  cardLastAgentPrefix: "最近 Agent",
  cardEventsPrefix: "事件",
  cardNoEvents: "（暂无事件）",
  cardRolePrefix: "角色",
  cardLastProjectPrefix: "最近项目",

  // Timeline meta line
  tlMetaNoProject: "（无项目）",
  tlMetaNoAgent: "（无 Agent）",

  // Footer
  footerPrefix: "控制塔 dashboard · ACT-13B 中文化",

  // Help page
  helpTitle: "帮助 — 如何使用这个控制塔",
  helpDescription:
    "这是控制塔的中文操作手册：如何上报阶段、双门模型、public-data 更新检查清单，以及去哪里找完整文档。",
  helpReadonlyNotice:
    "这是公开只读面板。只有仓库维护者可以更新 public-data；普通访客无法将项目推送到本面板。",

  // Permission / boundary callouts
  permBoundaryTitle: "权限边界",
  permBoundaryBody:
    "只有拥有 conanxin/agent-project-control-tower 写权限的维护者，才能修改 public-data 并触发线上 Dashboard 部署。其他用户可以 fork 仓库、参考流程搭建自己的控制塔，或提交 Pull Request。任何 public-data 变更都必须经过维护者审核后才能合并。",
} as const;

/* ============================================================ HELPERS */

/** Map an English HEALTH_COLOR to a Chinese label; preserves original value
 *  for downstream comparisons. */
export function colorFromHealth(h: Health): "green" | "yellow" | "red" | "gray" {
  return h;
}

/** Render an optional Chinese · English badge pair. */
export function bilingual(cn: string, en: string): string {
  if (!cn || cn === en) return en;
  return `${cn} · ${en}`;
}
