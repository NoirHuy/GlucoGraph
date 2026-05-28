import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Cấu hình Neo4j
    NEO4J_URI: str = "bolt://cdss_graph:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # --- THÊM DÒNG NÀY ĐỂ HỨNG KEY TỪ DOCKER ---
    GROQ_API_KEY: str = "" 
    # -------------------------------------------

    class Config:
        env_file = ".env"

settings = Settings()