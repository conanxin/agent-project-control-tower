"""
yaml_dumper.py — stdlib YAML dumper fallback used by
``scripts/export_public_data.py`` and
``scripts/build_public_data_candidate.py``.

Both scripts need to serialize ``list[dict[str, Any]]``
(the public-data registry shape) to YAML in environments
where:

  1. ``yaml_mini.dump`` is not available (yaml_mini is
     intentionally read-only), and
  2. PyYAML is not installed (e.g. a vanilla GitHub
     Actions runner).

This module provides :func:`dumper` which returns a
callable that produces YAML in the exact same shape as
``export_public_data.py``'s pre-ACT-9B output (so the
existing public-data trees do not need a re-format).

History:
  - ACT-8B: discovered the 2-space-list-item parser/dumper
    mismatch and applied a 4-space re-indent hotfix in
    ``export_public_data.py`` for the PyYAML fallback.
  - ACT-9B: generalized the same fix into this shared module
    and added a third (pure stdlib) fallback so the
    candidate workflow runs in CI without PyYAML.

Public API:
  - dumper() -> Callable[[Any], str]
"""
from __future__ import annotations

from typing import Any, Callable


def dumper() -> Callable[[Any], str]:
    """Return a callable ``_dump(obj) -> str`` that serializes
    a list-of-dicts to YAML.

    Tries three layers in order:

      1. ``yaml_mini.dump`` (typically absent; that's expected)
      2. ``PyYAML.safe_dump`` with the ACT-8B 4-space hotfix
      3. A pure-stdlib fallback for environments where
         neither helper is available.
    """
    # Layer 1: yaml_mini.dump (usually absent).
    try:
        from yaml_mini import dump as _dump  # type: ignore
        return _dump
    except Exception:
        pass

    # Layer 2: PyYAML with ACT-8B 4-space hotfix.
    try:
        import yaml  # type: ignore

        def _dump(obj: Any) -> str:
            raw = yaml.safe_dump(
                obj, sort_keys=False, allow_unicode=True,
            )
            # ACT-8B hotfix: yaml_mini parser mis-parses 2-space
            # nested list items as further top-level list
            # elements. PyYAML dumps with 2-space indent by
            # default; re-indent list items under `capabilities:`
            # to 4 spaces so the parser round-trips.
            out: list[str] = []
            in_caps = False
            for line in raw.splitlines():
                if line.strip() == "capabilities:":
                    out.append(line)
                    in_caps = True
                    continue
                if in_caps:
                    if line.startswith("  - "):
                        out.append("    " + line[2:])
                        continue
                    in_caps = False
                out.append(line)
            return "\n".join(out) + "\n"

        return _dump
    except Exception:
        pass

    # Layer 3: pure stdlib. Only handles list[dict[str, Any]]
    # (the public-data registry shape). 2-space indent for
    # map keys; 4-space indent for list items (matches the
    # ACT-8B round-trip contract).
    def _builtin_dump(obj: Any) -> str:
        lines: list[str] = []
        for entry in obj:
            if not isinstance(entry, dict):
                continue
            for k, v in entry.items():
                lines.extend(_dump_value(k, v, indent=0))
            lines.append("")
        return "\n".join(lines).rstrip("\n") + "\n"

    def _dump_value(
        key: str, value: Any, indent: int,
    ) -> list[str]:
        pad = "  " * indent
        if value is None:
            return [f"{pad}{key}: null"]
        if isinstance(value, bool):
            return [f"{pad}{key}: {'true' if value else 'false'}"]
        if isinstance(value, (int, float)):
            return [f"{pad}{key}: {value}"]
        if isinstance(value, str):
            v = value.replace("\\", "\\\\").replace('"', '\\"')
            return [f'{pad}{key}: "{v}"']
        if isinstance(value, list):
            if not value:
                return [f"{pad}{key}: []"]
            out_list: list[str] = []
            first = True
            for item in value:
                if first:
                    if isinstance(item, dict):
                        sub = _dump_dict(item, indent)
                        out_list.append(f"{pad}{key}:")
                        out_list.extend(sub)
                    else:
                        out_list.append(f"{pad}{key}: {_scalar(item)}")
                    first = False
                else:
                    if isinstance(item, dict):
                        sub = _dump_dict(item, indent)
                        out_list.extend(sub)
                    else:
                        # 4-space list item indent (ACT-8B).
                        out_list.append(f"{pad}    - {_scalar(item)}")
            return out_list
        if isinstance(value, dict):
            out_dict = [f"{pad}{key}:"]
            out_dict.extend(_dump_dict(value, indent + 1))
            return out_dict
        return [f"{pad}{key}: {_scalar(value)}"]

    def _dump_dict(
        d: dict[str, Any], indent: int,
    ) -> list[str]:
        out: list[str] = []
        for k, v in d.items():
            out.extend(_dump_value(k, v, indent))
        return out

    def _scalar(v: Any) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'

    return _builtin_dump
