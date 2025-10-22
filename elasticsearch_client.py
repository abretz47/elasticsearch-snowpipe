"""
Elasticsearch client for reading index data.
"""
import logging
from typing import List, Dict, Any, Generator
from elasticsearch import Elasticsearch
from config import ElasticsearchConfig


logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Client for connecting to and reading from Elasticsearch."""
    
    def __init__(self, config: ElasticsearchConfig):
        """
        Initialize Elasticsearch client.
        
        Args:
            config: Elasticsearch configuration
        """
        self.config = config
        self.client = None
        
    def connect(self) -> None:
        """Establish connection to Elasticsearch."""
        auth_params = {}
        
        if self.config.api_key:
            auth_params['api_key'] = self.config.api_key
        elif self.config.username and self.config.password:
            auth_params['basic_auth'] = (self.config.username, self.config.password)
        
        self.client = Elasticsearch(
            [f"{'https' if self.config.use_ssl else 'http'}://{self.config.host}:{self.config.port}"],
            verify_certs=self.config.verify_certs,
            ca_certs=self.config.ca_certs,
            **auth_params
        )
        
        # Test connection
        try:
            info = self.client.info()
            logger.info(f"Connected to Elasticsearch cluster: {info['cluster_name']}")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close Elasticsearch connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Elasticsearch")
    
    def get_matching_indexes(self) -> List[str]:
        """
        Get list of indexes matching the configured patterns.
        
        Returns:
            List of index names
        """
        if not self.client:
            raise RuntimeError("Not connected to Elasticsearch")
        
        all_indexes = []
        for pattern in self.config.indexes:
            try:
                indexes = self.client.indices.get(index=pattern)
                all_indexes.extend(indexes.keys())
            except Exception as e:
                logger.warning(f"Error getting indexes for pattern '{pattern}': {e}")
        
        # Remove duplicates and system indexes
        unique_indexes = list(set(all_indexes))
        filtered_indexes = [idx for idx in unique_indexes if not idx.startswith('.')]
        
        logger.info(f"Found {len(filtered_indexes)} indexes matching patterns: {self.config.indexes}")
        return filtered_indexes
    
    def get_index_mapping(self, index: str) -> Dict[str, Any]:
        """
        Get mapping for an index.
        
        Args:
            index: Index name
            
        Returns:
            Index mapping
        """
        if not self.client:
            raise RuntimeError("Not connected to Elasticsearch")
        
        try:
            mapping = self.client.indices.get_mapping(index=index)
            return mapping.get(index, {})
        except Exception as e:
            logger.error(f"Error getting mapping for index '{index}': {e}")
            raise
    
    def scroll_index(self, index: str, batch_size: int = 1000, query: Dict[str, Any] = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Scroll through all documents in an index.
        
        Args:
            index: Index name
            batch_size: Number of documents to fetch per batch
            query: Optional query to filter documents
            
        Yields:
            Batches of documents
        """
        if not self.client:
            raise RuntimeError("Not connected to Elasticsearch")
        
        if query is None:
            query = {"match_all": {}}
        
        try:
            # Initial search
            response = self.client.search(
                index=index,
                scroll='5m',
                size=batch_size,
                query=query
            )
            
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            
            while hits:
                # Prepare documents
                documents = []
                for hit in hits:
                    doc = {
                        '_id': hit['_id'],
                        '_index': hit['_index'],
                        '_source': hit['_source']
                    }
                    documents.append(doc)
                
                yield documents
                
                # Get next batch
                response = self.client.scroll(scroll_id=scroll_id, scroll='5m')
                scroll_id = response['_scroll_id']
                hits = response['hits']['hits']
            
            # Clean up scroll
            self.client.clear_scroll(scroll_id=scroll_id)
            logger.info(f"Finished scrolling index '{index}'")
            
        except Exception as e:
            logger.error(f"Error scrolling index '{index}': {e}")
            raise
    
    def count_documents(self, index: str) -> int:
        """
        Count documents in an index.
        
        Args:
            index: Index name
            
        Returns:
            Number of documents
        """
        if not self.client:
            raise RuntimeError("Not connected to Elasticsearch")
        
        try:
            result = self.client.count(index=index)
            return result['count']
        except Exception as e:
            logger.error(f"Error counting documents in index '{index}': {e}")
            raise
