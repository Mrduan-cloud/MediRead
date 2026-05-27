"""全局配置 — 12-Factor 风格，通过 .env / 环境变量加载。"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # ============ App ============
    app_name: str = "MediRead"
    app_env: str = Field("dev", description="dev / staging / prod")
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: list[str] = ["*"]

    # ============ Security ============
    jwt_secret_key: str = "change-me-in-prod-please"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24

    # ============ LLM (Ollama 私有化 — GLM-4-9B-Chat GGUF Q4_K_M) ============
    # 默认：单卡 RTX 4090 24G + Ollama backend (llama.cpp)
    # Q4_K_M 比 Q4_0 精度高，体检数据解读优先用 K_M
    llm_base_url: str = "http://ollama:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "glm4:9b-chat-q4_k_m"
    llm_timeout: int = 90
    llm_max_retries: int = 3
    llm_temperature: float = 0.2

    # ============ Embedding & Reranker ============
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    reranker_model: str = "BAAI/bge-reranker-large"
    embedding_dim: int = 1024
    model_cache_dir: str = "/app/.cache/models"

    # ============ PaddleOCR ============
    ocr_use_gpu: bool = False
    ocr_lang: str = "ch"
    ocr_det_model_dir: str = ""        # 留空走自动下载
    ocr_rec_model_dir: str = ""
    ocr_cls_model_dir: str = ""

    # ============ Milvus ============
    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_user: str = ""
    milvus_password: str = ""
    milvus_collection_medical: str = "medical_kb"

    # ============ MySQL ============
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "mediread"
    mysql_password: str = "changeme"
    mysql_db: str = "mediread"

    @property
    def mysql_dsn(self) -> str:
        return (
            f"mysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )

    # ============ Redis ============
    redis_url: str = "redis://redis:6379/0"

    # ============ MinIO ============
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "mediread"
    minio_secure: bool = False

    # ============ Upload limits ============
    upload_max_bytes: int = 20 * 1024 * 1024  # 20 MB
    upload_allowed_ext: list[str] = ["jpg", "jpeg", "png", "pdf"]

    # ============ Observability ============
    metrics_enabled: bool = True
    metrics_path: str = "/metrics"
    sentry_dsn: str = ""

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
