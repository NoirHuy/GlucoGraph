"""
config.py — Central configuration for the UMLS Knowledge Graph pipeline.
All tuneable parameters live here; never hardcode values in other modules.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────
UMLS_API_KEY: str = os.environ.get("UMLS_API_KEY", "")
UMLS_BASE_URL: str = "https://uts-ws.nlm.nih.gov/rest"
UMLS_VERSION: str = "current"          # UMLS release; "current" = latest

# HTTP behaviour
REQUEST_TIMEOUT: int = 30              # seconds per request
MAX_RETRIES: int = 5
RETRY_BACKOFF_FACTOR: float = 1.5      # exponential back-off multiplier
RATE_LIMIT_SLEEP: float = 0.3          # polite pause between requests (s)

# ──────────────────────────────────────────────
# GRAPH EXTRACTION
# ──────────────────────────────────────────────
DEFAULT_DEPTH: int = 2
MAX_ATOMS_PER_CUI: int = 50            # cap synonym atoms to avoid huge payloads
MAX_RELATIONS_PER_CUI: int = 5000      # cap relations per CUI

# Relation types we keep (UMLS relation abbreviations)
ALLOWED_RELATION_TYPES: set[str] = {"RO", "RB", "RN", "SY"}

# Human-readable labels for each relation type
RELATION_LABEL_MAP: dict[str, str] = {
    "RO": "associated_with",
    "RB": "broader_than",
    "RN": "narrower_than",
    "SY": "synonym_of",
}

# Semantic group → simplified node type
SEMANTIC_TYPE_MAP: dict[str, str] = {
    "Disease or Syndrome": "Disease",
    "Neoplastic Process": "Disease",
    "Mental or Behavioral Dysfunction": "Disease",
    "Pathologic Function": "Disease",
    "Sign or Symptom": "Symptom",
    "Finding": "Finding",
    "Pharmacologic Substance": "Drug",
    "Clinical Drug": "Drug",
    "Antibiotic": "Drug",
    "Hormone": "Drug",
    "Organic Chemical": "Chemical",
    "Amino Acid, Peptide, or Protein": "Protein",
    "Gene or Genome": "Gene",
    "Enzyme": "Enzyme",
    "Body Part, Organ, or Organ Component": "Anatomy",
    "Cell": "Cell",
    "Tissue": "Tissue",
    "Laboratory Procedure": "Procedure",
    "Diagnostic Procedure": "Procedure",
    "Therapeutic or Preventive Procedure": "Procedure",
    "Health Care Activity": "Procedure",
    "Clinical Attribute": "Attribute",
    "Quantitative Concept": "Attribute",
    "Functional Concept": "Concept",
    "Intellectual Product": "Concept",
    "Research Activity": "Concept",
}

# ──────────────────────────────────────────────
# CACHING
# ──────────────────────────────────────────────
CACHE_DIR: Path = Path(".umls_cache")
CACHE_ENABLED: bool = True

# ──────────────────────────────────────────────
# OUTPUT
# ──────────────────────────────────────────────
OUTPUT_DIR: Path = Path("output")
DEFAULT_OUTPUT_FILE: str = "knowledge_graph.json"
CYPHER_OUTPUT_FILE: str = "import.cypher"

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"