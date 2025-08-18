import sqlite3
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data", "kb.sqlite")
        self._ensure_data_directory()
        self._init_database()
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        data_dir = os.path.dirname(self.db_path)
        os.makedirs(data_dir, exist_ok=True)
        
        # Also ensure kb subdirectory for file storage
        kb_dir = os.path.join(data_dir, "kb")
        os.makedirs(kb_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Documents table - clean schema for LLM-generated metadata
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT NOT NULL,
                        name TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        description TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Chunks table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS chunks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_id INTEGER NOT NULL,
                        ord INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        milvus_pk INTEGER UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (doc_id) REFERENCES documents (id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_name ON documents(name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_milvus_pk ON chunks(milvus_pk)")
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def insert_document(
        self,
        path: str,
        name: str,
        file_size: int,
        description: str
    ) -> Optional[int]:
        """Insert a new document with LLM-generated metadata"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO documents 
                    (path, name, file_size, description)
                    VALUES (?, ?, ?, ?)
                """, (path, name, file_size, description))
                
                doc_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Inserted document {doc_id}: {name}")
                return doc_id
                
        except Exception as e:
            logger.error(f"Failed to insert document: {e}")
            return None
    
    def insert_chunks(self, doc_id: int, chunks: List[str]) -> List[int]:
        """Insert text chunks for a document and return chunk IDs"""
        chunk_ids = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                for i, chunk_text in enumerate(chunks):
                    cursor = conn.execute("""
                        INSERT INTO chunks (doc_id, ord, text)
                        VALUES (?, ?, ?)
                    """, (doc_id, i, chunk_text))
                    
                    chunk_ids.append(cursor.lastrowid)
                
                conn.commit()
                logger.info(f"Inserted {len(chunk_ids)} chunks for document {doc_id}")
                
        except Exception as e:
            logger.error(f"Failed to insert chunks: {e}")
            return []
            
        return chunk_ids
    
    def update_chunk_milvus_pk(self, chunk_id: int, milvus_pk: int):
        """Update the Milvus primary key for a chunk"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE chunks SET milvus_pk = ? WHERE id = ?
                """, (milvus_pk, chunk_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update chunk milvus_pk: {e}")
    
    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM documents WHERE id = ?
                """, (doc_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def get_chunks_by_milvus_pks(self, milvus_pks: List[int]) -> List[Dict[str, Any]]:
        """Get chunks and their document info by Milvus primary keys"""
        if not milvus_pks:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Create placeholders for IN clause
                placeholders = ",".join("?" * len(milvus_pks))
                
                cursor = conn.execute(f"""
                    SELECT 
                        c.id as chunk_id,
                        c.text,
                        c.milvus_pk,
                        c.ord,
                        d.id as doc_id,
                        d.path,
                        d.name as title,
                        d.description,
                        d.file_size,
                        d.created_at
                        -- TODO: Restore full metadata schema if needed
                        -- d.title,
                        -- d.jurisdiction,
                        -- d.industry,
                        -- d.doc_type,
                        -- d.source_url
                    FROM chunks c
                    JOIN documents d ON c.doc_id = d.id
                    WHERE c.milvus_pk IN ({placeholders})
                    ORDER BY c.doc_id, c.ord
                """, milvus_pks)
                
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Retrieved {len(results)} chunks for {len(milvus_pks)} milvus_pks")
                return results
                
        except Exception as e:
            logger.error(f"Failed to get chunks by milvus_pks: {e}")
            return []
    
    def search_documents(
        self,
        jurisdiction: str = None,
        industry: str = None,
        doc_type: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search documents by metadata filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                where_clauses = ["indexed = 1"]
                params = []
                
                if jurisdiction:
                    where_clauses.append("jurisdiction LIKE ?")
                    params.append(f"%{jurisdiction}%")
                    
                if industry:
                    where_clauses.append("industry LIKE ?")
                    params.append(f"%{industry}%")
                    
                if doc_type:
                    where_clauses.append("doc_type = ?")
                    params.append(doc_type)
                
                where_clause = " AND ".join(where_clauses)
                params.append(limit)
                
                cursor = conn.execute(f"""
                    SELECT * FROM documents 
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ?
                """, params)
                
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Found {len(results)} documents matching filters")
                return results
                
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM chunks WHERE milvus_pk IS NOT NULL")
                indexed_chunks = cursor.fetchone()[0]
                
                # cursor = conn.execute("""
                #     SELECT jurisdiction, COUNT(*) as count 
                #     FROM documents 
                #     WHERE jurisdiction IS NOT NULL 
                #     GROUP BY jurisdiction 
                #     ORDER BY count DESC 
                #     LIMIT 10
                # """)
                # top_jurisdictions = [{"jurisdiction": row[0], "count": row[1]} for row in cursor.fetchall()]
                
                # cursor = conn.execute("""
                #     SELECT industry, COUNT(*) as count 
                #     FROM documents 
                #     WHERE industry IS NOT NULL 
                #     GROUP BY industry 
                #     ORDER BY count DESC 
                #     LIMIT 10
                # """)
                # top_industries = [{"industry": row[0], "count": row[1]} for row in cursor.fetchall()]
                
                return {
                    "documents": doc_count,
                    "chunks": chunk_count,
                    "indexed_chunks": indexed_chunks,
                    "embedding_coverage": indexed_chunks / chunk_count if chunk_count > 0 else 0
                    # "top_jurisdictions": top_jurisdictions,
                    # "top_industries": top_industries
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}

# Global database service instance
db_service = DatabaseService()