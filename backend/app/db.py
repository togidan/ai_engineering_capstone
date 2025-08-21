import sqlite3
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

# PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_path: str = None):
        # Check if PostgreSQL URL is provided - use os.getenv for cloud platforms
        self.postgres_url = os.getenv('DATABASE_URL')
        self.use_postgres = bool(self.postgres_url and POSTGRES_AVAILABLE)
        
        # Detailed environment debugging
        logger.info(f"DATABASE_URL from env: {'[REDACTED]' if self.postgres_url else 'None'}")
        logger.info(f"DATABASE_URL length: {len(self.postgres_url) if self.postgres_url else 0}")
        logger.info(f"DATABASE_URL starts with postgresql: {self.postgres_url.startswith('postgresql://') if self.postgres_url else False}")
        logger.info(f"RENDER environment: {bool(os.getenv('RENDER'))}")
        logger.info(f"POSTGRES_AVAILABLE: {POSTGRES_AVAILABLE}")
        logger.info(f"Initial use_postgres decision: {self.use_postgres}")
        
        # Debug environment variable access methods
        database_url_environ = os.environ.get('DATABASE_URL')
        database_url_getenv = os.getenv('DATABASE_URL') 
        logger.info(f"DATABASE_URL via os.environ.get(): {'[REDACTED]' if database_url_environ else 'None'}")
        logger.info(f"DATABASE_URL via os.getenv(): {'[REDACTED]' if database_url_getenv else 'None'}")
        logger.info(f"URLs match: {database_url_environ == database_url_getenv}")
        
        # Test connection with SSL for Supabase - FAIL FAST if DATABASE_URL provided
        if self.postgres_url and POSTGRES_AVAILABLE:
            logger.info(f"Testing PostgreSQL connection...")
            logger.info(f"POSTGRES_AVAILABLE: {POSTGRES_AVAILABLE}")
            logger.info(f"Original URL length: {len(self.postgres_url)}")
            
            # Check psycopg2 availability first
            try:
                import psycopg2
                logger.info("✅ psycopg2 import successful")
            except ImportError as e:
                error_msg = f"psycopg2 not available but DATABASE_URL provided: {e}"
                logger.error(f"❌ {error_msg}")
                if os.getenv('RENDER'):  # Force failure on Render
                    raise Exception(error_msg)
                self.use_postgres = False
                return
            
            # Add SSL mode for Supabase
            ssl_url = self.postgres_url
            if '?sslmode=' not in ssl_url:
                ssl_url += '?sslmode=require'
                logger.info(f"Added SSL mode to URL")
            
            # Test connection - fail fast if on Render
            try:
                logger.info(f"Attempting connection with SSL...")
                test_conn = psycopg2.connect(ssl_url)
                test_conn.close()
                logger.info("✅ PostgreSQL connection test successful")
                # Update the URL to include SSL
                self.postgres_url = ssl_url
            except psycopg2.OperationalError as e:
                error_msg = f"PostgreSQL operational error: {e}. URL length: {len(self.postgres_url)}, starts with postgresql: {self.postgres_url.startswith('postgresql://')}"
                logger.error(f"❌ {error_msg}")
                if os.getenv('RENDER'):  # Force failure on Render  
                    raise Exception(error_msg)
                self.use_postgres = False
            except Exception as e:
                error_msg = f"PostgreSQL connection test failed: {type(e).__name__}: {e}. URL length: {len(self.postgres_url)}, starts with postgresql: {self.postgres_url.startswith('postgresql://')}"
                logger.error(f"❌ {error_msg}")
                if os.getenv('RENDER'):  # Force failure on Render
                    raise Exception(error_msg) 
                self.use_postgres = False
        
        if not self.use_postgres:
            # No SQLite fallback when DATABASE_URL is provided - force error visibility
            if self.postgres_url:
                raise Exception(f"PostgreSQL connection failed but DATABASE_URL is provided. Check your DATABASE_URL and psycopg2 installation.")
            
            # Only use SQLite for local development without DATABASE_URL
            if db_path:
                self.db_path = db_path
            else:
                self.db_path = os.path.join(os.path.dirname(__file__), "..", "data", "kb.sqlite")
        
        self._ensure_data_directory()
        self._init_database()
    
    def _get_connection(self):
        """Get database connection (PostgreSQL or SQLite)"""
        if self.use_postgres:
            return psycopg2.connect(self.postgres_url)
        else:
            return sqlite3.connect(self.db_path)
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        if not self.use_postgres:
            # Only create directories for SQLite
            data_dir = os.path.dirname(self.db_path) if hasattr(self, 'db_path') else None
            if data_dir:  # Only create if not root directory
                os.makedirs(data_dir, exist_ok=True)
        
        # For file storage, use /tmp/kb on Render
        if os.getenv('RENDER'):
            self.kb_storage_dir = "/tmp/kb"
        else:
            self.kb_storage_dir = os.path.join(os.path.dirname(__file__), "..", "data", "kb")
        
        os.makedirs(self.kb_storage_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize the database with required tables"""
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    # PostgreSQL schema
                    cursor = conn.cursor()
                    
                    # Documents table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS documents (
                            id SERIAL PRIMARY KEY,
                            path TEXT NOT NULL,
                            name TEXT NOT NULL,
                            file_size INTEGER NOT NULL,
                            description TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Chunks table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS chunks (
                            id SERIAL PRIMARY KEY,
                            doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                            ord INTEGER NOT NULL,
                            text TEXT NOT NULL,
                            milvus_pk INTEGER UNIQUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create indexes for PostgreSQL
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_name ON documents(name)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_milvus_pk ON chunks(milvus_pk)")
                    
                    conn.commit()
                    logger.info(f"PostgreSQL database initialized")
                    
                else:
                    # SQLite schema (original)
                    conn.execute("PRAGMA foreign_keys = ON")
                    
                    # Documents table
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
                    
                    # Create indexes for SQLite
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_name ON documents(name)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_milvus_pk ON chunks(milvus_pk)")
                    
                    conn.commit()
                    logger.info(f"SQLite database initialized at {self.db_path}")
                
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
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO documents 
                        (path, name, file_size, description)
                        VALUES (%s, %s, %s, %s) RETURNING id
                    """, (path, name, file_size, description))
                    
                    doc_id = cursor.fetchone()[0]
                    conn.commit()
                else:
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
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    for i, chunk_text in enumerate(chunks):
                        cursor.execute("""
                            INSERT INTO chunks (doc_id, ord, text)
                            VALUES (%s, %s, %s) RETURNING id
                        """, (doc_id, i, chunk_text))
                        
                        chunk_ids.append(cursor.fetchone()[0])
                    conn.commit()
                else:
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
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE chunks SET milvus_pk = %s WHERE id = %s
                    """, (milvus_pk, chunk_id))
                    conn.commit()
                else:
                    conn.execute("""
                        UPDATE chunks SET milvus_pk = ? WHERE id = ?
                    """, (milvus_pk, chunk_id))
                    conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update chunk milvus_pk: {e}")
    
    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cursor.execute("""
                        SELECT * FROM documents WHERE id = %s
                    """, (doc_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
                else:
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
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    
                    # Create placeholders for IN clause
                    placeholders = ",".join("%s" for _ in milvus_pks)
                    
                    cursor.execute(f"""
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
                        FROM chunks c
                        JOIN documents d ON c.doc_id = d.id
                        WHERE c.milvus_pk IN ({placeholders})
                        ORDER BY c.doc_id, c.ord
                    """, milvus_pks)
                    
                    results = [dict(row) for row in cursor.fetchall()]
                else:
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
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT COUNT(*) FROM documents")
                    doc_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM chunks")
                    chunk_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM chunks WHERE milvus_pk IS NOT NULL")
                    indexed_chunks = cursor.fetchone()[0]
                else:
                    cursor = conn.execute("SELECT COUNT(*) FROM documents")
                    doc_count = cursor.fetchone()[0]
                    
                    cursor = conn.execute("SELECT COUNT(*) FROM chunks")
                    chunk_count = cursor.fetchone()[0]
                    
                    cursor = conn.execute("SELECT COUNT(*) FROM chunks WHERE milvus_pk IS NOT NULL")
                    indexed_chunks = cursor.fetchone()[0]
                
                return {
                    "documents": doc_count,
                    "chunks": chunk_count,
                    "indexed_chunks": indexed_chunks,
                    "embedding_coverage": indexed_chunks / chunk_count if chunk_count > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}

# Global database service instance
db_service = DatabaseService()