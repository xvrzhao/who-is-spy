from logging import getLogger
from enum import Enum

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = getLogger(__name__)

class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    ENV: Environment = Environment.DEVELOPMENT
    APP_NAME: str = "who-is-spy"

    ALLOW_ORIGINS: list[str] = []

    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_DB: str = "who_is_spy"
    PG_USER: str = "postgres"
    PG_PSW: SecretStr = SecretStr("postgres")
    PG_CONN_MAX: int = 10

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PSW: str = ""

    # 说明：游戏侧配置（LLM_API_KEY / MINIMAX_API_KEY / MINIMAX_TTS_MODEL）由 src/game 的
    # load_dotenv()+getenv 直接读取同一个 .env，Settings 的 extra="ignore" 会跳过它们，
    # 保持 src/game 对服务器基础设施零依赖（CLI 可脱离 FastAPI/PG 独立运行）

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENV == Environment.PRODUCTION

    @property
    def postgres_uri(self) -> str:
        return f"postgresql://{self.PG_USER}:{self.PG_PSW.get_secret_value()}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}?sslmode=disable"

    @property
    def postgres_async_uri(self) -> str:
        return f"postgresql+psycopg://{self.PG_USER}:{self.PG_PSW.get_secret_value()}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"


settings = Settings()
