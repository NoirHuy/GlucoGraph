"""
main.py — CLI entry point for the UMLS Knowledge Graph pipeline.

Usage
-----
    # Basic (uses env var UMLS_API_KEY)
    python main.py --cui C0011849 --depth 2

    # Custom output location
    python main.py --cui C0011849 --depth 2 --output ./output/diabetes_kg.json

    # Also emit Cypher import script
    python main.py --cui C0011849 --depth 2 --cypher

    # Clear cache first
    python main.py --cui C0011849 --depth 2 --clear-cache

    # Skip cache entirely
    python main.py --cui C0011849 --depth 2 --no-cache
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import config
from api_client import UMLSApiError, UMLSClient
from extractor import UMLSExtractor
from transformer import KGTransformer
from utils import DiskCache, ensure_output_dir, get_logger, normalise_cui

logger = get_logger("main")


# ──────────────────────────────────────────────
# Cypher generator
# ──────────────────────────────────────────────

def generate_cypher(graph: dict, output_path: Path) -> None:
    """
    Write a Neo4j Cypher script that imports the knowledge graph.
    Uses MERGE so the script is idempotent (safe to re-run).
    """
    lines = [
        "// ============================================================",
        "// UMLS Medical Knowledge Graph — Auto-generated Cypher import",
        "// Run against Neo4j: cypher-shell -f import.cypher",
        "// Or paste into Neo4j Browser",
        "// ============================================================",
        "",
        "// 1. Constraints (run once; comment out if already exist)",
        "CREATE CONSTRAINT cui_unique IF NOT EXISTS",
        "  FOR (n:Concept) REQUIRE n.id IS UNIQUE;",
        "",
        "// 2. Nodes",
    ]

    for node in graph["nodes"]:
        node_type = node["type"]
        synonyms_escaped = json.dumps(node.get("synonyms", []))
        sem_types_escaped = json.dumps(node.get("semantic_types", []))
        definition = node.get("definition", "").replace("'", "\\'")
        name = node["name"].replace("'", "\\'")

        lines.append(
            f"MERGE (n:{node_type}:Concept {{id: '{node['id']}'}}) "
            f"SET n.name = '{name}', "
            f"n.definition = '{definition}', "
            f"n.synonyms = {synonyms_escaped}, "
            f"n.semantic_types = {sem_types_escaped};"
        )

    lines += ["", "// 3. Relationships"]

    for edge in graph["edges"]:
        rel_type = edge["relation"].upper()
        additional = edge.get("additional_label", "")
        add_prop = f", additional_label: '{additional}'" if additional else ""
        lines.append(
            f"MATCH (a:Concept {{id: '{edge['source']}'}}), "
            f"(b:Concept {{id: '{edge['target']}'}}) "
            f"MERGE (a)-[:{rel_type} {{relation_type: '{edge['relation_type']}'{add_prop}}}]->(b);"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Cypher script written to %s  (%d statements)", output_path, len(lines))


# ──────────────────────────────────────────────
# Pipeline orchestration
# ──────────────────────────────────────────────

def run_pipeline(
    cui: str,
    depth: int,
    output_path: Path,
    emit_cypher: bool,
    cache_enabled: bool,
) -> dict:
    """Full extract → transform → export pipeline."""

    # 1. Setup
    cache = DiskCache(enabled=cache_enabled)
    client = UMLSClient(cache=cache)
    extractor = UMLSExtractor(client=client, max_depth=depth)
    transformer = KGTransformer()

    # 2. Extract
    logger.info("═══ EXTRACTION starting (CUI=%s, depth=%d) ═══", cui, depth)
    concepts, relations = extractor.extract(cui)

    # 3. Transform
    logger.info("═══ TRANSFORMATION ═══")
    graph = transformer.transform(concepts, relations)
    stats = transformer.summary(graph)
    logger.info("Stats: %s", json.dumps(stats, indent=2))

    # 4. Export JSON
    ensure_output_dir(output_path.parent)
    output_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Knowledge graph JSON written to %s", output_path)

    # 5. Optional Cypher
    if emit_cypher:
        cypher_path = output_path.with_suffix(".cypher")
        generate_cypher(graph, cypher_path)

    return graph


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="umls_graph",
        description="Extract a UMLS concept sub-graph and export it for Neo4j / GraphRAG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --cui C0011849 --depth 2
  python main.py --cui C0011849 --depth 1 --cypher --output output/diabetes.json
  python main.py --cui C0011849 --depth 2 --no-cache
  python main.py --cui C0011849 --depth 2 --clear-cache
        """,
    )
    parser.add_argument(
        "--cui",
        required=True,
        metavar="CUI",
        help="Seed UMLS CUI to start from (e.g. C0011849 for Diabetes Mellitus)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=config.DEFAULT_DEPTH,
        metavar="N",
        help=f"Traversal depth (default: {config.DEFAULT_DEPTH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=config.OUTPUT_DIR / config.DEFAULT_OUTPUT_FILE,
        metavar="PATH",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--cypher",
        action="store_true",
        help="Also generate a Neo4j Cypher import script alongside the JSON",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable disk cache (force fresh API calls)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear disk cache before running",
    )
    parser.add_argument(
        "--log-level",
        default=config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Apply log level from CLI
    logging.getLogger().setLevel(args.log_level)

    # Validate API key early
    if not config.UMLS_API_KEY:
        logger.error(
            "UMLS_API_KEY environment variable is not set.\n"
            "  export UMLS_API_KEY=your_api_key_here\n"
            "  Get a free key at: https://uts.nlm.nih.gov/uts/signup-login"
        )
        sys.exit(1)

    # Handle cache management
    if args.clear_cache:
        DiskCache().clear()
        logger.info("Cache cleared.")

    cui = normalise_cui(args.cui)
    cache_enabled = not args.no_cache

    try:
        graph = run_pipeline(
            cui=cui,
            depth=args.depth,
            output_path=args.output,
            emit_cypher=args.cypher,
            cache_enabled=cache_enabled,
        )
        stats = KGTransformer.summary(graph)
        print("\n✅ Knowledge graph built successfully!")
        print(f"   Nodes : {stats['total_nodes']}")
        print(f"   Edges : {stats['total_edges']}")
        print(f"   Output: {args.output.resolve()}")
        if args.cypher:
            print(f"   Cypher: {args.output.with_suffix('.cypher').resolve()}")

    except UMLSApiError as exc:
        logger.error("UMLS API error: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()