from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def search():
    with driver.session() as session:
        print("--- Searching id and aliases properties ---")
        query = """
        MATCH (n)
        WHERE toLower(n.id) CONTAINS 'gout'
           OR (n.aliases IS NOT NULL AND any(a in n.aliases WHERE toLower(a) CONTAINS 'gout'))
        RETURN n.id as id, labels(n) as labels, n.aliases as aliases
        """
        result = session.run(query)
        records = list(result)
        print("Gout matches found:", len(records))
        for r in records:
            print(r)

        query_colchicine = """
        MATCH (n)
        WHERE toLower(n.id) CONTAINS 'colchicine'
           OR (n.aliases IS NOT NULL AND any(a in n.aliases WHERE toLower(a) CONTAINS 'colchicine'))
        RETURN n.id as id, labels(n) as labels, n.aliases as aliases
        """
        result = session.run(query_colchicine)
        records = list(result)
        print("\nColchicine matches found:", len(records))
        for r in records:
            print(r)

search()
driver.close()
