import os
import sys

# Add backend app directory to sys.path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.services.cdss import (
    get_all_cdss_nodes,
    chunk_match_entities,
    bfs_multi_hop_traversal,
    score_and_prune_triples,
    build_rich_graph_context,
    call_llm_api
)

def run_test():
    clinical_text = "Bệnh nhân nam, 45 tuổi, sưng đau dữ dội khớp bàn ngón chân cái bên phải khởi phát cấp tính sau bữa ăn nhiều hải sản. Tiền sử loét dạ dày tá tràng."
    patient_id = "john"

    print("=== Step 1: get_all_cdss_nodes ===")
    kg_nodes = get_all_cdss_nodes()
    print(f"Total KG nodes: {len(kg_nodes)}")

    print("\n=== Step 2: chunk_match_entities ===")
    matched_nodes, extracted_terms = chunk_match_entities(clinical_text, kg_nodes)
    print(f"Extracted terms: {extracted_terms}")
    print(f"Matched nodes: {matched_nodes}")

    print("\n=== Step 3: bfs_multi_hop_traversal ===")
    all_triples = bfs_multi_hop_traversal(matched_nodes)
    print(f"Total unique triples: {len(all_triples)}")

    print("\n=== Step 4: score_and_prune_triples ===")
    scored_triples = score_and_prune_triples(all_triples, max_triples=40)
    print(f"Pruned to {len(scored_triples)} triples")

    print("\n=== Step 5: build_rich_graph_context ===")
    graph_context = build_rich_graph_context(scored_triples, matched_nodes)
    print("--- Graph Context Sent to LLM ---")
    print(graph_context)
    print("---------------------------------")

if __name__ == "__main__":
    run_test()
