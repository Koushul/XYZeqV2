"""Minimal YAML subset loader (no PyYAML required).

Supports mappings, sequences, scalars, comments, and nested indentation.
Enough for simpleleaf sample configs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if not s or s in ("null", "~", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    try:
        if s.startswith("0") and len(s) > 1 and "." not in s:
            raise ValueError
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    out = []
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out).rstrip()


def loads(text: str) -> Any:
    lines = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.lstrip(" ")))

    def parse_block(i: int, indent: int) -> tuple[Any, int]:
        if i >= len(lines):
            return None, i
        _, content = lines[i]
        if content.startswith("- "):
            return parse_list(i, indent)
        return parse_map(i, indent)

    def parse_list(i: int, indent: int) -> tuple[list, int]:
        items: list[Any] = []
        while i < len(lines):
            ind, content = lines[i]
            if ind < indent:
                break
            if ind > indent:
                raise ValueError(f"Unexpected indent at list item: {content}")
            if not content.startswith("- "):
                break
            rest = content[2:].strip()
            i += 1
            if rest == "" or rest.endswith(":"):
                child_indent = lines[i][0] if i < len(lines) else indent + 2
                if rest.endswith(":"):
                    key = rest[:-1].strip()
                    child, i = parse_block(i, child_indent)
                    items.append({key: child})
                else:
                    child, i = parse_block(i, child_indent)
                    items.append(child)
            elif ":" in rest and not (rest.startswith('"') or rest.startswith("'")):
                # inline map start on list item: "key: value" then maybe nested
                key, _, val = rest.partition(":")
                key = key.strip()
                val = val.strip()
                if val == "":
                    child, i = parse_block(i, indent + 2)
                    items.append({key: child})
                else:
                    node: dict[str, Any] = {key: _parse_scalar(val)}
                    while i < len(lines):
                        nind, ncontent = lines[i]
                        if nind <= indent:
                            break
                        if ncontent.startswith("- "):
                            break
                        if ":" not in ncontent:
                            break
                        k, _, v = ncontent.partition(":")
                        k, v = k.strip(), v.strip()
                        if v == "":
                            child, i = parse_block(i + 1, nind + 2)
                            node[k] = child
                        else:
                            node[k] = _parse_scalar(v)
                            i += 1
                    items.append(node)
            else:
                items.append(_parse_scalar(rest))
        return items, i

    def parse_map(i: int, indent: int) -> tuple[dict, int]:
        node: dict[str, Any] = {}
        while i < len(lines):
            ind, content = lines[i]
            if ind < indent:
                break
            if ind > indent:
                raise ValueError(f"Unexpected indent at key: {content}")
            if content.startswith("- "):
                break
            if ":" not in content:
                raise ValueError(f"Expected key: value, got: {content}")
            key, _, val = content.partition(":")
            key, val = key.strip(), val.strip()
            i += 1
            if val == "":
                if i < len(lines) and lines[i][0] > indent:
                    child, i = parse_block(i, lines[i][0])
                    node[key] = child
                else:
                    node[key] = None
            else:
                node[key] = _parse_scalar(val)
        return node, i

    if not lines:
        return {}
    data, _ = parse_block(0, lines[0][0])
    return data


def load(path: str | Path) -> Any:
    path = Path(path)
    text = path.read_text()
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        return loads(text)
