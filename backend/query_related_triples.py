from app.database import get_db_driver

def check():
    driver = get_db_driver()
    if not driver:
        return
    
    query = """
    MATCH (s)-[r]->(o)
    WHERE toLower(s.id) IN ['pregnancy', 'hyperglycemia', 'donislecel'] 
       OR toLower(o.id) IN ['pregnancy', 'hyperglycemia', 'donislecel']
    RETURN s.id AS s, type(r) AS r, o.id AS o
    """
    with driver.session() as session:
        res = session.run(query)
        for row in res:
            print(f"  {row['s']} -[{row['r']}]-> {row['o']}")

if __name__ == "__main__":
    check()
