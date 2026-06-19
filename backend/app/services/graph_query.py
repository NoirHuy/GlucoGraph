from app.database import get_db_driver

# ─────────────────────────────────────────────────────────────────────────────
# RELATIONSHIP PRIORITY WEIGHTS — used by score_and_prune_triples in cdss.py
# Higher weight = more important for clinical decision-making
# ─────────────────────────────────────────────────────────────────────────────
RELATION_WEIGHTS = {
    "CONTRAINDICATED_WITH":   10,
    "TREATED_BY":              8,
    "HAS_FINDING":             8,
    "CAUSE_OF":                7,
    "HAS_ADVERSE_EFFECT":      7,
    "PREFERRED_OVER":          7,
    "INCREASES_RISK_OF":       6,
    "HAS_BIOMARKER":           4,
    "HAS_EVALUATION":          3,
    "HAS_ANATOMIC_SITE":       3,
    "CO_OCCURS_WITH":          2,
    "IS_A":                    2,
    "ADMINISTERED_VIA":        1,
    "DISPENSES":               1,
    "HAS_TITRATION_RULE":      1,
    "RELATION":                1,
}

# Node types that are the most clinically relevant for traversal expansion
PRIORITY_NODE_LABELS = {"Disease", "Drug", "Symptom", "Finding", "Anatomy"}


def get_all_cdss_nodes() -> list[dict]:
    """Retrieve all unique medical node IDs and their aliases from Neo4j for LLM entity mapping."""
    driver = get_db_driver()
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (n) WHERE n.id IS NOT NULL RETURN n.id AS id, coalesce(n.aliases, []) AS aliases"
            )
            return [{"id": r["id"], "aliases": r["aliases"]} for r in result]
    except Exception as e:
        print(f"⚠️ Neo4j error in get_all_cdss_nodes: {e}")
        return []


def get_contraindications_direct(seed_nodes: list[str]) -> list[dict]:
    """
    HIGH-PRIORITY query: fetch all CONTRAINDICATED_WITH edges involving seed nodes.
    These power the Circuit Breaker mechanism and are always fetched first.
    """
    driver = get_db_driver()
    if not driver or not seed_nodes:
        return []
    query = """
    MATCH (a)-[r:CONTRAINDICATED_WITH]->(b)
    WHERE a.id IN $nodes OR b.id IN $nodes
    RETURN a.id AS subject, type(r) AS relation, b.id AS object,
           labels(a)[0] AS subject_type, labels(b)[0] AS object_type,
           1 AS hop, coalesce(r.confidence, 100.0) AS confidence
    UNION
    MATCH (a)<-[r:CONTRAINDICATED_WITH]-(b)
    WHERE a.id IN $nodes OR b.id IN $nodes
    RETURN b.id AS subject, type(r) AS relation, a.id AS object,
           labels(b)[0] AS subject_type, labels(a)[0] AS object_type,
           1 AS hop, coalesce(r.confidence, 100.0) AS confidence
    """
    try:
        with driver.session() as session:
            results = session.run(query, nodes=seed_nodes)
            seen = set()
            triples = []
            for r in results:
                key = (r["subject"], r["relation"], r["object"])
                if key not in seen:
                    seen.add(key)
                    triples.append({
                        "subject": r["subject"],
                        "relation": r["relation"],
                        "object": r["object"],
                        "subject_type": r["subject_type"],
                        "object_type": r["object_type"],
                        "hop": r["hop"],
                        "confidence": r["confidence"],
                    })
            return triples
    except Exception as e:
        print(f"⚠️ Neo4j error in get_contraindications_direct: {e}")
        return []


def get_bfs_hop1(seed_nodes: list[str], limit: int = 60) -> list[dict]:
    """
    BFS Hop 1: expand from seed_nodes in BOTH directions across all relation types.
    Returns (subject, relation, object) triples with hop=1 marker.
    """
    driver = get_db_driver()
    if not driver or not seed_nodes:
        return []
    query = """
    MATCH (a)-[r]->(b)
    WHERE a.id IN $nodes
      AND type(r) <> 'CONTRAINDICATED_WITH'
    RETURN a.id AS subject, type(r) AS relation, b.id AS object,
           labels(a)[0] AS subject_type, labels(b)[0] AS object_type,
           1 AS hop, coalesce(r.confidence, 100.0) AS confidence
    UNION
    MATCH (a)<-[r]-(b)
    WHERE a.id IN $nodes
      AND type(r) <> 'CONTRAINDICATED_WITH'
    RETURN b.id AS subject, type(r) AS relation, a.id AS object,
           labels(b)[0] AS subject_type, labels(a)[0] AS object_type,
           1 AS hop, coalesce(r.confidence, 100.0) AS confidence
    LIMIT $limit
    """
    try:
        with driver.session() as session:
            results = session.run(query, nodes=seed_nodes, limit=limit)
            seen = set()
            triples = []
            for r in results:
                key = (r["subject"], r["relation"], r["object"])
                if key not in seen:
                    seen.add(key)
                    triples.append({
                        "subject": r["subject"],
                        "relation": r["relation"],
                        "object": r["object"],
                        "subject_type": r["subject_type"],
                        "object_type": r["object_type"],
                        "hop": r["hop"],
                        "confidence": r["confidence"],
                    })
            return triples
    except Exception as e:
        print(f"⚠️ Neo4j error in get_bfs_hop1: {e}")
        return []


def get_bfs_hop2(hop1_triples: list[dict], original_seeds: list[str], limit: int = 60) -> list[dict]:
    """
    BFS Hop 2: expand from the targets of hop-1 triples.
    Focuses on Disease/Drug/Symptom/Finding nodes for clinical relevance.
    Only returns triples NOT already covered in hop-1 or original seeds.
    """
    driver = get_db_driver()
    if not driver or not hop1_triples:
        return []

    # Collect unique target node IDs from hop 1 (prioritize clinical types)
    hop1_targets = set()
    for t in hop1_triples:
        if t.get("object_type") in PRIORITY_NODE_LABELS:
            hop1_targets.add(t["object"])
        if t.get("subject_type") in PRIORITY_NODE_LABELS:
            hop1_targets.add(t["subject"])

    # Exclude original seeds to avoid cycles
    hop1_targets -= set(original_seeds)
    if not hop1_targets:
        return []

    hop1_target_list = list(hop1_targets)[:30]  # cap to avoid huge queries

    query = """
    MATCH (a)-[r]->(b)
    WHERE a.id IN $targets
      AND NOT a.id IN $seeds
      AND (labels(b)[0] IN ['Disease', 'Drug', 'Symptom', 'Finding', 'Anatomy', 'BodyPart'])
    RETURN a.id AS subject, type(r) AS relation, b.id AS object,
           labels(a)[0] AS subject_type, labels(b)[0] AS object_type,
           2 AS hop, coalesce(r.confidence, 100.0) AS confidence
    UNION
    MATCH (a)<-[r]-(b)
    WHERE a.id IN $targets
      AND NOT a.id IN $seeds
      AND (labels(b)[0] IN ['Disease', 'Drug', 'Symptom', 'Finding', 'Anatomy', 'BodyPart'])
    RETURN b.id AS subject, type(r) AS relation, a.id AS object,
           labels(b)[0] AS subject_type, labels(a)[0] AS object_type,
           2 AS hop, coalesce(r.confidence, 100.0) AS confidence
    LIMIT $limit
    """
    try:
        with driver.session() as session:
            results = session.run(
                query,
                targets=hop1_target_list,
                seeds=list(original_seeds),
                limit=limit
            )
            seen = set()
            triples = []
            for r in results:
                key = (r["subject"], r["relation"], r["object"])
                if key not in seen:
                    seen.add(key)
                    triples.append({
                        "subject": r["subject"],
                        "relation": r["relation"],
                        "object": r["object"],
                        "subject_type": r["subject_type"],
                        "object_type": r["object_type"],
                        "hop": r["hop"],
                        "confidence": r["confidence"],
                    })
            return triples
    except Exception as e:
        print(f"⚠️ Neo4j error in get_bfs_hop2: {e}")
        return []


def check_contraindications(disease_name: str) -> list[dict]:
    """Legacy: Query Neo4j for drugs contraindicated with a specific condition."""
    driver = get_db_driver()
    if not driver:
        return []
    query = """
    MATCH (d)-[r]->(dr)
    WHERE toLower(d.id) CONTAINS toLower($disease)
      AND (type(r) = 'CONTRAINDICATED_WITH')
    RETURN d.id AS disease, dr.id AS drug, toLower(type(r)) AS relation
    """
    try:
        with driver.session() as session:
            results = session.run(query, disease=disease_name)
            return [
                {"disease": r["disease"], "drug": r["drug"], "relation": r["relation"]}
                for r in results
            ]
    except Exception as e:
        print(f"⚠️ Neo4j error in check_contraindications: {e}")
        return []


def get_node_relations(node_name: str) -> list[dict]:
    """Retrieve all direct relations for a given node to draw the GraphRAG reasoning path."""
    driver = get_db_driver()
    if not driver:
        return []
    query = """
    MATCH (a)-[r]->(b)
    WHERE a.id = $name
    RETURN a.id AS subject, toLower(type(r)) AS relation, b.id AS object,
           labels(a)[0] AS subject_type, labels(b)[0] AS object_type
    UNION
    MATCH (a)-[r]->(b)
    WHERE b.id = $name
    RETURN a.id AS subject, toLower(type(r)) AS relation, b.id AS object,
           labels(a)[0] AS subject_type, labels(b)[0] AS object_type
    """
    try:
        with driver.session() as session:
            results = session.run(query, name=node_name)
            return [
                {
                    "subject": r["subject"],
                    "relation": r["relation"],
                    "object": r["object"],
                    "subject_type": r["subject_type"],
                    "object_type": r["object_type"],
                }
                for r in results
            ]
    except Exception as e:
        print(f"⚠️ Neo4j error in get_node_relations: {e}")
        return []


def execute_raw_cypher(query: str) -> list[dict]:
    """Execute a raw Cypher query safely on the active Neo4j session and return the results.
    Raises exception on syntax error or failure to let caller fall back.
    """
    driver = get_db_driver()
    if not driver:
        return []
    try:
        with driver.session() as session:
            results = session.run(query)
            return [dict(record) for record in results]
    except Exception as e:
        print(f"⚠️ Neo4j error in execute_raw_cypher: {e}")
        raise e

