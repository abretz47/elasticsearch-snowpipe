"""
Snowflake client for streaming data using Snowpipe.
"""
import logging
import json
from typing import List, Dict, Any
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import snowflake.connector
from config import SnowflakeConfig


logger = logging.getLogger(__name__)


class SnowflakeClient:
    """Client for connecting to Snowflake and streaming data."""
    
    def __init__(self, config: SnowflakeConfig):
        """
        Initialize Snowflake client.
        
        Args:
            config: Snowflake configuration
        """
        self.config = config
        self.connection = None
        
    def _load_private_key(self) -> bytes:
        """Load private key for authentication."""
        if not self.config.private_key_path:
            return None
        
        with open(self.config.private_key_path, 'rb') as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(),
                password=self.config.private_key_passphrase.encode() if self.config.private_key_passphrase else None,
                backend=default_backend()
            )
        
        return p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def connect(self) -> None:
        """Establish connection to Snowflake."""
        conn_params = {
            'account': self.config.account,
            'user': self.config.user,
            'database': self.config.database,
            'schema': self.config.schema,
            'warehouse': self.config.warehouse,
        }
        
        if self.config.role:
            conn_params['role'] = self.config.role
        
        # Authentication
        if self.config.private_key_path:
            conn_params['private_key'] = self._load_private_key()
        elif self.config.password:
            conn_params['password'] = self.config.password
        else:
            raise ValueError("Either password or private_key_path must be provided")
        
        try:
            self.connection = snowflake.connector.connect(**conn_params)
            logger.info(f"Connected to Snowflake account: {self.config.account}")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close Snowflake connection."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Snowflake")
    
    def create_table_if_not_exists(self, table_name: str, mapping: Dict[str, Any]) -> None:
        """
        Create table in Snowflake if it doesn't exist.
        
        Args:
            table_name: Name of the table
            mapping: Elasticsearch index mapping
        """
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake")
        
        # Create a simple schema with common fields
        # Store the full document as JSON in a VARIANT column for flexibility
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id VARCHAR(256) PRIMARY KEY,
            index_name VARCHAR(256),
            document VARIANT,
            ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_sql)
            cursor.close()
            logger.info(f"Ensured table '{table_name}' exists")
        except Exception as e:
            logger.error(f"Error creating table '{table_name}': {e}")
            raise
    
    def insert_batch(self, table_name: str, documents: List[Dict[str, Any]]) -> int:
        """
        Insert a batch of documents into Snowflake.
        
        Args:
            table_name: Name of the table
            documents: List of documents to insert
            
        Returns:
            Number of rows inserted
        """
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake")
        
        if not documents:
            return 0
        
        try:
            cursor = self.connection.cursor()
            
            # Prepare data for insertion
            values = []
            for doc in documents:
                doc_id = doc.get('_id')
                index_name = doc.get('_index')
                source = doc.get('_source', {})
                
                # Convert source to JSON string
                source_json = json.dumps(source)
                values.append((doc_id, index_name, source_json))
            
            # Insert using parameterized query to prevent SQL injection
            insert_sql = f"""
            INSERT INTO {table_name} (id, index_name, document)
            VALUES (%s, %s, PARSE_JSON(%s))
            """
            
            cursor.executemany(insert_sql, values)
            rows_inserted = cursor.rowcount
            cursor.close()
            
            logger.info(f"Inserted {rows_inserted} rows into '{table_name}'")
            return rows_inserted
            
        except Exception as e:
            logger.error(f"Error inserting batch into '{table_name}': {e}")
            raise
    
    def merge_batch(self, table_name: str, documents: List[Dict[str, Any]]) -> int:
        """
        Merge (upsert) a batch of documents into Snowflake.
        
        Args:
            table_name: Name of the table
            documents: List of documents to merge
            
        Returns:
            Number of rows affected
        """
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake")
        
        if not documents:
            return 0
        
        try:
            cursor = self.connection.cursor()
            
            # Create temporary table
            temp_table = f"{table_name}_temp"
            cursor.execute(f"""
            CREATE TEMPORARY TABLE {temp_table} (
                id VARCHAR(256),
                index_name VARCHAR(256),
                document VARIANT
            )
            """)
            
            # Insert into temp table
            values = []
            for doc in documents:
                doc_id = doc.get('_id')
                index_name = doc.get('_index')
                source = doc.get('_source', {})
                source_json = json.dumps(source)
                values.append((doc_id, index_name, source_json))
            
            cursor.executemany(
                f"INSERT INTO {temp_table} (id, index_name, document) VALUES (%s, %s, PARSE_JSON(%s))",
                values
            )
            
            # Merge from temp table to target table
            merge_sql = f"""
            MERGE INTO {table_name} target
            USING {temp_table} source
            ON target.id = source.id
            WHEN MATCHED THEN
                UPDATE SET
                    target.document = source.document,
                    target.ingested_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
                INSERT (id, index_name, document)
                VALUES (source.id, source.index_name, source.document)
            """
            
            cursor.execute(merge_sql)
            rows_affected = cursor.rowcount
            
            # Clean up
            cursor.execute(f"DROP TABLE {temp_table}")
            cursor.close()
            
            logger.info(f"Merged {rows_affected} rows into '{table_name}'")
            return rows_affected
            
        except Exception as e:
            logger.error(f"Error merging batch into '{table_name}': {e}")
            raise
    
    def get_table_name(self, index_name: str) -> str:
        """
        Get Snowflake table name for an Elasticsearch index.
        
        Args:
            index_name: Elasticsearch index name
            
        Returns:
            Snowflake table name
        """
        # Replace hyphens and dots with underscores for valid table names
        clean_name = index_name.replace('-', '_').replace('.', '_')
        return f"{self.config.table_prefix}{clean_name}"
