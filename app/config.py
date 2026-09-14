"""全局配置：从环境变量 / .env 读取（对应 BACKEND_SPEC §6.2，Key 严禁硬编码进库）"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 数据库（OceanBase MySQL 租户模式）
    db_host: str = "localhost"
    db_port: int = 2881
    db_user: str = "root@test"
    db_password: str = ""
    db_name: str = "wealth_copilot"

    # DeepSeek 大模型（§6.2）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    llm_timeout_s: float = 30.0


settings = Settings()
