import time
from neo4j import GraphDatabase
from app.config import settings

# Biến toàn cục lưu kết nối
_driver = None

def get_db_driver():
    """
    Tạo hoặc lấy kết nối tới Neo4j với cơ chế tự động thử lại (retry) và phát hiện kết nối chết (stale connection).
    """
    global _driver
    
    # 1. Nếu đã có driver, kiểm tra xem kết nối còn sống không
    if _driver is not None:
        try:
            _driver.verify_connectivity()
        except Exception as e:
            print(f"[Neo4j] Ket noi Neo4j hien tai bi mat: {e}. Dang thu ket noi lai...")
            try:
                _driver.close()
            except Exception:
                pass
            _driver = None

    # 2. Nếu chưa có driver hoặc kết nối cũ đã bị hủy, tiến hành tạo mới với cơ chế retry
    if _driver is None:
        retries = 6
        delay = 2.0
        for i in range(retries):
            try:
                driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                driver.verify_connectivity()
                _driver = driver
                print("[Neo4j] Da ket noi thanh cong toi Neo4j!")
                break
            except Exception as e:
                print(f"[Neo4j] Thu ket noi toi Neo4j lan {i+1}/{retries} that bai: {e}")
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    print("[Neo4j] Khong the ket noi toi Neo4j sau nhieu lan thu.")
                    _driver = None
                    
    return _driver

def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None