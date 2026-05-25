import os
import ast
import json
import logging
import requests
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class UMLSNormalizer:
    """Post-processor that maps and aligns raw/canonical triplets to the UMLS dictionary.
    Connects to the NIH UTS REST API (Option B) for accurate online matching.
    Includes persistent on-disk caching to optimize performance and prevent redundant API requests.
    """

    def __init__(self, api_key: str = None, cache_path: str = None):
        self.api_key = api_key or os.environ.get("UMLS_API_KEY", "")
        self.base_url = "https://uts-ws.nlm.nih.gov/rest"
        # Default cache file in the output directory
        self.cache_path = cache_path or "./output/umls_cache.json"
        self.cache = {}
        
        if not self.api_key:
            logger.warning("[UMLSNormalizer] No UMLS API Key provided (via argument or UMLS_API_KEY env var). "
                           "UMLS mapping will run in dry-run mode (no API calls, terms will map to themselves).")
        
        self.load_cache()

    def load_cache(self):
        """Loads persistent cache of UMLS term mappings from disk."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"[UMLSNormalizer] Loaded {len(self.cache)} entries from cache: {self.cache_path}")
            except Exception as e:
                logger.warning(f"[UMLSNormalizer] Failed to load cache file: {e}. Starting fresh.")
                self.cache = {}

    def save_cache(self):
        """Saves persistent cache of UMLS term mappings to disk."""
        # Ensure parent directory exists
        cache_dir = os.path.dirname(os.path.abspath(self.cache_path))
        os.makedirs(cache_dir, exist_ok=True)
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4, ensure_ascii=False)
            logger.debug(f"[UMLSNormalizer] Saved {len(self.cache)} entries to cache.")
        except Exception as e:
            logger.warning(f"[UMLSNormalizer] Failed to save cache file: {e}")

    def query_term(self, term: str) -> Dict[str, Any]:
        """Queries NLM UTS REST API to search for CUI and semantic types for a term.
        Uses cached data if available.
        """
        term_clean = term.strip()
        if not term_clean:
            return {"cui": "NONE", "canonical": "", "semantic_type": "Unknown", "score": 0.0}

        term_key = term_clean.lower()
        if term_key in self.cache:
            return self.cache[term_key]

        # Dry-run if no API key is set
        if not self.api_key:
            res = {"cui": "NONE", "canonical": term_clean, "semantic_type": "Unknown", "score": 0.0}
            self.cache[term_key] = res
            return res

        try:
            # 1. Search for CUI using 'words' match type (robust to slight variants)
            search_url = f"{self.base_url}/search/current"
            # Try to query the search endpoint
            search_params = {
                "string": term_clean,
                "apiKey": self.api_key,
                "pageSize": 1
            }
            
            logger.debug(f"[UMLSNormalizer] Querying UTS Search for: '{term_clean}'")
            response = requests.get(search_url, params=search_params, timeout=12)
            response.raise_for_status()
            search_data = response.json()
            
            results = search_data.get("result", {}).get("results", [])
            if not results:
                # No match found
                res = {"cui": "NONE", "canonical": term_clean, "semantic_type": "Unknown", "score": 0.0}
                self.cache[term_key] = res
                self.save_cache()
                return res

            best_match = results[0]
            cui = best_match.get("ui", "NONE")
            pref_name = best_match.get("name", term_clean)

            # 2. Query specific concept details to get Semantic Types
            semantic_type = "Unknown"
            if cui != "NONE":
                detail_url = f"{self.base_url}/content/current/CUI/{cui}"
                detail_params = {"apiKey": self.api_key}
                
                logger.debug(f"[UMLSNormalizer] Fetching CUI details for: {cui} ({pref_name})")
                detail_response = requests.get(detail_url, params=detail_params, timeout=12)
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    sem_types = detail_data.get("result", {}).get("semanticTypes", [])
                    if sem_types:
                        sem_type_list = []
                        for st in sem_types:
                            st_name = st.get("name", "")
                            st_uri = st.get("uri", "")
                            # Extract TUI from URI (e.g. "https://.../TUI/T047" -> "T047")
                            st_tui = st_uri.split("/")[-1] if st_uri else ""
                            if st_tui:
                                sem_type_list.append(f"{st_name} ({st_tui})")
                            else:
                                sem_type_list.append(st_name)
                        semantic_type = ", ".join(sem_type_list)

            res = {
                "cui": cui,
                "canonical": pref_name,
                "semantic_type": semantic_type,
                "score": 1.0  # Top API result treated as confidence score 1.0
            }
            
            # Save to persistent cache
            self.cache[term_key] = res
            self.save_cache()
            return res

        except Exception as e:
            logger.warning(f"[UMLSNormalizer] Error querying UMLS API for '{term_clean}': {e}. Falling back to default.")
            # Do not write temporary failures to the persistent cache so they can be retried later
            return {"cui": "NONE", "canonical": term_clean, "semantic_type": "Unknown", "score": 0.0}

    def normalize_triplets(self, triplets: List[List[str]]) -> Tuple[List[Dict[str, Any]], List[List[str]]]:
        """Maps a list of raw triplets to UMLS.
        Returns:
            - A list of detailed dictionary mappings (with CUIs and semantic types).
            - A list of clean [UMLS_Preferred_Subject, relation, UMLS_Preferred_Object] lists.
        """
        mapped_triplets = []
        plain_triplets = []

        for triplet in triplets:
            if len(triplet) != 3:
                # If malformed, preserve as-is
                plain_triplets.append(triplet)
                mapped_triplets.append({
                    "subject": {"original": str(triplet), "canonical": str(triplet), "cui": "NONE", "semantic_type": "Unknown", "score": 0.0},
                    "relation": "Unknown",
                    "object": {"original": "", "canonical": "", "cui": "NONE", "semantic_type": "Unknown", "score": 0.0}
                })
                continue

            sub, rel, obj = triplet
            sub_res = self.query_term(sub)
            obj_res = self.query_term(obj)

            mapped_triplets.append({
                "subject": {
                    "original": sub,
                    "canonical": sub_res["canonical"],
                    "cui": sub_res["cui"],
                    "semantic_type": sub_res["semantic_type"],
                    "score": sub_res["score"]
                },
                "relation": rel,
                "object": {
                    "original": obj,
                    "canonical": obj_res["canonical"],
                    "cui": obj_res["cui"],
                    "semantic_type": obj_res["semantic_type"],
                    "score": obj_res["score"]
                }
            })

            plain_triplets.append([sub_res["canonical"], rel, obj_res["canonical"]])

        return mapped_triplets, plain_triplets

    def normalize_file(self, input_file_path: str, output_json_path: str, output_txt_path: str):
        """Processes a canon_kg.txt file, normalizes all entities, and writes structured JSON and clean TXT outputs."""
        if not os.path.exists(input_file_path):
            logger.error(f"[UMLSNormalizer] Input file not found: {input_file_path}")
            return

        logger.info(f"[UMLSNormalizer] Reading canonicalized triplets from: {input_file_path}")
        
        with open(input_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        json_output = []
        txt_lines = []

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                txt_lines.append("")
                continue

            try:
                # Safely parse the Python list from the line
                triplets = ast.literal_eval(line_str)
                if not isinstance(triplets, list):
                    logger.warning(f"[UMLSNormalizer] Line {idx} is not a valid list: {line_str}")
                    txt_lines.append(line_str)
                    continue

                mapped_trips, plain_trips = self.normalize_triplets(triplets)
                
                json_output.append({
                    "line_index": idx,
                    "raw_triplets": triplets,
                    "umls_mapped_triplets": mapped_trips
                })
                
                txt_lines.append(str(plain_trips))

            except Exception as e:
                logger.error(f"[UMLSNormalizer] Failed to parse/normalize line {idx}: {line_str}. Error: {e}")
                txt_lines.append(line_str)

        # Write output_json_path
        os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
        try:
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(json_output, f, indent=4, ensure_ascii=False)
            logger.info(f"[UMLSNormalizer] Successfully saved rich UMLS JSON graph to: {output_json_path}")
        except Exception as e:
            logger.error(f"[UMLSNormalizer] Failed to save JSON output: {e}")

        # Write output_txt_path
        os.makedirs(os.path.dirname(os.path.abspath(output_txt_path)), exist_ok=True)
        try:
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(txt_lines))
            logger.info(f"[UMLSNormalizer] Successfully saved clean UMLS text graph to: {output_txt_path}")
        except Exception as e:
            logger.error(f"[UMLSNormalizer] Failed to save TXT output: {e}")
