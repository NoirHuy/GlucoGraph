#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_packer.py — Standalone CLI entry point for quantitative Property Packing.

Loads result_at_each_stage_debated.json, runs regex-based clinical cleaning,
packs quantitative thresholds/adjustments into relationship and node properties,
and generates `canon_kg_debated_packed.json` ready for high-fidelity Neo4j importing.
"""

import sys
import os
import json

# Try loading .env variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import logging
from argparse import ArgumentParser

# Ensure root of edc-main is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from post_processing.property_packer import pack_properties

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PropertyPackerRunner")


def main():
    parser = ArgumentParser(description="Property Packing post-processor for Neo4j importing.")
    parser.add_argument(
        "--input_json_path",
        required=True,
        help="Path to 'result_at_each_stage_debated.json' from completed debate gate phase."
    )
    parser.add_argument(
        "--output_dir",
        default="",
        help="Target output directory (defaults to the same directory as input_json_path)."
    )
    parser.add_argument(
        "--umls_api_key",
        default=None,
        help="Optional UMLS API key to enable online mapping/verification."
    )
    
    args = parser.parse_args()
    
    input_path = args.input_json_path
    if not os.path.exists(input_path):
        logger.error(f"Input JSON file not found at: {input_path}")
        sys.exit(1)
        
    output_dir = args.output_dir
    if not output_dir:
        output_dir = os.path.dirname(input_path)
        if not output_dir:
            output_dir = "."
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load records
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    logger.info(f"Loaded {len(records)} records from {input_path}")
    
    # Calculate pre-packing node count (treating every object in OIE as a node)
    pre_nodes = set()
    pre_triples_count = 0
    for r in records:
        for t in r.get("schema_canonicalizaiton", []):
            if t and len(t) >= 3:
                pre_nodes.add(t[0])
                pre_nodes.add(t[2])
                pre_triples_count += 1
                
    # 2. Run Property Packing
    packed_graph = pack_properties(records, umls_api_key=args.umls_api_key)
    
    # 3. Write Output JSON
    output_json_path = os.path.join(output_dir, "canon_kg_debated_packed.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(packed_graph, f, indent=2, ensure_ascii=False)
    logger.info(f"Packed graph JSON written to: {output_json_path}")
    
    # 4. Print Summary statistics
    nodes_count = len(packed_graph["nodes"])
    rels_count = len(packed_graph["relationships"])
    
    packed_rels_count = sum(
        1 for r in packed_graph["relationships"] if r.get("properties")
    )
    packed_nodes_count = sum(
        1 for n in packed_graph["nodes"] if n.get("properties")
    )
    
    logger.info(
        f"\n"
        f"╔══════════════════════════════════════════════════════════╗\n"
        f"║           QUANTITATIVE PROPERTY PACKING SUMMARY          ║\n"
        f"╠══════════════════════════════════════════════════════════╣\n"
        f"║  Total Triples Pre-Packing: {pre_triples_count:>5}                        ║\n"
        f"║  Total Nodes Pre-Packing:   {len(pre_nodes):>5} (With value nodes)      ║\n"
        f"╠══════════════════════════════════════════════════════════╣\n"
        f"║  Neo4j Concept Nodes:       {nodes_count:>5} (No value nodes) ✅   ║\n"
        f"║  Neo4j Relationships:       {rels_count:>5}                      ║\n"
        f"╠══════════════════════════════════════════════════════════╣\n"
        f"║  Relationships with packed properties: {packed_rels_count:>3}            ║\n"
        f"║  Nodes with packed properties:         {packed_nodes_count:>3}            ║\n"
        f"║  Total Node Reduction:                 {len(pre_nodes) - nodes_count:>3} ({((len(pre_nodes) - nodes_count)/len(pre_nodes)*100 if len(pre_nodes) > 0 else 0):.1f}%) 📉       ║\n"
        f"╚══════════════════════════════════════════════════════════╝"
    )


if __name__ == "__main__":
    main()
