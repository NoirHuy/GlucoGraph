# -*- coding: utf-8 -*-
"""
table_translator.py — Translates markdown tables into narrative text
                      configured to use the unified API key pool in llm_utils.py.
"""

import logging
from typing import Optional
import os
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class TableTranslator:
    """
    A specialized class to handle the translation of Markdown tables
    into flat, narrative clinical English sentences using the global APIKeyPool.
    """
    def __init__(self, model_name: str = "meta-llama/llama-3.3-70b-instruct", temperature: float = 0.0):
        logger.info("[TableTranslator] Initializing preprocessor LLM wrapper...")
        self.model_name = model_name
        self.temperature = temperature
        
        self.prompt = PromptTemplate(
            input_variables=["section_headers", "table_content"],
            template=(
                "You are an expert medical data extractor and clinical writer.\n"
                "The following markdown table was found under the section(s): '{section_headers}'.\n"
                "Please translate this table into clear, standalone, narrative clinical English sentences. "
                "Ensure that every relationship, metric, or clinical fact in the table rows is captured accurately. "
                "If the table contains abbreviations, keep them intact but structure the sentences clearly. "
                "Do NOT include conversational filler or your own commentary, just output the narrative text.\n\n"
                "Table:\n"
                "{table_content}\n\n"
                "Narrative translation:"
            )
        )

    def translate_table(self, table_content: str, section_headers: str) -> Optional[str]:
        """
        Translates a markdown table into narrative text.
        
        Args:
            table_content (str): The raw markdown string containing the table.
            section_headers (str): A string representation of the headers where the table was found.
            
        Returns:
            Optional[str]: The translated narrative string, or None if translation failed.
        """
        import sys
        # Ensure root of edc-main is in sys.path
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            
        import edc.utils.llm_utils as llm_utils
        
        try:
            user_content = self.prompt.format(
                section_headers=section_headers,
                table_content=table_content
            )
            messages = [{"role": "user", "content": user_content}]
            
            narrative = llm_utils.api_chat_completion(
                model=self.model_name,
                system_prompt=None,
                history=messages,
                temperature=self.temperature,
                max_tokens=2048
            )
            return narrative.strip()
        except Exception as e:
            logger.error(f"Error translating table: {e}")
            return None
