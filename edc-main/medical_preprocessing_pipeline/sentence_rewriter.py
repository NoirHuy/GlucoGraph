import logging
from typing import List
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

class SentenceRewriter:
    """
    A class to split text into smaller sentences and perform coreference resolution
    using an LLM, making each sentence standalone and suitable for Information Extraction.
    """
    def __init__(self, model_name: str = "meta-llama/llama-3.3-70b-instruct", temperature: float = 0.0):
        self.llm = ChatOpenAI(
            model=model_name, 
            temperature=temperature,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        
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
        self.chain = self.prompt | self.llm | StrOutputParser()

    def rewrite(self, chunk_content: str, section_headers: str) -> List[str]:
        """
        Rewrites a chunk of text into standalone sentences with coreference resolution.
        """
        try:
            result = self.chain.invoke({
                "section_headers": section_headers,
                "chunk_content": chunk_content
            })
            
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
