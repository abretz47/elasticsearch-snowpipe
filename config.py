"""
Configuration management for Elasticsearch-Snowpipe application.
"""
import os
import yaml
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ElasticsearchConfig:
    """Configuration for Elasticsearch connection."""
    host: str
    port: int = 9200
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = True
    verify_certs: bool = True
    ca_certs: Optional[str] = None
    api_key: Optional[str] = None
    indexes: List[str] = None  # List of index patterns to sync
    
    def __post_init__(self):
        if self.indexes is None:
            self.indexes = ["*"]


@dataclass
class SnowflakeConfig:
    """Configuration for Snowflake connection."""
    account: str
    user: str
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    database: str = "ES_DATA"
    schema: str = "PUBLIC"
    warehouse: str = "COMPUTE_WH"
    role: Optional[str] = None
    table_prefix: str = "es_"


@dataclass
class AppConfig:
    """Main application configuration."""
    elasticsearch: ElasticsearchConfig
    snowflake: SnowflakeConfig
    batch_size: int = 1000
    sync_interval: int = 300  # seconds
    log_level: str = "INFO"


def load_config_from_env() -> AppConfig:
    """
    Load configuration from environment variables.
    """
    # Elasticsearch config
    es_indexes = os.getenv("ES_INDEXES", "*").split(",")
    es_config = ElasticsearchConfig(
        host=os.getenv("ES_HOST", "localhost"),
        port=int(os.getenv("ES_PORT", "9200")),
        username=os.getenv("ES_USERNAME"),
        password=os.getenv("ES_PASSWORD"),
        use_ssl=os.getenv("ES_USE_SSL", "true").lower() == "true",
        verify_certs=os.getenv("ES_VERIFY_CERTS", "true").lower() == "true",
        ca_certs=os.getenv("ES_CA_CERTS"),
        api_key=os.getenv("ES_API_KEY"),
        indexes=[idx.strip() for idx in es_indexes]
    )
    
    # Snowflake config
    sf_config = SnowflakeConfig(
        account=os.getenv("SF_ACCOUNT", ""),
        user=os.getenv("SF_USER", ""),
        password=os.getenv("SF_PASSWORD"),
        private_key_path=os.getenv("SF_PRIVATE_KEY_PATH"),
        private_key_passphrase=os.getenv("SF_PRIVATE_KEY_PASSPHRASE"),
        database=os.getenv("SF_DATABASE", "ES_DATA"),
        schema=os.getenv("SF_SCHEMA", "PUBLIC"),
        warehouse=os.getenv("SF_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SF_ROLE"),
        table_prefix=os.getenv("SF_TABLE_PREFIX", "es_")
    )
    
    # App config
    app_config = AppConfig(
        elasticsearch=es_config,
        snowflake=sf_config,
        batch_size=int(os.getenv("BATCH_SIZE", "1000")),
        sync_interval=int(os.getenv("SYNC_INTERVAL", "300")),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    return app_config


def load_config_from_file(file_path: str) -> AppConfig:
    """
    Load configuration from YAML file.
    """
    with open(file_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    es_dict = config_dict.get('elasticsearch', {})
    es_config = ElasticsearchConfig(
        host=es_dict.get('host', 'localhost'),
        port=es_dict.get('port', 9200),
        username=es_dict.get('username'),
        password=es_dict.get('password'),
        use_ssl=es_dict.get('use_ssl', True),
        verify_certs=es_dict.get('verify_certs', True),
        ca_certs=es_dict.get('ca_certs'),
        api_key=es_dict.get('api_key'),
        indexes=es_dict.get('indexes', ['*'])
    )
    
    sf_dict = config_dict.get('snowflake', {})
    sf_config = SnowflakeConfig(
        account=sf_dict.get('account', ''),
        user=sf_dict.get('user', ''),
        password=sf_dict.get('password'),
        private_key_path=sf_dict.get('private_key_path'),
        private_key_passphrase=sf_dict.get('private_key_passphrase'),
        database=sf_dict.get('database', 'ES_DATA'),
        schema=sf_dict.get('schema', 'PUBLIC'),
        warehouse=sf_dict.get('warehouse', 'COMPUTE_WH'),
        role=sf_dict.get('role'),
        table_prefix=sf_dict.get('table_prefix', 'es_')
    )
    
    app_config = AppConfig(
        elasticsearch=es_config,
        snowflake=sf_config,
        batch_size=config_dict.get('batch_size', 1000),
        sync_interval=config_dict.get('sync_interval', 300),
        log_level=config_dict.get('log_level', 'INFO')
    )
    
    return app_config


def load_config(config_file: Optional[str] = None) -> AppConfig:
    """
    Load configuration from file if provided, otherwise from environment variables.
    """
    if config_file and os.path.exists(config_file):
        return load_config_from_file(config_file)
    else:
        return load_config_from_env()
