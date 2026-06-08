from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def search():
    with driver.session() as session:
        print("--- Searching for Robert nodes ---")
        query = """
        MATCH (n)
        WHERE toLower(n.id) CONTAINS 'diabetes mellitus'
           OR toLower(n.id) CONTAINS 'metformin'
           OR toLower(n.id) CONTAINS 'kidney disease'
           OR toLower(n.id) CONTAINS 'lactic'
        RETURN n.id as id, labels(n) as labels
        """
        result = session.run(query)
        records = list(result)
        print("Robert matches found:", len(records))
        for r in records:
            print(r)

search()
driver.close()
