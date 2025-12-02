from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # ignore any env vars we didn't define here
    )

    # ---------- Azure / Entra / Microsoft Graph ----------
    TENANT_ID: str | None = None
    CLIENT_ID: str | None = None
    CLIENT_SECRET: str | None = None
    GRAPH_SCOPE: str = "https://graph.microsoft.com/.default"

    # ---------- LLM Provider selection ----------
    # Options: "llama" or "gemini"
    LLM_PROVIDER: str = "llama"

    # ---------- Llama config ----------
    LLAMA_API_KEY: str | None = None
    LLAMA_API_BASE_URL: str | None = None
    LLAMA_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"

    # ---------- Gemini config ----------
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_API_BASE_URL: str | None = None  # optional

    # ---------- Vector DB (Chroma) ----------
    VECTOR_DB_DIR: str = "./chroma_db"   # default folder on disk

settings = Settings()
