"""Validate every PBIR/PBIP JSON in the repo against Microsoft's official schemas.

CI only (needs `pip install jsonschema` and a clone of microsoft/json-schemas):
    python _sistema/testes/check_schemas.py <path-to-json-schemas-clone>
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

BASE = "https://developer.microsoft.com/json-schemas/fabric/"
LOCAL = Path(sys.argv[1]) / "fabric"
SKIP = ("BaseThemes", "RegisteredResources", "catalogo.json", "extraction.json")


def retrieve(uri: str) -> Resource:
    return Resource.from_contents(json.loads((LOCAL / uri.replace(BASE, "")).read_text(encoding="utf-8")),
                                  default_specification=DRAFT7)


registry = Registry(retrieve=retrieve)
checked = errors = 0
for f in Path(".").rglob("*"):
    if not f.is_file() or any(s in str(f) for s in SKIP) or ".git" in f.parts:
        continue
    if f.suffix not in {".json", ".pbir", ".pbism", ".pbip"} and f.name != ".platform":
        continue
    data = json.loads(f.read_text(encoding="utf-8"))
    uri = data.get("$schema") if isinstance(data, dict) else None
    if not uri or not uri.startswith(BASE):
        continue
    schema = json.loads((LOCAL / uri.replace(BASE, "")).read_text(encoding="utf-8"))
    checked += 1
    for e in Draft7Validator(schema, registry=registry).iter_errors(data):
        errors += 1
        print(f"{f}: {e.message[:200]} at {list(e.path)}")
print(f"{checked} files checked against official schemas, {errors} error(s)")
sys.exit(1 if errors or not checked else 0)
