import os
import json
import re
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# LangChain imports
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Local imports
from table_translator import TableTranslator
from sentence_rewriter import SentenceRewriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env file and check for OPENROUTER_API_KEY."""
    load_dotenv()
    if not os.getenv("OPENROUTER_API_KEY"):
        raise ValueError("OPENROUTER_API_KEY environment variable is not set in .env")

def detect_table(content: str) -> bool:
    """
    Detect if the markdown content contains a table.
    We look for the typical markdown table separator pattern: |---|
    """
    # Regex to match a line that contains pipe and dashes indicating a table separator
    return bool(re.search(r'\|[\s\-:]+\|', content))

def process_markdown_file(file_path: str, output_path: str):
    """
    Main pipeline to process a markdown file:
    1. Chunk by headers
    2. Detect tables and translate using LLM
    3. Rewrite chunks into standalone sentences with coreference resolution
    4. Save as TXT with one sentence per line
    """
    logger.info(f"Starting pipeline for file: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # 1. Semantic Chunking
    logger.info("Chunking document based on Markdown headers...")
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # Split text into Document objects (each has page_content and metadata)
    md_header_splits = markdown_splitter.split_text(markdown_text)
    
    logger.info(f"Created {len(md_header_splits)} semantic chunks.")

    translator = TableTranslator()
    rewriter = SentenceRewriter()
    
    all_sentences: List[str] = []

    # 2. Iterate through chunks and detect/translate tables
    for i, doc in enumerate(md_header_splits):
        content = doc.page_content
        metadata = doc.metadata
        
        # Flatten headers for context (e.g., "Header 1: Intro > Header 2: Background")
        headers_str = " > ".join([f"{k}: {v}" for k, v in metadata.items()])
        
        logger.info(f"Processing chunk {i+1}/{len(md_header_splits)} (Headers: {headers_str})")
        
        # 3. Table Detection and Translation
        if detect_table(content):
            logger.info("Markdown table detected in this chunk. Sending to LLM for translation...")
            narrative_text = translator.translate_table(
                table_content=content,
                section_headers=headers_str
            )
            
            if narrative_text:
                # Replace the original table content with the flattened narrative
                content = narrative_text
                logger.info("Table translated successfully.")
            else:
                logger.warning("Table translation failed. Keeping original content.")
        
        # 4. Sentence rewriting and coreference resolution
        logger.info("Rewriting chunk into resolved standalone sentences...")
        sentences = rewriter.rewrite(
            chunk_content=content,
            section_headers=headers_str
        )
        
        if sentences:
            all_sentences.extend(sentences)
            logger.info(f"Extracted {len(sentences)} sentences.")
        else:
            logger.warning("No sentences extracted from this chunk.")

    # 5. Output to TXT
    logger.info(f"Saving {len(all_sentences)} sentences to {output_path}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for sentence in all_sentences:
            f.write(sentence + '\n')
        
    logger.info(f"Pipeline completed successfully. Output saved to {output_path}")

if __name__ == "__main__":
    try:
        load_environment()
        
        # Paths for the script. Update these to point to the actual files you want to run.
        input_file = "../edc-main/datasets/disease/diabetes/PIIS1530891X23000344_cleaned.md" 
        output_file = "output/processed_narrative.txt"
        
        if not os.path.exists(input_file):
            logger.warning(f"File {input_file} not found.")
            print(f"Please update the 'input_file' variable in main_pipeline.py to point to your specific Markdown file.")
        else:
            process_markdown_file(input_file, output_file)
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
