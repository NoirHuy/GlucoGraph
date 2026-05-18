# UMLS Medical Knowledge Graph Pipeline

A production-quality Python pipeline that extracts a sub-graph from the
**Unified Medical Language System (UMLS) REST API** and transforms it into
structured JSON ready for import into **Neo4j** or use in a **GraphRAG** pipeline.

---

## 📐 Architecture

```
umls_graph/
├── config.py        ← All tuneable constants (depth, relation filters, type maps…)
├── utils.py         ← Logging, DiskCache, helpers
├── api_client.py    ← Reusable UMLS REST client (auth, pagination, retries, caching)
├── extractor.py     ← BFS graph traversal; produces RawConcept / RawRelation objects
├── transformer.py   ← Maps raw UMLS data → clean KG nodes/edges schema
└── main.py          ← CLI entry point; orchestrates the full pipeline
```

### Data flow

```
UMLS REST API
      │
      ▼
UMLSClient  (api_client.py)
  • Auth + pagination
  • Exponential back-off
  • DiskCache (JSON files)
      │
      ▼
UMLSExtractor  (extractor.py)
  • BFS to max_depth hops
  • Cycle detection (visited set)
  • Relation filtering (RO/RB/RN/SY)
      │
      ▼
KGTransformer  (transformer.py)
  • Semantic type → node type mapping
  • Relation abbreviation → readable label
  • Deduplication + referential integrity
      │
      ▼
output/knowledge_graph.json   +   output/import.cypher (optional)
```

---

## 🔑 Prerequisites

1. **Python 3.11+**
2. **Free UMLS API key** — register at <https://uts.nlm.nih.gov/uts/signup-login>
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Export your API key:

```bash
export UMLS_API_KEY=your_api_key_here
```

---

## 🚀 Quick Start

```bash
# Diabetes Mellitus, depth 2 (default)
python main.py --cui C0011849 --depth 2

# Also emit a Neo4j Cypher import script
python main.py --cui C0011849 --depth 2 --cypher

# Custom output path
python main.py --cui C0011849 --depth 2 --output ./data/diabetes_kg.json

# Force fresh API calls (bypass cache)
python main.py --cui C0011849 --depth 1 --no-cache

# Debug logging
python main.py --cui C0011849 --depth 1 --log-level DEBUG
```

---

## 📦 Output Format

### `knowledge_graph.json`

```json
{
  "nodes": [
    {
      "id": "C0011849",
      "name": "Diabetes Mellitus",
      "type": "Disease",
      "semantic_types": ["Disease or Syndrome"],
      "synonyms": ["DM", "Diabetes", "Sugar Diabetes", "..."],
      "definition": "A heterogeneous group of disorders..."
    }
  ],
  "edges": [
    {
      "source": "C0011849",
      "target": "C0020429",
      "relation": "associated_with",
      "relation_type": "RO",
      "additional_label": "has_finding_site"
    }
  ]
}
```

### Node types (mapped from UMLS semantic types)

| Semantic Type             | KG Node Type |
|---------------------------|--------------|
| Disease or Syndrome       | Disease      |
| Sign or Symptom           | Symptom      |
| Pharmacologic Substance   | Drug         |
| Clinical Drug             | Drug         |
| Gene or Genome            | Gene         |
| Body Part / Organ         | Anatomy      |
| Laboratory Procedure      | Procedure    |
| …                         | Concept      |

### Edge relation labels

| UMLS Code | KG Label        |
|-----------|-----------------|
| RO        | associated_with |
| RB        | broader_than    |
| RN        | narrower_than   |
| SY        | synonym_of      |

---

## 🗄️ Neo4j Import

### With the generated Cypher script

```bash
# Generate alongside JSON
python main.py --cui C0011849 --depth 2 --cypher

# Import into Neo4j (requires cypher-shell)
cypher-shell -u neo4j -p password -f output/knowledge_graph.cypher
```

### Or paste `import.cypher` directly into **Neo4j Browser**.

### Sample queries after import

```cypher
// Find all diseases related to Diabetes
MATCH (d:Disease {id: 'C0011849'})-[:ASSOCIATED_WITH]->(n)
RETURN n.name, n.type LIMIT 25;

// Shortest path between Diabetes and Insulin
MATCH path = shortestPath(
  (a:Disease {id: 'C0011849'})-[*..5]-(b:Drug {name: 'Insulin'})
)
RETURN path;

// All drugs associated with Diabetes (within 2 hops)
MATCH (d:Disease {id: 'C0011849'})-[*1..2]-(drug:Drug)
RETURN DISTINCT drug.name ORDER BY drug.name;
```

---

## ⚙️ Configuration (`config.py`)

| Variable                 | Default        | Description                          |
|--------------------------|----------------|--------------------------------------|
| `DEFAULT_DEPTH`          | `2`            | BFS traversal hops                   |
| `MAX_ATOMS_PER_CUI`      | `50`           | Cap on synonym atoms per concept     |
| `MAX_RELATIONS_PER_CUI`  | `100`          | Cap on relations per concept         |
| `ALLOWED_RELATION_TYPES` | `{RO,RB,RN,SY}`| UMLS relation types to keep         |
| `CACHE_ENABLED`          | `True`         | Disk cache toggle                    |
| `CACHE_DIR`              | `.umls_cache/` | Cache directory                      |
| `RATE_LIMIT_SLEEP`       | `0.3s`         | Polite pause between API calls       |
| `MAX_RETRIES`            | `5`            | Retry attempts on 429/5xx            |

---

## 🩺 Extending to Other Diseases

The pipeline is disease-agnostic. Just pass a different CUI:

```bash
# Hypertension
python main.py --cui C0020538 --depth 2

# Alzheimer's Disease
python main.py --cui C0002395 --depth 2

# COVID-19
python main.py --cui C5203670 --depth 2
```

---

## 🔗 GraphRAG Integration

The JSON output is directly usable as a GraphRAG context source:

```python
import json

with open("output/knowledge_graph.json") as f:
    kg = json.load(f)

# Build a context string for the RAG prompt
def kg_context(cui: str, kg: dict, hops: int = 1) -> str:
    node = next((n for n in kg["nodes"] if n["id"] == cui), None)
    if not node:
        return ""
    edges = [e for e in kg["edges"] if e["source"] == cui]
    neighbors = [
        f"  - {e['relation']} → {next((n['name'] for n in kg['nodes'] if n['id'] == e['target']), e['target'])}"
        for e in edges
    ]
    return f"{node['name']} ({node['type']}):\n" + "\n".join(neighbors)

print(kg_context("C0011849", kg))
```

---

## 📝 Notes

- The UMLS API is free but requires registration and agreement to the UMLS license.
- Depth 2 can generate hundreds of API calls; the disk cache ensures you don't re-fetch.
- At depth 3+ expect thousands of nodes — consider narrowing `ALLOWED_RELATION_TYPES`.