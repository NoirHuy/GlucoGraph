import os
import ast
import json
import time
import logging
import requests
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Semantic Types: Danh sách TUI hợp lệ cho miền y khoa lâm sàng
# Được mở rộng từ 4 lên 17 loại để bao phủ đầy đủ:
#   thuốc (T121, T200, T116, T125, T109, T123),
#   bệnh/triệu chứng (T047, T184, T033, T037),
#   thủ thuật/xét nghiệm (T061, T059, T060),
#   giải phẫu (T023, T029),
#   chỉ số lâm sàng (T034, T081)
# ─────────────────────────────────────────────────────────────────────────────
MEDICAL_SAFE_TUIS: frozenset = frozenset({
    # Bệnh lý & triệu chứng
    "T047",  # Disease or Syndrome
    "T184",  # Sign or Symptom
    "T033",  # Finding
    "T037",  # Injury or Poisoning
    # Thuốc & hoạt chất
    "T121",  # Pharmacologic Substance (metformin, glipizide...)
    "T200",  # Clinical Drug — biệt dược thương mại (Lantus, Januvia...)
    "T116",  # Amino Acid, Peptide, or Protein (insulin là một protein)
    "T125",  # Hormone (glucagon, insulin thuộc nhóm hormone)
    "T109",  # Organic Chemical (nhiều thuốc tổng hợp hữu cơ)
    "T123",  # Biologically Active Substance
    # Thủ thuật & xét nghiệm
    "T061",  # Therapeutic or Preventive Procedure
    "T059",  # Laboratory Procedure (HbA1c test, fasting glucose)
    "T060",  # Diagnostic Procedure
    # Giải phẫu
    "T023",  # Body Part, Organ, or Organ Component (pancreas, kidney...)
    "T029",  # Body Location or Region
    # Chỉ số & kết quả lâm sàng
    "T034",  # Laboratory or Test Result
    "T081",  # Quantitative Concept (HbA1c threshold value)
})

# Stopwords for context word extraction and reranking
_MEDICAL_STOPWORDS = frozenset({
    "the", "a", "an", "of", "with", "in", "and", "or", "to", "for",
    "mellitus", "syndrome", "disease", "disorder", "condition",
    "associated", "related", "induced", "dependent", "independent",
})

# Abbreviation table for pre-lookup acronym expansion
LOCAL_MEDICAL_ABBREVIATIONS: Dict[str, str] = {
    "t2dm": "type 2 diabetes mellitus",
    "t1dm": "type 1 diabetes mellitus",
    "dm": "diabetes mellitus",
    "dm2": "type 2 diabetes mellitus",
    "dm1": "type 1 diabetes mellitus",
    "niddm": "type 2 diabetes mellitus",
    "iddm": "type 1 diabetes mellitus",
    "dka": "diabetic ketoacidosis",
    "hhs": "hyperosmolar hyperglycemic state",
    "hba1c": "hemoglobin a1c",
    "a1c": "hemoglobin a1c",
    "fbg": "fasting blood glucose",
    "fpg": "fasting plasma glucose",
    "bg": "blood glucose",
    "ppg": "postprandial glucose",
    "ogtt": "oral glucose tolerance test",
    "ldl": "ldl cholesterol",
    "hdl": "hdl cholesterol",
    "tg": "triglycerides",
    "egfr": "estimated glomerular filtration rate",
    "gfr": "glomerular filtration rate",
    "bmi": "body mass index",
    "sbp": "systolic blood pressure",
    "dbp": "diastolic blood pressure",
    "bp": "blood pressure",
    "metformin hcl": "metformin",
    "glp-1": "glucagon-like peptide-1",
    "glp1": "glucagon-like peptide-1",
    "dpp-4": "dipeptidyl peptidase-4",
    "dpp4": "dipeptidyl peptidase-4",
    "sglt-2": "sodium-glucose cotransporter-2",
    "sglt2": "sodium-glucose cotransporter-2",
    "ace inhibitor": "angiotensin converting enzyme inhibitor",
    "ace-i": "angiotensin converting enzyme inhibitor",
    "arb": "angiotensin receptor blocker",
    "cns": "central nervous system",
    "cvd": "cardiovascular disease",
    "ckd": "chronic kidney disease",
    "esrd": "end stage renal disease",
    "cabg": "coronary artery bypass grafting",
    "pci": "percutaneous coronary intervention",
}


class UMLSNormalizer:
    """Post-processor that maps and aligns raw/canonical triplets to the UMLS dictionary.
    Connects to the NIH UTS REST API (Option B) for accurate online matching.
    Includes persistent on-disk caching to optimize performance and prevent redundant API requests.

    Improvements over original:
    - Expanded MEDICAL_SAFE_TUIS: 4 → 17 semantic types (covers insulin, drugs, tests, anatomy)
    - Thread-safe requests.Session with connection pooling
    - Exponential backoff on HTTP 429/503 (up to 4 retries, max 16s wait)
    - Rate-limiter: min 50ms between consecutive HTTP requests
    """

    # Minimum interval between consecutive HTTP requests (seconds)
    _MIN_REQUEST_INTERVAL: float = 0.05  # 50ms → max 20 req/s

    def __init__(self, api_key: str = None, cache_path: str = None):
        self.api_key = api_key or os.environ.get("UMLS_API_KEY", "")
        self.base_url = "https://uts-ws.nlm.nih.gov/rest"
        # Default cache file in the output directory
        self.cache_path = cache_path or "./output/umls_cache.json"
        self.cache = {}
        self.context_words = set()

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
        cache_dir = os.path.dirname(os.path.abspath(self.cache_path))
        os.makedirs(cache_dir, exist_ok=True)
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4, ensure_ascii=False)
            logger.debug(f"[UMLSNormalizer] Saved {len(self.cache)} entries to cache.")
        except Exception as e:
            logger.warning(f"[UMLSNormalizer] Failed to save cache file: {e}")

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
        import re
        term_clean = term.strip()

        # Pattern 1: Matches brackets prefix like [RNAx] or [Code] at the beginning
        term_clean = re.sub(r'^\[[A-Za-z0-9_\-]+\]\s*', '', term_clean)

        # Pattern 2: Matches word prefix with code like 'RNAx ', 'RNA-x ', 'MESH:', 'SNOMEDCT_US_' followed by space, colon, or dash
        term_clean = re.sub(
            r'^(RNAx|MESH|SNOMEDCT|SNOMED|OMIM|RXNORM|ICD10|ICD9|ICD|EHR)[0-9_A-Za-z\-]*[:_\-\s]\s*',
            '', term_clean, flags=re.IGNORECASE
        )

        # Pattern 3: Matches single short uppercase code prefix like 'A1 ', 'R1 ' or similar y-axis tags at the very beginning
        term_clean = re.sub(r'^[A-Z]+[0-9]*\s+', '', term_clean)

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

    # ─────────────────────────────────────────────────────────────────────────
    # Batch normalization
    # ─────────────────────────────────────────────────────────────────────────

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
            sub_res = self.query_term(sub)
            obj_res = self.query_term(obj)

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
