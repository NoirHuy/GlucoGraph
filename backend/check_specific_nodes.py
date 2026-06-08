from app.database import get_db_driver

def check():
    driver = get_db_driver()
    if not driver:
        print("Could not connect to Neo4j database.")
        return

    terms = ["polydipsia", "polyuria", "nocturia", "fasting", "glucose"]
    q = """
    MATCH (n)
    WHERE any(term in $terms WHERE toLower(n.id) CONTAINS term)
    RETURN n.id AS node, labels(n) AS labels
    """
    with driver.session() as session:
        results = session.run(q, terms=terms)
        for r in results:
            print(f"  {r['node']} ({r['labels']})")

if __name__ == "__main__":
    check()
