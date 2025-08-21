import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pymilvus import (
    connections, 
    Collection, 
    CollectionSchema, 
    FieldSchema, 
    DataType,
    utility
)
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class MilvusService:
    def __init__(self):
        self.uri = os.getenv("MILVUS_URI")
        self.token = os.getenv("MILVUS_TOKEN") 
        self.db_name = os.getenv("MILVUS_DB", "capstone")
        self.collection_name = os.getenv("MILVUS_COLLECTION", "kb_chunks")
        self.connection_alias = "default"
        self.collection = None
        
        # OpenAI for embeddings
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
        self.embedding_model = "text-embedding-3-large"
        self.embedding_dim = 3072
        
        self._connect()
        
    def _connect(self):
        """Connect to Milvus managed service"""
        try:
            if not self.uri or not self.token:
                logger.error("Milvus URI and TOKEN required in environment variables")
                return False
                
            connections.connect(
                alias=self.connection_alias,
                uri=self.uri,
                token=self.token,
                db_name=self.db_name
            )
            logger.info(f"Connected to Milvus at {self.uri}")
            
            # Load collection if it exists
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Loaded existing collection: {self.collection_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Milvus service is available"""
        return self.collection is not None or (self.uri and self.token)
    
    def ensure_collection(self) -> bool:
        """Ensure the target collection exists and has the expected schema."""
        try:
            if not (self.uri and self.token):
                return False
            # Connect if not already
            if self.collection is None and utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
            # Create if missing
            if self.collection is None and not utility.has_collection(self.collection_name):
                logger.warning(f"Milvus collection '{self.collection_name}' not found. Creating it now...")
                created = self.create_collection()
                if not created:
                    return False
            # Validate schema
            field_names = [f.name for f in self.collection.schema.fields]
            if "embedding" not in field_names:
                msg = (
                    "Milvus collection schema mismatch: missing 'embedding' field. "
                    "Drop the existing collection or update code to use the correct field."
                )
                logger.error(msg)
                raise RuntimeError(msg)
            # Validate primary key is not auto_id (we provide our own chunk IDs)
            try:
                pk_field = next((f for f in self.collection.schema.fields if f.name == "primary_key"), None)
                if pk_field is None:
                    raise RuntimeError("Milvus schema missing 'primary_key' field")
                # Some versions use attribute 'auto_id'
                auto_id = getattr(pk_field, 'auto_id', None)
                if auto_id is True:
                    raise RuntimeError(
                        "Milvus collection uses auto_id for primary_key; reset the collection to use explicit IDs."
                    )
            except Exception as e:
                logger.error(f"ensure_collection primary key validation failed: {e}")
                raise
            return True
        except Exception as e:
            logger.error(f"ensure_collection failed: {e}")
            return False
    
    def create_collection(self) -> bool:
        """Create the kb_chunks collection with proper schema"""
        try:
            # Define schema
            fields = [
                FieldSchema(name="primary_key", dtype=DataType.INT64, is_primary=True, auto_id=False),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                # FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="jurisdiction", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="industry", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=64),
            ]
            
            schema = CollectionSchema(
                fields=fields,
                description="Knowledge base chunks with embeddings and metadata"
            )
            
            # Create collection
            self.collection = Collection(
                name=self.collection_name,
                schema=schema
            )
            
            # Create HNSW index on embedding field
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200}
            }
            
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            logger.info(f"Created collection {self.collection_name} with HNSW index (explicit primary keys)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False
    
    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate embeddings using OpenAI text-embedding-3-large"""
        if not self.openai_client:
            logger.error("OpenAI client not available - no API key")
            return None
            
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings ({self.embedding_dim}-dim)")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return None
    
    def insert_chunks(self, chunks_data: List[Dict[str, Any]]) -> List[int]:
        """Insert chunk data with embeddings into Milvus using explicit primary keys from chunks_data."""
        if not self.ensure_collection():
            logger.error("Milvus collection not ready")
            return []
         
        try:
            # Extract texts for embedding
            texts = [chunk["text"] for chunk in chunks_data]
            embeddings = self.generate_embeddings(texts)
            
            if not embeddings:
                logger.error("Failed to generate embeddings for chunks")
                return []
            
            # Collect explicit primary keys
            try:
                primary_keys = [int(chunk["primary_key"]) for chunk in chunks_data]
            except Exception:
                raise RuntimeError("chunks_data must include 'primary_key' for explicit ID insertion")
            
            # Prepare data for insertion - match schema order
            data = [
                primary_keys,                        # primary_key field
                embeddings,                          # embedding field
                [chunk.get("jurisdiction", "None") for chunk in chunks_data],
                [chunk.get("industry", "None") for chunk in chunks_data],
                [chunk.get("doc_type", "None") for chunk in chunks_data],
            ]
            
            # Insert data
            mr = self.collection.insert(data)
            self.collection.flush()
            
            # With explicit IDs, Milvus may not echo primary_keys in response; return our list
            pks = primary_keys
            logger.info(f"Inserted {len(chunks_data)} chunks into Milvus with explicit IDs")
            return pks
            
        except Exception as e:
            logger.error(f"Failed to insert chunks: {e}")
            return []
    
    def search_similar(
        self, 
        query_text: str, 
        k: int = 5, 
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks with optional metadata filters"""
        if not self.ensure_collection():
            logger.error("Milvus collection not ready")
            return []
         
        try:
            # Generate query embedding
            query_embedding = self.generate_embeddings([query_text])
            if not query_embedding:
                return []
            
            # Build filter expression
            filter_expr = ""
            if filters:
                filter_parts = []
                for field, value in filters.items():
                    if value and field in ["jurisdiction", "industry", "doc_type"]:
                        filter_parts.append(f'{field} == "{value}"')
                
                if filter_parts:
                    filter_expr = " && ".join(filter_parts)
            
            # Search parameters
            search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
            
            # Perform search
            results = self.collection.search(
                data=query_embedding,
                anns_field="embedding",
                param=search_params,
                limit=k * 2,  # Get more results for re-ranking
                expr=filter_expr if filter_expr else None,
                output_fields=["primary_key", "jurisdiction", "industry", "doc_type"]
            )
            
            # Format results
            hits = []
            for result in results[0]:  # First query results
                hits.append({
                    "primary_key": result.entity.get("primary_key"),
                    "score": float(result.distance),
                    # "text": result.entity.get("text"),
                    "jurisdiction": result.entity.get("jurisdiction"),
                    "industry": result.entity.get("industry"),
                    "doc_type": result.entity.get("doc_type")
                })
            
            logger.info(f"Found {len(hits)} similar chunks for query")
            return hits[:k]  # Return top k after any re-ranking
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self.collection:
            return {"error": "Collection not available"}
            
        try:
            self.collection.load()
            stats = {
                "name": self.collection.name,
                "num_entities": self.collection.num_entities,
                "schema": {
                    "fields": [{"name": f.name, "type": f.dtype.name} for f in self.collection.schema.fields]
                }
            }
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    def load_collection(self):
        """Load collection into memory for searching"""
        if self.ensure_collection():
            try:
                self.collection.load()
                logger.info("Collection loaded into memory")
            except Exception as e:
                logger.error(f"Failed to load collection: {e}")

    def reset_collection(self) -> bool:
        """Drop and recreate the collection with explicit primary keys (no auto_id)."""
        try:
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
                logger.info(f"Dropped existing collection {self.collection_name}")
            self.collection = None
            return self.create_collection()
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False

# Global Milvus service instance
milvus_service = MilvusService()