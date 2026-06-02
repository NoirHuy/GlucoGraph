# -*- coding: utf-8 -*-
"""
sentence_rewriter.py — Sentence splitter and coreference resolution engine
                        configured to use the unified API key pool in llm_utils.py.
"""

import logging
from typing import List
import os
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class SentenceRewriter:
    """
    A class to split text into smaller sentences and perform coreference resolution
    using the global APIKeyPool, making each sentence standalone and suitable for Information Extraction.
    """
    def __init__(self, model_name: str = "meta-llama/llama-3.3-70b-instruct", temperature: float = 0.0):
        logger.info("[SentenceRewriter] Initializing preprocessor LLM wrapper...")
        self.model_name = model_name
        self.temperature = temperature
            
        self.prompt = PromptTemplate(
            input_variables=["section_headers", "chunk_content"],
            template=(
                "You are an expert medical linguist and data engineer.\n"
                "I will give you a chunk of medical text from the section '{section_headers}'.\n"
                "Your task is to break this text down into simple, standalone, clinical English sentences.\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Coreference Resolution: You MUST replace all pronouns (it, they, this, these, he, she, etc.) and implicit references (e.g., 'the disease', 'the drug', 'this treatment', 'the patients') with the explicit entity names they refer to, using the surrounding text or the section headers.\n"
                "2. Standalone: Every single sentence must make complete sense on its own without needing any preceding or succeeding context.\n"
                "3. Formatting: Output strictly ONE sentence per line. Do not use bullet points, numbering, or introductory/concluding conversational text. Just the sentences.\n\n"
                "Original Text:\n"
                "{chunk_content}\n\n"
                "Resolved Standalone Sentences (one per line):"
            )
        )

    def rewrite(self, chunk_content: str, section_headers: str) -> List[str]:
        """
        Rewrites a chunk of text into standalone sentences with coreference resolution.
        """
        import sys
        # Ensure root of edc-main is in sys.path
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            
        import edc.utils.llm_utils as llm_utils
        
        try:
            # Format the user prompt
            user_message = self.prompt.format(
                section_headers=section_headers,
                chunk_content=chunk_content
            )
            messages = [{"role": "user", "content": user_message}]
            
            result = llm_utils.api_chat_completion(
                model=self.model_name,
                system_prompt=None,
                history=messages,
                temperature=self.temperature,
                max_tokens=2048
            )
            
            # Post-process the output
            lines = result.split('\n')
            sentences = []
            for line in lines:
                line = line.strip()
                # Skip empty lines or conversational fillers
                if not line or line.lower().startswith("here are") or line.lower().startswith("resolved"):
                    continue
                # Remove common list indicators if the LLM adds them
                line = line.lstrip('-*• ')
                import re
                line = re.sub(r'^\d+\.\s*', '', line)
                if line:
                    sentences.append(line)
            return sentences
        except Exception as e:
            logger.error(f"Error rewriting sentences: {e}")
            return []
