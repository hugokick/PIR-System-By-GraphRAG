from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

EDITOR_HEADERS = {"X-User-Role": "editor"}
ADMIN_HEADERS = {"X-User-Role": "admin"}


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


def csv_bytes_with_headers_encoding(headers: list[str], rows: list[list[str]], encoding: str) -> bytes:
    lines = [",".join(headers), *[",".join(row) for row in rows]]
    return ("\n".join(lines) + "\n").encode(encoding)


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


def test_import_preview_reports_empty_files_as_structured_error():
    response = client.post(
        "/api/exhibits/import",
        data={"commit": "false"},
        files={
            "file": (
                "empty-import.csv",
                csv_bytes([]),
                "text/csv",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 0
    assert payload["valid_rows"] == 0
    assert payload["imported_count"] == 0
    assert payload["items"] == []
    assert payload["errors"] == [
        {
            "row": 1,
            "field": "file",
            "message": "No import rows found",
        }
    ]


def test_import_commit_upserts_valid_rows_and_graph_relationships():
    try:
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
    finally:
        client.delete("/api/exhibits/committed-import-demo", headers=ADMIN_HEADERS)


def test_import_update_moves_approved_exhibit_back_to_pending_for_editors():
    original = client.get("/api/exhibits/lever-play").json()
    row = valid_import_row("lever-play")
    row[-1] = "pulley-wall"

    try:
        response = client.post(
            "/api/exhibits/import",
            data={"commit": "true"},
            files={
                "file": (
                    "existing-review-status.csv",
                    csv_bytes([row]),
                    "text/csv",
                )
            },
            headers=EDITOR_HEADERS,
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["imported_count"] == 1
        assert payload["items"][0]["review_status"] == "待审核"

        detail_response = client.get("/api/exhibits/lever-play")
        assert detail_response.status_code == 200
        assert detail_response.json()["review_status"] == "待审核"

        audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
        entries = audit_response.json()["items"]
        assert any(
            entry["action"] == "import_update_exhibit"
            and entry["resource_id"] == "lever-play"
            and "审核状态已回到待审核" in entry["summary"]
            and "Updated exhibit" not in entry["summary"]
            for entry in entries
        )
    finally:
        client.put("/api/exhibits/lever-play", json=original, headers=ADMIN_HEADERS)


def test_import_rejects_duplicate_exhibit_ids_in_same_file_before_persisting():
    first = valid_import_row("duplicate-import-demo")
    second = valid_import_row("duplicate-import-demo")
    second[1] = "Duplicate Import Demo Updated"

    response = client.post(
        "/api/exhibits/import",
        data={"commit": "true"},
        files={
            "file": (
                "duplicate-import.csv",
                csv_bytes([first, second]),
                "text/csv",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_rows"] == 0
    assert payload["imported_count"] == 0
    assert payload["errors"] == [
        {
            "row": 2,
            "field": "id",
            "message": "Duplicate exhibit id in import file: duplicate-import-demo",
        },
        {
            "row": 3,
            "field": "id",
            "message": "Duplicate exhibit id in import file: duplicate-import-demo",
        },
    ]
    assert client.get("/api/exhibits/duplicate-import-demo").status_code == 404


def test_import_rejects_unknown_related_exhibit_ids_before_persisting():
    row = valid_import_row("invalid-related-import-demo")
    row[-1] = "missing-related-exhibit"

    response = client.post(
        "/api/exhibits/import",
        data={"commit": "true"},
        files={
            "file": (
                "invalid-related.csv",
                csv_bytes([row]),
                "text/csv",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_rows"] == 0
    assert payload["imported_count"] == 0
    assert payload["errors"] == [
        {
            "row": 2,
            "field": "related_exhibit_ids",
            "message": "Unknown or self-referencing exhibit id: missing-related-exhibit",
        }
    ]
    assert client.get("/api/exhibits/invalid-related-import-demo").status_code == 404


def test_import_allows_related_exhibit_ids_from_same_batch():
    first = valid_import_row("batch-relation-a")
    first[-1] = "batch-relation-b"
    second = valid_import_row("batch-relation-b")
    second[-1] = "batch-relation-a"

    try:
        response = client.post(
            "/api/exhibits/import",
            data={"commit": "true"},
            files={
                "file": (
                    "batch-relations.csv",
                    csv_bytes([first, second]),
                    "text/csv",
                )
            },
            headers=EDITOR_HEADERS,
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["valid_rows"] == 2
        assert payload["imported_count"] == 2
        assert payload["errors"] == []

        graph_response = client.get("/api/exhibits/batch-relation-a/graph")
        assert graph_response.status_code == 200
        edge_types = {edge["type"] for edge in graph_response.json()["edges"]}
        assert "similar_to" in edge_types
    finally:
        client.delete("/api/exhibits/batch-relation-a", headers=ADMIN_HEADERS)
        client.delete("/api/exhibits/batch-relation-b", headers=ADMIN_HEADERS)


def test_import_commit_records_batch_audit_summary():
    first = valid_import_row("audit-batch-import-a")
    first[-1] = "audit-batch-import-b"
    second = valid_import_row("audit-batch-import-b")
    second[-1] = "audit-batch-import-a"

    try:
        response = client.post(
            "/api/exhibits/import",
            data={"commit": "true"},
            files={
                "file": (
                    "audit-batch.csv",
                    csv_bytes([first, second]),
                    "text/csv",
                )
            },
            headers=EDITOR_HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["imported_count"] == 2

        audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
        assert audit_response.status_code == 200
        entries = audit_response.json()["items"]
        assert any(
            entry["actor_role"] == "editor"
            and entry["action"] == "import_batch"
            and entry["resource_id"] == "audit-batch.csv"
            and "total_rows=2" in entry["summary"]
            and "imported=2" in entry["summary"]
            for entry in entries
        )
    finally:
        client.delete("/api/exhibits/audit-batch-import-a", headers=ADMIN_HEADERS)
        client.delete("/api/exhibits/audit-batch-import-b", headers=ADMIN_HEADERS)


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


def test_import_rejects_malformed_xlsx_with_structured_error():
    safe_client = TestClient(app, raise_server_exceptions=False)

    response = safe_client.post(
        "/api/exhibits/import",
        data={"commit": "false"},
        files={
            "file": (
                "broken.xlsx",
                b"not a valid xlsx archive",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=EDITOR_HEADERS,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error": "InvalidImportFile",
        "message": "Import file could not be parsed",
        "details": {
            "filename": "broken.xlsx",
            "supported_formats": ["csv", "xlsx"],
        },
    }


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


def test_import_accepts_gb18030_encoded_chinese_csv():
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
    row = valid_import_row("gb18030-import-demo")
    row[1] = "中文编码展项"
    row[2] = "基础科学"
    row[3] = "力学"
    row[4] = "儿童科技馆"
    row[16] = "GB18030 编码的历史资料行。"

    response = client.post(
        "/api/exhibits/import",
        data={"commit": "false"},
        files={
            "file": (
                "gb18030-headers.csv",
                csv_bytes_with_headers_encoding(chinese_headers, [row], "gb18030"),
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
    assert payload["items"][0]["id"] == "gb18030-import-demo"
    assert payload["items"][0]["name"] == "中文编码展项"
    assert client.get("/api/exhibits/gb18030-import-demo").status_code == 404


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
