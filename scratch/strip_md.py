import re

def strip_base64_images(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace base64 image data with a placeholder
    # Base64 strings can be very long and can contain A-Za-z0-9+/ and =
    pattern = r'!\[.*?\]\(data:image\/[a-zA-Z]+;base64,[a-zA-Z0-9\/\+=\s\n\r]+?\)'
    
    # We can also do a simpler replacement for any markdown image with data:image
    # or just clean up the content. Let's do a regex replacement.
    cleaned_content, count = re.subn(pattern, '[IMAGE_PLACEHOLDER]', content)
    print(f"Stripped {count} base64 images.")
    
    # Let's also do a fallback if there's any remaining massive data:image URL
    # such as src="data:image/..." or similar
    pattern_html = r'src="data:image\/[a-zA-Z]+;base64,[a-zA-Z0-9\/\+=\s\n\r]+?"'
    cleaned_content, count_html = re.subn(pattern_html, 'src="[IMAGE_PLACEHOLDER]"', cleaned_content)
    print(f"Stripped {count_html} HTML base64 images.")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    print(f"Cleaned file written to {output_path}")

if __name__ == '__main__':
    strip_base64_images(
        r'e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\de_cuong_chi_tiet_khoa_luan.md',
        r'e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\scratch\de_cuong_stripped.md'
    )
