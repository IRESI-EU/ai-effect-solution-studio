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
    design_ai_enabled: bool = False
    # Explicitly shared, operator-selected templates; never inferred by an LLM.
    design_ai_templates: str = "{}"
    openai_api_key: str = ""
    design_ai_model: str = ""
    design_ai_reasoning_effort: str = ""
    design_ai_max_output_tokens: int = 3000
    # Opt-in local acceptance ledger; never enabled in production by default.
    design_ai_acceptance_budget_file: str = ""
    design_ai_timeout_seconds: int = 40
    design_ai_context_chars: int = 48000
    design_ai_tool_limit: int = 8


settings = Settings()
