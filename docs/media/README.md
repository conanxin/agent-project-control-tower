# Media Assets

Public-facing images and videos for the Agent Project Control Tower.

## v0.1.0

**Online source**: <https://control-tower.conanxin.com/> (Cloudflare Pages, custom domain)

**Capture method**: Playwright 1.58 + Chromium 1.5× DPI capture, 2026-06-12.

**Capture script** (one-shot, not committed): `/tmp/capture_v010_screenshots.py` — feel free to re-run on a future revision to refresh.

### Files in `v0.1.0/`

| File | Source URL | Viewport | Notes |
|---|---|---|---|
| `dashboard-home.png` | `/` | 1440×900 desktop | Home with 3 projects + 2 agents + events |
| `dashboard-home-mobile.png` | `/` | 390×844 mobile | Mobile home (full page) |
| `dashboard-timeline.png` | `/timeline/` | 1440×900 desktop | Cross-project timeline |
| `project-agent-control-tower.png` | `/projects/agent-project-control-tower/` | 1440×900 desktop | Tower self-tracking page |
| `project-booktrans-desk.png` | `/projects/booktrans-desk/` | 1440×900 desktop | Third real project — S13 / 16f38b6 / PARTIAL |
| `agent-cloud-openclaw.png` | `/agents/cloud-openclaw/` | 1440×900 desktop | VPS secondary agent page |

### How to refresh

```bash
# 1. Make sure playwright + chromium are installed
python3 -c "from playwright.sync_api import sync_playwright; sync_playwright().start().chromium.launch()"

# 2. Re-run the capture (re-creates every PNG in-place)
python3 /tmp/capture_v010_screenshots.py

# 3. Verify they look right (open in any image viewer)
xdg-open docs/media/v0.1.0/dashboard-home.png
```

### Deferred

- `demo-flow.gif` — interactive demo is **deferred**. The static screenshots above cover the visual release needs; a GIF walkthrough is nice-to-have for v0.2.0+.
- Each project's full event list screenshot — current pages already embed it; no separate asset needed.
