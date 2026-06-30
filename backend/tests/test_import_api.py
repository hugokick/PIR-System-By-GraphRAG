from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

EDITOR_HEADERS = {"X-User-Role": "editor"}


CSV_HEADERS = [
    "id",
    "name",
    "category",
    "theme",
    "venue_type",
    "budget_min",
    "budget_max",
    "materials",
    "dimensions",
    "interactions",
    "supplier",
    "project_id",
    "project_name",
    "owner",
    "project_year",
    "status",
    "description",
    "tags",
    "related_exhibit_ids",
]


def csv_bytes(rows: list[list[str]]) -> bytes:
    lines = [",".join(CSV_HEADERS), *[",".join(row) for row in rows]]
    return ("\n".join(lines) + "\n").encode("utf-8")


def csv_bytes_with_headers(headers: list[str], rows: list[list[str]]) -> bytes:
    lines = [",".join(headers), *[",".join(row) for row in rows]]
    return ("\n".join(lines) + "\n").encode("utf-8")


def minimal_xlsx_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    def cell_ref(column_index: int, row_index: int) -> str:
        column = chr(ord("A") + column_index)
        return f"{column}{row_index}"

    def sheet_row(row: list[str], row_index: int) -> str:
        cells = []
        for column_index, value in enumerate(row):
            escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            cells.append(
                f'<c r="{cell_ref(column_index, row_index)}" t="inlineStr">'
                f"<is><t>{escaped}</t></is></c>"
            )
        return f'<row r="{row_index}">{"".join(cells)}</row>'

    sheet_data = "".join(
        sheet_row(row, index + 1)
        for index, row in enumerate([headers, *rows])
    )
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
  <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{sheet_data}</sheetData>
</worksheet>""",
        )
    return workbook.getvalue()


def valid_import_row(exhibit_id: str) -> list[str]:
    return [
        exhibit_id,
        "Import Demo",
        "Physics",
        "Mechanics",
        "Children Museum",
        "120000",
        "260000",
        "Metal|Acrylic",
        "3000x1800x1800mm",
        "Hands-on|Mechanical",
        "Qisi Workshop",
        "import-2026",
        "Import Project",
        "Demo Owner",
        "2026",
        "Concept",
        "Imported exhibit for spreadsheet workflow.",
        "import|spreadsheet",
        "lever-play",
    ]


def test_import_preview_validates_rows_without_persisting():
    response = client.post(
        "/api/exhibits/import",
        data={"commit": "false"},
        files={
            "file": (
                "exhibits.csv",
                csv_bytes(
                    [
                        valid_import_row("preview-import-demo"),
                        [
                            "bad-budget",
                            "Bad Budget",
                            "Physics",
                            "Mechanics",
                            "Children Museum",
                            "not-a-number",
                            "260000",
                            "Metal",
                            "3000x1800x1800mm",
                            "Hands-on",
                            "Qisi Workshop",
                            "import-2026",
                            "Import Project",
                            "Demo Owner",
                            "2026",
                            "Concept",
                            "Invalid row.",
                            "import",
                            "",
                        ],
                    ]
                ),
                "text/csv",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["valid_rows"] == 1
    assert payload["imported_count"] == 0
    assert payload["errors"] == [
        {
            "row": 3,
            "field": "budget_min",
            "message": "Must be an integer",
        }
    ]
    assert client.get("/api/exhibits/preview-import-demo").status_code == 404


def test_import_commit_upserts_valid_rows_and_graph_relationships():
    response = client.post(
        "/api/exhibits/import",
        data={"commit": "true"},
        files={
            "file": (
                "exhibits.csv",
                csv_bytes([valid_import_row("committed-import-demo")]),
                "text/csv",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 1
    assert payload["valid_rows"] == 1
    assert payload["imported_count"] == 1
    assert payload["items"][0]["id"] == "committed-import-demo"

    detail_response = client.get("/api/exhibits/committed-import-demo")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["materials"] == [
        {"id": "metal", "name": "Metal"},
        {"id": "acrylic", "name": "Acrylic"},
    ]

    graph_response = client.get("/api/exhibits/committed-import-demo/graph")
    edge_types = {edge["type"] for edge in graph_response.json()["edges"]}
    assert "uses_material" in edge_types
    assert "similar_to" in edge_types


def test_import_accepts_basic_xlsx_files():
    response = client.post(
        "/api/exhibits/import",
        data={"commit": "false"},
        files={
            "file": (
                "exhibits.xlsx",
                minimal_xlsx_bytes(CSV_HEADERS, [valid_import_row("xlsx-import-demo")]),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 1
    assert payload["valid_rows"] == 1
    assert payload["items"][0]["id"] == "xlsx-import-demo"


def test_import_accepts_chinese_header_aliases():
    chinese_headers = [
        "展项编号",
        "展项名称",
        "类别",
        "主题",
        "适用场馆",
        "造价下限",
        "造价上限",
        "材料",
        "尺寸",
        "交互方式",
        "供应商",
        "项目编号",
        "项目名称",
        "业主",
        "项目年份",
        "状态",
        "展项说明",
        "标签",
        "相似展项",
    ]

    response = client.post(
        "/api/exhibits/import",
        data={"commit": "false"},
        files={
            "file": (
                "chinese-headers.csv",
                csv_bytes_with_headers(chinese_headers, [valid_import_row("chinese-header-demo")]),
                "text/csv",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 1
    assert payload["valid_rows"] == 1
    assert payload["errors"] == []
    assert payload["items"][0]["id"] == "chinese-header-demo"
    assert payload["items"][0]["venue_type"] == "Children Museum"
    assert payload["items"][0]["materials"] == [
        {"id": "metal", "name": "Metal"},
        {"id": "acrylic", "name": "Acrylic"},
    ]
    assert client.get("/api/exhibits/chinese-header-demo").status_code == 404


def test_import_template_downloads_xlsx_with_field_descriptions():
    response = client.get("/api/exhibits/import-template")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "exhibit-import-template.xlsx" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")

    with ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        assert "xl/workbook.xml" in names

        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        template_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        field_xml = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")

    assert "导入模板" in workbook_xml
    assert "字段说明" in workbook_xml
    assert "展项名称" in template_xml
    assert "造价下限" in template_xml
    assert "related_exhibit_ids" in field_xml
    assert "venue_type" in field_xml
    assert "budget_min" in field_xml
    assert "是否必填" in field_xml
    assert "展项唯一编号" in field_xml
    assert "中文表头" in field_xml
