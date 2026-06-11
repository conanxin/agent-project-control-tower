"""
yaml_mini.py — a tiny YAML reader for ACT-1.

Supports the subset used by examples/projects.yml and examples/agents.yml:

  - Top-level: list of mappings, or single mapping
  - Keys are strings
  - Values: string, int, float, bool, null, inline list [a, b, c]
  - List items:
      * mapping: `- key: value` (rest of mapping on following indented lines)
      * scalar:  `- value`
  - Comments: full-line `# ...` and inline `# ...` after a value
  - Indentation: 2-space increments
  - Quoted strings: "..." or '...'
  - Booleans: true/false/yes/no (case-insensitive)
  - Null: null/~/None (case-insensitive)

If the file format outgrows this, ACT-2 will replace it with PyYAML.
"""
from __future__ import annotations

import re
from typing import Any


class YAMLError(ValueError):
    pass


_BOOL_TRUE = {"true", "yes", "on"}
_BOOL_FALSE = {"false", "no", "off"}
_NULL = {"null", "~", "none"}


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def _coerce_scalar(raw: str) -> Any:
    s = raw.strip()
    if not s:
        return ""
    if (s.startswith('"') and s.endswith('"')) or (
        s.startswith("'") and s.endswith("'")
    ):
        return s[1:-1]
    low = s.lower()
    if low in _BOOL_TRUE:
        return True
    if low in _BOOL_FALSE:
        return False
    if low in _NULL:
        return None
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(p.strip()) for p in inner.split(",")]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _split_kv(content: str) -> tuple[str, str]:
    if ":" not in content:
        return content.strip(), ""
    k, _, v = content.partition(":")
    return k.strip(), v.strip()


def _peek_dash_indent(line: str) -> int | None:
    """Return the indent of the `-` token if line starts a list item, else None.

    A line is a list-item start when:
      - the first non-space char is `-`
      - the next char is a space OR the line ends (so we don't confuse `-foo`
        which is a string with `- foo` which is a list marker)
    """
    s = line.lstrip(" ")
    if not s.startswith("-"):
        return None
    if len(s) > 1 and s[1] not in (" ", "\t"):
        return None
    return _indent_of(line)


class _Parser:
    def __init__(self, lines: list[str]):
        self.lines = lines
        self.pos = 0

    def done(self) -> bool:
        return self.pos >= len(self.lines)

    def cur(self) -> str:
        return self.lines[self.pos]

    def advance(self) -> None:
        self.pos += 1

    # ----- top-level entry -------------------------------------------------

    def parse(self) -> Any:
        if not self.lines:
            return None
        ind = _indent_of(self.lines[0])
        if _peek_dash_indent(self.lines[0]) is not None:
            return self._parse_seq(ind)
        # Mapping
        return self._parse_map(ind)

    # ----- list ------------------------------------------------------------

    def _parse_seq(self, indent: int) -> list[Any]:
        """Parse a list whose dash items are at exactly `indent`."""
        out: list[Any] = []
        while not self.done():
            line = self.cur()
            dash_ind = _peek_dash_indent(line)
            if dash_ind is None or dash_ind < indent:
                break
            if dash_ind > indent:
                # This line is indented deeper than our dash level but not
                # starting with a dash — it's a continuation of the previous
                # list item's mapping. Stop the list.
                break
            # dash_ind == indent
            content = line[dash_ind + 1 :].lstrip()  # skip the `-`
            if ":" in content and not content.startswith("["):
                # Mapping list item
                k, v = _split_kv(content)
                item: dict[str, Any] = {k: _coerce_scalar(v) if v else None}
                self.advance()
                # Always absorb continuation (other k:v pairs and nested
                # list/mapping values), even if `v` was set inline. The
                # next lines at indent > dash_ind belong to this item.
                self._absorb_mapping(item, dash_ind + 2)
                out.append(item)
            else:
                # Scalar list item
                self.advance()
                out.append(_coerce_scalar(content))
        return out

    # ----- mapping body ----------------------------------------------------

    def _absorb_mapping(self, target: dict[str, Any], min_indent: int) -> None:
        """Read key:value pairs into `target` until a line at indent < min_indent
        appears, or the end of input. Nested lists/mappings become values of
        the most-recent key."""
        while not self.done():
            line = self.cur()
            cur_ind = _indent_of(line)
            if cur_ind < min_indent:
                return
            # A nested list?
            dash_ind = _peek_dash_indent(line)
            if dash_ind is not None and dash_ind >= min_indent:
                last_key = next(reversed(list(target.keys())))
                target[last_key] = self._parse_seq(dash_ind)
                return
            content = line[cur_ind:]
            if ":" not in content:
                # Unknown line; stop here to be safe
                return
            k, v = _split_kv(content)
            if v:
                target[k] = _coerce_scalar(v)
                self.advance()
            else:
                # Value on following lines
                self.advance()
                if self.done():
                    target[k] = None
                    return
                nxt = self.cur()
                nxt_ind = _indent_of(nxt)
                nxt_dash = _peek_dash_indent(nxt)
                if nxt_ind > cur_ind and nxt_dash is not None:
                    target[k] = self._parse_seq(nxt_dash)
                elif nxt_ind > cur_ind and ":" in nxt:
                    sub: dict[str, Any] = {}
                    self._absorb_mapping(sub, nxt_ind)
                    target[k] = sub
                else:
                    target[k] = None

    def _parse_map(self, min_indent: int) -> dict[str, Any]:
        out: dict[str, Any] = {}
        self._absorb_mapping(out, min_indent)
        return out


def loads(text: str) -> Any:
    raw_lines = text.splitlines()
    cleaned: list[str] = []
    for ln in raw_lines:
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cleaned.append(_strip_comment(ln))
    return _Parser(cleaned).parse()


def load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return loads(f.read())


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python yaml_mini.py <file.yml>")
        sys.exit(1)
    print(json.dumps(load(sys.argv[1]), indent=2, ensure_ascii=False))
