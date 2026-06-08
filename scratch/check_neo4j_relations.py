import os
import sys

# Reconfigure encoding to avoid UnicodeEncodeError on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import get_db_driver

def check():
    driver = get_db_driver()
    if not driver:
        print("❌ Could not connect to Neo4j database.")
        return

    print("=== SEARCHING NODES IN NEO4J ===")
    with driver.session() as session:
        # Search for Exercise and Glucose related nodes
        query_nodes = """
        MATCH (n)
        WHERE toLower(n.id) CONTAINS 'exercise' 
           OR toLower(n.id) CONTAINS 'glucose'
           OR toLower(n.id) CONTAINS 'plasma'
           OR (n.aliases IS NOT NULL AND any(a in n.aliases WHERE toLower(a) CONTAINS 'exercise' OR toLower(a) CONTAINS 'glucose'))
        RETURN n.id AS id, labels(n) AS labels, n.aliases AS aliases
        """
        results = session.run(query_nodes)
        found_any = False
        for r in results:
            found_any = True
            print(f"Node: {r['id']} | Labels: {r['labels']} | Aliases: {r['aliases']}")
        if not found_any:
            print("No matching nodes found.")

        print("\n=== SEARCHING TRIPLES IN NEO4J ===")
        # Search for any relations involving 'exercise' or 'glucose'
        query_triples = """
        MATCH (s)-[r]->(o)
        WHERE (toLower(s.id) CONTAINS 'exercise' AND toLower(o.id) CONTAINS 'glucose')
           OR (toLower(s.id) CONTAINS 'glucose' AND toLower(o.id) CONTAINS 'exercise')
        RETURN s.id AS subject, labels(s) AS s_labels, type(r) AS relation, o.id AS object, labels(o) AS o_labels
        """
        results = session.run(query_triples)
        found_any = False
        for r in results:
            found_any = True
            print(f"Triple: [{r['subject']} ({r['s_labels']})] -[{r['relation']}]-> [{r['object']} ({r['o_labels']})]")
        if not found_any:
            print("No matching relations between 'exercise' and 'glucose' found.")

        print("\n=== SEARCHING GENERAL RELATIONS FOR 'EXERCISE' ===")
        query_exercise_rels = """
        MATCH (s)-[r]->(o)
        WHERE toLower(s.id) CONTAINS 'exercise' OR toLower(o.id) CONTAINS 'exercise'
        RETURN s.id AS subject, type(r) AS relation, o.id AS object
        LIMIT 20
        """
        results = session.run(query_exercise_rels)
        for r in results:
            print(f"  [{r['subject']}] -[{r['relation']}]-> [{r['object']}]")

if __name__ == "__main__":
    check()
