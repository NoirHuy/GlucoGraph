from neo4j import GraphDatabase
import os

# Neo4j connection details
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def verify_triples():
    with driver.session() as session:
        print("Checking node Gout...")
        result = session.run("MATCH (n) WHERE n.id = 'Gout' RETURN n, labels(n) as labels")
        record = result.single()
        if record:
            print(f"Found node Gout: {record['n']} with labels {record['labels']}")
        else:
            print("Node Gout NOT found!")

        print("\nChecking node Colchicine...")
        result = session.run("MATCH (n) WHERE n.id = 'Colchicine' RETURN n, labels(n) as labels")
        record = result.single()
        if record:
            print(f"Found node Colchicine: {record['n']} with labels {record['labels']}")
        else:
            print("Node Colchicine NOT found!")

        print("\nChecking connections between Gout and Colchicine...")
        result = session.run("MATCH (a {id: 'Gout'})-[r]-(b {id: 'Colchicine'}) RETURN type(r) as rel_type, startNode(r).id as start, endNode(r).id as end")
        records = list(result)
        if records:
            for rec in records:
                print(f"Relationship: ({rec['start']})-[:{rec['rel_type']}]->({rec['end']})")
        else:
            print("No relationships found between Gout and Colchicine!")

        print("\nChecking relationships connected to Gout of type HAS_FINDING or related to symptoms...")
        result = session.run("MATCH (a {id: 'Gout'})-[r]-(b) RETURN labels(b)[0] as b_type, type(r) as rel_type, b.id as b_id")
        records = list(result)
        if records:
            print("Found Gout relationships:")
            for rec in records:
                print(f"- ({rec['b_id']} : {rec['b_type']}) -[:{rec['rel_type']}]- (Gout)")
        else:
            print("No relationships connected to Gout found!")

verify_triples()
driver.close()
