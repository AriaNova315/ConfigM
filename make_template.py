from docx import Document

doc = Document()
table = doc.add_table(rows=4, cols=4)

# 表头
hdr = table.rows[0].cells
hdr[0].text = "序号"
hdr[1].text = "产品名称"
hdr[2].text = "产品标识"
hdr[3].text = "版本号"

# for 控制行（只放标签，数据不在这行）
table.rows[1].cells[0].text = "{%tr for item in items %}"

# 数据行（这行会被循环复制）
data = table.rows[2].cells
data[0].text = "{{ loop.index }}"
data[1].text = "{{ item.name }}"
data[2].text = "{{ item.code }}"
data[3].text = "{{ item.version }}"

# endfor 控制行
table.rows[3].cells[0].text = "{%tr endfor %}"

doc.save("test_template_prog.docx")
print("模板生成：test_template_prog.docx")
