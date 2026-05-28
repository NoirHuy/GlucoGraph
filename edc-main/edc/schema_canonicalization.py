from typing import List
import os
from pathlib import Path
import edc.utils.llm_utils as llm_utils
import re
from edc.utils.e5_mistral_utils import MistralForSequenceEmbedding
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np
import copy
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class SchemaCanonicalizer:
    # The class to handle the last stage: Schema Canonicalization
    def __init__(
        self,
        target_schema_dict: dict,
        embedder: SentenceTransformer,
        verify_model: AutoTokenizer = None,
        verify_tokenizer: AutoTokenizer = None,
        verify_openai_model: AutoTokenizer = None,
    ) -> None:
        # The canonicalizer uses an embedding model to first fetch candidates from the target schema, then uses a verifier schema to decide which one to canonicalize to or not
        # canonoicalize at all.

        assert verify_openai_model is not None or (verify_model is not None and verify_tokenizer is not None)
        self.verifier_model = verify_model
        self.verifier_tokenizer = verify_tokenizer
        self.verifier_openai_model = verify_openai_model
        self.schema_dict = target_schema_dict

        self.embedder = embedder

        # Embed the target schema
        self.schema_embedding_dict = {}

        print("Embedding target schema...")
        for relation, relation_definition in tqdm(target_schema_dict.items()):
            embedding = self.embedder.encode(relation_definition)
            self.schema_embedding_dict[relation] = embedding

    def retrieve_similar_relations(self, query_relation_definition: str, top_k=5):
        target_relation_list = list(self.schema_embedding_dict.keys())
        target_relation_embedding_list = list(self.schema_embedding_dict.values())
        if "sts_query" in self.embedder.prompts:
            query_embedding = self.embedder.encode(query_relation_definition, prompt_name="sts_query")
        else:
            query_embedding = self.embedder.encode(query_relation_definition)

        scores = np.array([query_embedding]) @ np.array(target_relation_embedding_list).T

        scores = scores[0]
        highest_score_indices = np.argsort(-scores)

        return {
            target_relation_list[idx]: self.schema_dict[target_relation_list[idx]]
            for idx in highest_score_indices[:top_k]
        }, [scores[idx] for idx in highest_score_indices[:top_k]]

    def llm_verify(
        self,
        input_text_str: str,
        query_triplet: List[str],
        query_relation_definition: str,
        prompt_template_str: str,
        candidate_relation_definition_dict: dict,
        relation_example_dict: dict = None,
        subject_type: str = "Unknown",
        object_type: str = "Unknown",
    ):
        canonicalized_triplet = copy.deepcopy(query_triplet)
        choice_letters_list = []
        choices = ""
        candidate_relations = list(candidate_relation_definition_dict.keys())
        candidate_relation_descriptions = list(candidate_relation_definition_dict.values())
        
        # Mapping to trace which relation and direction is chosen
        choice_mapping = {}
        
        letter_idx = 0
        for idx, rel in enumerate(candidate_relations):
            # Option 1: Original direction
            letter_orig = chr(ord("@") + letter_idx + 1)
            choice_letters_list.append(letter_orig)
            choice_mapping[letter_orig] = (rel, False)
            choices += f"{letter_orig}. '{rel}' (Original direction: Subject='{query_triplet[0]}', Object='{query_triplet[2]}')\n"
            choices += f"   Definition: {candidate_relation_descriptions[idx]}\n\n"
            letter_idx += 1
            
            # Option 2: Swapped direction (if swapping Subject & Object makes it fit better)
            letter_swap = chr(ord("@") + letter_idx + 1)
            choice_letters_list.append(letter_swap)
            choice_mapping[letter_swap] = (rel, True)
            choices += f"{letter_swap}. '{rel}' (Swapped direction: Subject='{query_triplet[2]}', Object='{query_triplet[0]}')\n"
            choices += f"   Definition: {candidate_relation_descriptions[idx]}\n\n"
            letter_idx += 1
            
        none_letter = chr(ord("@") + letter_idx + 1)
        choices += f"{none_letter}. None of the above.\n"

        verification_prompt = prompt_template_str.format_map(
            {
                "input_text": input_text_str,
                "query_triplet": query_triplet,
                "subject_type": subject_type,
                "object_type": object_type,
                "query_relation": query_triplet[1],
                "query_relation_definition": query_relation_definition,
                "choices": choices,
            }
        )

        messages = [{"role": "user", "content": verification_prompt}]
        if self.verifier_openai_model is None:
            verification_result = llm_utils.generate_completion_transformers(
                messages, self.verifier_model, self.verifier_tokenizer, answer_prepend="Answer: ", max_new_token=5
            )
        else:
            verification_result = llm_utils.api_chat_completion(
                self.verifier_openai_model, None, messages, max_tokens=256
            )

        # ── Robust letter extraction supporting both small and reasoning models ──
        selected_letter = None
        if verification_result:
            cleaned = verification_result.strip()

            # Priority 1 — explicit answer marker (MiMo usually writes "Answer: A")
            answer_match = re.search(r'[Aa]nswer\s*[:.=]?\s*([A-Z])', cleaned)
            if answer_match and answer_match.group(1).upper() in choice_letters_list:
                selected_letter = answer_match.group(1).upper()

            # Priority 2 — last isolated valid letter (e.g. "...therefore I choose A")
            if selected_letter is None:
                isolated = re.findall(r'(?<![A-Za-z])([A-Z])(?![A-Za-z])', cleaned)
                for letter in reversed(isolated):
                    if letter.upper() in choice_letters_list:
                        selected_letter = letter.upper()
                        break

            # Priority 3 — original scan from start (fallback for plain "A" responses)
            if selected_letter is None:
                for char in cleaned.strip(" `\"'*:-_"):
                    if char.upper() in choice_letters_list:
                        selected_letter = char.upper()
                        break

        if selected_letter is not None:
            chosen_rel, should_swap = choice_mapping[selected_letter]
            if should_swap:
                canonicalized_triplet[0] = query_triplet[2]
                canonicalized_triplet[1] = chosen_rel
                canonicalized_triplet[2] = query_triplet[0]
                logger.info(f"[CANONICALIZER] Successfully swapped direction for: {query_triplet} -> {canonicalized_triplet}")
            else:
                canonicalized_triplet[1] = chosen_rel
        else:
            return None

        return canonicalized_triplet

    def canonicalize(
        self,
        input_text_str: str,
        open_triplet,
        open_relation_definition_dict: dict,
        verify_prompt_template: str,
        enrich=False,
    ):

        open_relation = open_triplet[1].strip()

        # Clean keys in the dictionary just in case
        cleaned_def_dict = {k.strip(): v for k, v in open_relation_definition_dict.items()}

        if open_relation in self.schema_dict:
            # The relation is already canonical
            # candidate_relations, candidate_scores = self.retrieve_similar_relations(
            #     open_relation_definition_dict[open_relation]
            # )
            return open_triplet, {}

        candidate_relations = []
        candidate_scores = []

        if len(self.schema_dict) != 0:
            if open_relation not in cleaned_def_dict:
                canonicalized_triplet = None
            else:
                # Find subject and object types from _entries
                subject_type = "Unknown"
                object_type = "Unknown"
                if "_entries" in open_relation_definition_dict:
                    for entry in open_relation_definition_dict["_entries"]:
                        if (entry.get("subject") == open_triplet[0] and
                            entry.get("relation") == open_triplet[1] and
                            entry.get("object") == open_triplet[2]):
                            subject_type = entry.get("subject_type") or "Unknown"
                            object_type = entry.get("object_type") or "Unknown"
                            break

                candidate_relations, candidate_scores = self.retrieve_similar_relations(
                    cleaned_def_dict[open_relation]
                )
                canonicalized_triplet = self.llm_verify(
                    input_text_str,
                    open_triplet,
                    cleaned_def_dict[open_relation],
                    verify_prompt_template,
                    candidate_relations,
                    None,
                    subject_type=subject_type,
                    object_type=object_type,
                )
        else:
            canonicalized_triplet = None

        if canonicalized_triplet is None:
            # Cannot be canonicalized
            if enrich:
                self.schema_dict[open_relation] = open_relation_definition_dict[open_relation]
                if "sts_query" in self.embedder.prompts:
                    embedding = self.embedder.encode(
                        open_relation_definition_dict[open_relation], prompt_name="sts_query"
                    )
                else:
                    embedding = self.embedder.encode(open_relation_definition_dict[open_relation])
                self.schema_embedding_dict[open_relation] = embedding
                canonicalized_triplet = open_triplet
        return canonicalized_triplet, dict(zip(candidate_relations, candidate_scores))
