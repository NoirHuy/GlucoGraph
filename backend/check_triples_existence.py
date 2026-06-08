import json
from app.database import get_db_driver

def check():
    driver = get_db_driver()
    if not driver:
        print("No DB connection")
        return
    
    # We want to check if these specific triples exist in Neo4j:
    triples_to_check = [
        ("pregnancy", "INCREASES_RISK_OF", "Hyperglycemia"),
        ("Hypoglycemia", "HAS_FINDING", "Palpitations"),
        ("Hypoglycemia", "TREATED_BY", "glucagon"),
        ("Hyperglycemia", "TREATED_BY", "donislecel"),
    ]
    
    query = """
    MATCH (s)-[r]->(o)
    WHERE toLower(s.id) = toLower($subj) 
      AND toLower(o.id) = toLower($obj) 
      AND toLower(type(r)) = toLower($rel)
    RETURN s.id AS s, type(r) AS r, o.id AS o
    """
    
    with driver.session() as session:
        for s, r, o in triples_to_check:
            res = list(session.run(query, subj=s, rel=r, obj=o))
            if res:
                print(f"✅ EXIST: {res[0]['s']} -[{res[0]['r']}]-> {res[0]['o']}")
            else:
                print(f"❌ NOT EXIST: {s} -[{r}]-> {o}")

if __name__ == "__main__":
    check()
