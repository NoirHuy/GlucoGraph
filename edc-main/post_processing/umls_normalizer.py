import os
import re
import ast
import json
import time
import logging
import requests
from typing import List, Dict, Any, Tuple

# Import shared constants from single source of truth
from post_processing.constants import (
    MEDICAL_SAFE_TUIS,
    MEDICAL_STOPWORDS as _MEDICAL_STOPWORDS,
    LOCAL_MEDICAL_ABBREVIATIONS,
    CACHE_VERSION,
)

logger = logging.getLogger(__name__)

# LOCAL_MEDICAL_ABBREVIATIONS is now imported from constants.py


class UMLSNormalizer:
    """Post-processor that maps and aligns raw/canonical triplets to the UMLS dictionary.
    Connects to the NIH UTS REST API (Option B) for accurate online matching.
    Includes persistent on-disk caching to optimize performance and prevent redundant API requests.

    Improvements over original:
    - Expanded MEDICAL_SAFE_TUIS: 4 → 17 semantic types (covers insulin, drugs, tests, anatomy)
    - Thread-safe requests.Session with connection pooling
    - Exponential backoff on HTTP 429/503 (up to 4 retries, max 16s wait)
    - Rate-limiter: min 50ms between consecutive HTTP requests
    - Deferred cache saving: save every N queries instead of per-query (reduces I/O)
    - Cache versioning: auto-invalidates stale caches when schema changes
    """

    # Minimum interval between consecutive HTTP requests (seconds)
    _MIN_REQUEST_INTERVAL: float = 0.05  # 50ms → max 20 req/s

    # Deferred save interval — cache is saved to disk every N new queries
    _SAVE_INTERVAL: int = 10

    def __init__(self, api_key: str = None, cache_path: str = None):
        self.api_key = api_key or os.environ.get("UMLS_API_KEY", "")
        self.base_url = "https://uts-ws.nlm.nih.gov/rest"
        # Default cache file in the output directory
        self.cache_path = cache_path or "./output/umls_cache.json"
        self.cache = {}
        self.context_words = set()
        # Counter for deferred cache saving
        self._queries_since_save: int = 0

        # HTTP session for connection pooling (reuse TCP connections)
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        # Track timestamp of last request for rate-limiting
        self._last_request_time: float = 0.0

        if not self.api_key:
            logger.warning(
                "[UMLSNormalizer] No UMLS API Key provided (via argument or UMLS_API_KEY env var). "
                "UMLS mapping will run in dry-run mode (no API calls, terms will map to themselves)."
            )

        self.load_cache()

    def set_context_words(self, words: set):
        """Sets the dynamic document domain context keywords for context-aware reranking."""
        self.context_words = {w.lower() for w in words if w}
        logger.info(f"[UMLSNormalizer] Dynamically loaded {len(self.context_words)} context keywords for domain-aware reranking.")

    # ─────────────────────────────────────────────────────────────────────────
    # Cache management
    # ─────────────────────────────────────────────────────────────────────────

    def load_cache(self):
        """Loads persistent cache of UMLS term mappings from disk.
        Automatically invalidates caches with a different CACHE_VERSION."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                # Cache versioning: if the cache has a __version__ key that
                # differs from the current CACHE_VERSION, invalidate it.
                cached_version = raw.pop("__version__", None) if isinstance(raw, dict) else None
                if cached_version is not None and cached_version != CACHE_VERSION:
                    logger.warning(
                        f"[UMLSNormalizer] Cache version mismatch ({cached_version} != {CACHE_VERSION}). "
                        f"Invalidating stale cache and starting fresh."
                    )
                    self.cache = {}
                    return

                self.cache = raw if isinstance(raw, dict) else {}
                logger.info(f"[UMLSNormalizer] Loaded {len(self.cache)} entries from cache: {self.cache_path}")
            except Exception as e:
                logger.warning(f"[UMLSNormalizer] Failed to load cache file: {e}. Starting fresh.")
                self.cache = {}

    def save_cache(self, force: bool = False):
        """Saves persistent cache of UMLS term mappings to disk.
        Uses deferred saving: only writes every _SAVE_INTERVAL queries unless force=True."""
        if not force:
            self._queries_since_save += 1
            if self._queries_since_save < self._SAVE_INTERVAL:
                return  # Skip — will save later or on flush

        self._queries_since_save = 0
        cache_dir = os.path.dirname(os.path.abspath(self.cache_path))
        os.makedirs(cache_dir, exist_ok=True)
        try:
            # Stamp cache version for future invalidation
            out = {"__version__": CACHE_VERSION, **self.cache}
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=4, ensure_ascii=False)
            logger.debug(f"[UMLSNormalizer] Saved {len(self.cache)} entries to cache.")
        except Exception as e:
            logger.warning(f"[UMLSNormalizer] Failed to save cache file: {e}")

    def flush_cache(self):
        """Force-saves the cache to disk. Call this at the end of a batch run."""
        self.save_cache(force=True)

    # ─────────────────────────────────────────────────────────────────────────
    # HTTP helper with rate-limiting and exponential backoff
    # ─────────────────────────────────────────────────────────────────────────

    def _safe_get(self, url: str, params: dict, timeout: int = 12) -> requests.Response:
        """Perform a GET request with:
        - Rate-limiting: enforces minimum interval between requests.
        - Exponential backoff: retries on HTTP 429 / 503 up to 4 times.
        Raises requests.HTTPError on non-retryable errors.
        """
        max_retries = 4
        for attempt in range(max_retries):
            # Rate-limiting: ensure minimum gap between requests
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._MIN_REQUEST_INTERVAL:
                time.sleep(self._MIN_REQUEST_INTERVAL - elapsed)

            self._last_request_time = time.monotonic()
            try:
                resp = self._session.get(url, params=params, timeout=timeout)
            except requests.RequestException as exc:
                wait = (2 ** attempt) * 0.5
                logger.warning(
                    f"[UMLSNormalizer] Network error on attempt {attempt+1}/{max_retries}: {exc}. "
                    f"Retrying in {wait:.1f}s..."
                )
                time.sleep(wait)
                continue

            if resp.status_code in (429, 503):
                wait = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s, 4s
                logger.warning(
                    f"[UMLSNormalizer] HTTP {resp.status_code} on attempt {attempt+1}/{max_retries}. "
                    f"Retrying in {wait:.1f}s..."
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp

        raise requests.HTTPError(f"[UMLSNormalizer] Failed after {max_retries} retries: {url}")

    # ─────────────────────────────────────────────────────────────────────────
    # Text preprocessing
    # ─────────────────────────────────────────────────────────────────────────

    def _strip_ontology_noise(self, term: str) -> str:
        """Removes common ontology noise prefixes (e.g. 'RNAx ', 'MESH:', '[RNAx] ') from entities."""
        term_clean = term.strip()

        # Pattern 1: Matches brackets prefix like [RNAx] or [Code] at the beginning
        term_clean = re.sub(r'^\[[A-Za-z0-9_\-]+\]\s*', '', term_clean)

        # Pattern 2: Matches word prefix with code like 'RNAx ', 'RNA-x ', 'MESH:', 'SNOMEDCT_US_' followed by space, colon, or dash
        term_clean = re.sub(
            r'^(RNAx|MESH|SNOMEDCT|SNOMED|OMIM|RXNORM|ICD10|ICD9|ICD|EHR)[0-9_A-Za-z\-]*[:_\-\s]\s*',
            '', term_clean, flags=re.IGNORECASE
        )

        # Pattern 3: Matches ONLY known ontology-code prefixes (1-2 uppercase letters + digits)
        # that are followed by a space and then the actual term.
        # Restricted to max 4 characters to avoid stripping valid clinical terms
        # like 'HbA1c', 'LDL Cholesterol', 'BMI Category'.
        term_clean = re.sub(r'^[A-Z]{1,2}[0-9]{1,3}\s+', '', term_clean)

        return term_clean.strip()

    def _expand_abbreviations(self, term: str) -> str:
        """Expands common clinical abbreviations to their full canonical forms."""
        clean = term.strip().lower()
        if clean in LOCAL_MEDICAL_ABBREVIATIONS:
            return LOCAL_MEDICAL_ABBREVIATIONS[clean]
        tokens = clean.split()
        expanded = [LOCAL_MEDICAL_ABBREVIATIONS.get(t, t) for t in tokens]
        return " ".join(expanded)

    # ─────────────────────────────────────────────────────────────────────────
    # Core query
    # ─────────────────────────────────────────────────────────────────────────

    def query_term(self, term: str, node_labels: List[str] = None) -> Dict[str, Any]:
        """Queries NLM UTS REST API to search for CUI and semantic types for a term.
        Uses cached data if available.
        """
        _empty_result = {
            "cui": "NONE",
            "canonical": "",
            "semantic_type": "Unknown",
            "score": 0.0,
            "icd10_code": "NONE",
            "rxnorm_id": "NONE",
            "definition": ""
        }

        # Clean term from any ontology prefix noise first
        term_stripped = self._strip_ontology_noise(term)
        term_clean = term_stripped.strip()

        if not term_clean:
            return {**_empty_result}

        # Dynamic acronym expansion (e.g. CKD -> chronic kidney disease)
        term_clean = self._expand_abbreviations(term_clean)

        term_key = term_clean.lower()
        if term_key in self.cache:
            cached_val = self.cache[term_key]
            # Migration check: must contain the new clinical keys
            if isinstance(cached_val, dict) and "definition" in cached_val and "icd10_code" in cached_val and "rxnorm_id" in cached_val:
                return cached_val


        # Dry-run if no API key is set
        if not self.api_key:
            res = {**_empty_result, "canonical": term_clean}
            self.cache[term_key] = res
            return res

        try:
            # ── Stage 1: Multi-strategy Search ───────────────────────────────
            search_types = ["exact", "normalizedString", "words"]
            results = []

            for s_type in search_types:
                search_url = f"{self.base_url}/search/current"
                search_params = {
                    "string": term_clean,
                    "apiKey": self.api_key,
                    "searchType": s_type,
                    "pageSize": 10,
                    "sabs": "RXNORM,SNOMEDCT_US,MSH",
                }

                logger.debug(f"[UMLSNormalizer] Querying UTS Search ({s_type}) for: '{term_clean}'")
                response = self._safe_get(search_url, search_params)
                search_data = response.json()

                cur_results = search_data.get("result", {}).get("results", [])
                cur_results = [r for r in cur_results if r.get("ui") != "NONE"]
                if cur_results:
                    logger.debug(
                        f"[UMLSNormalizer] Found {len(cur_results)} CUI candidate(s) "
                        f"using searchType={s_type} for '{term_clean}'"
                    )
                    results = cur_results
                    break

            if not results:
                res = {**_empty_result, "canonical": term_clean}
                self.cache[term_key] = res
                self.save_cache()
                return res

            # ── Stage 2: Smart Reranking ──────────────────────────────────────
            # Semantic TUI group mapping for node labels
            LABEL_TO_TUI_GROUPS = {
                "Disease": {"T047", "T184", "T033", "T037"},
                "Symptom": {"T047", "T184", "T033", "T037"},
                "Drug": {"T121", "T200", "T116", "T125", "T109", "T123"},
                "Anatomical Site": {"T023", "T029"},
                "Clinical Metric": {"T034", "T081", "T059", "T060", "T061"},
                "Treatment Procedure": {"T061", "T060", "T059", "T034", "T081"}
            }

            allowed_tuis = set()
            has_specific_medical_label = False
            if node_labels:
                for label in node_labels:
                    if label in LABEL_TO_TUI_GROUPS:
                        allowed_tuis.update(LABEL_TO_TUI_GROUPS[label])
                        has_specific_medical_label = True

            ranked_results = []
            for idx, r in enumerate(results):
                ui = r.get("ui", "NONE")
                name = r.get("name", "")
                if not name or ui == "NONE":
                    continue

                base_score = 0.1 - (idx * 0.01)
                name_lower = name.lower()
                term_lower = term_clean.lower()

                # Lexical matching score
                if name_lower == term_lower:
                    match_score = 10.0
                elif name_lower.startswith(term_lower + " ") or name_lower.endswith(" " + term_lower):
                    match_score = 5.0
                elif term_lower in name_lower:
                    match_score = 2.0
                else:
                    match_score = 0.0

                # Word overlap score
                term_words = set(term_lower.split())
                name_words = set(name_lower.split())
                overlap = len(term_words.intersection(name_words))
                overlap_ratio = overlap / len(term_words) if term_words else 0.0
                match_score += overlap_ratio * 3.0

                # Penalties for badly-formatted LOINC-style strings
                if "^" in name or name.count(":") >= 2:
                    match_score -= 8.0

                # Penalty: name far longer than query term
                if len(name_words) > len(term_words) * 2 and len(term_words) <= 3:
                    match_score -= 4.0

                # ── Context-Aware Reranking ────────────────────────
                # Boost candidate if it has overlap with dynamic document context words
                if hasattr(self, "context_words") and self.context_words:
                    name_words_clean = {w for w in name_lower.split() if w not in _MEDICAL_STOPWORDS}
                    context_overlap = len(name_words_clean.intersection(self.context_words))
                    if context_overlap > 0:
                        match_score += min(4.0, context_overlap * 1.5)

                # Strict Word Difference Penalty
                if len(name_words) > len(term_words):
                    match_score -= 1.5 * (len(name_words) - len(term_words))

                total_score = base_score + match_score
                ranked_results.append((total_score, r))

            ranked_results.sort(key=lambda x: x[0], reverse=True)

            # ── Stage 3: Semantic Type Safety Check ───────────────────────────
            best_cui = "NONE"
            best_pref_name = term_clean
            best_semantic_type = "Unknown"
            best_score_val = 0.0

            for score, match in ranked_results[:5]:  # Expanded inspect window to top 5
                cui_cand = match.get("ui", "NONE")
                pref_name_cand = match.get("name", term_clean)

                if score < 3.0:  # Prevent weak, low-confidence forced matches (keep as NONE)
                    continue

                detail_url = f"{self.base_url}/content/current/CUI/{cui_cand}"
                detail_params = {"apiKey": self.api_key}

                logger.debug(f"[UMLSNormalizer] Fetching CUI details for candidate: {cui_cand} ({pref_name_cand})")
                detail_response = self._safe_get(detail_url, detail_params)

                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    sem_types = detail_data.get("result", {}).get("semanticTypes", [])
                    tuis = []
                    sem_type_list = []

                    if sem_types:
                        for st in sem_types:
                            st_name = st.get("name", "")
                            st_uri = st.get("uri", "")
                            st_tui = st_uri.split("/")[-1] if st_uri else ""
                            if st_tui:
                                tuis.append(st_tui)
                                sem_type_list.append(f"{st_name} ({st_tui})")
                            else:
                                sem_type_list.append(st_name)

                    # Verify Semantic Type Safety against expanded MEDICAL_SAFE_TUIS
                    if not any(t in MEDICAL_SAFE_TUIS for t in tuis):
                        logger.info(
                            f"[UMLSNormalizer] Rejected candidate CUI {cui_cand} '{pref_name_cand}' "
                            f"due to unsafe Semantic Types: {tuis}"
                        )
                        continue

                    # Dynamic Label-Based TUI Alignment Check
                    if has_specific_medical_label and allowed_tuis:
                        if not any(t in allowed_tuis for t in tuis):
                            logger.info(
                                f"[UMLSNormalizer] Rejected candidate CUI {cui_cand} '{pref_name_cand}' "
                                f"due to mismatch between TUIs {tuis} and allowed TUIs {allowed_tuis} for labels {node_labels}"
                            )
                            continue

                    best_cui = cui_cand
                    best_pref_name = pref_name_cand
                    best_semantic_type = ", ".join(sem_type_list) if sem_type_list else "Unknown"
                    best_score_val = float(score)
                    break

            if best_cui == "NONE":
                res = {**_empty_result, "canonical": term_clean}
                self.cache[term_key] = res
                self.save_cache()
                return res

            # ── Stage 4: Gather extended properties ───────────────────────────
            cui = best_cui

            # 4a. Definitions
            # Strategy: request English-only vocabs first (NCI, MSH, CHV, SNOMEDCT_US).
            # We strictly avoid non-English definitions.
            definition = ""
            def_url = f"{self.base_url}/content/current/CUI/{cui}/definitions"
            logger.debug(f"[UMLSNormalizer] Fetching English definitions for: {cui}")
            try:
                # Strictly query English-only sources via sabs filter
                def_response = self._safe_get(
                    def_url,
                    {"apiKey": self.api_key, "sabs": "NCI,MSH,CHV,MEDLINEPLUS,SNOMEDCT_US,HPO"},
                    timeout=10
                )
                eng_defs = []
                if def_response.status_code == 200:
                    def_data = def_response.json()
                    eng_defs = def_data.get("result", [])

                if eng_defs:
                    nci_def = msh_def = chv_def = any_eng_def = None
                    for d in eng_defs:
                        vocab = d.get("sourceVocab", "").upper()
                        val = d.get("value", "").strip()
                        if not val:
                            continue
                        if not any_eng_def:
                            any_eng_def = val
                        if vocab == "NCI" and not nci_def:
                            nci_def = val
                        elif vocab == "MSH" and not msh_def:
                            msh_def = val
                        elif vocab == "CHV" and not chv_def:
                            chv_def = val
                    definition = nci_def or msh_def or chv_def or any_eng_def or ""
            except Exception as e:
                logger.debug(f"[UMLSNormalizer] Could not fetch definition for {cui}: {e}")


            # 4b. ICD-10 Code
            icd10_code = "NONE"
            atoms_url = f"{self.base_url}/content/current/CUI/{cui}/atoms"
            logger.debug(f"[UMLSNormalizer] Fetching ICD10CM atoms for: {cui}")
            try:
                icd_response = self._safe_get(atoms_url, {"apiKey": self.api_key, "sabs": "ICD10CM"}, timeout=10)
                if icd_response.status_code == 200:
                    icd_data = icd_response.json()
                    results_atoms = icd_data.get("result", [])
                    if results_atoms:
                        code_val = results_atoms[0].get("code", "")
                        if "/" in code_val:
                            code_val = code_val.split("/")[-1]
                        if code_val:
                            icd10_code = code_val
            except Exception as e:
                logger.debug(f"[UMLSNormalizer] Could not fetch ICD-10 for {cui}: {e}")

            # 4c. RxNorm ID
            rxnorm_id = "NONE"
            logger.debug(f"[UMLSNormalizer] Fetching RXNORM atoms for: {cui}")
            try:
                rx_response = self._safe_get(atoms_url, {"apiKey": self.api_key, "sabs": "RXNORM"}, timeout=10)
                if rx_response.status_code == 200:
                    rx_data = rx_response.json()
                    results_atoms = rx_data.get("result", [])
                    if results_atoms:
                        code_val = results_atoms[0].get("code", "")
                        if "/" in code_val:
                            code_val = code_val.split("/")[-1]
                        if code_val:
                            rxnorm_id = code_val
            except Exception as e:
                logger.debug(f"[UMLSNormalizer] Could not fetch RxNorm for {cui}: {e}")

            res = {
                "cui": cui,
                "canonical": best_pref_name,
                "semantic_type": best_semantic_type,
                "score": best_score_val,
                "icd10_code": icd10_code,
                "rxnorm_id": rxnorm_id,
                "definition": definition,
            }

            # Save to persistent cache
            self.cache[term_key] = res
            self.save_cache()
            return res

        except Exception as e:
            logger.warning(f"[UMLSNormalizer] Error querying UMLS API for '{term_clean}': {e}. Falling back to default.")
            # Save failure to cache to avoid re-querying same bad term
            res = {**_empty_result, "canonical": term_clean}
            self.cache[term_key] = res
            self.save_cache()
            return res

    def _fallback_to_raw(self, term_res: dict, raw_term: str) -> dict:
        """Helper to revert a mapped node back to its raw original term when an ontology check fails."""
        return {
            "cui": "NONE",
            "canonical": raw_term,
            "semantic_type": "Unknown",
            "score": 0.0,
            "icd10_code": "NONE",
            "rxnorm_id": "NONE",
            "definition": f"Raw uncanonicalized concept: {raw_term} (Fallback due to ontology mismatch)"
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Batch normalization
    # ─────────────────────────────────────────────────────────────────────────

    def normalize_triplets(self, triplets: List[List[str]]) -> Tuple[List[Dict[str, Any]], List[List[str]]]:
        """Maps a list of raw triplets to UMLS.

        Uses batch pre-collection: extracts all unique terms first, resolves them
        in a single pass (leveraging cache), then assembles the output.
        Flushes the cache once at the end instead of per-query.

        Returns:
            - A list of detailed dictionary mappings (with CUIs and semantic types).
            - A list of clean [UMLS_Preferred_Subject, relation, UMLS_Preferred_Object] lists.
        """
        # ── Batch pre-collection: gather all unique terms ─────────────────────
        unique_terms = set()
        for triplet in triplets:
            if len(triplet) == 3:
                unique_terms.add(triplet[0])
                unique_terms.add(triplet[2])

        # Pre-resolve all unique terms (cache will absorb duplicates)
        term_results: Dict[str, Dict[str, Any]] = {}
        for term in unique_terms:
            term_results[term] = self.query_term(term)

        # Flush cache once after batch resolution
        self.flush_cache()

        # ── Assemble output ───────────────────────────────────────────────────
        mapped_triplets = []
        plain_triplets = []

        for triplet in triplets:
            if len(triplet) != 3:
                # If malformed, preserve as-is
                plain_triplets.append(triplet)
                mapped_triplets.append({
                    "subject": {"original": str(triplet), "canonical": str(triplet), "cui": "NONE",
                                "semantic_type": "Unknown", "score": 0.0, "icd10_code": "NONE",
                                "rxnorm_id": "NONE", "definition": ""},
                    "relation": "Unknown",
                    "object": {"original": "", "canonical": "", "cui": "NONE",
                               "semantic_type": "Unknown", "score": 0.0, "icd10_code": "NONE",
                               "rxnorm_id": "NONE", "definition": ""}
                })
                continue

            sub, rel, obj = triplet
            sub_res = term_results[sub].copy()
            obj_res = term_results[obj].copy()

            # Ontology check to catch semantic errors during mapping
            rel_upper = rel.upper().strip()
            sub_tuis = re.findall(r'T\d{3}', sub_res.get("semantic_type", ""))
            obj_tuis = re.findall(r'T\d{3}', obj_res.get("semantic_type", ""))

            if rel_upper in {"TREATED_BY", "CONTRAINDICATED_WITH"}:
                # 1. A laboratory or diagnostic procedure (T059, T060) cannot be treated or contraindicated
                if any(tui in {"T059", "T060"} for tui in sub_tuis):
                    logger.warning(
                        f"[UMLSNormalizer] Ontology violation detected: Subject '{sub}' resolved to procedure "
                        f"'{sub_res['canonical']}' ({sub_res['semantic_type']}) but has relation '{rel}'. Falling back to raw term."
                    )
                    sub_res = self._fallback_to_raw(sub_res, sub)

                # 2. A drug cannot be treated by something (subject of TREATED_BY is usually a disease or symptom)
                if rel_upper == "TREATED_BY" and any(tui in {"T121", "T200", "T116", "T125", "T109", "T123"} for tui in sub_tuis):
                    logger.warning(
                        f"[UMLSNormalizer] Ontology violation detected: Subject '{sub}' resolved to drug "
                        f"'{sub_res['canonical']}' ({sub_res['semantic_type']}) but has relation '{rel}'. Falling back to raw term."
                    )
                    sub_res = self._fallback_to_raw(sub_res, sub)

            mapped_triplets.append({
                "subject": {
                    "original": sub,
                    "canonical": sub_res["canonical"],
                    "cui": sub_res["cui"],
                    "semantic_type": sub_res["semantic_type"],
                    "score": sub_res["score"],
                    "icd10_code": sub_res.get("icd10_code", "NONE"),
                    "rxnorm_id": sub_res.get("rxnorm_id", "NONE"),
                    "definition": sub_res.get("definition", "")
                },
                "relation": rel,
                "object": {
                    "original": obj,
                    "canonical": obj_res["canonical"],
                    "cui": obj_res["cui"],
                    "semantic_type": obj_res["semantic_type"],
                    "score": obj_res["score"],
                    "icd10_code": obj_res.get("icd10_code", "NONE"),
                    "rxnorm_id": obj_res.get("rxnorm_id", "NONE"),
                    "definition": obj_res.get("definition", "")
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
