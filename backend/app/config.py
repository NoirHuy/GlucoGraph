import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Resolve the absolute path to .env in the parent root directory
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(env_path)

class Settings(BaseSettings):
    # Cấu hình Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # --- THÊM DÒNG NÀY ĐỂ HỨNG KEY TỪ DOCKER ---
    GROQ_API_KEY: str = "" 
    # -------------------------------------------

    class Config:
        env_file = env_path
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        if os.getenv("NEO4J_USERNAME"):
            self.NEO4J_USER = os.getenv("NEO4J_USERNAME")

settings = Settings()