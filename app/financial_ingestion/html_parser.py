"""CPU-only SEC HTML/iXBRL parser preserving hierarchy, tables and locators."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import re
from typing import Iterable

from app.financial_ingestion.schemas import (
    FilingMetadata, FinancialTable, SourceLocation, StructuredElement,
    StructuredFiling, TableCell,
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    parent: "Node | None" = None
    children: list["Node"] = field(default_factory=list)
    content: list["Node | str"] = field(default_factory=list)
    path: str = ""

    def text(self) -> str:
        values = []
        for item in self.content:
            if isinstance(item, str):
                values.append(item)
            elif item.tag not in {"script", "style"}:
                values.append(item.text())
        return normalize_text(" ".join(values))

    def descendants(self, tags: set[str]) -> Iterable["Node"]:
        for child in self.children:
            if child.tag in tags:
                yield child
            yield from child.descendants(tags)


class TreeParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {}, path="/document[1]")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs):
        tag = tag.casefold()
        parent = self.stack[-1]
        same_tag = sum(child.tag == tag for child in parent.children) + 1
        node = Node(tag, {str(key).casefold(): str(value or "") for key, value in attrs},
                    parent=parent, path=f"{parent.path}/{tag}[{same_tag}]")
        parent.children.append(node)
        parent.content.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs):
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str):
        tag = tag.casefold()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str):
        if self.stack[-1].tag not in {"script", "style"}:
            self.stack[-1].content.append(data)


def _anchor(node: Node) -> str | None:
    return node.attrs.get("id") or node.attrs.get("name") or None


def _stable_id(prefix: str, filing_id: str, path: str) -> str:
    return f"{prefix}_{sha256(f'{filing_id}|{path}'.encode()).hexdigest()[:24]}"


def _walk(node: Node, in_table: bool = False):
    for child in node.children:
        child_in_table = in_table or child.tag == "table"
        yield child, in_table
        yield from _walk(child, child_in_table)


def _explicit_ix_metadata(root: Node) -> tuple[int | None, str | None]:
    fiscal_year = None
    fiscal_period = None
    for node, _ in _walk(root):
        if not (node.tag.startswith("ix:") or node.tag.startswith("ix")):
            continue
        name = (node.attrs.get("name") or "").casefold()
        value = node.text()
        if name.endswith("documentfiscalyearfocus") and re.fullmatch(r"\d{4}", value):
            fiscal_year = int(value)
        elif name.endswith("documentfiscalperiodfocus") and value:
            fiscal_period = value.upper()
    return fiscal_year, fiscal_period


def _table_rows(table: Node) -> list[Node]:
    return list(table.descendants({"tr"}))


def _direct_cells(row: Node) -> list[Node]:
    result = []
    queue = list(row.children)
    while queue:
        node = queue.pop(0)
        if node.tag in {"td", "th"}:
            result.append(node)
        elif node.tag not in {"tr", "table"}:
            queue[0:0] = node.children
    return result


def _extract_table(table: Node, filing_id: str, section: str | None) -> FinancialTable:
    table_id = _stable_id("table", filing_id, table.path)
    occupied: dict[tuple[int, int], str] = {}
    cells = []
    partial = False
    row_count = 0
    for row_index, row in enumerate(_table_rows(table)):
        row_count += 1
        column = 0
        for cell in _direct_cells(row):
            while (row_index, column) in occupied:
                column += 1
            text = cell.text()
            try:
                rowspan = max(1, int(cell.attrs.get("rowspan", "1") or "1"))
                colspan = max(1, int(cell.attrs.get("colspan", "1") or "1"))
            except ValueError:
                rowspan = colspan = 1
                partial = True
            ix_nodes = list(cell.descendants({"ix:nonfraction", "ix:nonnumeric", "ixnonfraction", "ixnonnumeric"}))
            unit_ref = next((item.attrs.get("unitref") for item in ix_nodes if item.attrs.get("unitref")), None)
            context_ref = next((item.attrs.get("contextref") for item in ix_nodes if item.attrs.get("contextref")), None)
            cells.append(TableCell(
                row=row_index, column=column, text=text, is_header=cell.tag == "th",
                rowspan=rowspan, colspan=colspan, unit_ref=unit_ref,
                context_ref=context_ref,
                source_location=SourceLocation(section=section, html_anchor=_anchor(cell),
                                               structural_path=cell.path, table_id=table_id,
                                               row_index=row_index, column_index=column),
            ))
            for row_offset in range(rowspan):
                for column_offset in range(colspan):
                    occupied[(row_index + row_offset, column + column_offset)] = text
            column += colspan
    width = max((column + 1 for row, column in occupied), default=0)
    height = max(row_count, max((row + 1 for row, _ in occupied), default=0))
    grid = [[occupied.get((row, column), "") for column in range(width)]
            for row in range(height)]
    if not grid or width < 2 or len({len(row) for row in grid}) != 1:
        partial = True
    caption_node = next(iter(table.descendants({"caption"})), None)
    caption = caption_node.text() if caption_node else None
    header_rows = {cell.row for cell in cells if cell.is_header}
    header_end = max(header_rows) if header_rows else 0
    columns = grid[header_end] if grid else []
    rows = grid[header_end + 1:] if grid else []
    if not any(columns) and any(cell.text for cell in cells):
        partial = True
    raw_text = table.text()
    units = sorted({cell.unit_ref for cell in cells if cell.unit_ref})
    units.extend(value for value in re.findall(
        r"(?i)(?:in|amounts? in)\s+(thousands|millions|billions)", raw_text)
                 if value.casefold() not in {item.casefold() for item in units})
    periods = sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", " ".join(columns))))
    footnotes = []
    for node in table.descendants({"tfoot"}):
        value = node.text()
        if value:
            footnotes.append(value)
    return FinancialTable(
        table_id=table_id, section=section, caption=caption, columns=columns,
        rows=rows, cells=cells, units=units, reporting_periods=periods,
        footnotes=footnotes,
        source_location=SourceLocation(section=section, html_anchor=_anchor(table),
                                       structural_path=table.path, table_id=table_id),
        extraction_status="PARTIAL_EXTRACTION" if partial else "OK",
        raw_text=raw_text, raw_content_hash=sha256(raw_text.encode("utf-8")).hexdigest(),
    )


def parse_sec_html(raw: bytes, metadata: FilingMetadata) -> StructuredFiling:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    if "<html" not in text[:10000].casefold() and "<xhtml" not in text[:10000].casefold():
        raise ValueError("SEC primary document is not recognizable HTML/XHTML")
    parser = TreeParser()
    parser.feed(text)
    parser.close()
    title_node = next((node for node, _ in _walk(parser.root) if node.tag == "title"), None)
    title = title_node.text() if title_node else None
    fiscal_year, fiscal_period = _explicit_ix_metadata(parser.root)
    if fiscal_year is not None:
        metadata.fiscal_year = fiscal_year
        metadata.unknown_reasons.pop("fiscal_year", None)
    if fiscal_period:
        metadata.fiscal_period = fiscal_period
        metadata.unknown_reasons.pop("fiscal_period", None)

    elements = []
    tables = []
    current_section = None
    for node, parent_in_table in _walk(parser.root):
        value = node.text()
        if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and value:
            current_section = value
            kind = "heading"
        elif node.tag == "table":
            tables.append(_extract_table(node, metadata.filing_id, current_section))
            continue
        elif parent_in_table or not value:
            continue
        elif node.tag == "p":
            kind = "footnote" if "footnote" in (node.attrs.get("class") or "").casefold() else "paragraph"
        elif node.tag == "li":
            kind = "list_item"
        elif node.tag == "div" and len(value) >= 30 and not any(
                child.tag in {"div", "p", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"}
                for child in node.children):
            kind = "paragraph"
        else:
            continue
        location = SourceLocation(section=current_section, html_anchor=_anchor(node),
                                  structural_path=node.path, text_start=0, text_end=len(value))
        elements.append(StructuredElement(
            element_id=_stable_id("element", metadata.filing_id, node.path),
            kind=kind, text=value, source_location=location,
            source_text_hash=sha256(value.encode("utf-8")).hexdigest(),
        ))
    warnings = []
    if not elements:
        warnings.append("NO_TEXT_BLOCKS")
    if any(table.extraction_status == "PARTIAL_EXTRACTION" for table in tables):
        warnings.append("PARTIAL_TABLE_EXTRACTION")
    return StructuredFiling(metadata=metadata, title=title, elements=elements,
                            tables=tables, parser_warnings=warnings)


def normalized_filing_text(filing: StructuredFiling) -> str:
    parts = [f"{item.kind.upper()}|{item.source_location.structural_path}|{item.text}"
             for item in filing.elements]
    for table in filing.tables:
        parts.append(f"TABLE|{table.source_location.structural_path}|{table.raw_text}")
    return "\n".join(parts)
