# -*- coding: utf-8 -*-
"""
HaluEval Unified Evaluator
=========================
Runs the Multi-Agent Debate Gate on a mixed dataset (50 or 100 triples containing
both correct and trap triples) and computes:
1. Accuracy = (TP + TN) / Total
2. FNR (False Negative Rate - Rò rỉ ảo giác) = FN / (TN + FN) * 100%
3. FPR (False Positive Rate - Từ chối nhầm) = FP / (TP + FP) * 100%
4. Trap Rejection Rate (Tỷ lệ chặn bẫy thành công) = 100% - FNR = TN / (TN + FN) * 100%

Usage:
    python HaluEval/run.py --size 50
    python HaluEval/run.py --size 100
"""

import os
import sys
import json
import argparse
import subprocess
import logging
import ast
from pathlib import Path

# Fix Windows console encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("HaluEval")

# ─────────────────────────────────────────────────────────────────────────────
# Paths Setup
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
EDC_MAIN_DIR = PROJECT_ROOT.parent / "edc-main"
CONFIG_PATH = PROJECT_ROOT / "config.json"

# Load env variables and find OpenRouter api key pool
def load_env():
    env_path = PROJECT_ROOT.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
    
    if not os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("OPENROUTER_KEY"):
        for i in range(1, 21):
            k = os.environ.get(f"OPENROUTER_API_KEY_{i}") or os.environ.get(f"OPENROUTER_KEY_{i}")
            if k:
                os.environ["OPENROUTER_API_KEY"] = k
                logger.info(f"Auto-selected active OPENROUTER_API_KEY from pool index {i}")
                break
    
    if "GROQ_API_KEY" in os.environ and "GROQ_KEY" not in os.environ:
        os.environ["GROQ_KEY"] = os.environ["GROQ_API_KEY"]

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_triple(t):
    if not t:
        return None
    return (
        str(t[0]).strip().lower(),
        str(t[1]).strip().lower().replace("_", " "),
        str(t[2]).strip().lower(),
    )

def load_references(ref_txt_path):
    refs = []
    if not ref_txt_path.exists():
        return refs
    with open(ref_txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = ast.literal_eval(line)
                refs.append([normalize_triple(t) for t in parsed])
            except Exception as e:
                logger.error(f"Error parsing reference line: {line}. Error: {e}")
                refs.append([])
    return refs

def run_debate_gate(config, input_json_path, output_dir):
    run_debate_script = EDC_MAIN_DIR / "debate_gate" / "run_debate.py"
    if not run_debate_script.exists():
        logger.error(f"run_debate.py not found at {run_debate_script}")
        return False

    cmd = [
        sys.executable,
        str(run_debate_script),
        "--input_json_path", str(input_json_path),
        "--schema_path", str(PROJECT_ROOT.parent / config["schema_path"]),
        "--output_dir", str(output_dir),
        "--debate_gate_model", config["debate_gate_model"],
        "--clinical_specialist_model", config["clinical_specialist_model"],
        "--ontology_inspector_model", config["ontology_inspector_model"],
        "--medical_skeptic_model", config["medical_skeptic_model"],
        "--debate_gate_fcs_threshold", str(config["fcs_threshold"]),
        "--debate_gate_veto_threshold", str(config["veto_confidence_threshold"]),
        "--debate_gate_max_rounds", str(config["max_rounds"]),
        "--debate_gate_max_concurrent", str(config["max_concurrent"]),
    ]

    logger.info(f"Running Multi-Agent Debate gate for input: {input_json_path.name}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(EDC_MAIN_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(cmd, env=env)
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="HaluEval Unified Evaluator")
    parser.add_argument(
        "--size",
        type=int,
        default=100,
        help="Size of test dataset to run (e.g., 50, 100, 200)"
    )
    args = parser.parse_args()

    load_env()
    config = load_config()

    # Dynamic paths based on size parameter
    data_dir = PROJECT_ROOT / "data" / f"{args.size}_triples"
    input_json_path = data_dir / "dataset.json"
    ref_txt_path = data_dir / "references.txt"
    output_dir = PROJECT_ROOT / "output" / f"{args.size}_triples"
    debated_json_path = output_dir / "result_at_each_stage_debated.json"
    summary_report_json = output_dir / "summary.json"

    if not input_json_path.exists():
        logger.error(f"Input dataset not found at: {input_json_path}")
        sys.exit(1)
    if not ref_txt_path.exists():
        logger.error(f"References file not found at: {ref_txt_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run debate gate
    if not run_debate_gate(config, input_json_path, output_dir):
        logger.error("Debate gate execution failed.")
        sys.exit(1)

    # 2. Load input and output records
    with open(input_json_path, "r", encoding="utf-8") as f:
        input_records = json.load(f)
    if not debated_json_path.exists():
        logger.error(f"Debated output file not found: {debated_json_path}")
        sys.exit(1)
    with open(debated_json_path, "r", encoding="utf-8") as f:
        debated_records = json.load(f)

    # 3. Load Ground Truth references
    references = load_references(ref_txt_path)
    while len(references) < len(input_records):
        references.append([])

    # Metrics classifications
    tps, tns, fps, fns = [], [], [], []

    print("\n" + "="*80)
    print(f"  HALUEVAL UNIFIED TRIPLE CLASSIFICATION ({args.size} TRIPLES)")
    print("="*80)

    for idx, (in_rec, deb_rec, ref_list) in enumerate(zip(input_records, debated_records, references)):
        print(f"\nDocument {idx}: {in_rec['input_text'].strip()}")
        
        pre_triples = [t for t in in_rec.get("schema_canonicalizaiton", []) if t is not None]
        post_triples = [t for t in deb_rec.get("schema_canonicalizaiton", []) if t is not None]
        
        accepted_set = {normalize_triple(t) for t in post_triples}
        gt_set = set(ref_list)

        for t in pre_triples:
            norm_t = normalize_triple(t)
            is_correct = norm_t in gt_set
            was_accepted = norm_t in accepted_set
            triple_str = f"({t[0]}, {t[1]}, {t[2]})"
            
            if is_correct:
                if was_accepted:
                    tps.append(t)
                    print(f"  [TP] [CORRECT -> ACCEPTED] {triple_str}")
                else:
                    fps.append(t)
                    print(f"  [FP] [CORRECT -> REJECTED] {triple_str}  <-- !! Incorrect rejection")
            else:
                if was_accepted:
                    fns.append(t)
                    print(f"  [FN] [TRAP    -> ACCEPTED] {triple_str}  <-- !! Leaked hallucination")
                else:
                    tns.append(t)
                    print(f"  [TN] [TRAP    -> REJECTED] {triple_str}")

    # 4. Compute metrics
    tp_count, tn_count, fp_count, fn_count = len(tps), len(tns), len(fps), len(fns)
    total_cases = tp_count + tn_count + fp_count + fn_count

    accuracy = (tp_count + tn_count) / total_cases if total_cases > 0 else 0.0
    total_traps = tn_count + fn_count
    fnr = (fn_count / total_traps * 100) if total_traps > 0 else 0.0
    total_correct = tp_count + fp_count
    fpr = (fp_count / total_correct * 100) if total_correct > 0 else 0.0
    rejection_rate = (tn_count / total_traps * 100) if total_traps > 0 else 0.0

    print("\n" + "="*80)
    print(f"  HALUEVAL INTEGRATED SUMMARY REPORT ({args.size} TRIPLES)")
    print("="*80)
    print(f"  Total Cases Evaluated  : {total_cases}")
    print(f"  - True Positives (TP)  : {tp_count} (Correct accepted)")
    print(f"  - True Negatives (TN)  : {tn_count} (Trap blocked)")
    print(f"  - False Positives (FP) : {fp_count} (Correct rejected nhầm)")
    print(f"  - False Negatives (FN) : {fn_count} (Trap lọt lưới)")
    print("-" * 80)
    print(f"  1. Accuracy (Độ chính xác)                   : {accuracy:.2%}")
    print(f"  2. False Negative Rate (FNR - Rò rỉ)          : {fnr:.2f}%")
    print(f"  3. False Positive Rate (FPR - Từ chối nhầm)   : {fpr:.2f}%")
    print(f"  4. Trap Rejection Rate (Chặn bẫy thành công)  : {rejection_rate:.2f}%")
    print("="*80 + "\n")

    summary = {
        "metrics": {
            "accuracy": accuracy,
            "false_negative_rate_percent": fnr,
            "false_positive_rate_percent": fpr,
            "trap_rejection_rate_percent": rejection_rate,
        },
        "counts": {
            "total_cases": total_cases,
            "true_positives": tp_count,
            "true_negatives": tn_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
        },
        "details": {
            "true_positives_list": tps,
            "true_negatives_list": tns,
            "false_positives_list": fps,
            "false_negatives_list": fns,
        }
    }
    with open(summary_report_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"Summary report saved to: {summary_report_json}")


if __name__ == "__main__":
    main()
