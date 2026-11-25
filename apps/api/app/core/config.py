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
    # Saved run outputs (see services/run_snapshots.py)
    run_snapshot_max_bytes: int = 1_048_576  # larger outputs are saved trimmed
    run_snapshot_retention_days: int = 90  # 0 keeps saved outputs forever
    # Design with AI (see app/design_ai). Provider "openai" works with any
    # OpenAI-compatible endpoint (OpenAI, Azure-compatible gateways, or a local
    # small model served by Ollama/vLLM via design_ai_base_url).
    design_ai_enabled: bool = False
    design_ai_provider: str = "offline"  # "openai" or "offline"
    design_ai_base_url: str = "https://api.openai.com/v1"
    design_ai_api_key: str = ""
    design_ai_model: str = "gpt-4.1-mini"
    design_ai_timeout_seconds: int = 60
    design_ai_daily_requests_per_user: int = 40


settings = Settings()
