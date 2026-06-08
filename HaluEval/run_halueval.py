# -*- coding: utf-8 -*-
"""
HaluEval — Main Runner
=======================
Loads the adversarial diabetes triple dataset, runs the schema validator
on each corrupted triple, and prints a structured evaluation report
showing which attack types were correctly detected (True Positives)
vs. missed (False Negatives).

Usage:
    python HaluEval/run_halueval.py
    python HaluEval/run_halueval.py --data HaluEval/data/adversarial_diabetes_triples.json
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict

# Fix Windows console encoding
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# ── Path setup ────────────────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _PROJECT_ROOT)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("HaluEval")

# ── Local imports ─────────────────────────────────────────────────────────────
from HaluEval.schema_validator import HaluEvalSchemaValidator


# ─────────────────────────────────────────────────────────────────────────────
# Dataset loader
# ─────────────────────────────────────────────────────────────────────────────

def load_adversarial_dataset(path: str) -> List[Dict]:
    """Load the JSON adversarial dataset."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} adversarial test cases from: {path}")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation logic
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_pipeline_rejection(dataset: List[Dict]) -> Dict:
    """
    For each test case, run the validator on every corrupted triple
    and check whether the validator correctly rejects (True Positive)
    or misses (False Negative) the adversarial attack.

    Returns a summary dict with per-attack-type metrics.
    """
    validator = HaluEvalSchemaValidator()

    total = 0
    true_positives = 0   # Correctly REJECTED adversarial triples
    false_negatives = 0  # Adversarial triples incorrectly ACCEPTED

    per_type_stats: Dict[str, Dict] = {}

    print("\n" + "=" * 70)
    print("   HALUEVAL --- ADVERSARIAL TRIPLE REJECTION BENCHMARK")
    print("=" * 70)

    for case in dataset:
        case_id       = case.get("id", "?")
        attack_type   = case.get("type_of_attack", "Unknown")
        perturbed_text = case.get("perturbed_text", "")
        corrupted_triples = case.get("corrupted_triples", [])

        if attack_type not in per_type_stats:
            per_type_stats[attack_type] = {"tp": 0, "fn": 0, "total": 0}

        print(f"\n" + "-" * 70)
        print(f"  Case ID   : {case_id}")
        print(f"  Attack    : {attack_type}")
        print(f"  Text      : {perturbed_text[:100]}{'...' if len(perturbed_text) > 100 else ''}")

        for triple in corrupted_triples:
            if len(triple) != 3:
                logger.warning(f"Skipping malformed triple: {triple}")
                continue

            subj, rel, obj = triple
            result = validator.validate_triple(subj, rel, obj)

            total += 1
            per_type_stats[attack_type]["total"] += 1

            verdict = result["verdict"]
            detected_type = result["attack_type_detected"]
            reasons = result["reasons"]

            print(f"\n  Triple    : ({subj!r}, {rel!r}, {obj!r})")
            print(f"  Verdict   : {'✅ REJECT (TP)' if verdict == 'REJECT' else '❌ ACCEPT (FN — Missed!)'}")
            if detected_type:
                print(f"  Detected  : {detected_type}")
            for r in reasons:
                print(f"  Reason    : {r}")

            if verdict == "REJECT":
                true_positives += 1
                per_type_stats[attack_type]["tp"] += 1
            else:
                false_negatives += 1
                per_type_stats[attack_type]["fn"] += 1

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n" + "=" * 70)
    print("   BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"  Total adversarial triples  : {total}")
    print(f"  Correctly rejected (TP)    : {true_positives}")
    print(f"  Missed / accepted (FN)     : {false_negatives}")
    precision = true_positives / total if total > 0 else 0.0
    print(f"  Rejection Rate             : {precision:.1%}")

    print(f"\n  Per-Attack-Type Breakdown:")
    print(f"  {'Attack Type':<35} {'TP':>5} {'FN':>5} {'Total':>7} {'Rate':>8}")
    print(f"  {'-'*35} {'-'*5} {'-'*5} {'-'*7} {'-'*8}")
    for atype, stats in per_type_stats.items():
        rate = stats["tp"] / stats["total"] if stats["total"] > 0 else 0.0
        print(f"  {atype:<35} {stats['tp']:>5} {stats['fn']:>5} {stats['total']:>7} {rate:>7.1%}")
    print("=" * 70 + "\n")

    return {
        "total": total,
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "rejection_rate": precision,
        "per_type": per_type_stats,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_halueval(data_path: str):
    dataset = load_adversarial_dataset(data_path)
    results = evaluate_pipeline_rejection(dataset)

    # Save results
    out_path = os.path.join(_THIS_DIR, "data", "halueval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HaluEval — Adversarial Hallucination Evaluation for KG Pipeline"
    )
    parser.add_argument(
        "--data",
        default=os.path.join(_THIS_DIR, "data", "adversarial_diabetes_triples.json"),
        help="Path to the adversarial dataset JSON file."
    )
    args = parser.parse_args()
    run_halueval(args.data)
