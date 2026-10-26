from docxtpl import DocxTemplate

tpl = DocxTemplate("test_template_fixed.docx")

context = {
    "items": [
        {"name": "XXX软件", "code": "SW-001", "version": "V1.0"},
        {"name": "配置管理工具", "code": "SW-002", "version": "V2.1"},
        {"name": "测试框架", "code": "SW-003", "version": "V0.9"},
    ]
}

tpl.render(context)
tpl.save("test_output.docx")
print("生成成功：test_output.docx")
