import csv
import re
from io import BytesIO, StringIO
from pathlib import Path
from xml.sax.saxutils import escape
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

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
    ("id", True, "展项唯一编号，建议使用英文、数字和短横线", "lever-play"),
    ("name", True, "展项名称", "杠杆乐园"),
    ("category", True, "学科领域或展项类别", "基础科学"),
    ("theme", True, "主题名称", "力学"),
    ("venue_type", True, "适用场馆类型", "儿童科技馆"),
    ("budget_min", True, "最低造价，整数，单位元", "200000"),
    ("budget_max", True, "最高造价，整数，单位元", "350000"),
    ("materials", False, "材料列表，用竖线分隔多个值", "金属|木作|亚克力"),
    ("dimensions", False, "尺寸说明", "4200x2200x1800mm"),
    ("interactions", False, "交互方式列表，用竖线分隔多个值", "机械互动|亲子协作"),
    ("supplier", True, "供应商名称", "启思互动工坊"),
    ("project_id", True, "项目唯一编号", "qinghe-2024"),
    ("project_name", True, "项目名称", "青禾儿童科技馆更新项目"),
    ("owner", True, "业主名称", "青禾儿童科技馆"),
    ("project_year", True, "项目年份，整数", "2024"),
    ("status", True, "展项状态", "已落地"),
    ("description", True, "展项说明", "通过杠杆装置展示力矩平衡。"),
    ("tags", False, "标签列表，用竖线分隔多个值", "低龄儿童|力学"),
    ("related_exhibit_ids", False, "相似展项编号列表，用竖线分隔多个值", "pulley-wall"),
]


def parse_import_file(file: UploadFile) -> list[dict[str, str]]:
    content = file.file.read()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix == ".xlsx":
        return parse_xlsx(content)
    return parse_csv(content)


def parse_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


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


def build_import_items(rows: list[dict[str, str]]) -> tuple[list[ExhibitResponse], list[ExhibitImportError]]:
    items: list[ExhibitResponse] = []
    errors: list[ExhibitImportError] = []

    for index, raw_row in enumerate(rows, start=2):
        row = normalize_row(raw_row)
        row_errors = validate_row(row, index)
        if row_errors:
            errors.extend(row_errors)
            continue
        items.append(row_to_exhibit(row))

    return items, errors


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {
        (key or "").strip(): (value or "").strip()
        for key, value in row.items()
    }


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
        [field for field, _required, _description, _example in import_template_fields],
        [example for _field, _required, _description, example in import_template_fields],
    ]
    description_rows = [
        ["字段", "是否必填", "说明", "示例"],
        *[
            [field, "是" if required else "否", description, example]
            for field, required, description, example in import_template_fields
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
