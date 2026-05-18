"""
extractor.py — BFS/DFS graph traversal over UMLS concepts.

Starting from a seed CUI, this module:
  1. Fetches concept metadata, atoms, relations
  2. Filters relations by allowed types
  3. Expands neighbours up to `max_depth` levels
  4. Tracks visited CUIs to prevent cycles
  5. Returns raw intermediate dicts (transformation happens in transformer.py)
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import config
from api_client import UMLSClient
from utils import get_logger, normalise_cui

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Raw data containers  (plain dataclasses → easy to serialise)
# ──────────────────────────────────────────────

@dataclass
class RawConcept:
    cui: str
    name: str
    semantic_types: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    definition: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class RawRelation:
    source_cui: str
    target_cui: str
    target_name: str
    relation_type: str          # UMLS abbreviation, e.g. "RO"
    relation_label: str         # UMLS relation label, e.g. "has_finding_site"
    additional_relation_label: str = ""


# ──────────────────────────────────────────────
# Extractor
# ──────────────────────────────────────────────

class UMLSExtractor:
    """
    Orchestrates BFS expansion of the UMLS graph starting from a seed CUI.

    Parameters
    ----------
    client : UMLSClient
        Authenticated API client.
    max_depth : int
        How many hops to traverse from the seed (default 2).
    allowed_relations : set[str]
        UMLS relation type abbreviations to keep (e.g. {"RO", "RB", "RN"}).
    """

    def __init__(
        self,
        client: UMLSClient,
        max_depth: int = config.DEFAULT_DEPTH,
        allowed_relations: set[str] = config.ALLOWED_RELATION_TYPES,
    ):
        self._client = client
        self._max_depth = max_depth
        self._allowed = allowed_relations

        # Results accumulate here
        self._concepts: dict[str, RawConcept] = {}
        self._relations: list[RawRelation] = []
        self._visited: set[str] = set()

    # ──────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────

    def extract(self, seed_cui: str) -> tuple[dict[str, RawConcept], list[RawRelation]]:
        """
        Run BFS from `seed_cui` up to `max_depth` hops.

        Returns
        -------
        concepts : dict[CUI → RawConcept]
        relations : list[RawRelation]
        """
        seed_cui = normalise_cui(seed_cui)
        logger.info("Starting BFS from %s (depth=%d)", seed_cui, self._max_depth)

        # BFS queue: (cui, depth)
        queue: deque[tuple[str, int]] = deque([(seed_cui, 0)])

        while queue:
            cui, depth = queue.popleft()

            if cui in self._visited:
                continue
            self._visited.add(cui)

            logger.info("Processing CUI=%s  depth=%d  (queue=%d)", cui, depth, len(queue))

            concept = self._fetch_concept(cui)
            if concept is None:
                logger.warning("Skipping CUI %s — concept not found", cui)
                continue
            self._concepts[cui] = concept

            # Only expand neighbours if we haven't hit the depth limit
            if depth < self._max_depth:
                neighbours = self._fetch_relations(cui)
                for rel in neighbours:
                    self._relations.append(rel)
                    if rel.target_cui not in self._visited:
                        queue.append((rel.target_cui, depth + 1))

        logger.info(
            "Extraction complete: %d concepts, %d relations",
            len(self._concepts),
            len(self._relations),
        )
        return self._concepts, self._relations

    # ──────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────

    def _fetch_concept(self, cui: str) -> Optional[RawConcept]:
        """Fetch and assemble a RawConcept for a given CUI."""
        raw = self._client.get_concept(cui)
        if raw is None:
            return None

        name = raw.get("name", "")

        # Semantic types
        sem_types = [st.get("name", "") for st in raw.get("semanticTypes", []) if st.get("name")]

        # Synonyms from atoms
        synonyms = self._fetch_synonyms(cui)

        # Definition — take the first English one if available
        definition = self._fetch_definition(cui)

        return RawConcept(
            cui=cui,
            name=name,
            semantic_types=sem_types,
            synonyms=synonyms,
            definition=definition,
            raw=raw,
        )

    def _fetch_synonyms(self, cui: str) -> list[str]:
        """Collect unique synonym strings from atom records."""
        atoms = self._client.get_atoms(cui)
        seen: set[str] = set()
        syns: list[str] = []
        for atom in atoms:
            term = atom.get("name", "").strip()
            if term and term not in seen:
                seen.add(term)
                syns.append(term)
        return syns

    def _fetch_definition(self, cui: str) -> str:
        """Return the first available definition string."""
        defs = self._client.get_definitions(cui)
        if not defs:
            return ""
        # Prefer English NCI or MSH definitions if available
        preferred_sources = {"NCI", "MSH", "SNOMEDCT_US", "HPO"}
        for d in defs:
            if d.get("rootSource", "") in preferred_sources:
                return d.get("value", "").strip()
        # Fall back to first definition
        return defs[0].get("value", "").strip()

    def _fetch_relations(self, cui: str) -> list[RawRelation]:
        """Fetch, filter, and build RawRelation objects for a CUI."""
        raw_rels = self._client.get_relations(cui)
        results: list[RawRelation] = []

        for r in raw_rels:
            rel_type = r.get("relationLabel", "").upper()   # e.g. "RO"

            # Filter: only keep allowed relation types
            if rel_type not in self._allowed:
                continue

            # Extract target CUI from the relatedId URI
            target_uri: str = r.get("relatedId", "")
            target_cui = self._extract_cui_from_uri(target_uri)
            if not target_cui:
                continue

            target_name = r.get("relatedIdName", "")
            additional_label = r.get("additionalRelationLabel", "")

            results.append(RawRelation(
                source_cui=cui,
                target_cui=target_cui,
                target_name=target_name,
                relation_type=rel_type,
                relation_label=r.get("relationLabel", ""),
                additional_relation_label=additional_label,
            ))

        logger.debug("Kept %d/%d relations for %s", len(results), len(raw_rels), cui)
        return results

    @staticmethod
    def _extract_cui_from_uri(uri: str) -> str:
        """
        UMLS API returns relatedId as a full URI, e.g.:
          https://uts-ws.nlm.nih.gov/rest/content/current/CUI/C0001234
        Extract just the CUI token.
        """
        if not uri:
            return ""
        parts = uri.rstrip("/").split("/")
        for part in reversed(parts):
            if part.startswith("C") and part[1:].isdigit():
                return part
        return ""