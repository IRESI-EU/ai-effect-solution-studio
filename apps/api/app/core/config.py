from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://solution_studio:solution_studio@postgres:5432/solution_studio"
    orchestrator_base_url: str = "http://host.docker.internal:18000"
    


settings = Settings()