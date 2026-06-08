from neo4j import GraphDatabase

# Neo4j connection details
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def query_triples():
    with driver.session() as session:
        print("Querying all triples connected to 'Exercise'...")
        result = session.run("MATCH (a)-[r]-(b) WHERE toLower(a.id) CONTAINS 'exercise' OR toLower(b.id) CONTAINS 'exercise' RETURN a.id as a_id, labels(a) as a_labels, type(r) as rel_type, b.id as b_id, labels(b) as b_labels")
        records = list(result)
        if records:
            print(f"Found {len(records)} relationships connected to 'Exercise':")
            for rec in records:
                print(f"- ({rec['a_id']} :{rec['a_labels']}) -[:{rec['rel_type']}]-> ({rec['b_id']} :{rec['b_labels']})")
        else:
            print("No relationships found connected to 'Exercise'!")

        print("\nQuerying specific node 'Plasma fasting glucose measurement'...")
        result = session.run("MATCH (n) WHERE toLower(n.id) CONTAINS 'glucose' RETURN n.id as node_id, labels(n) as labels, n.aliases as aliases, n.umls_cui as umls_cui, n.umls_canonical as umls_canonical")
        records = list(result)
        if records:
            print(f"Found {len(records)} nodes containing 'glucose':")
            for rec in records:
                print(f"- ID: {rec['node_id']}, Labels: {rec['labels']}, CUI: {rec['umls_cui']}, Canonical: {rec['umls_canonical']}, Aliases: {rec['aliases']}")
        else:
            print("No nodes found containing 'glucose'!")

query_triples()
driver.close()
