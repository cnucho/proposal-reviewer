from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from .utils import read_json


@dataclass
class ValidationReport:
    ok: bool
    checked: int
    failures: list[str]

    def to_text(self) -> str:
        lines = [f"checked={self.checked}", f"ok={self.ok}"]
        lines.extend(self.failures or ["All validated files passed."])
        return "\n".join(lines)


def _validator(root: Path, schema_name: str) -> Draft202012Validator:
    schema = read_json(root / "schemas" / schema_name)
    return Draft202012Validator(schema)


def validate_project(root: str | Path) -> ValidationReport:
    root = Path(root).resolve()
    failures: list[str] = []
    checked = 0
    targets = [
        ("requests/*.json", "review_request_v1.schema.json"),
        ("results/*.json", "review_result_v1.schema.json"),
    ]
    for pattern, schema_name in targets:
        validator = _validator(root, schema_name)
        for path in sorted(root.glob(pattern)):
            checked += 1
            data = read_json(path)
            errors = sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path))
            for error in errors:
                where = ".".join(str(part) for part in error.absolute_path) or "$"
                failures.append(f"{path.relative_to(root).as_posix()}: {where}: {error.message}")
    return ValidationReport(ok=not failures, checked=checked, failures=failures)
