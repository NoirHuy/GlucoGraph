# -*- coding: utf-8 -*-
"""
clean_prose.py — Specialized medical prose text cleaner to remove web scraping noise, 
                  navigation menus, social media footers, and citation brackets.
"""

import re

def clean_medical_prose(text: str) -> str:
    """Cleans raw scraped medical prose text by removing website noise,
    social media tags, disclaimers, copyrights, author/reviewer bios,
    empty/pipe lines, and cleaning citations.
    """
    if not text:
        return ""
        
    lines = text.split('\n')
    cleaned_lines = []
    
    # Noise line patterns
    noise_patterns = [
        re.compile(r'^\s*\|\s*$'),  # Single pipes
        re.compile(r'^\s*(View Patient Education|Multimedia|About|Disclaimer|Cookie Preferences|quizzes_lightbulb_red|Test your Knowledge.*)\s*$', re.I),
        re.compile(r'^\s*(video|multimedia|About|Disclaimer|Cookie Preferences)\s*$', re.I),
        re.compile(r'^\s*follow us on (facebook|youtube|x|instagram)\s*$', re.I),
        re.compile(r'^\s*Copyright©.*$', re.I),
        re.compile(r'^\s*(Reviewed By|Reviewed/Revised|ByErika F\.|Reviewed ByGlenn).*$', re.I),
        re.compile(r'^\s*(In this topic|Other topics in this chapter)\s*$', re.I),
        re.compile(r'^\s*This icon serves as a link to download.*$', re.I),
        re.compile(r'^Diabetes in children and adolescents is discussed in detail elsewhere\.$', re.I),
    ]
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
            
        # Check if line matches any noise pattern
        is_noise = False
        for pattern in noise_patterns:
            if pattern.match(stripped):
                is_noise = True
                break
                
        if is_noise:
            continue
            
        # Clean inline citation numbers e.g. (1, 2), (3), [4]
        # Clean parentheses citations like "(1, 2)" or "(1)"
        line_cleaned = re.sub(r'\s*\(\d+(?:\s*,\s*\d+)*\)', '', line)
        # Clean bracket citations like "[1]" or "[1, 2]"
        line_cleaned = re.sub(r'\s*\[\d+(?:\s*,\s*\d+)*\]', '', line_cleaned)
        
        cleaned_lines.append(line_cleaned)
        
    # Collapse multiple consecutive empty lines
    collapsed_lines = []
    prev_was_empty = False
    for line in cleaned_lines:
        if line.strip() == "":
            if not prev_was_empty:
                collapsed_lines.append("")
                prev_was_empty = True
        else:
            collapsed_lines.append(line)
            prev_was_empty = False
            
    return "\n".join(collapsed_lines).strip()
