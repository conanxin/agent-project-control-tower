"""
build_embedded_site.py — produce a self-contained, double-clickable dashboard.

Reads:
  generated/index.json   (produced by build_index.py)
  site/index.html        (template)

Writes:
  site/index.embedded.html

The embedded file is `site/index.html` with the JSON inlined into a
`<script>window.__TOWER_DATA__ = {...};</script>` block. When opened via
file:// (or any HTTP origin), the page reads the inlined data instead of
attempting fetch, so there are no CORS / file-protocol failures.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INDEX_JSON = ROOT / "generated" / "index.json"
TEMPLATE_HTML = ROOT / "site" / "index.html"
EMBEDDED_HTML = ROOT / "site" / "index.embedded.html"


def main() -> int:
    p = argparse.ArgumentParser(description="build embedded dashboard")
    p.add_argument(
        "--index",
        default=str(INDEX_JSON),
        help="path to index.json (default: generated/index.json)",
    )
    p.add_argument(
        "--template",
        default=str(TEMPLATE_HTML),
        help="path to template HTML (default: site/index.html)",
    )
    p.add_argument(
        "--output",
        default=str(EMBEDDED_HTML),
        help="output path (default: site/index.embedded.html)",
    )
    args = p.parse_args()

    index_path = Path(args.index)
    template_path = Path(args.template)
    output_path = Path(args.output)

    if not index_path.exists():
        print(f"  [FAIL] {index_path} not found. Run `build` first.")
        return 1
    if not template_path.exists():
        print(f"  [FAIL] {template_path} not found.")
        return 1

    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    inline = (
        "<script>\n"
        "// Inlined by build_embedded_site.py for offline / file:// use\n"
        "window.__TOWER_DATA__ = "
        + json.dumps(data, ensure_ascii=False)
        + ";\n"
        "</script>\n"
    )

    marker = "  <script>\n    // -------- data loader"
    if marker not in html:
        marker_close = "</body>"
        if marker_close not in html:
            print("  [FAIL] template HTML missing expected marker")
            return 1
        out = html.replace(marker_close, inline + marker_close, 1)
    else:
        out = html.replace(marker, inline + marker, 1)

    output_path.write_text(out, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"  wrote {output_path.relative_to(ROOT)} ({size_kb:.1f} KB)")
    print("  open with: xdg-open site/index.embedded.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
