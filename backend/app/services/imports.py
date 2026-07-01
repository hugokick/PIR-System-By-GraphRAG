import csv
import re
from io import BytesIO, StringIO
from pathlib import Path
from xml.sax.saxutils import escape
from xml.etree import ElementTree
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from fastapi import UploadFile

from app.schemas import EntityRef, ExhibitImportError, ExhibitResponse


required_fields = {
    "id",
    "name",
    "category",
    "theme",
    "venue_type",
    "budget_min",
    "budget_max",
    "supplier",
    "project_id",
    "project_name",
    "owner",
    "project_year",
    "status",
    "description",
}

import_template_fields = [
    ("id", "展项编号", True, "展项唯一编号，建议使用英文、数字和短横线", "lever-play"),
    ("name", "展项名称", True, "展项名称", "杠杆乐园"),
    ("category", "类别", True, "学科领域或展项类别", "基础科学"),
    ("theme", "主题", True, "主题名称", "力学"),
    ("venue_type", "适用场馆", True, "适用场馆类型", "儿童科技馆"),
    ("budget_min", "造价下限", True, "最低造价，整数，单位元", "200000"),
    ("budget_max", "造价上限", True, "最高造价，整数，单位元", "350000"),
    ("materials", "材料", False, "材料列表，用竖线分隔多个值", "金属|木作|亚克力"),
    ("dimensions", "尺寸", False, "尺寸说明", "4200x2200x1800mm"),
    ("interactions", "交互方式", False, "交互方式列表，用竖线分隔多个值", "机械互动|亲子协作"),
    ("supplier", "供应商", True, "供应商名称", "启思互动工坊"),
    ("project_id", "项目编号", True, "项目唯一编号", "qinghe-2024"),
    ("project_name", "项目名称", True, "项目名称", "青禾儿童科技馆更新项目"),
    ("owner", "业主", True, "业主名称", "青禾儿童科技馆"),
    ("project_year", "项目年份", True, "项目年份，整数", "2024"),
    ("status", "状态", True, "展项状态", "已落地"),
    ("description", "展项说明", True, "展项说明", "通过杠杆装置展示力矩平衡。"),
    ("tags", "标签", False, "标签列表，用竖线分隔多个值", "低龄儿童|力学"),
    ("related_exhibit_ids", "相似展项", False, "相似展项编号列表，用竖线分隔多个值", "pulley-wall"),
]

field_aliases = {
    "id": {"展项编号", "展项id", "展项ID", "编号"},
    "name": {"展项名称", "名称"},
    "category": {"类别", "学科领域", "分类"},
    "theme": {"主题", "主题名称"},
    "venue_type": {"适用场馆", "场馆类型", "展馆类型", "适用场馆类型"},
    "budget_min": {"造价下限", "最低造价", "预算下限", "预算最低", "最小预算"},
    "budget_max": {"造价上限", "最高造价", "预算上限", "预算最高", "最大预算"},
    "materials": {"材料", "材质", "材料列表"},
    "dimensions": {"尺寸", "规格", "外形尺寸"},
    "interactions": {"交互方式", "互动形式", "互动方式", "交互形式"},
    "supplier": {"供应商", "制作单位"},
    "project_id": {"项目编号", "项目id", "项目ID"},
    "project_name": {"项目名称", "项目案例"},
    "owner": {"业主", "业主单位", "甲方"},
    "project_year": {"项目年份", "年份", "项目年度"},
    "status": {"状态", "展项状态"},
    "description": {"展项说明", "说明", "描述", "简介"},
    "tags": {"标签", "关键词"},
    "related_exhibit_ids": {"相似展项", "关联展项", "相似展项编号", "相关展项"},
}

header_alias_lookup = {
    alias.strip().lower(): field
    for field, aliases in field_aliases.items()
    for alias in aliases | {field}
}


class ImportFileParseError(ValueError):
    pass


def parse_import_file(file: UploadFile) -> list[dict[str, str]]:
    content = file.file.read()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix == ".xlsx":
        try:
            return parse_xlsx(content)
        except (BadZipFile, ElementTree.ParseError, KeyError, ValueError, IndexError) as exc:
            raise ImportFileParseError("Import file could not be parsed") from exc
    return parse_csv(content)


def parse_csv(content: bytes) -> list[dict[str, str]]:
    text = decode_csv_text(content)
    return list(csv.DictReader(StringIO(text)))


def decode_csv_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def parse_xlsx(content: bytes) -> list[dict[str, str]]:
    with ZipFile(BytesIO(content)) as archive:
        shared_strings = read_shared_strings(archive)
        sheet_name = first_sheet_name(archive)
        root = ElementTree.fromstring(archive.read(sheet_name))

    rows: list[list[str]] = []
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    for row in root.findall(".//s:sheetData/s:row", namespace):
        values: dict[int, str] = {}
        for cell in row.findall("s:c", namespace):
            ref = cell.attrib.get("r", "")
            column_index = column_number(ref) - 1
            values[column_index] = cell_value(cell, shared_strings, namespace)
        if values:
            width = max(values) + 1
            rows.append([values.get(index, "") for index in range(width)])

    if not rows:
        return []
    headers = rows[0]
    return [
        {headers[index]: value for index, value in enumerate(row) if index < len(headers)}
        for row in rows[1:]
        if any(value.strip() for value in row)
    ]


def read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("s:si", namespace):
        text_parts = [node.text or "" for node in item.findall(".//s:t", namespace)]
        values.append("".join(text_parts))
    return values


def first_sheet_name(archive: ZipFile) -> str:
    for name in archive.namelist():
        if name.startswith("xl/worksheets/") and name.endswith(".xml"):
            return name
    raise ValueError("No worksheet found")


def column_number(cell_ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - ord("A") + 1
    return value or 1


def cell_value(cell: ElementTree.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//s:t", namespace)).strip()

    value_node = cell.find("s:v", namespace)
    if value_node is None or value_node.text is None:
        return ""
    raw_value = value_node.text.strip()
    if cell_type == "s":
        index = int(raw_value)
        return shared_strings[index] if index < len(shared_strings) else ""
    return raw_value


def build_import_items(
    rows: list[dict[str, str]],
    known_exhibit_ids: set[str] | None = None,
) -> tuple[list[ExhibitResponse], list[ExhibitImportError]]:
    parsed_items: list[tuple[int, ExhibitResponse]] = []
    errors: list[ExhibitImportError] = []

    if not rows:
        return [], [ExhibitImportError(row=1, field="file", message="No import rows found")]

    for index, raw_row in enumerate(rows, start=2):
        row = normalize_row(raw_row)
        row_errors = validate_row(row, index)
        if row_errors:
            errors.extend(row_errors)
            continue
        parsed_items.append((index, row_to_exhibit(row)))

    if known_exhibit_ids is not None:
        duplicate_errors = validate_duplicate_import_ids(parsed_items)
        errors.extend(duplicate_errors)
        duplicate_rows = {error.row for error in duplicate_errors}
        parsed_items = [
            (row_number, item)
            for row_number, item in parsed_items
            if row_number not in duplicate_rows
        ]

        relation_errors = validate_related_exhibit_ids(parsed_items, known_exhibit_ids)
        errors.extend(relation_errors)
        invalid_rows = {error.row for error in relation_errors}
        parsed_items = [
            (row_number, item)
            for row_number, item in parsed_items
            if row_number not in invalid_rows
        ]

    items = [item for _row_number, item in parsed_items]
    return items, errors


def validate_duplicate_import_ids(
    parsed_items: list[tuple[int, ExhibitResponse]],
) -> list[ExhibitImportError]:
    rows_by_id: dict[str, list[int]] = {}
    for row_number, item in parsed_items:
        rows_by_id.setdefault(item.id, []).append(row_number)

    errors: list[ExhibitImportError] = []
    for exhibit_id, row_numbers in rows_by_id.items():
        if len(row_numbers) <= 1:
            continue
        for row_number in row_numbers:
            errors.append(
                ExhibitImportError(
                    row=row_number,
                    field="id",
                    message=f"Duplicate exhibit id in import file: {exhibit_id}",
                )
            )
    return errors


def validate_related_exhibit_ids(
    parsed_items: list[tuple[int, ExhibitResponse]],
    known_exhibit_ids: set[str],
) -> list[ExhibitImportError]:
    import_ids = {item.id for _row_number, item in parsed_items}
    allowed_ids = known_exhibit_ids | import_ids
    errors: list[ExhibitImportError] = []

    for row_number, item in parsed_items:
        invalid_ids = [
            related_id
            for related_id in item.related_exhibit_ids
            if related_id == item.id or related_id not in allowed_ids
        ]
        if invalid_ids:
            errors.append(
                ExhibitImportError(
                    row=row_number,
                    field="related_exhibit_ids",
                    message=f"Unknown or self-referencing exhibit id: {', '.join(invalid_ids)}",
                )
            )

    return errors


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {
        normalize_header(key): (value or "").strip()
        for key, value in row.items()
        if normalize_header(key)
    }


def normalize_header(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return header_alias_lookup.get(normalized, normalized)


def validate_row(row: dict[str, str], row_number: int) -> list[ExhibitImportError]:
    errors: list[ExhibitImportError] = []
    for field in sorted(required_fields):
        if not row.get(field):
            errors.append(ExhibitImportError(row=row_number, field=field, message="Required"))

    for field in ("budget_min", "budget_max", "project_year"):
        if row.get(field) and parse_int(row[field]) is None:
            errors.append(ExhibitImportError(row=row_number, field=field, message="Must be an integer"))

    budget_min = parse_int(row.get("budget_min", ""))
    budget_max = parse_int(row.get("budget_max", ""))
    if budget_min is not None and budget_max is not None and budget_max < budget_min:
        errors.append(ExhibitImportError(row=row_number, field="budget_max", message="Must be greater than or equal to budget_min"))
    return errors


def row_to_exhibit(row: dict[str, str]) -> ExhibitResponse:
    return ExhibitResponse(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        theme=entity_ref(row["theme"]),
        venue_type=row["venue_type"],
        budget_min=int(row["budget_min"]),
        budget_max=int(row["budget_max"]),
        materials=[entity_ref(value) for value in split_list(row.get("materials", ""))],
        dimensions=row.get("dimensions", ""),
        interactions=[entity_ref(value) for value in split_list(row.get("interactions", ""))],
        supplier=entity_ref(row["supplier"]),
        project=EntityRef(id=row["project_id"], name=row["project_name"]),
        owner=entity_ref(row["owner"]),
        project_year=int(row["project_year"]),
        status=row["status"],
        description=row["description"],
        tags=split_list(row.get("tags", "")),
        media_assets=[],
        documents=[],
        related_exhibit_ids=split_list(row.get("related_exhibit_ids", "")),
    )


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def split_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[|,，、]", value) if item.strip()]


def entity_ref(name: str) -> EntityRef:
    return EntityRef(id=slugify(name), name=name)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.strip().lower()).strip("-")
    return slug or "entity"


def build_import_template_xlsx() -> bytes:
    template_rows = [
        [label for _field, label, _required, _description, _example in import_template_fields],
        [example for _field, _label, _required, _description, example in import_template_fields],
    ]
    description_rows = [
        ["字段", "中文表头", "是否必填", "说明", "示例"],
        *[
            [field, label, "是" if required else "否", description, example]
            for field, label, required, description, example in import_template_fields
        ],
    ]

    workbook = BytesIO()
    with ZipFile(workbook, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="导入模板" sheetId="1" r:id="rId1"/>
    <sheet name="字段说明" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
</Relationships>""",
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml(template_rows))
        archive.writestr("xl/worksheets/sheet2.xml", worksheet_xml(description_rows))
    return workbook.getvalue()


def worksheet_xml(rows: list[list[str]]) -> str:
    sheet_data = "".join(
        worksheet_row(row, row_index)
        for row_index, row in enumerate(rows, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{sheet_data}</sheetData>
</worksheet>"""


def worksheet_row(row: list[str], row_index: int) -> str:
    cells = "".join(
        f'<c r="{cell_ref(column_index, row_index)}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        for column_index, value in enumerate(row)
    )
    return f'<row r="{row_index}">{cells}</row>'


def cell_ref(column_index: int, row_index: int) -> str:
    column_number_value = column_index + 1
    letters = ""
    while column_number_value:
        column_number_value, remainder = divmod(column_number_value - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return f"{letters}{row_index}"
