from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def search():
    with driver.session() as session:
        print("--- Searching for EmilyWatson nodes (Hyperthyroidism / Methimazole / Propylthiouracil) ---")
        query = """
        MATCH (n)
        WHERE toLower(n.id) CONTAINS 'hyperthyroid'
           OR toLower(n.id) CONTAINS 'methimazole'
           OR toLower(n.id) CONTAINS 'propylthiouracil'
           OR toLower(n.id) CONTAINS 'pregnancy'
        RETURN n.id as id, labels(n) as labels
        """
        result = session.run(query)
        records = list(result)
        print("Emily matches found:", len(records))
        for r in records:
            print(r)

search()
driver.close()
