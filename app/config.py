from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    app_env: str = "development"
    log_level: str = "info"
    # MCP 服务的 resource 标识（RFC 8707 Resource Indicators）。
    # 必须与 blunt-serv 侧的 app.core.config.Settings.MCP_RESOURCE_URI 完全一致：
    # 该值同时作为 PRM 元数据的 resource 字段和 JWT 的 aud 声明目标值。
    mcp_resource: str = "https://incremental.icu/mcp"


settings = Settings()
