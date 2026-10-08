from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://solution_studio:solution_studio@postgres:5432/solution_studio"
    orchestrator_base_url: str = "http://host.docker.internal:18000"
    orchestrator_api_key: str = ""
    session_cookie_name: str = "ai_effect_session"
    session_hours: int = 12
    secure_cookies: bool = False
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "Platform Administrator"
    service_contract_path: str = "/service-contracts"


settings = Settings()
