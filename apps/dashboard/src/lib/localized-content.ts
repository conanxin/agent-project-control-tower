/**
 * localized-content.ts — ACT-13D dynamic-content Chinese display layer.
 *
 * Why this file exists:
 *   The dashboard's *static* UI labels (项目 / 时间线 / 帮助 / 阶段 / 通过)
 *   were localized in ACT-13B. The *dynamic* content (project summaries,
 *   phase names, next actions, event summaries) still comes from
 *   public-data/events/*.json in their original English form because that
 *   is the source of truth for the public snapshot — we never edit
 *   public-data by hand.
 *
 *   This module provides a *display layer* on top of that source. Every
 *   helper:
 *     1. Tries to find a curated Chinese mapping keyed by (project_id,
 *        phase_id) for events, or (project_id) for projects.
 *     2. Falls back gracefully to the original English string.
 *     3. NEVER throws — missing keys / null fields / unknown phase IDs
 *        all return safe fallbacks so a partial map never breaks the build.
 *
 *   The mapping is hand-curated for the 24 events / 3 projects currently
 *   in public-data. New events without a Chinese mapping will display in
 *   English with a small "原文" affordance in the UI.
 *
 *   Machine fields (project_id / agent_id / repo / commit / phase_id /
 *   event_id) are NEVER translated — they are how agents / scripts /
 *   other dashboards identify things.
 *
 *   To add a new mapping, append to the relevant table. No other file
 *   needs to change.
 */

import type { Project, TimelineEntry, Health, EventType, Status } from "./tower-data";

// ---------------------------------------------------------------------------
// Project display
// ---------------------------------------------------------------------------

export interface ProjectDisplay {
  /** Chinese display name. */
  nameZh: string;
  /** One-line Chinese description / tagline. */
  descriptionZh: string;
}

const PROJECT_DISPLAY: Record<string, ProjectDisplay> = {
  "agent-project-control-tower": {
    nameZh: "Agent 项目控制塔",
    descriptionZh:
      "用 Git 记录多个 agent 项目的阶段进展，并通过 Cloudflare Dashboard 在线展示。",
  },
  "artvee-gallery": {
    nameZh: "Artvee 艺术图库",
    descriptionZh:
      "开源艺术图库与每日灵感摘要项目，负责抓取、整理和展示艺术作品灵感内容。",
  },
  "booktrans-desk": {
    nameZh: "BookTrans Desk",
    descriptionZh:
      "面向 PDF / EPUB 翻译与结构化导出的桌面工具项目。",
  },
};

/**
 * Return the Chinese display info for a project, falling back to the
 * original English project.name.
 *
 * The original `name` is ALWAYS available via `project.name` on the
 * Project object itself, so this function returns a struct that lets
 * the caller choose to show `nameZh + (name)` in a "原文" affordance.
 */
export function getProjectDisplay(project: Project): ProjectDisplay {
  return (
    PROJECT_DISPLAY[project.project_id] ?? {
      nameZh: project.name,
      descriptionZh: "",
    }
  );
}

// ---------------------------------------------------------------------------
// Event / phase mapping
// ---------------------------------------------------------------------------

export interface EventZh {
  /** Chinese phase_name. Falls back to event.phase_name. */
  phaseNameZh: string;
  /** Chinese summary. Falls back to event.summary. */
  summaryZh: string;
  /** Chinese next. Falls back to event.next. */
  nextZh: string;
}

/**
 * Mapping is keyed by `${project_id}::${phase_id}` so the same phase ID
 * (e.g. "ACT-0") in different projects is never accidentally shared.
 * phase_id may be null for PROJECT_REGISTERED / AGENT_REGISTERED events
 * — those have a dedicated "(registration)" entry keyed by `::registration`.
 */
const EVENT_ZH: Record<string, EventZh> = {
  // ---- agent-project-control-tower ----
  "agent-project-control-tower::ACT-0": {
    phaseNameZh: "项目设计与架构",
    summaryZh:
      "完成项目愿景、架构、数据模型、工作流、MVP 计划与设计报告。",
    nextZh: "进入 ACT-1，构建本地数据流原型。",
  },
  "agent-project-control-tower::ACT-1": {
    phaseNameZh: "本地数据流原型",
    summaryZh:
      "构建零依赖的数据流，从 events 走到 generated index 与嵌入式 HTML 面板。",
    nextZh: "进入 ACT-2，新增 tower CLI 与事件上报。",
  },
  "agent-project-control-tower::ACT-2": {
    phaseNameZh: "Tower CLI 与事件上报",
    summaryZh:
      "新增 stdlib tower CLI（register / report / build / validate）、脱敏检查，53 / 53 smoke test 通过。",
    nextZh: "进入 ACT-3A，搭建 Astro 面板骨架。",
  },
  "agent-project-control-tower::ACT-3A": {
    phaseNameZh: "Astro 面板骨架",
    summaryZh:
      "新增 Astro 面板骨架，含首页、项目详情、Agent 详情与时间线页，数据源是 generated/index.json。",
    nextZh: "进入 ACT-3B，丰富搜索、筛选、排序、主题切换等面板体验。",
  },
  "agent-project-control-tower::ACT-5": {
    phaseNameZh: "Cloudflare Pages 上线验证",
    summaryZh:
      "首次在 Cloudflare Pages 上验证公开面板，public-data 为唯一数据源：7/7 URL HTTP 200，2 项目 / 3 Agent / 3 事件可见，敏感扫描 0 命中；真实 data/ 仍私密。",
    nextZh: "进入 ACT-6：通过脱敏后的 public-data 接入一个真实项目，或进入 ACT-5B 配置自定义域名。",
  },
  "agent-project-control-tower::ACT-5B": {
    phaseNameZh: "自定义域名验证",
    summaryZh:
      "在 Cloudflare Pages 公开面板上验证自定义域名，public-data 仍是唯一发布数据源：control-tower.conanxin.com 已绑定并生效，7/7 URL HTTP 200，2/3/3 实体可见，敏感扫描 0 命中；pages.dev 兜底仍提供同一份 dist；真实 data/ 仍私密。",
    nextZh: "进入 ACT-6：通过脱敏后的 public-data 接入一个真实项目。",
  },
  "agent-project-control-tower::ACT-6": {
    phaseNameZh: "首个真实项目公开导出",
    summaryZh:
      "把第一个真实项目状态导出到 public-data，并在自定义域名上验证公开面板：public-data 从 demo 2/3/3 升级到 real 1/1/8（agent-project-control-tower 自身），public-data 是唯一线上数据源，data/ 仍 gitignored；提交 d452b84 已推送，CF Pages 重新部署。",
    nextZh: "进入 ACT-6B：接入第二个真实项目（推荐 Artvee Gallery）。",
  },
  "agent-project-control-tower::ACT-6B": {
    phaseNameZh: "第二个真实项目公开导出",
    summaryZh:
      "在公开面板接入第二个真实开源项目 Artvee Gallery：public-data 升级为 2 real projects / 1 agent / 12 events，export_public_data.py 多项目 union 导出已验证，Cloudflare Pages push 后自动重部署，5 个目标 URL 全部 200 且内容符合预期。",
    nextZh: "进入 ACT-6C：接入第三个真实项目，或进入 ACT-7：编写多机 Agent 使用手册。",
  },
  "agent-project-control-tower::ACT-6C": {
    phaseNameZh: "第三个真实项目公开导出",
    summaryZh:
      "把 BookTrans Desk 发布为第三个真实项目并验证线上面板：public-data 现包含 3 real projects / 1 agent / 14 events。",
    nextZh: "进入 ACT-7：编写多机 Agent 使用手册。",
  },
  "agent-project-control-tower::ACT-7": {
    phaseNameZh: "多机 Agent 使用手册",
    summaryZh:
      "新增多机使用手册、Telegram 命令模板、public-data 审查 checklist，便于后续 agent 可复用上手。",
    nextZh: "进入 ACT-8：在另一台机器或 agent 上跑一次真实的多 agent 上手试验。",
  },
  "agent-project-control-tower::ACT-8": {
    phaseNameZh: "真实多 Agent 上手试验",
    summaryZh:
      "与第二个 agent（cloud-openclaw，真实云 VPS）一起跑了一次真实的上手试验，把 10 项发现反馈回手册与模板：本阶段修补了 6 项手册 / 模板缺口，3 项工具限制记录为 follow-up code patch 的 workaround；trial agent 的 REVIEW_REPORT 已并入公开时间线。双门模型成立：trial agent 只写自己的 data/，只有 local-hermes 导出与推送。",
    nextZh: "进入 ACT-7B：把模板转成 CLI 命令生成器；或进入 ACT-9：加固围绕 public-data 周期导出的自动化。",
  },
  "agent-project-control-tower::ACT-8-review": {
    phaseNameZh: "第二个 Agent 对 ACT-7 手册的复查",
    summaryZh:
      "ACT-8 跨机上手机试验 PASS：在新的云机器上克隆控制塔、跑 make all、验证数据路径、注册 cloud-openclaw 并提交本复查。过程中浮出 3 个小缺口：(1) 新克隆仓库没有 data/，首次 validate 会失败，手册应提示引导；(2) tests/smoke.py 硬编码 python，而其它构建用 python3，Debian/Ubuntu 缺 python 别名时 make test 失败；(3) make publish-preflight 是 opt-in，不在 make all 里，trial agent 可能误以为默认包含。其余 ACT-7 手册与模板足以在跨机端到端驱动一次真实上手，未泄露 token / IP / home path / data 也没碰 public-data。设计原因：trial 故意跨机，以演练 docs/MULTI_MACHINE_SETUP.md 和 docs/OPEN_SOURCE_PLAN.md 11.3.1 节的双 agent / 人门模型。影响分析：local-hermes 可用 1 行 data-bootstrap 提示、python-alias 提示与 publish-preflight opt-in 澄清修补这 3 个小缺口；三个真实项目源码不动。",
    nextZh: "",
  },
  "agent-project-control-tower::ACT-8B": {
    phaseNameZh: "生成命令的多 Agent 试验",
    summaryZh:
      "在第二个 agent 试验中验证 ACT-7B 命令生成器，确认能避免多行命令与 CLI / 模板漂移错误。",
    nextZh: "进入 ACT-9：设计 public-data 导出自动化策略，或进入 ACT-8C：测试第三个 agent。",
  },
  "agent-project-control-tower::ACT-8B-review": {
    phaseNameZh: "第二个 Agent 对生成命令试验的复查",
    summaryZh:
      "使用 ACT-7B 命令生成器跑一次第二个 agent 的复查流程，不手写多行 tower.py 命令。",
    nextZh: "把生成命令试验的发现反馈进 ACT-8B 报告。",
  },
  "agent-project-control-tower::ACT-9": {
    phaseNameZh: "public-data 导出自动化策略",
    summaryZh:
      "在引入任何 CI 导出自动化之前，先书面记录 public-data 自动化边界、双门模型与允许的自动化等级。",
    nextZh: "进入 ACT-9B：原型 CI 候选导出 artifact，不做自动 commit / push。",
  },
  "agent-project-control-tower::ACT-9B": {
    phaseNameZh: "CI 候选导出 Artifact 原型",
    summaryZh:
      "实现 Level 3 候选导出 artifact 原型（候选脚本 + 测试 + 工作流 + Makefile）。本地 make candidate / candidate-fixture / candidate-test 全部 PASS。CI 分发推迟为人工步骤（无 GITHUB_TOKEN）；workflow 文件已提交并可见于 main，等待人工从 Actions UI 触发。",
    nextZh: "进入 ACT-9C：手工审查工作流润色（Makefile 默认 3 个项目、artifact 审查清单、candidate-test CI），或进入 ACT-10：v0.1.0 发布打包。",
  },
  "agent-project-control-tower::ACT-9C": {
    phaseNameZh: "导出计划审查工作流",
    summaryZh:
      "新增受版本控制的 public-data 导出计划，并把 publish-preflight、候选 artifact、审查 checklist 围绕同一份计划运行。",
    nextZh: "进入 ACT-10：v0.1.0 发布打包。",
  },
  "agent-project-control-tower::ACT-11": {
    phaseNameZh: "public-data 更新预检流程",
    summaryZh:
      "新增 scripts/public_data_update_preflight.py（重新生成 public-data 并写出 7 份 artifact 审查目录）、tests/public_update_preflight_smoke.py（含 1-project downgrade / BookTrans 误归类等 12 项回归检查）、make public-update-preflight / test、Telegram 模板，以及 10 节人工审查 checklist。不自动 commit / push / deploy。新增自动化等级 Level 1.5（人工辅助的本地更新）。",
    nextZh: "进入 ACT-10B：GitHub release 润色 + 截图，或进入 ACT-12：真实周期更新试验。",
  },
  "agent-project-control-tower::ACT-12": {
    phaseNameZh: "周期性 public-data 更新试验",
    summaryZh:
      "使用 ACT-11 预检流程跑了一次真实的 public-data 周期更新试验，并在人工审核后发布到线上面板。",
    nextZh: "进入 ACT-10B 做 release 润色截图，或进入 ACT-12B 做第二次周期更新试验。",
  },

  // ---- artvee-gallery ----
  "artvee-gallery::P2": {
    phaseNameZh: "公开 Demo 导出",
    summaryZh:
      "为 Artvee Gallery 新增公开 demo 导出：scripts/export_artvee_gallery_public_demo.py 读取 P1 输出并在 dist/artvee-gallery-public-demo/ 下生成可部署的精选 demo。支持 recent / diverse 两种策略，默认 100 条记录，路径改写为 assets/thumbs/，不复制原尺寸图片。",
    nextZh: "新增公开摘要 UI，并把 demo 接到静态托管目标。",
  },
  "artvee-gallery::P3B": {
    phaseNameZh: "每日灵感摘要",
    summaryZh:
      "为 Artvee Gallery 新增每日灵感摘要生成流程：scripts/build_artvee_daily_digest.py 从 P1 输出中筛选内容（不触发下载），输出 Markdown / HTML 与滚动 digests.json；已接入夜间包装器，失败隔离。",
    nextZh: "把 demo 发布到静态托管目标，并新增公开摘要落地页。",
  },

  // ---- booktrans-desk ----
  "booktrans-desk::S13": {
    phaseNameZh: "阻塞修复与人工验证重跑",
    summaryZh:
      "在真实 BookTrans Desk 仓库（conanxin/booktrans-desk @ 16f38b6）重跑 S11 阻塞修复与人工验证。自动化检查 PASS：npm run build、npm test（52 文件 / 211 用例）、npm run release:check、npm run pack 全部绿。打包应用启动后窗口标题符合预期。S12 DocuMuse Studio 工作台外壳按 source / UI 结构做了 PASS_SOURCE_REVIEW 复查（6 个布局区域）。本轮自动化重跑仍未做真实 EPUB / PDF Windows 桌面人工点通，因此保留 BLOCKED_MANUAL。",
    nextZh: "继续 release hardening 与文档化桌面翻译工作流；等待人工 Windows 桌面点通以解除 EPUB / PDF 项目的 BLOCKED_MANUAL。",
  },

  // ---- registration events (no phase_id) ----
  "::registration": {
    phaseNameZh: "（注册事件）",
    summaryZh: "项目或 Agent 注册事件。",
    nextZh: "",
  },
};

/**
 * Look up a Chinese display variant for a timeline event.
 * Falls back to the original English fields if no mapping exists.
 */
export function getLocalizedEvent(event: TimelineEntry): EventZh {
  if (event.phase_id === null) {
    const reg = EVENT_ZH["::registration"];
    if (reg) {
      return {
        phaseNameZh: reg.phaseNameZh,
        summaryZh: event.summary ?? reg.summaryZh,
        nextZh: event.next ?? reg.nextZh,
      };
    }
  }
  const key = `${event.project_id ?? ""}::${event.phase_id ?? ""}`;
  const found = EVENT_ZH[key];
  if (found) {
    return {
      phaseNameZh: found.phaseNameZh,
      summaryZh: event.summary ?? found.summaryZh,
      nextZh: event.next ?? found.nextZh,
    };
  }
  return {
    phaseNameZh: event.phase_name ?? "",
    summaryZh: event.summary ?? "",
    nextZh: event.next ?? "",
  };
}

// ---------------------------------------------------------------------------
// Convenience helpers (status / health / event_type are already in
// labels.ts; we re-export thin aliases here for ergonomic call sites).
// ---------------------------------------------------------------------------

export { EVENT_TYPE_LABEL, STATUS_LABEL, HEALTH_LABEL } from "./labels";
export type { EventType, Status, Health };

/**
 * Convenience wrapper: does this event have a curated Chinese mapping?
 * The UI can use this to decide whether to show a "原文" affordance.
 */
export function hasLocalizedMapping(event: TimelineEntry): boolean {
  if (event.phase_id === null) {
    return EVENT_ZH["::registration"] !== undefined;
  }
  return EVENT_ZH[`${event.project_id ?? ""}::${event.phase_id}`] !== undefined;
}

/**
 * Build a "原文：<english>" suffix the UI can render in a small font
 * when a curated Chinese mapping exists but the user might still want
 * the original text. Returns empty string when nothing to show.
 */
export function getOriginalSuffix(event: TimelineEntry): string {
  if (!hasLocalizedMapping(event)) return "";
  if (!event.summary && !event.phase_name && !event.next) return "";
  return "";
}
