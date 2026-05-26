#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_debate.py — Standalone CLI entry point for Multi-Agent Debate verification.

This script executes Phase 3.5 independently after EDC triple extraction is 100% complete.
It loads `result_at_each_stage.json` (or a custom triples JSON), reads the schema CSV,
runs the multi-agent debate concurrently, filters out rejected triples, and generates:
  - `canon_kg_debated.txt` (filtered triples list)
  - `result_at_each_stage_debated.json` (filtered detailed stage log)
  - `debate_log_all.json` (complete execution trace for audits)
"""

import sys
import os
import csv
import json
import logging
import asyncio
from argparse import ArgumentParser
from typing import Dict, List, Tuple

# Ensure the root of edc-main is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from debate_gate.agent_debate_gate import AgentLLMDebateGate, filter_triples_by_debate, DebateResult

# Setup pretty logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("DebateGateRunner")


def load_relation_schema(schema_path: str) -> Dict[str, str]:
    """Load the relation schema CSV dynamically."""
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found at: {schema_path}")
        sys.exit(1)
        
    schema = {}
    with open(schema_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            relation = row[0]
            definition = ",".join(row[1:])
            schema[relation] = definition
            
    logger.info(f"Loaded {len(schema)} relation definitions from {schema_path}")
    return schema


async def run_standalone_debate(args):
    # 1. Validate inputs
    input_json_path = args.input_json_path
    if not os.path.exists(input_json_path):
        logger.error(f"Input JSON file not found at: {input_json_path}")
        sys.exit(1)
        
    # Determine output directory
    output_dir = args.output_dir
    if not output_dir:
        parent_dir = os.path.dirname(input_json_path)
        if not parent_dir:
            parent_dir = "."
        output_dir = os.path.join(parent_dir, "debated_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Load schema CSV
    schema = load_relation_schema(args.schema_path)
    
    # 3. Load input JSON
    with open(input_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    logger.info(f"Loaded {len(records)} records from {input_json_path}")
    
    # 4. Initialize Debate Gate
    gate = AgentLLMDebateGate(
        model_name=args.debate_gate_model,
        schema=schema,
        fcs_threshold=args.debate_gate_fcs_threshold,
        veto_confidence_threshold=args.debate_gate_veto_threshold,
        max_rounds=args.debate_gate_max_rounds,
        max_concurrent=args.debate_gate_max_concurrent,
        clinical_specialist_model=args.clinical_specialist_model,
        ontology_inspector_model=args.ontology_inspector_model,
        medical_skeptic_model=args.medical_skeptic_model,
    )
    
    # 5. Process records
    debated_records = []
    all_debate_results: List[DebateResult] = []
    
    total_triples_pre = 0
    total_triples_post = 0
    
    logger.info("Starting Multi-Agent Debate Verification...")
    
    for idx, record in enumerate(records):
        input_text = record.get("input_text", "")
        # schema_canonicalizaiton holds canon triplets
        triplets = record.get("schema_canonicalizaiton", [])
        
        # Filter out None values if any
        non_null_triplets = [t for t in triplets if t is not None]
        total_triples_pre += len(non_null_triplets)
        
        if not non_null_triplets:
            record["schema_canonicalizaiton"] = []
            debated_records.append(record)
            continue
            
        logger.info(f"\n--- Processing Record {idx+1}/{len(records)} (contains {len(non_null_triplets)} triples) ---")
        
        # Convert to tuple list for debate gate
        triple_tuples = [tuple(t) for t in non_null_triplets]
        source_texts = [input_text] * len(triple_tuples)
        
        # Run debate batch for this record
        debate_results = await gate.verify_batch(triple_tuples, source_texts)
        all_debate_results.extend(debate_results)
        
        # Filter accepted triples
        accepted_triples = filter_triples_by_debate(non_null_triplets, debate_results)
        total_triples_post += len(accepted_triples)
        
        # Update record with filtered results
        record["schema_canonicalizaiton"] = accepted_triples
        debated_records.append(record)
        
    # 6. Write final outputs
    # Write debated result_at_each_stage.json
    output_json_path = os.path.join(output_dir, "result_at_each_stage_debated.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(debated_records, f, indent=4, ensure_ascii=False)
    logger.info(f"Updated stage log written to: {output_json_path}")
    
    # Write debated canon_kg.txt
    output_txt_path = os.path.join(output_dir, "canon_kg_debated.txt")
    with open(output_txt_path, "w", encoding="utf-8") as f:
        for idx, record in enumerate(debated_records):
            triplets = record.get("schema_canonicalizaiton", [])
            f.write(str(triplets))
            if idx != len(debated_records) - 1:
                f.write("\n")
    logger.info(f"Filtered triples txt written to: {output_txt_path}")
    
    # Write audit log containing all agent response logs
    audit_log_path = os.path.join(output_dir, "debate_log_all.json")
    audit_data = {
        "config": {
            "model": args.debate_gate_model,
            "clinical_specialist_model": args.clinical_specialist_model or args.debate_gate_model,
            "ontology_inspector_model": args.ontology_inspector_model or args.debate_gate_model,
            "medical_skeptic_model": args.medical_skeptic_model or args.debate_gate_model,
            "fcs_threshold": args.debate_gate_fcs_threshold,
            "veto_threshold": args.debate_gate_veto_threshold,
            "max_rounds": args.debate_gate_max_rounds,
        },
        "stats": gate.get_stats(),
        "results": [r.to_dict() for r in all_debate_results],
    }
    with open(audit_log_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Audit debate log written to: {audit_log_path}")
    
    # 7. Pretty-print final verification summary
    logger.info(
        f"\n"
        f"╔══════════════════════════════════════════════════════════╗\n"
        f"║           STANDALONE DEBATE GATE VERIFICATION SUMMARY     ║\n"
        f"╠══════════════════════════════════════════════════════════╣\n"
        f"║  Total Triples Pre-Debate:  {total_triples_pre:>5}                        ║\n"
        f"║  Total Triples Post-Debate: {total_triples_post:>5} ✅                     ║\n"
        f"║  Total Triples Filtered:    {total_triples_pre - total_triples_post:>5} ❌                     ║\n"
        f"║  Accepted Ratio:            {total_triples_post / total_triples_pre * 100:>5.1f}%                        ║\n"
        f"╚══════════════════════════════════════════════════════════╝"
    )


if __name__ == "__main__":
    parser = ArgumentParser(description="Standalone Multi-Agent Debate Gate for Medical KG Triple Verification.")
    
    # Files
    parser.add_argument(
        "--input_json_path",
        required=True,
        help="Path to 'result_at_each_stage.json' from completed EDC extraction."
    )
    parser.add_argument(
        "--schema_path",
        required=True,
        help="Path to the target relation schema CSV file."
    )
    parser.add_argument(
        "--output_dir",
        default="",
        help="Target output directory (defaults to the same directory as input_json_path)."
    )
    
    # Debate Gate hyperparameters
    parser.add_argument(
        "--debate_gate_model",
        required=True,
        help="LLM model identifier (e.g. 'openai/gpt-4o', 'google/gemini-2.5-pro')."
    )
    parser.add_argument(
        "--clinical_specialist_model",
        default=None,
        help="Dedicated model for Clinical Specialist (e.g. 'meta-llama/llama-3.3-70b-instruct')."
    )
    parser.add_argument(
        "--ontology_inspector_model",
        default=None,
        help="Dedicated model for Ontology Inspector (e.g. 'meta-llama/llama-3.1-8b-instruct')."
    )
    parser.add_argument(
        "--medical_skeptic_model",
        default=None,
        help="Dedicated model for Medical Skeptic (e.g. 'google/gemma-4-26b-a4b-it')."
    )
    parser.add_argument(
        "--debate_gate_fcs_threshold",
        default=80.0,
        type=float,
        help="Final Consensus Score (FCS) threshold for triple acceptance (default: 80.0)."
    )
    parser.add_argument(
        "--debate_gate_veto_threshold",
        default=70,
        type=int,
        help="Confidence threshold for agent veto power (default: 70)."
    )
    parser.add_argument(
        "--debate_gate_max_rounds",
        default=3,
        type=int,
        help="Maximum debate rounds (default: 3)."
    )
    parser.add_argument(
        "--debate_gate_max_concurrent",
        default=5,
        type=int,
        help="Maximum concurrent triple verifications (default: 5)."
    )
    
    args = parser.parse_args()
    
    # Execute runner using asyncio
    asyncio.run(run_standalone_debate(args))
