# -*- coding: utf-8 -*-
"""
main_pipeline.py — Unified medical text pre-processing pipeline.
                   Capable of processing both Markdown (.md) and raw clinical prose (.txt).
                   Clean web scraping artifacts, parse tables, resolve pronouns, and segment.
"""

import os
import json
import re
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# LangChain splitters for Markdown
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Local imports
from clean_prose import clean_medical_prose
from table_translator import TableTranslator
from sentence_rewriter import SentenceRewriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MedicalPreprocessingPipeline")

def load_environment():
    """Load environment variables from local and root .env files."""
    # Try loading root .env
    load_dotenv(dotenv_path="../.env")
    # Try loading current folder .env
    load_dotenv()
    if not os.getenv("OPENROUTER_API_KEY"):
        raise ValueError("OPENROUTER_API_KEY environment variable is not configured in the environment or .env file.")

def detect_table(content: str) -> bool:
    """Detect if markdown content contains a table separator line (|---|)."""
    return bool(re.search(r'\|[\s\-:]+\|', content))

def chunk_prose_by_paragraphs(text: str, max_chars: int = 1500) -> List[str]:
    """Splits text into paragraphs, grouping adjacent small paragraphs
    to form larger, context-rich chunks of about max_chars.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        if current_length + len(p_clean) > max_chars and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p_clean]
            current_length = len(p_clean)
        else:
            current_chunk.append(p_clean)
            current_length += len(p_clean) + 2  # plus newline separator
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def process_markdown(markdown_text: str, translator: TableTranslator, rewriter: SentenceRewriter) -> List[str]:
    """Process structured Markdown content with headers and tables."""
    logger.info("Splitting structured Markdown document by headers...")
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(markdown_text)
    logger.info(f"Created {len(md_header_splits)} semantic markdown chunks.")
    
    all_sentences = []
    for i, doc in enumerate(md_header_splits):
        content = doc.page_content
        metadata = doc.metadata
        headers_str = " > ".join([f"{k}: {v}" for k, v in metadata.items()])
        
        logger.info(f"Processing Markdown chunk {i+1}/{len(md_header_splits)} ({headers_str})")
        
        # 1. Table Detection & Translation
        if detect_table(content):
            logger.info("Markdown table detected. Sending to LLM for translation...")
            narrative = translator.translate_table(content, headers_str)
            if narrative:
                content = narrative
                logger.info("Table translated successfully.")
        
        # 2. Pronoun & Coreference Resolution
        sentences = rewriter.rewrite(content, headers_str)
        if sentences:
            all_sentences.extend(sentences)
            
    return all_sentences

def process_prose(raw_text: str, rewriter: SentenceRewriter) -> List[str]:
    """Clean, chunk, and resolve raw clinical prose text."""
    logger.info("Cleaning raw prose text using clean_medical_prose...")
    cleaned_text = clean_medical_prose(raw_text)
    
    logger.info("Segmenting cleaned prose into context-rich paragraph chunks...")
    chunks = chunk_prose_by_paragraphs(cleaned_text, max_chars=1500)
    logger.info(f"Created {len(chunks)} prose paragraph chunks.")
    
    all_sentences = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing prose chunk {i+1}/{len(chunks)} (len={len(chunk)})")
        # Pronoun & Coreference Resolution
        sentences = rewriter.rewrite(chunk, "Clinical Narrative Overview")
        if sentences:
            all_sentences.extend(sentences)
            
    return all_sentences

def process_medical_file(file_path: str, output_path: str):
    """Unified entry point to process a medical file (Markdown or Text)."""
    logger.info(f"Starting pre-processing pipeline for file: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found at: {file_path}")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
        
    translator = TableTranslator()
    rewriter = SentenceRewriter()
    
    is_markdown = file_path.lower().endswith(('.md', '.markdown'))
    
    if is_markdown:
        all_sentences = process_markdown(file_content, translator, rewriter)
    else:
        all_sentences = process_prose(file_content, rewriter)
        
    logger.info(f"Saving {len(all_sentences)} pre-processed sentences to {output_path}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for sentence in all_sentences:
            f.write(sentence + '\n')
            
    logger.info(f"Pre-processing completed successfully! Output saved to: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run medical text preprocessing pipeline.")
    parser.add_argument("--input", help="Path to input text or markdown file.")
    parser.add_argument("--output", help="Path to output cleaned sentences file.")
    args = parser.parse_args()

    try:
        load_environment()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        if args.input and args.output:
            input_file = args.input
            output_file = args.output
        else:
            # Default fallback
            input_file = os.path.join(script_dir, "datasets", "Overview_of_Diabetes_Mellitus.txt")
            output_file = os.path.join(script_dir, "output", "Overview_of_Diabetes_Mellitus_cleaned_sentences.txt")
            
        if not os.path.exists(input_file):
            logger.warning(f"File {input_file} not found. Please ensure the dataset file exists.")
        else:
            process_medical_file(input_file, output_file)
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
