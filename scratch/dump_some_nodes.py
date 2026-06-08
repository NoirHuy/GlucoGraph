from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def search_nodes():
    with driver.session() as session:
        print("--- Total node count in DB ---")
        result = session.run("MATCH (n) RETURN count(n) as count")
        print("Node count:", result.single()["count"])

        print("\n--- First 30 nodes in DB ---")
        result = session.run("MATCH (n) RETURN n.id as id, labels(n) as labels LIMIT 30")
        for rec in result:
            # Safely encode/decode to avoid print errors
            node_id = str(rec['id']).encode('ascii', 'replace').decode('ascii')
            print(f"ID: {node_id}, Labels: {rec['labels']}")

        print("\n--- Search for node types ---")
        result = session.run("MATCH (n) RETURN labels(n) as labels, count(*) as count")
        for rec in result:
            print(f"Labels: {rec['labels']}, Count: {rec['count']}")

search_nodes()
driver.close()
