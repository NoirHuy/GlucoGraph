from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def dump_all_nodes():
    with driver.session() as session:
        result = session.run("MATCH (n) WHERE n.id IS NOT NULL RETURN n.id as id, labels(n) as labels ORDER BY n.id")
        with open("scratch/all_node_ids.txt", "w", encoding="utf-8") as f:
            for rec in result:
                f.write(f"{rec['id']} | {rec['labels']}\n")

dump_all_nodes()
driver.close()
print("Dumped all node IDs to scratch/all_node_ids.txt")
