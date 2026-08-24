import logging
import os
from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings
from starlette.config import Config

from .enums import CacheBackend, LogFormat, LogLevel, TaskiqBrokerType

logger = logging.getLogger(__name__)

current_file_dir = os.path.dirname(os.path.realpath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, "..", "..", "..", ".."))

env_paths = [
    "/app/.env",
    os.path.join(project_root, ".env"),
    "/.env",
]

env_path = next((path for path in env_paths if os.path.isfile(path)), env_paths[0])
logger.info(f"Using environment file at: {env_path}")

config = Config(env_path)


class EnvironmentOption(StrEnum):
    """Environment options for the application."""

    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    LOCAL = "local"


class EnvironmentSettings(BaseSettings):
    """Environment-related settings."""

    ENVIRONMENT: EnvironmentOption = config("ENVIRONMENT", default=EnvironmentOption.DEVELOPMENT, cast=EnvironmentOption)


class DatabaseSettings(BaseSettings):
    """Database-related settings."""

    POSTGRES_USER: str = config("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="postgres")
    POSTGRES_SERVER: str = config("POSTGRES_SERVER", default="localhost")
    POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432)
    POSTGRES_DB: str = config("POSTGRES_DB", default="postgres")
    POSTGRES_SYNC_PREFIX: str = config("POSTGRES_SYNC_PREFIX", default="postgresql://")
    POSTGRES_ASYNC_PREFIX: str = config("POSTGRES_ASYNC_PREFIX", default="postgresql+asyncpg://")
    CREATE_TABLES_ON_STARTUP: bool = config("CREATE_TABLES_ON_STARTUP", default=True, cast=bool)

    POSTGRES_POOL_SIZE: int = config("POSTGRES_POOL_SIZE", default=20, cast=int)
    POSTGRES_MAX_OVERFLOW: int = config("POSTGRES_MAX_OVERFLOW", default=0, cast=int)
    POSTGRES_POOL_PRE_PING: bool = config("POSTGRES_POOL_PRE_PING", default=True, cast=bool)
    POSTGRES_POOL_RECYCLE: int = config("POSTGRES_POOL_RECYCLE", default=-1, cast=int)

    # A field rather than a lookup inside DATABASE_URL, so callers can tell an
    # explicit URL apart from one built out of the POSTGRES_* parts.
    DATABASE_URL_OVERRIDE: str | None = Field(
        default=config("DATABASE_URL", default=None),
        validation_alias="DATABASE_URL",
    )

    @property
    def DATABASE_URL(self) -> str:
        """Get the full database URL.

        Checks for DATABASE_URL environment variable first (production pattern),
        then falls back to constructing from individual components (development pattern).
        """
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE

        return (
            f"{self.POSTGRES_ASYNC_PREFIX}{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class CacheSettings(BaseSettings):
    """Cache-related settings.

    This class defines settings for cache connections and behavior across
    the application.

    Attributes:
        CACHE_ENABLED: Whether to enable caching. Default is True.
        CACHE_BACKEND: The cache backend to use. Default is "memcached".

        # Memcached settings
        CACHE_MEMCACHED_HOST: Memcached server hostname. Default is "localhost".
        CACHE_MEMCACHED_PORT: Memcached server port. Default is 11211.
        CACHE_MEMCACHED_POOL_SIZE: Maximum number of connections in the pool. Default is 10.
        CACHE_MEMCACHED_CONNECT_TIMEOUT: Connection timeout in seconds. Default is 5.
            Note: This is not currently used by aiomcache.Client but is
            kept for API consistency with other cache backends.

        # Redis settings
        CACHE_REDIS_HOST: Redis server hostname. Default is "localhost".
        CACHE_REDIS_PORT: Redis server port. Default is 6379.
        CACHE_REDIS_DB: Redis database number. Default is 0.
        CACHE_REDIS_PASSWORD: Redis server password. Default is None.
        CACHE_REDIS_CONNECT_TIMEOUT: Connection timeout in seconds. Default is 5.
        CACHE_REDIS_POOL_SIZE: Maximum number of connections in the pool. Default is 10.

        DEFAULT_CACHE_EXPIRATION: Default expiration time for cache entries in seconds.
            Default is 3600 (1 hour).
    """

    CACHE_ENABLED: bool = config("CACHE_ENABLED", default=True, cast=bool)
    CACHE_BACKEND: str = config("CACHE_BACKEND", default=CacheBackend.MEMCACHED.value)

    CACHE_MEMCACHED_HOST: str = config("CACHE_MEMCACHED_HOST", default="localhost")
    CACHE_MEMCACHED_PORT: int = config("CACHE_MEMCACHED_PORT", default=11211, cast=int)
    CACHE_MEMCACHED_POOL_SIZE: int = config("CACHE_MEMCACHED_POOL_SIZE", default=10, cast=int)
    CACHE_MEMCACHED_CONNECT_TIMEOUT: int = config("CACHE_MEMCACHED_CONNECT_TIMEOUT", default=5, cast=int)

    CACHE_REDIS_HOST: str = config("CACHE_REDIS_HOST", default="localhost")
    CACHE_REDIS_PORT: int = config("CACHE_REDIS_PORT", default=6379, cast=int)
    CACHE_REDIS_DB: int = config("CACHE_REDIS_DB", default=0, cast=int)
    CACHE_REDIS_PASSWORD: str | None = config("CACHE_REDIS_PASSWORD", default=None)
    CACHE_REDIS_CONNECT_TIMEOUT: int = config("CACHE_REDIS_CONNECT_TIMEOUT", default=5, cast=int)
    CACHE_REDIS_POOL_SIZE: int = config("CACHE_REDIS_POOL_SIZE", default=10, cast=int)

    DEFAULT_CACHE_EXPIRATION: int = config("DEFAULT_CACHE_EXPIRATION", default=3600, cast=int)

    CLIENT_CACHE_ENABLED: bool = config("CLIENT_CACHE_ENABLED", default=True, cast=bool)
    CLIENT_CACHE_MAX_AGE: int = config("CLIENT_CACHE_MAX_AGE", default=60, cast=int)


class CORSSettings(BaseSettings):
    """CORS-related settings."""

    CORS_ENABLED: bool = config("CORS_ENABLED", default=True, cast=bool)
    CORS_ORIGINS: str = config("CORS_ORIGINS", default="*")
    CORS_ALLOW_CREDENTIALS: bool = config("CORS_ALLOW_CREDENTIALS", default=True, cast=bool)

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        """Get CORS origins as a list."""
        if not self.CORS_ORIGINS:
            return ["*"]
        return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]

    CORS_ALLOW_METHODS: str = config("CORS_ALLOW_METHODS", default="*")
    CORS_ALLOW_HEADERS: str = config("CORS_ALLOW_HEADERS", default="*")


class CompressionSettings(BaseSettings):
    """Compression-related settings."""

    GZIP_ENABLED: bool = config("GZIP_ENABLED", default=True, cast=bool)
    GZIP_MINIMUM_SIZE: int = config("GZIP_MINIMUM_SIZE", default=1000, cast=int)


class APIDocSettings(BaseSettings):
    """API documentation settings."""

    ENABLE_DOCS_IN_PRODUCTION: bool = config("ENABLE_DOCS_IN_PRODUCTION", default=False, cast=bool)
    OPENAPI_PREFIX: str = config("OPENAPI_PREFIX", default="")
    DOCS_URL: str = config("DOCS_URL", default="/docs")
    REDOC_URL: str = config("REDOC_URL", default="/redoc")
    OPENAPI_URL: str = config("OPENAPI_URL", default="/openapi.json")

    API_TITLE: str = config("API_TITLE", default="")
    API_SUMMARY: str = config("API_SUMMARY", default="")
    API_DESCRIPTION: str = config("API_DESCRIPTION", default="")
    API_VERSION: str = config("API_VERSION", default="")
    API_TERMS_OF_SERVICE: str = config("API_TERMS_OF_SERVICE", default="")

    API_CONTACT_NAME: str = config("API_CONTACT_NAME", default="")
    API_CONTACT_URL: str = config("API_CONTACT_URL", default="")
    API_CONTACT_EMAIL: str = config("API_CONTACT_EMAIL", default="")

    API_LICENSE_NAME: str = config("API_LICENSE_NAME", default="")
    API_LICENSE_URL: str = config("API_LICENSE_URL", default="")
    API_LICENSE_IDENTIFIER: str = config("API_LICENSE_IDENTIFIER", default="")

    API_TAGS_METADATA: str = config("API_TAGS_METADATA", default="[]")


class APISettings(BaseSettings):
    """API-related settings."""

    API_PREFIX: str = "/api"


class AppSettings(BaseSettings):
    """Application-related settings."""

    # Note: For API documentation, prefer using API_* fields in APIDocSettings
    APP_NAME: str = config("APP_NAME", default="GTM Waterfall Enrichment")
    APP_DESCRIPTION: str = config("APP_DESCRIPTION", default="Self-hosted lead enrichment waterfall + CRM sync engine")
    DEBUG: bool = config("DEBUG", default=False, cast=bool)
    VERSION: str = config("VERSION", default="0.1.0")
    CONTACT_NAME: str = config("CONTACT_NAME", default="Support")
    CONTACT_EMAIL: str = config("CONTACT_EMAIL", default="support@example.com")
    LICENSE_NAME: str = config("LICENSE_NAME", default="MIT")


class SecuritySettings(BaseSettings):
    """Security settings."""

    SECURITY_HEADERS_ENABLED: bool = config("SECURITY_HEADERS_ENABLED", default=True, cast=bool)


class ProviderSettings(BaseSettings):
    """Enrichment provider credentials.

    Each key defaults to None. A provider client checks its own key at call time:
    if unset, it runs in mock mode and returns fake data instead of calling the
    live API, so the waterfall is testable end-to-end before any keys exist.
    """

    HUNTER_API_KEY: str | None = config("HUNTER_API_KEY", default=None)
    APOLLO_API_KEY: str | None = config("APOLLO_API_KEY", default=None)


class CRMSettings(BaseSettings):
    """CRM sync credentials.

    Same mock-mode pattern as ProviderSettings: unset means the CRM client
    returns a fake external id instead of calling the live API.
    """

    HUBSPOT_PRIVATE_APP_TOKEN: str | None = config("HUBSPOT_PRIVATE_APP_TOKEN", default=None)


class LoggingSettings(BaseSettings):
    """Centralized logging configuration settings."""

    LOG_LEVEL: str = config("LOG_LEVEL", default=LogLevel.INFO.value)
    LOG_FORMAT: str = config("LOG_FORMAT", default=LogFormat.STRUCTURED.value)

    LOG_CONSOLE_ENABLED: bool = config("LOG_CONSOLE_ENABLED", default=True, cast=bool)
    LOG_FILE_ENABLED: bool = config("LOG_FILE_ENABLED", default=False, cast=bool)
    LOG_FILE_PATH: str = config("LOG_FILE_PATH", default="logs/app.log")
    LOG_FILE_MAX_SIZE: int = config("LOG_FILE_MAX_SIZE", default=10485760, cast=int)
    LOG_FILE_BACKUP_COUNT: int = config("LOG_FILE_BACKUP_COUNT", default=5, cast=int)

    LOG_CORRELATION_ID: bool = config("LOG_CORRELATION_ID", default=True, cast=bool)
    LOG_STRUCTURED_CONTEXT: bool = config("LOG_STRUCTURED_CONTEXT", default=True, cast=bool)
    LOG_PERFORMANCE_METRICS: bool = config("LOG_PERFORMANCE_METRICS", default=False, cast=bool)

    LOG_SQL_QUERIES: bool = config("LOG_SQL_QUERIES", default=False, cast=bool)
    LOG_INCLUDE_STACKTRACE: bool = config("LOG_INCLUDE_STACKTRACE", default=True, cast=bool)

    LOG_DEVELOPMENT_VERBOSE: bool = config("LOG_DEVELOPMENT_VERBOSE", default=True, cast=bool)
    LOG_PRODUCTION_OPTIMIZE: bool = config("LOG_PRODUCTION_OPTIMIZE", default=True, cast=bool)

    @property
    def LOG_LEVEL_INT(self) -> int:
        """Convert string log level to integer."""
        level_map = {
            LogLevel.DEBUG.value: logging.DEBUG,
            LogLevel.INFO.value: logging.INFO,
            LogLevel.WARNING.value: logging.WARNING,
            LogLevel.ERROR.value: logging.ERROR,
            LogLevel.CRITICAL.value: logging.CRITICAL,
        }
        return level_map.get(self.LOG_LEVEL.upper(), logging.INFO)


class TaskiqSettings(BaseSettings):
    """Taskiq async task queue settings."""

    TASKIQ_ENABLED: bool = config("TASKIQ_ENABLED", default=True, cast=bool)
    TASKIQ_BROKER_TYPE: str = config("TASKIQ_BROKER_TYPE", default=TaskiqBrokerType.REDIS.value)

    TASKIQ_REDIS_HOST: str = config("TASKIQ_REDIS_HOST", default="localhost")
    TASKIQ_REDIS_PORT: int = config("TASKIQ_REDIS_PORT", default=6379, cast=int)
    TASKIQ_REDIS_DB: int = config("TASKIQ_REDIS_DB", default=3, cast=int)
    TASKIQ_REDIS_PASSWORD: str | None = config("TASKIQ_REDIS_PASSWORD", default=None)

    TASKIQ_RABBITMQ_HOST: str = config("TASKIQ_RABBITMQ_HOST", default="localhost")
    TASKIQ_RABBITMQ_PORT: int = config("TASKIQ_RABBITMQ_PORT", default=5672, cast=int)
    TASKIQ_RABBITMQ_USER: str = config("TASKIQ_RABBITMQ_USER", default="guest")
    TASKIQ_RABBITMQ_PASSWORD: str = config("TASKIQ_RABBITMQ_PASSWORD", default="guest")
    TASKIQ_RABBITMQ_VHOST: str = config("TASKIQ_RABBITMQ_VHOST", default="/")

    TASKIQ_WORKER_CONCURRENCY: int = config("TASKIQ_WORKER_CONCURRENCY", default=2, cast=int)
    TASKIQ_MAX_TASKS_PER_WORKER: int = config("TASKIQ_MAX_TASKS_PER_WORKER", default=1000, cast=int)

    @property
    def TASKIQ_BROKER_URL(self) -> str:
        """Generate broker URL based on configured backend."""
        if self.TASKIQ_BROKER_TYPE == TaskiqBrokerType.REDIS.value:
            password_part = f":{self.TASKIQ_REDIS_PASSWORD}@" if self.TASKIQ_REDIS_PASSWORD else ""
            return f"redis://{password_part}{self.TASKIQ_REDIS_HOST}:{self.TASKIQ_REDIS_PORT}/{self.TASKIQ_REDIS_DB}"
        elif self.TASKIQ_BROKER_TYPE == TaskiqBrokerType.RABBITMQ.value:
            vhost = self.TASKIQ_RABBITMQ_VHOST
            if vhost.startswith("/"):
                vhost = vhost[1:]
            return f"amqp://{self.TASKIQ_RABBITMQ_USER}:{self.TASKIQ_RABBITMQ_PASSWORD}@{self.TASKIQ_RABBITMQ_HOST}:{self.TASKIQ_RABBITMQ_PORT}/{vhost}"
        else:
            raise ValueError(f"Unsupported broker type: {self.TASKIQ_BROKER_TYPE}")


class Settings(
    EnvironmentSettings,
    DatabaseSettings,
    CacheSettings,
    CORSSettings,
    CompressionSettings,
    APIDocSettings,
    APISettings,
    AppSettings,
    SecuritySettings,
    ProviderSettings,
    CRMSettings,
    LoggingSettings,
    TaskiqSettings,
):
    """Main settings class that combines all setting categories."""

    pass


settings = Settings()


def get_settings() -> Settings:
    """Get application settings.

    Returns:
        The application settings.
    """
    return settings
