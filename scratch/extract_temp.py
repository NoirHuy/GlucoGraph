# -*- coding: utf-8 -*-
import zipfile
import xml.etree.ElementTree as ET
import os

def get_docx_text(path):
    doc = zipfile.ZipFile(path)
    xml_content = doc.read('word/document.xml')
    root = ET.fromstring(xml_content)
    
    text = []
    for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
        p_text = []
        for run in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if run.text:
                p_text.append(run.text)
        text.append("".join(p_text))
    return "\n".join(text)

if __name__ == "__main__":
    docx_path = "thesis/Báo Cáo Khóa Luận/BaoCaoKhoaLuan_LeQuangHuy_223571.docx"
    output_path = "scratch/extracted_thesis_text.txt"
    try:
        text = get_docx_text(docx_path)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print("SUCCESS")
    except Exception as e:
        print("ERROR:", str(e))
