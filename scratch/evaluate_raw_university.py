import os
import re
import ast
import csv

project_root = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject"
evaluate_dir = os.path.join(project_root, "evaluate")
uni_dir = os.path.join(evaluate_dir, "dbpedia_webnlg", "eval_university")
outputs_dir = os.path.join(uni_dir, "outputs")

pred_file = os.path.join(outputs_dir, "canon_kg.txt")
ref_file = os.path.join(outputs_dir, "subset_references.txt")
target_schema_path = os.path.join(uni_dir, "schemas", "relation_schema.csv")

def normalize_triple(sub_label: str, rel_label: str, obj_label: str) -> str:
    sub_label = re.sub(r"(_|\s+)", '', sub_label).lower()
    rel_label = re.sub(r"(_|\s+)", '', rel_label).lower()
    obj_label = re.sub(r"(_|\s+)", '', obj_label).lower()
    return f"{sub_label}{rel_label}{obj_label}"

def calculate_precision_recall_f1(gold: set, pred: set) -> tuple:
    if len(pred) == 0:
        return 0.0, 0.0, 0.0
    p = len(gold.intersection(pred)) / len(pred)
    r = len(gold.intersection(pred)) / len(gold)
    if p + r > 0:
        f1 = 2 * ((p * r) / (p + r))
    else:
        f1 = 0.0
    return p, r, f1

def main():
    # Load ontology relations
    ont_rels = set()
    if os.path.exists(target_schema_path):
        try:
            with open(target_schema_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    if row:
                        ont_rels.add(row[0].strip().replace(" ", "_"))
        except Exception as e:
            print(f"Error loading target schema: {e}")

    with open(pred_file, "r", encoding="utf-8") as f:
        pred_lines = [line.strip() for line in f if line.strip()]
    with open(ref_file, "r", encoding="utf-8") as f:
        ref_lines = [line.strip() for line in f if line.strip()]

    num_cases = min(len(pred_lines), len(ref_lines))
    print(f"Loaded {num_cases} test cases.")
    
    t_p, t_r, t_f1, t_onto_conf, t_rel_halluc = 0.0, 0.0, 0.0, 0.0, 0.0

    for idx in range(num_cases):
        try:
            pred_triples = ast.literal_eval(pred_lines[idx])
        except Exception:
            pred_triples = []
        try:
            gt_triples = ast.literal_eval(ref_lines[idx])
        except Exception:
            gt_triples = []

        # Ground truth relations (with space to underscore)
        gt_relations = {tr[1].replace(" ", "_") for tr in gt_triples if len(tr) == 3}

        # Filter pred triples to only match GT relations
        filtered_pred_triples = [tr for tr in pred_triples if len(tr) == 3 and tr[1].replace(" ", "_") in gt_relations]

        # Normalize S-P-O for set comparison
        normalized_pred = {normalize_triple(tr[0], tr[1], tr[2]) for tr in filtered_pred_triples}
        normalized_gt = {normalize_triple(tr[0], tr[1], tr[2]) for tr in gt_triples if len(tr) == 3}

        precision, recall, f1 = calculate_precision_recall_f1(normalized_gt, normalized_pred)

        # Ontology conformance
        if len(pred_triples) == 0:
            ont_conformance = 1.0
        else:
            num_rels_conformant = len([tr for tr in pred_triples if len(tr) == 3 and tr[1].replace(" ", "_") in ont_rels])
            ont_conformance = num_rels_conformant / len(pred_triples)
        rel_hallucination = 1.0 - ont_conformance

        t_p += precision
        t_r += recall
        t_f1 += f1
        t_onto_conf += ont_conformance
        t_rel_halluc += rel_hallucination

    avg_precision = t_p / num_cases if num_cases > 0 else 0.0
    avg_recall = t_r / num_cases if num_cases > 0 else 0.0
    avg_f1 = t_f1 / num_cases if num_cases > 0 else 0.0
    avg_onto_conf = t_onto_conf / num_cases if num_cases > 0 else 1.0
    avg_rel_halluc = t_rel_halluc / num_cases if num_cases > 0 else 0.0

    report_lines = []
    report_lines.append("\n" + "="*70)
    report_lines.append("       EVALUATION RESULTS (RAW / UNNORMALIZED): DBpedia WebNLG (1_university)")
    report_lines.append("="*70)
    report_lines.append(f"Text2Bench Evaluation Metrics (Macro-Average across {num_cases} docs):")
    report_lines.append(f"  Precision:              {avg_precision*100:.2f}%")
    report_lines.append(f"  Recall:                 {avg_recall*100:.2f}%")
    report_lines.append(f"  F1-Score:               {avg_f1*100:.2f}%")
    report_lines.append(f"  Ontology Conformance:   {avg_onto_conf*100:.2f}%")
    report_lines.append(f"  Relation Hallucination: {avg_rel_halluc*100:.2f}%")
    report_lines.append("="*70)
    report_lines.append("          BASELINE METRICS COMPARISON (1_university)")
    report_lines.append("="*70)
    report_lines.append("Alpaca-LoRA-13B baseline:")
    report_lines.append("  Precision: 29.0% | Recall: 16.0% | F1-Score: 20.0%")
    report_lines.append("  Rel Hallucination: 11.0%")
    report_lines.append("-" * 70)
    report_lines.append("Vicuna-13B baseline:")
    report_lines.append("  Precision: 31.0% | Recall: 19.0% | F1-Score: 23.0%")
    report_lines.append("  Rel Hallucination: 8.0%")
    report_lines.append("="*70)

    report_text = "\n".join(report_lines)
    print(report_text)

    output_report_path = os.path.join(outputs_dir, "evaluation_results_raw_comparison.txt")
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nSaved raw report successfully.")

if __name__ == "__main__":
    main()
