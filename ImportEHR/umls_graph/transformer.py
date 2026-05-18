"""
transformer.py — Converts raw UMLS data into Knowledge Graph schema.

Input  : dict[CUI → RawConcept], list[RawRelation]
Output : {"nodes": [...], "edges": [...]}  (clean, Neo4j-importable JSON)
"""

from dataclasses import asdict, dataclass, field
from typing import Any

import config
from extractor import RawConcept, RawRelation
from utils import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# KG schema dataclasses
# ──────────────────────────────────────────────

@dataclass
class KGNode:
    id: str                         # CUI
    name: str
    type: str                       # Simplified semantic type, e.g. "Disease"
    semantic_types: list[str]       # Original UMLS semantic type strings
    synonyms: list[str]
    definition: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "semantic_types": self.semantic_types,
            "synonyms": self.synonyms,
            "definition": self.definition,
        }


@dataclass
class KGEdge:
    source: str                     # source CUI
    target: str                     # target CUI
    relation: str                   # human-readable label
    relation_type: str              # original UMLS abbreviation (for traceability)
    additional_label: str = ""      # UMLS additionalRelationLabel (finer detail)

    def to_dict(self) -> dict:
        d = {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "relation_type": self.relation_type,
        }
        if self.additional_label:
            d["additional_label"] = self.additional_label
        return d


# ──────────────────────────────────────────────
# Transformer
# ──────────────────────────────────────────────

class KGTransformer:
    """
    Transforms extracted UMLS data into a clean KG payload.

    Key responsibilities
    --------------------
    - Map UMLS semantic types → simplified node types
    - Map UMLS relation abbreviations → readable edge labels
    - Deduplicate nodes and edges
    - Ensure referential integrity (only keep edges whose endpoints exist as nodes)
    """

    def __init__(
        self,
        sem_type_map: dict[str, str] = config.SEMANTIC_TYPE_MAP,
        relation_label_map: dict[str, str] = config.RELATION_LABEL_MAP,
    ):
        self._sem_type_map = sem_type_map
        self._rel_label_map = relation_label_map

    # ──────────────────────────────────────────
    # Public
    # ──────────────────────────────────────────

    def transform(
        self,
        concepts: dict[str, RawConcept],
        relations: list[RawRelation],
    ) -> dict[str, Any]:
        """
        Returns
        -------
        {
            "nodes": [KGNode.to_dict(), ...],
            "edges": [KGEdge.to_dict(), ...]
        }
        """
        nodes = self._build_nodes(concepts)
        edges = self._build_edges(relations, known_cuis=set(concepts.keys()))

        logger.info(
            "Transformation complete: %d nodes, %d edges",
            len(nodes),
            len(edges),
        )
        return {
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
        }

    # ──────────────────────────────────────────
    # Node building
    # ──────────────────────────────────────────

    def _build_nodes(self, concepts: dict[str, RawConcept]) -> list[KGNode]:
        nodes: list[KGNode] = []
        for cui, concept in concepts.items():
            node_type = self._resolve_node_type(concept.semantic_types)
            # Deduplicate synonyms and exclude the canonical name from the list
            unique_synonyms = list(dict.fromkeys(
                s for s in concept.synonyms if s.lower() != concept.name.lower()
            ))
            nodes.append(KGNode(
                id=cui,
                name=concept.name,
                type=node_type,
                semantic_types=concept.semantic_types,
                synonyms=unique_synonyms,
                definition=concept.definition,
            ))
        return nodes

    def _resolve_node_type(self, semantic_types: list[str]) -> str:
        """
        Map the first matching semantic type to a simplified label.
        Falls back to "Concept" if nothing matches.
        """
        for st in semantic_types:
            mapped = self._sem_type_map.get(st)
            if mapped:
                return mapped
        return "Concept"

    # ──────────────────────────────────────────
    # Edge building
    # ──────────────────────────────────────────

    def _build_edges(
        self,
        relations: list[RawRelation],
        known_cuis: set[str],
    ) -> list[KGEdge]:
        """
        Build deduplicated edges, keeping only those whose source AND target
        are both present in the extracted concept set.
        """
        seen: set[tuple[str, str, str]] = set()
        edges: list[KGEdge] = []

        for rel in relations:
            # Referential integrity: both endpoints must be known nodes
            if rel.source_cui not in known_cuis or rel.target_cui not in known_cuis:
                continue

            # Skip self-loops
            if rel.source_cui == rel.target_cui:
                continue

            readable = self._rel_label_map.get(rel.relation_type, rel.relation_type.lower())

            # Deduplicate by (source, target, relation)
            key = (rel.source_cui, rel.target_cui, readable)
            if key in seen:
                continue
            seen.add(key)

            edges.append(KGEdge(
                source=rel.source_cui,
                target=rel.target_cui,
                relation=readable,
                relation_type=rel.relation_type,
                additional_label=rel.additional_relation_label,
            ))

        return edges

    # ──────────────────────────────────────────
    # Convenience: stats summary
    # ──────────────────────────────────────────

    @staticmethod
    def summary(graph: dict[str, Any]) -> dict[str, Any]:
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        type_counts: dict[str, int] = {}
        for n in nodes:
            t = n.get("type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        rel_counts: dict[str, int] = {}
        for e in edges:
            r = e.get("relation", "unknown")
            rel_counts[r] = rel_counts.get(r, 0) + 1

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_type_distribution": type_counts,
            "relation_distribution": rel_counts,
        }