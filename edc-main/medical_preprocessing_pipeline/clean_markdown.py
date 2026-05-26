import re

def clean_md(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    
    # Patterns to remove
    footer_patterns = [
        re.compile(r'^S\.L\. Samson, P\. Vellanki, L\. Blonde et al\.$'),
        re.compile(r'^Endocrine Practice 29 \(2023\) 305[-–ₑ]340$'),
        re.compile(r'^diabetes treatment$'),
        re.compile(r'^type 2 diabetes$'),
        re.compile(r'^---$'),
        re.compile(r'^\d+$'), # page numbers like 306, 335
    ]
    
    for line in lines:
        if line.strip() == '## Acknowledgment' or line.strip() == '## References':
            break # Stop at acknowledgments
            
        # Remove images
        line = re.sub(r'!\[.*?\]\(.*?\)', '', line)
        
        # Remove footers
        skip_line = False
        for pattern in footer_patterns:
            if pattern.match(line.strip()):
                skip_line = True
                break
        
        if not skip_line:
            cleaned_lines.append(line)

    # Remove consecutive blank lines
    final_text = []
    blank_count = 0
    for line in cleaned_lines:
        if line.strip() == '':
            blank_count += 1
        else:
            blank_count = 0
            
        if blank_count <= 2:
            final_text.append(line)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(final_text)

if __name__ == '__main__':
    clean_md('PIIS1530891X23000344.md', 'PIIS1530891X23000344_cleaned.md')
