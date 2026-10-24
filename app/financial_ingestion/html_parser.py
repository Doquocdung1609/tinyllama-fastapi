"""CPU-only SEC HTML/iXBRL parser preserving hierarchy, tables and locators."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import json
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
    def nearest_table(node):
        parent = node.parent
        while parent and parent.tag != "table":
            parent = parent.parent
        return parent
    return [row for row in table.descendants({"tr"}) if nearest_table(row) is table]


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


PERIOD = re.compile(r"(?i)\b(?:19|20)\d{2}\b|\b(?:months?|years?|quarters?)\s+ended\b")
TITLE = re.compile(r"(?i)balance\s+sheets?|statements?\s+of\s+|^note\s+\d+|\bcontinued\b")


def _extract_table(table: Node, filing_id: str, section: str | None,
                   context: list[tuple[str, SourceLocation]] | None = None) -> FinancialTable:
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
                numeric_facts=[{**{key: value for key, value in item.attrs.items()
                                  if key in {"name", "sign", "scale", "unitref", "contextref", "format"}},
                                "source_text": item.text()} for item in ix_nodes
                               if item.tag in {"ix:nonfraction", "ixnonfraction"}],
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
    header_indices = []
    source_rows = _table_rows(table)
    for index, row in enumerate(source_rows):
        direct = _direct_cells(row)
        row_values = grid[index] if index < len(grid) else []
        if any(any(cell.descendants({"table"})) for cell in direct):
            break
        # Stop before financial data, including body row headers using <th>.
        numeric_facts = any(node.tag in {"ix:nonfraction", "ixnonfraction"}
                            for cell in direct for node in cell.descendants({"ix:nonfraction", "ixnonfraction"}))
        amount = any(re.fullmatch(r"[$(\-\s]*\d[\d,]*(?:\.\d+)?[%\s)]*", cell.text())
                     and not re.fullmatch(r"(?:19|20)\d{2}", cell.text()) for cell in direct[1:])
        if numeric_facts or (amount and row_values and row_values[0]):
            break
        nonempty = list(dict.fromkeys(value for value in row_values if value))
        if header_indices and row_values and PERIOD.search(row_values[0]) and not any(row_values[1:]):
            break
        if any(cell.tag == "th" for cell in direct) or any(PERIOD.search(value) for value in row_values):
            header_indices.append(index)
        elif len(nonempty) >= 2 and all(re.search(r"[A-Za-z]", value) for value in nonempty):
            header_indices.append(index)
        elif any(row_values):
            # Unlabelled narrative/group rows remain data rather than guessed headers.
            break
    header_end = max(header_indices) if header_indices else -1
    headers = [grid[index] for index in header_indices]
    columns = [" / ".join(dict.fromkeys(row[column] for row in headers if row[column]))
               for column in range(width)]
    rows = grid[header_end + 1:] if grid else []
    row_context = {}
    group = None
    for row_index in range(header_end + 1, height):
        values = grid[row_index]
        has_data = any(cell.row == row_index and cell.column > 0 and (
            cell.numeric_facts or re.fullmatch(r"[$(\-\s]*\d[\d,]*(?:\.\d+)?[%\s)]*", cell.text))
            for cell in cells)
        if values and PERIOD.search(values[0]):
            if has_data:
                row_context[row_index] = values[0]
            elif not any(values[1:]):
                group = values[0]
        if group and row_index not in row_context:
            row_context[row_index] = group
    row_axis = not any(columns) and bool(row_context) and any(
        cell.column > 0 and cell.numeric_facts for cell in cells)
    if row_axis:
        for row_index in range(header_end + 1, height):
            if grid[row_index] and grid[row_index][0]:
                row_context[row_index] = grid[row_index][0]
    if not any(columns) and any(cell.text for cell in cells) and not row_axis:
        partial = True
    raw_text = table.text()
    context = context or []
    statement_title = next((value for value, _ in reversed(context)
                            if len(value) <= 250 and TITLE.search(value)), None)
    if statement_title is None and section:
        statement_title = section
    unit_context = next((value for value, _ in reversed(context)
                         if re.search(r"(?i)\bin\s+(?:thousands|millions|billions)\b|per.share", value)), None)
    if not unit_context and caption and re.search(r"(?i)\bin\s+(?:thousands|millions|billions)\b", caption):
        unit_context = caption
    units = sorted({cell.unit_ref for cell in cells if cell.unit_ref})
    units.extend(value for value in re.findall(
        r"(?i)(?:in|amounts? in)\s+(thousands|millions|billions)", raw_text + " " + (unit_context or ""))
                 if value.casefold() not in {item.casefold() for item in units})
    periods = sorted({column for column in columns if re.search(r"\b(?:19|20)\d{2}\b", column)})
    if row_axis:
        periods = sorted(set(row_context.values()))
    elif not periods and context:
        periods = re.findall(
            r"(?i)\b(?:three|six|nine|twelve|\d+)\s+months?\s+ended\s+"
            r"[A-Za-z]+\s+\d{1,2},\s+(?:19|20)\d{2}", context[-1][0])
    footnotes = []
    footnote_locations = []
    for node in table.descendants({"tfoot"}):
        value = node.text()
        if value:
            footnotes.append(value)
            footnote_locations.append(SourceLocation(structural_path=node.path, html_anchor=_anchor(node)))
    warnings = []
    parent = table.parent
    while parent and parent.tag != "table":
        parent = parent.parent
    parent_table_id = _stable_id("table", filing_id, parent.path) if parent else None
    if any(table.descendants({"table"})):
        warnings.append("NESTED_TABLE_PRESERVED_SEPARATELY")
        partial = True
    if not header_indices and any(cell.text for cell in cells) and not row_axis:
        warnings.append("AMBIGUOUS_COLUMN_HEADERS")
        partial = True
    return FinancialTable(
        table_id=table_id, section=section, caption=caption or statement_title, columns=columns,
        statement_title=statement_title, header_rows=headers,
        row_indices=list(range(header_end + 1, height)),
        row_context=row_context,
        context_text=[value for value, _ in context],
        context_locations=[location for _, location in context], unit_context=unit_context,
        parent_table_id=parent_table_id, extraction_warnings=warnings,
        rows=rows, cells=cells, units=units, reporting_periods=periods,
        footnotes=footnotes, footnote_locations=footnote_locations,
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
    recent_context = []
    table_nodes = {}
    for node, parent_in_table in _walk(parser.root):
        value = node.text()
        visual_heading = (node.tag in {"p", "div"} and 0 < len(value) <= 180 and "|" not in value
                          and any(child.text() == value and re.search(
                              r"(?i)font-weight\s*:\s*(?:bold|[6-9]00)", child.attrs.get("style", ""))
                              for child in node.children if child.tag in {"span", "b", "strong"}))
        if (not parent_in_table and node.tag in {"div", "p", "h1", "h2", "h3", "h4", "h5", "h6"}
                and value and len(value) < 2000 and not any(
                    child.tag in {"div", "p", "table", "h1", "h2", "h3", "h4", "h5", "h6"}
                    for child in node.children)):
            recent_context.append((value, SourceLocation(
                structural_path=node.path, html_anchor=_anchor(node))))
            recent_context = recent_context[-8:]
        if not parent_in_table and (node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"} or visual_heading) and value:
            current_section = value
            kind = "heading"
        elif node.tag == "table":
            extracted = _extract_table(node, metadata.filing_id, current_section,
                                       [] if parent_in_table else recent_context)
            if tables and not parent_in_table and not recent_context and not extracted.header_rows:
                previous = tables[-1]
                topic = next((value.rstrip(":").casefold() for row in extracted.rows
                              for value in row if value), "")
                introduction = previous.context_text[-1] if previous.context_text else ""
                # Share context only when an immediately preceding introduction explicitly
                # names this table's topic and the column layout is identical.
                if (len(topic) >= 8 and topic in introduction.casefold()
                        and len(extracted.columns) == len(previous.columns) and previous.header_rows):
                    extracted.columns = previous.columns.copy()
                    extracted.reporting_periods = previous.reporting_periods.copy()
                    extracted.continuation_of = previous.table_id
                    extracted.caption = previous.caption or introduction
                    extracted.context_text = previous.context_text.copy()
                    extracted.context_locations = previous.context_locations.copy()
                    extracted.extraction_warnings = [warning for warning in extracted.extraction_warnings
                                                    if warning != "AMBIGUOUS_COLUMN_HEADERS"]
                    extracted.extraction_warnings.append("EXPLICIT_SHARED_INTRODUCTION")
                    if "percentage" in topic and any(cell.text.rstrip().endswith("%") for cell in extracted.cells):
                        extracted.unit_context = "%"
                        extracted.units = sorted(set(extracted.units + ["%"]))
                    if "NESTED_TABLE_PRESERVED_SEPARATELY" not in extracted.extraction_warnings:
                        extracted.extraction_status = "OK"
            if tables and extracted.statement_title and re.search(r"(?i)\bcontinued\b", extracted.statement_title):
                base = re.sub(r"(?i)[\s()–—-]*continued[\s()]*", "", extracted.statement_title).strip()
                previous = tables[-1]
                old = re.sub(r"(?i)[\s()–—-]*continued[\s()]*", "", previous.statement_title or "").strip()
                if base.casefold() == old.casefold() and base:
                    extracted.continuation_of = previous.table_id
                    if not extracted.header_rows and len(extracted.columns) == len(previous.columns):
                        extracted.columns = previous.columns.copy()
                        extracted.reporting_periods = previous.reporting_periods.copy()
                        extracted.extraction_warnings.append("HEADERS_FROM_EXPLICIT_CONTINUATION")
                    if not extracted.unit_context:
                        extracted.unit_context = previous.unit_context
                        extracted.units = sorted(set(extracted.units + previous.units))
                        extracted.context_locations.extend(previous.context_locations)
            tables.append(extracted)
            table_nodes[extracted.table_id] = node
            if not parent_in_table:
                recent_context = []
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
    # Associate only explicit footnote anchors or directly following labelled notes.
    anchors = {_anchor(node): node for node, _ in _walk(parser.root) if _anchor(node)}
    for table in tables:
        source = table_nodes[table.table_id]
        for link in source.descendants({"a"}):
            target = anchors.get(link.attrs.get("href", "").removeprefix("#"))
            if target is not None and target.text() and target.text() not in table.footnotes:
                table.footnotes.append(target.text())
                table.footnote_locations.append(SourceLocation(
                    structural_path=target.path, html_anchor=_anchor(target)))
        sibling = source
        for _ in range(3):
            if not sibling.parent:
                break
            siblings = sibling.parent.children
            position = next(index for index, item in enumerate(siblings) if item is sibling)
            for following in siblings[position + 1:position + 4]:
                note = following.text()
                if following.tag == "table" or any(following.descendants({"table"})):
                    break
                if re.match(r"(?i)^(?:\(\d+\)|\d+\)|see accompanying|\*|footnote)", note):
                    if note not in table.footnotes:
                        table.footnotes.append(note)
                        table.footnote_locations.append(SourceLocation(
                            structural_path=following.path, html_anchor=_anchor(following)))
            sibling = sibling.parent
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
        parts.append("CONTEXT|" + json.dumps({
            "title": table.statement_title, "caption": table.caption,
            "columns": table.columns, "periods": table.reporting_periods,
            "units": table.units, "unit_context": table.unit_context,
            "footnotes": table.footnotes, "continuation_of": table.continuation_of,
        }, sort_keys=True, ensure_ascii=False))
    return "\n".join(parts)
