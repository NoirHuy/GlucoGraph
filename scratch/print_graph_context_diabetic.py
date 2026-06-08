import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

# Load .env variables
try:
    with open(os.path.join(os.path.dirname(__file__), '../.env'), 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ[k] = v.strip('"').strip("'")
except Exception as e:
    print("Warning loading .env:", e)

from app.services.cdss import get_all_cdss_nodes, chunk_match_entities, bfs_multi_hop_traversal, score_and_prune_triples, build_rich_graph_context

clinical_text = (
    "Một bệnh nhân nam 56 tuổi đến khám vì tiểu nhiều lần trong ngày, đặc biệt về đêm, kèm theo khát nước liên tục trong khoảng 3 tháng gần đây. "
    "Bệnh nhân cho biết thường xuyên cảm thấy mệt mỏi, giảm khả năng tập trung trong công việc và gần đây xuất hiện tình trạng nhìn mờ. "
    "Tiền sử gia đình ghi nhận cha ruột mắc đái tháo đường type 2. Bệnh nhân có BMI 31 kg/m². Kết quả xét nghiệm cho thấy đường huyết lúc đói là 156 mg/dL, "
    "HbA1c 8,2% và đường huyết ngẫu nhiên 245 mg/dL."
)

kg_nodes = get_all_cdss_nodes()
matched, extracted = chunk_match_entities(clinical_text, kg_nodes)
print("Matched entities:", matched)

all_triples = bfs_multi_hop_traversal(matched)
print(f"Total unique triples retrieved: {len(all_triples)}")

scored = score_and_prune_triples(all_triples)
print("\n--- GRAPH CONTEXT SENT TO LLM ---")
print(build_rich_graph_context(scored, matched))
