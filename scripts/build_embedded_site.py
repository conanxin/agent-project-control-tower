"""
build_embedded_site.py — produce a self-contained, double-clickable dashboard.

Reads:
  generated/index.json
  site/index.html

Writes:
  site/index.embedded.html

The embedded file is `site/index.html` with the JSON inlined into a
`<script>window.__TOWER_DATA__ = {...};</script>` block. When opened via
file:// (or any HTTP origin), the page reads the inlined data instead of
attempting fetch, so there are no CORS / file-protocol failures.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INDEX_JSON = ROOT / "generated" / "index.json"
TEMPLATE_HTML = ROOT / "site" / "index.html"
EMBEDDED_HTML = ROOT / "site" / "index.embedded.html"


def main() -> int:
    if not INDEX_JSON.exists():
        print(f"  [FAIL] {INDEX_JSON} not found. Run `make build` first.")
        return 1
    if not TEMPLATE_HTML.exists():
        print(f"  [FAIL] {TEMPLATE_HTML} not found.")
        return 1

    with open(INDEX_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    inline = (
        "<script>\n"
        "// Inlined by build_embedded_site.py for offline / file:// use\n"
        "window.__TOWER_DATA__ = "
        + json.dumps(data, ensure_ascii=False)
        + ";\n"
        "</script>\n"
    )

    # Insert right before the existing <script> block that contains
    # `async function loadData()`. Inserting *before* keeps the existing
    # loader untouched; loadData() prefers window.__TOWER_DATA__ when set.
    marker = "  <script>\n    // -------- data loader"
    if marker not in html:
        # Fallback: insert before </body>
        marker_close = "</body>"
        if marker_close not in html:
            print("  [FAIL] template HTML missing expected marker")
            return 1
        out = html.replace(marker_close, inline + marker_close, 1)
    else:
        out = html.replace(marker, inline + marker, 1)

    EMBEDDED_HTML.write_text(out, encoding="utf-8")
    size_kb = EMBEDDED_HTML.stat().st_size / 1024
    print(f"  wrote {EMBEDDED_HTML.relative_to(ROOT)} ({size_kb:.1f} KB)")
    print("  open with: xdg-open site/index.embedded.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
