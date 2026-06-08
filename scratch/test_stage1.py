import os
import sys
sys.path.append("backend")

# Mock settings and DB for testing imports if needed, but we can just import from app.services.cdss
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"

from app.services.cdss import chunk_match_entities
from app.services.graph_query import get_all_cdss_nodes

clinical_text = "Bệnh nhân nam, 45 tuổi, sưng đau dữ dội khớp bàn ngón chân cái bên phải khởi phát cấp tính sau bữa ăn nhiều hải sản. Tiền sử loét dạ dày tá tràng."

kg_nodes = get_all_cdss_nodes()
print(f"Total KG nodes fetched: {len(kg_nodes)}")
print(f"First 10 nodes: {kg_nodes[:10]}")

matched = chunk_match_entities(clinical_text, kg_nodes, chunk_size=100)
print(f"Matched nodes: {matched}")
