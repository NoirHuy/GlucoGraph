# -*- coding: utf-8 -*-
"""
table_translator.py — Translates markdown tables into narrative text
                      configured to strictly use OpenRouter API.
"""

import logging
from typing import Optional
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

class TableTranslator:
    """
    A specialized class to handle the translation of Markdown tables
    into flat, narrative clinical English sentences using an LLM.
    """
    def __init__(self, model_name: str = "meta-llama/llama-3.3-70b-instruct", temperature: float = 0.0):
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set in the environment or .env file.")
            
        logger.info("[TableTranslator] Initializing preprocessor LLM via OpenRouter API...")
        self.llm = ChatOpenAI(
            model=model_name, 
            temperature=temperature,
            api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # We include the section headers as context so the LLM understands the context of the table.
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
        self.chain = self.prompt | self.llm | StrOutputParser()

    def translate_table(self, table_content: str, section_headers: str) -> Optional[str]:
        """
        Translates a markdown table into narrative text.
        
        Args:
            table_content (str): The raw markdown string containing the table.
            section_headers (str): A string representation of the headers where the table was found.
            
        Returns:
            Optional[str]: The translated narrative string, or None if translation failed.
        """
        try:
            narrative = self.chain.invoke({
                "section_headers": section_headers,
                "table_content": table_content
            })
            return narrative.strip()
        except Exception as e:
            logger.error(f"Error translating table: {e}")
            return None
