import zipfile
import xml.etree.ElementTree as ET
import sys

# Set encoding to utf-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

def get_docx_text(path):
    try:
        doc = zipfile.ZipFile(path)
        xml_content = doc.read('word/document.xml')
        root = ET.fromstring(xml_content)
        
        text = []
        # Find all paragraphs
        for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
            p_text = []
            # Find all text runs in this paragraph
            for run in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                if run.text:
                    p_text.append(run.text)
            text.append("".join(p_text))
        return "\n".join(text)
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    docx_path = "e:/HK2(2025-2026)/Đồ Án 2/MainFolder/MyProject/BaiBaoKhoaHoc_LeQuangHuy_IEEE.docx"
    output_path = "e:/HK2(2025-2026)/Đồ Án 2/MainFolder/MyProject/scratch/paper_text.txt"
    text = get_docx_text(docx_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Extracted text successfully written to scratch/paper_text.txt")
