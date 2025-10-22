#!/usr/bin/env python3
"""
Elasticsearch-Snowpipe Streaming Application

This application reads data from Elasticsearch indexes and streams them
to Snowflake using Snowpipe streaming API.
"""
import logging
import sys
import time
import argparse
from typing import Optional, Dict
from dotenv import load_dotenv

from config import load_config, AppConfig
from elasticsearch_client import ElasticsearchClient
from snowflake_client import SnowflakeClient


# Set up logging
def setup_logging(log_level: str) -> None:
    """Configure logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


logger = logging.getLogger(__name__)


class ElasticsearchSnowpipeApp:
    """Main application for syncing Elasticsearch to Snowflake."""
    
    def __init__(self, config: AppConfig):
        """
        Initialize the application.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.es_client = ElasticsearchClient(config.elasticsearch)
        self.sf_client = SnowflakeClient(config.snowflake)
        self.running = False
    
    def connect(self) -> None:
        """Connect to Elasticsearch and Snowflake."""
        logger.info("Connecting to Elasticsearch...")
        self.es_client.connect()
        
        logger.info("Connecting to Snowflake...")
        self.sf_client.connect()
    
    def disconnect(self) -> None:
        """Disconnect from Elasticsearch and Snowflake."""
        logger.info("Disconnecting from services...")
        self.es_client.disconnect()
        self.sf_client.disconnect()
    
    def sync_index(self, index_name: str) -> int:
        """
        Sync a single index from Elasticsearch to Snowflake.
        
        Args:
            index_name: Name of the index to sync
            
        Returns:
            Number of documents synced
        """
        logger.info(f"Starting sync for index: {index_name}")
        
        try:
            # Get index mapping
            mapping = self.es_client.get_index_mapping(index_name)
            
            # Create/ensure table exists in Snowflake
            table_name = self.sf_client.get_table_name(index_name)
            self.sf_client.create_table_if_not_exists(table_name, mapping)
            
            # Get document count
            doc_count = self.es_client.count_documents(index_name)
            logger.info(f"Index '{index_name}' contains {doc_count} documents")
            
            # Stream documents in batches
            total_synced = 0
            for batch in self.es_client.scroll_index(index_name, self.config.batch_size):
                # Use merge to handle updates (upsert behavior)
                rows_affected = self.sf_client.merge_batch(table_name, batch)
                total_synced += len(batch)
                
                logger.info(f"Progress: {total_synced}/{doc_count} documents synced for '{index_name}'")
            
            logger.info(f"Completed sync for index '{index_name}': {total_synced} documents")
            return total_synced
            
        except Exception as e:
            logger.error(f"Error syncing index '{index_name}': {e}")
            raise
    
    def sync_all_indexes(self) -> Dict[str, int]:
        """
        Sync all configured indexes from Elasticsearch to Snowflake.
        
        Returns:
            Dictionary mapping index names to number of documents synced
        """
        logger.info("Starting sync for all indexes")
        
        # Get matching indexes
        indexes = self.es_client.get_matching_indexes()
        
        if not indexes:
            logger.warning("No indexes found matching the configured patterns")
            return {}
        
        results = {}
        for index in indexes:
            try:
                count = self.sync_index(index)
                results[index] = count
            except Exception as e:
                logger.error(f"Failed to sync index '{index}': {e}")
                results[index] = -1
        
        logger.info(f"Completed sync for all indexes: {len(results)} indexes processed")
        return results
    
    def run_once(self) -> None:
        """Run a single sync operation."""
        try:
            self.connect()
            results = self.sync_all_indexes()
            
            # Log summary
            total_docs = sum(count for count in results.values() if count > 0)
            failed = sum(1 for count in results.values() if count < 0)
            logger.info(f"Sync complete: {total_docs} total documents synced, {failed} indexes failed")
            
        finally:
            self.disconnect()
    
    def run_continuous(self) -> None:
        """Run continuous sync with configured interval."""
        self.running = True
        logger.info(f"Starting continuous sync (interval: {self.config.sync_interval}s)")
        
        try:
            self.connect()
            
            while self.running:
                try:
                    results = self.sync_all_indexes()
                    
                    # Log summary
                    total_docs = sum(count for count in results.values() if count > 0)
                    failed = sum(1 for count in results.values() if count < 0)
                    logger.info(f"Sync complete: {total_docs} total documents synced, {failed} indexes failed")
                    
                    # Wait for next sync
                    logger.info(f"Waiting {self.config.sync_interval}s until next sync...")
                    time.sleep(self.config.sync_interval)
                    
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping...")
                    break
                except Exception as e:
                    logger.error(f"Error during sync cycle: {e}")
                    logger.info(f"Waiting {self.config.sync_interval}s before retry...")
                    time.sleep(self.config.sync_interval)
                    
        finally:
            self.running = False
            self.disconnect()
    
    def stop(self) -> None:
        """Stop the application."""
        logger.info("Stopping application...")
        self.running = False


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description='Stream Elasticsearch indexes to Snowflake using Snowpipe'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (YAML)',
        default=None
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (default is continuous mode)',
        default=False
    )
    parser.add_argument(
        '--env-file',
        type=str,
        help='Path to .env file',
        default='.env'
    )
    
    args = parser.parse_args()
    
    # Load environment variables from .env file if it exists
    load_dotenv(args.env_file)
    
    # Load configuration
    try:
        config = load_config(args.config)
        setup_logging(config.log_level)
        
        logger.info("Starting Elasticsearch-Snowpipe application")
        logger.info(f"Configuration loaded: ES={config.elasticsearch.host}:{config.elasticsearch.port}, "
                   f"SF={config.snowflake.account}")
        
        # Create and run application
        app = ElasticsearchSnowpipeApp(config)
        
        if args.once:
            app.run_once()
        else:
            app.run_continuous()
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
