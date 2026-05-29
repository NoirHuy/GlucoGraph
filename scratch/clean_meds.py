import re
import os

def clean_text(text):
    # 1. Remove parenthetical references like (1), (2), (1, 2), (1, 2, 3, 4, 5), (6,7), [1], [2]
    text = re.sub(r'\s*\(\d+(?:,\s*\d+)*\)', '', text)
    text = re.sub(r'\s*\[\d+(?:,\s*\d+)*\]', '', text)
    
    # 2. Fix typos/spacing issues
    # e.g., "adequate insulin(due to" -> "adequate insulin (due to"
    text = re.sub(r'(\w)\((\w)', r'\1 (\2', text)
    # e.g., "PCSK -9" -> "PCSK-9"
    text = re.sub(r'PCSK\s*-9', 'PCSK-9', text)
    
    return text

def split_into_sentences(text):
    # Pure Python sentence splitter considering common abbreviations in the text
    abbreviations = {
        'eg', 'ie', 'al', 'dr', 'vs', 'mr', 'mrs', 'ms', 'prof', 'u-500', 'u-300', 'u-100', 'am', 'pm'
    }
    
    # Simple regex to split sentences, keeping delimiters
    sentences = re.split(r'(\. |\? |\! )', text)
    
    result = []
    current = ""
    for item in sentences:
        if not item:
            continue
        if item in {'. ', '? ', '! '}:
            current += item.strip()
            # Check if current sentence ends with an abbreviation
            last_word = re.sub(r'[^\w\-]', '', current.split()[-1]).lower() if current.split() else ""
            if last_word in abbreviations:
                current += " "
            else:
                result.append(current.strip())
                current = ""
        else:
            current += item
            
    if current.strip():
        result.append(current.strip())
        
    return result

def clean_and_chunk(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return
        
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    cleaned_sentences = []
    
    # Headers to ignore entirely
    ignored_headers = {
        'insulin', 'insulin preparations', 'table', 
        'onset, peak, and duration of action of human insulin preparations*',
        'insulin regimens for type 1 diabetes', 'insulin pumps',
        'insulin regimens for type 2 diabetes', 'complications of insulin treatment',
        'insulin references', 'oral antihyperglycemic medications',
        'characteristics of oral antihyperglycemics', 'sulfonylureas',
        'short-acting insulin secretagogues', 'biguanides', 'thiazolidinediones',
        'alpha-glucosidase inhibitors', 'dipeptidyl peptidase-4 inhibitors',
        'sodium glucose cotransporter 2 inhibitors', 'dopamine agonist',
        'oral antihyperglycemic medications references',
        'injectable antihyperglycemic medications', 'glucagon-like peptide-1 (glp-1) receptor agonists',
        'dual incretin agonists (glucose-dependent insulinotropic polypeptide [gip]/ glucagon-like peptide-1 [glp-1] receptor agonist)',
        'characteristics of injectable non-insulin antihyperglycemic medications',
        'amylin analog', 'injectable antihyperglycemic medications references',
        'disease-modifying medications for diabetes', 'disease-modifying medications references',
        'adjunctive medications for diabetes', 'statins for ascvd prevention'
    }
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # Check if line is a header
        if line.lower() in ignored_headers or re.match(r'^\d+\.\s+.*', line) or (len(line) < 60 and not line.endswith('.')):
            i += 1
            continue
            
        # Handle list structure (e.g. "Insulin is typically administered as either:" followed by list items)
        if line.endswith(':'):
            intro = line[:-1].strip()
            # Look ahead for list items
            items = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                # If next line ends with period or is a long sentence, or looks like a new header, stop list item reading
                if next_line.lower() in ignored_headers or (len(next_line) < 60 and not next_line.endswith('.')) and not next_line.startswith('-'):
                    break
                
                # Check if it looks like a list item
                items.append(next_line)
                j += 1
            
            if items:
                # Combine intro with each item to form a complete sentence
                for item in items:
                    # Clean and strip bullet symbols or lowercase start
                    cleaned_item = re.sub(r'^[-\*\u2022]\s*', '', item).strip()
                    # Lowercase first letter if item starts with capital but intro connects to it
                    if cleaned_item and cleaned_item[0].isupper() and intro.endswith(('either', 'following', 'as')):
                        cleaned_item = cleaned_item[0].lower() + cleaned_item[1:]
                    
                    full_sentence = f"{intro} {cleaned_item}"
                    full_sentence = clean_text(full_sentence)
                    
                    # Ensure ends with period
                    if not full_sentence.endswith('.'):
                        full_sentence += '.'
                    cleaned_sentences.append(full_sentence)
                
                i = j # skip processed lines
                continue
            else:
                # If no list items found, just treat it as regular sentence
                line = clean_text(line)
                cleaned_sentences.append(line)
                i += 1
                continue
                
        # Regular paragraph handling
        cleaned_line = clean_text(line)
        sentences = split_into_sentences(cleaned_line)
        for sent in sentences:
            sent_str = sent.strip()
            if sent_str:
                # Skip numeric example data lines if too short or not grammatical
                if sent_str.startswith(('Preprandial fingerstick', 'Total daily dose', 'Correction factor', 'Estimated carbohydrate', 'Carbohydrate:insulin', 'Target glucose', 'Prandial insulin dose', 'Correction dose', 'Total dose prior')):
                    continue
                # Skip literature reference lines like "Kravarusic J, Aleppo G: ..." or doi links
                if 'doi:' in sent_str.lower() or 'vol.' in sent_str.lower() or re.search(r'\d{4};\d+', sent_str):
                    continue
                if not sent_str.endswith('.'):
                    sent_str += '.'
                cleaned_sentences.append(sent_str)
        i += 1
        
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        for sent in cleaned_sentences:
            f.write(sent + '\n')
            
    print(f"Successfully processed {len(lines)} lines into {len(cleaned_sentences)} clean chunks!")

if __name__ == '__main__':
    input_file = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\datasets\disease\diabetes\merckmanuals\Medications for Diabetes Mellitus Treatment.txt"
    output_file = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\datasets\disease\diabetes\merckmanuals\Medications for Diabetes Mellitus Treatment_chunked.txt"
    clean_and_chunk(input_file, output_file)
