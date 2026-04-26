"""Small YAML subset loader used when PyYAML is unavailable."""

from __future__ import annotations

from dataclasses import dataclass


class YAMLError(ValueError):
    """Raised when the fallback YAML parser cannot parse the input."""


def safe_load(text: str):
    """Parse a small YAML subset used by the project mapping files."""

    parser = _Parser(text)
    return parser.parse()


@dataclass
class _Line:
    indent: int
    text: str


class _Parser:
    def __init__(self, text: str) -> None:
        self._lines = self._prepare_lines(text)
        self._index = 0

    def parse(self):
        if not self._lines:
            return None
        value = self._parse_block(self._lines[0].indent)
        return value

    def _parse_block(self, indent: int):
        if self._index >= len(self._lines):
            return None
        line = self._lines[self._index]
        if line.indent != indent:
            raise YAMLError(f"Unexpected indentation at line: {line.text}")
        if line.text.startswith("- "):
            return self._parse_list(indent)
        return self._parse_dict(indent)

    def _parse_dict(self, indent: int) -> dict[str, object]:
        result: dict[str, object] = {}
        while self._index < len(self._lines):
            line = self._lines[self._index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise YAMLError(f"Unexpected indentation at line: {line.text}")
            if line.text.startswith("- "):
                raise YAMLError(f"Unexpected list entry at line: {line.text}")

            if ":" not in line.text:
                raise YAMLError(f"Expected key/value pair at line: {line.text}")
            key, rest = line.text.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            self._index += 1

            if rest:
                result[key] = _parse_scalar(rest)
                continue

            if self._index >= len(self._lines) or self._lines[self._index].indent <= indent:
                result[key] = {}
                continue

            result[key] = self._parse_block(self._lines[self._index].indent)

        return result

    def _parse_list(self, indent: int) -> list[object]:
        result: list[object] = []
        while self._index < len(self._lines):
            line = self._lines[self._index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise YAMLError(f"Unexpected indentation at line: {line.text}")
            if not line.text.startswith("- "):
                break

            item_text = line.text[2:].strip()
            self._index += 1
            if item_text:
                result.append(_parse_scalar(item_text))
                continue

            if self._index >= len(self._lines) or self._lines[self._index].indent <= indent:
                result.append(None)
                continue
            result.append(self._parse_block(self._lines[self._index].indent))

        return result

    @staticmethod
    def _prepare_lines(text: str) -> list[_Line]:
        lines: list[_Line] = []
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            lines.append(_Line(indent=indent, text=stripped))
        return lines


def _parse_scalar(value: str):
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "none", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
