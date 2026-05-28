from app.database import get_db_driver

# Standard clinical relations in diabetes_schema.csv
CLINICAL_RELATIONS = [
    "is a",
    "has anatomic site",
    "cause of",
    "has finding",
    "has biomarker",
    "co occurs with",
    "treated by",
    "has adverse effect",
    "contraindicated with",
    "preferred over",
    "has evaluation",
    "has titration rule"
]


def get_all_cdss_nodes() -> list[str]:
    """Retrieve all unique medical node names (Disease, Drug, Symptom, Anatomy) for LLM mapping."""
    driver = get_db_driver()
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) WHERE n.name IS NOT NULL RETURN collect(DISTINCT n.name) AS names")
            record = result.single()
            return record["names"] if record and record["names"] else []
    except Exception as e:
        print(f"⚠️ Neo4j error in get_all_cdss_nodes: {e}")
        return []


def check_contraindications(disease_name: str) -> list[dict]:
    """Query Neo4j for drugs contraindicated with a specific medical condition/disease."""
    driver = get_db_driver()
    if not driver:
        return []

    # Querying either standard 'contraindicated with' or custom vietnamese equivalent
    query = """
    MATCH (d)-[r]->(dr)
    WHERE toLower(d.name) CONTAINS toLower($disease)
      AND (toLower(r.relation) CONTAINS 'contraindicate' OR toLower(r.relation) CONTAINS 'chống chỉ định')
    RETURN d.name AS disease, dr.name AS drug, r.relation AS relation
    """
    try:
        with driver.session() as session:
            results = session.run(query, disease=disease_name)
            return [
                {
                    "disease": r["disease"],
                    "drug": r["drug"],
                    "relation": r["relation"]
                }
                for r in results
            ]
    except Exception as e:
        print(f"⚠️ Neo4j error in check_contraindications: {e}")
        return []


def get_diseases_by_symptoms(symptoms: list[str]) -> list[dict]:
    """Query Neo4j to find potential diseases associated with a list of symptoms for differential diagnosis."""
    driver = get_db_driver()
    if not driver or not symptoms:
        return []

    query = """
    MATCH (s)-[r]->(d)
    WHERE s.name IN $symptoms 
      AND (toLower(r.relation) CONTAINS 'manifestation' OR toLower(r.relation) CONTAINS 'finding' OR toLower(r.relation) CONTAINS 'triệu chứng')
    RETURN s.name AS symptom, d.name AS disease, r.relation AS relation
    """
    try:
        with driver.session() as session:
            results = session.run(query, symptoms=symptoms)
            return [
                {
                    "symptom": r["symptom"],
                    "disease": r["disease"],
                    "relation": r["relation"]
                }
                for r in results
            ]
    except Exception as e:
        print(f"⚠️ Neo4j error in get_diseases_by_symptoms: {e}")
        return []


def get_node_relations(node_name: str) -> list[dict]:
    """Retrieve all direct relations for a given node to draw the GraphRAG reasoning path."""
    driver = get_db_driver()
    if not driver:
        return []

    query = """
    MATCH (a)-[r]->(b)
    WHERE a.name = $name
    RETURN a.name AS subject, r.relation AS relation, b.name AS object,
           labels(a)[0] AS subject_type, labels(b)[0] AS object_type
    UNION
    MATCH (a)-[r]->(b)
    WHERE b.name = $name
    RETURN a.name AS subject, r.relation AS relation, b.name AS object,
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
                    "object_type": r["object_type"]
                }
                for r in results
            ]
    except Exception as e:
        print(f"⚠️ Neo4j error in get_node_relations: {e}")
        return []
