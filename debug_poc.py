from docxtpl import DocxTemplate

tpl = DocxTemplate("test_template_prog.docx")

context = {
    "items": [
        {"name": "XXX软件", "code": "SW-001", "version": "V1.0"},
        {"name": "配置管理工具", "code": "SW-002", "version": "V2.1"},
        {"name": "测试框架", "code": "SW-003", "version": "V0.9"},
    ]
}

tpl.render(context)

for i, table in enumerate(tpl.docx.tables):
    print(f"=== 输出表格 {i}，共 {len(table.rows)} 行 ===")
    for j, row in enumerate(table.rows):
        print(f"  行 {j}: {[cell.text for cell in row.cells]}")
