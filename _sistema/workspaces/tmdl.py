"""Minimal, tolerant TMDL reader — enough for documentation and governance checks.

It does NOT aim to be a full TMDL parser (use Tabular Editor / the Power BI Modeling MCP
for that). It reads tables, columns, measures, partitions, relationships and model
annotations from a PBIP `*.SemanticModel/definition` folder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

NAME = r"(?:'(?:[^']|'')+'|[^\s=']+)"
OBJ_RE = re.compile(rf"^(?P<kind>table|column|measure|partition|hierarchy|calculationItem|relationship|expression)\s+(?P<name>{NAME})(?:\s*=\s*(?P<rest>.*))?$")
PROP_RE = re.compile(r"^(?P<key>[A-Za-z]+)\s*:\s*(?P<value>.*)$")
FLAG_RE = re.compile(r"^(?P<key>isHidden|isKey|isNameInferred|isDataTypeInferred|discourageImplicitMeasures)$")


def unquote(name: str) -> str:
    name = name.strip()
    if name.startswith("'") and name.endswith("'"):
        return name[1:-1].replace("''", "'")
    return name


def _tabs(line: str) -> int:
    n = 0
    for ch in line:
        if ch == "\t":
            n += 1
        elif ch == " ":
            # tolerate 4-space indentation
            n += 0.25  # type: ignore[assignment]
        else:
            break
    return int(n)


@dataclass
class Column:
    name: str
    data_type: str = ""
    source_column: str = ""
    expression: str = ""          # calculated column DAX
    format_string: str = ""
    is_hidden: bool = False
    is_key: bool = False
    sort_by: str = ""
    description: str = ""


@dataclass
class Measure:
    name: str
    expression: str = ""
    format_string: str = ""
    display_folder: str = ""
    is_hidden: bool = False
    description: str = ""


@dataclass
class Partition:
    name: str
    kind: str = ""                # m | calculated | entity ...
    mode: str = ""
    source: str = ""


@dataclass
class Table:
    name: str
    file: Path
    description: str = ""
    is_hidden: bool = False
    data_category: str = ""
    columns: list[Column] = field(default_factory=list)
    measures: list[Measure] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)

    @property
    def is_calculated(self) -> bool:
        return any(p.kind == "calculated" for p in self.partitions)


@dataclass
class Relationship:
    name: str
    from_column: str = ""
    to_column: str = ""
    cross_filter: str = ""
    is_active: bool = True
    from_cardinality: str = ""
    to_cardinality: str = ""

    def ends(self) -> tuple[str, str, str, str]:
        ft, fc = split_ref(self.from_column)
        tt, tc = split_ref(self.to_column)
        return ft, fc, tt, tc


@dataclass
class Model:
    folder: Path
    tables: list[Table] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    annotations: dict[str, str] = field(default_factory=dict)
    expressions: dict[str, str] = field(default_factory=dict)

    def table(self, name: str) -> Table | None:
        return next((t for t in self.tables if t.name == name), None)

    @property
    def measures(self) -> list[tuple[Table, Measure]]:
        return [(t, m) for t in self.tables for m in t.measures]


def split_ref(ref: str) -> tuple[str, str]:
    """Sales.'Order Date' -> ('Sales', 'Order Date')."""
    m = re.match(rf"^({NAME})\.({NAME})$", ref.strip())
    if not m:
        return ref, ""
    return unquote(m.group(1)), unquote(m.group(2))


def _collect_block(lines: list[str], i: int, first: str, min_indent: int) -> tuple[str, int]:
    """Collect a multi-line expression starting after `= first`."""
    body: list[str] = []
    first = first.rstrip()
    if first.startswith("```"):
        rest = first[3:]
        if rest.strip():
            body.append(rest)
        i += 1
        while i < len(lines) and not lines[i].strip().startswith("```"):
            body.append(lines[i].strip("\t"))
            i += 1
        return "\n".join(body).strip(), i + 1
    if first:
        body.append(first)
    i += 1
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == "":
            # blank line inside an expression only if followed by deeper indentation
            j = i + 1
            if j < len(lines) and lines[j].strip() and _tabs(lines[j]) >= min_indent:
                body.append("")
                i += 1
                continue
            break
        if _tabs(ln) < min_indent:
            break
        body.append(ln.strip("\t"))
        i += 1
    return "\n".join(body).strip(), i


def parse_table_file(path: Path) -> list[Table]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    tables: list[Table] = []
    doc: list[str] = []
    table: Table | None = None
    current: Column | Measure | Partition | None = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        depth = _tabs(raw)
        if not stripped:
            i += 1
            continue
        if stripped.startswith("///"):
            doc.append(stripped[3:].strip())
            i += 1
            continue
        m = OBJ_RE.match(stripped)
        if m and depth == 0 and m.group("kind") == "table":
            table = Table(name=unquote(m.group("name")), file=path, description="\n".join(doc))
            tables.append(table)
            doc, current = [], None
            i += 1
            continue
        if table is None:
            i += 1
            continue
        if m and depth == 1:
            kind, name, rest = m.group("kind"), unquote(m.group("name")), m.group("rest")
            description = "\n".join(doc)
            doc = []
            if kind == "measure":
                expr, i = _collect_block(lines, i, rest or "", 3)
                current = Measure(name=name, expression=expr, description=description)
                table.measures.append(current)
                continue
            if kind == "column":
                current = Column(name=name, description=description)
                if rest is not None:
                    expr, i = _collect_block(lines, i, rest, 3)
                    current.expression = expr
                    table.columns.append(current)
                    continue
                table.columns.append(current)
            elif kind == "partition":
                current = Partition(name=name, kind=(rest or "").strip())
                table.partitions.append(current)
            else:
                current = None
            i += 1
            continue
        if depth == 1:
            pm = PROP_RE.match(stripped)
            if pm:
                key, value = pm.group("key"), pm.group("value").strip()
                if key == "dataCategory":
                    table.data_category = value
            elif stripped == "isHidden":
                table.is_hidden = True
            i += 1
            continue
        if depth == 2 and current is not None:
            if isinstance(current, Partition) and stripped.startswith("source"):
                after = stripped.split("=", 1)[1] if "=" in stripped else ""
                expr, i = _collect_block(lines, i, after.strip(), 3)
                current.source = expr
                continue
            pm = PROP_RE.match(stripped)
            if pm:
                key, value = pm.group("key"), pm.group("value").strip()
                if isinstance(current, Column):
                    if key == "dataType":
                        current.data_type = value
                    elif key == "sourceColumn":
                        current.source_column = value.strip("[]")
                    elif key == "formatString":
                        current.format_string = value
                    elif key == "sortByColumn":
                        current.sort_by = unquote(value)
                elif isinstance(current, Measure):
                    if key == "formatString":
                        current.format_string = value
                    elif key == "displayFolder":
                        current.display_folder = value
                elif isinstance(current, Partition) and key == "mode":
                    current.mode = value
            elif stripped == "isHidden" and isinstance(current, (Column, Measure)):
                current.is_hidden = True
            elif stripped == "isKey" and isinstance(current, Column):
                current.is_key = True
        i += 1
    return tables


def parse_relationships(path: Path) -> list[Relationship]:
    rels: list[Relationship] = []
    cur: Relationship | None = None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        s = raw.strip()
        if not s or s.startswith("///"):
            continue
        if _tabs(raw) == 0 and s.startswith("relationship "):
            cur = Relationship(name=s.split(None, 1)[1])
            rels.append(cur)
            continue
        if cur is None:
            continue
        pm = PROP_RE.match(s)
        if pm:
            key, value = pm.group("key"), pm.group("value").strip()
            if key == "fromColumn":
                cur.from_column = value
            elif key == "toColumn":
                cur.to_column = value
            elif key == "crossFilteringBehavior":
                cur.cross_filter = value
            elif key == "isActive":
                cur.is_active = value.lower() != "false"
            elif key == "fromCardinality":
                cur.from_cardinality = value
            elif key == "toCardinality":
                cur.to_cardinality = value
    return rels


def parse_model(definition: Path) -> Model:
    model = Model(folder=definition)
    for f in sorted((definition / "tables").glob("*.tmdl")):
        model.tables.extend(parse_table_file(f))
    rel = definition / "relationships.tmdl"
    if rel.exists():
        model.relationships = parse_relationships(rel)
    mt = definition / "model.tmdl"
    if mt.exists():
        for raw in mt.read_text(encoding="utf-8-sig").splitlines():
            s = raw.strip()
            if _tabs(raw) == 0 and s.startswith("annotation "):
                key, _, value = s[len("annotation "):].partition("=")
                model.annotations[key.strip()] = value.strip()
    ex = definition / "expressions.tmdl"
    if ex.exists():
        for raw in ex.read_text(encoding="utf-8-sig").splitlines():
            s = raw.strip()
            if _tabs(raw) == 0 and s.startswith("expression "):
                key, _, value = s[len("expression "):].partition("=")
                model.expressions[unquote(key.strip())] = value.strip()
    return model


def find_definition(src: Path) -> Path | None:
    hits = sorted(src.glob("*.SemanticModel/definition"))
    return hits[0] if hits else None


def replace_partition_source(path: Path, table: str, new_m_lines: list[str]) -> bool:
    """Replace the `source =` block of the first M partition in *path*. Returns True if changed."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    out: list[str] = []
    i = 0
    changed = False
    in_m_partition = False
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if _tabs(ln) == 1 and s.startswith("partition ") and s.endswith("= m"):
            in_m_partition = True
            out.append(ln)
            i += 1
            continue
        if in_m_partition and _tabs(ln) == 2 and s.startswith("source"):
            out.append("\t\tsource =")
            out.extend("\t\t\t\t" + x for x in new_m_lines)
            # skip old body
            after = s.split("=", 1)[1].strip() if "=" in s else ""
            _, i = _collect_block(lines, i, after, 3)
            changed = True
            in_m_partition = False
            continue
        out.append(ln)
        i += 1
    if changed:
        new = "\n".join(out) + "\n"
        old = path.read_text(encoding="utf-8-sig")
        if new != old:
            path.write_text(new, encoding="utf-8", newline="\n")
            return True
    return False
