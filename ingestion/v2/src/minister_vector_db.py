"""
PostgreSQL + pgvector schema for minister vector database.

This module defines the database schema for storing minister embeddings
at both combined and domain-specific levels.
"""

# SQL Schema for minister embeddings

INIT_COMBINED_TABLE = """
CREATE TABLE IF NOT EXISTS minister_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    embedding VECTOR(1536),
    source_book VARCHAR(255),
    source_chapter INT,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_minister_embeddings_domain ON minister_embeddings(domain);
CREATE INDEX IF NOT EXISTS idx_minister_embeddings_category ON minister_embeddings(category);
CREATE INDEX IF NOT EXISTS idx_minister_embeddings_book ON minister_embeddings(source_book);
CREATE INDEX IF NOT EXISTS idx_minister_embeddings_vector 
    ON minister_embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 200);
"""

INIT_DOMAIN_TABLES = """
CREATE TABLE IF NOT EXISTS minister_domain_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    embedding VECTOR(1536),
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_minister_domain_embeddings_domain ON minister_domain_embeddings(domain);
CREATE INDEX IF NOT EXISTS idx_minister_domain_embeddings_category ON minister_domain_embeddings(category);
CREATE INDEX IF NOT EXISTS idx_minister_domain_embeddings_vector
    ON minister_domain_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
"""

# Utility queries

QUERY_BY_DOMAIN = """
SELECT id, domain, category, text, embedding, weight, source_book, source_chapter
FROM minister_embeddings
WHERE domain = %s
ORDER BY embedding <-> %s
LIMIT %s;
"""

QUERY_BY_DOMAIN_AND_CATEGORY = """
SELECT id, domain, category, text, embedding, weight
FROM minister_embeddings
WHERE domain = %s AND category = %s
ORDER BY embedding <-> %s
LIMIT %s;
"""

QUERY_COMBINED_VECTOR_SEARCH = """
SELECT id, domain, category, text, embedding, weight, source_book, source_chapter,
       (embedding <-> %s) as distance
FROM minister_embeddings
ORDER BY distance
LIMIT %s;
"""

INSERT_COMBINED_EMBEDDING = """
INSERT INTO minister_embeddings (domain, category, text, embedding, source_book, source_chapter, weight)
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING id;
"""

INSERT_DOMAIN_EMBEDDING = """
INSERT INTO minister_domain_embeddings (domain, category, text, embedding, weight)
VALUES (%s, %s, %s, %s, %s)
RETURNING id;
"""

# Python client helper class

class MinisterVectorDB:
    """Helper class for interacting with minister embeddings database."""
    
    def __init__(self, connection_string: str):
        """
        Initialize database connection.
        
        Args:
            connection_string: PostgreSQL connection string (e.g., 
                "postgresql://user:pass@localhost:5432/minister_db")
        """
        self.connection_string = connection_string
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection."""
        try:
            import psycopg2
            self.conn = psycopg2.connect(self.connection_string)
            self.cursor = self.conn.cursor()
        except ImportError:
            raise ImportError("psycopg2 required: pip install psycopg2-binary")
    
    def init_schema(self):
        """Initialize database schema."""
        if not self.cursor:
            self.connect()
        
        self.cursor.execute(INIT_COMBINED_TABLE)
        self.cursor.execute(INIT_DOMAIN_TABLES)
        self.conn.commit()
    
    def insert_combined_embedding(self, domain: str, category: str, text: str, 
                                  embedding: list, source_book: str, 
                                  source_chapter: int, weight: float = 1.0) -> str:
        """
        Insert embedding into combined table.
        
        Args:
            domain: Domain name
            category: principle/rule/claim/warning
            text: Entry text
            embedding: Vector embedding (1536 dims)
            source_book: Book identifier
            source_chapter: Chapter number
            weight: Importance weight
            
        Returns:
            UUID of inserted row
        """
        if not self.cursor:
            self.connect()
        
        from pgvector.psycopg2 import register_vector
        register_vector(self.conn)
        
        self.cursor.execute(
            INSERT_COMBINED_EMBEDDING,
            (domain, category, text, embedding, source_book, source_chapter, weight)
        )
        result = self.cursor.fetchone()
        self.conn.commit()
        return str(result[0])
    
    def search_by_domain(self, domain: str, query_vector: list, limit: int = 10) -> list:
        """
        Search embeddings for a specific domain.
        
        Args:
            domain: Domain name
            query_vector: Query vector (1536 dims)
            limit: Max results
            
        Returns:
            List of matching records
        """
        if not self.cursor:
            self.connect()
        
        from pgvector.psycopg2 import register_vector
        register_vector(self.conn)
        
        self.cursor.execute(QUERY_BY_DOMAIN, (domain, query_vector, limit))
        return self.cursor.fetchall()
    
    def search_combined(self, query_vector: list, limit: int = 10) -> list:
        """
        Search all embeddings across all domains.
        
        Args:
            query_vector: Query vector (1536 dims)
            limit: Max results
            
        Returns:
            List of matching records with distance scores
        """
        if not self.cursor:
            self.connect()
        
        from pgvector.psycopg2 import register_vector
        register_vector(self.conn)
        
        self.cursor.execute(QUERY_COMBINED_VECTOR_SEARCH, (query_vector, limit))
        results = self.cursor.fetchall()
        return [
            {
                "id": r[0],
                "domain": r[1],
                "category": r[2],
                "text": r[3],
                "distance": r[8]
            }
            for r in results
        ]
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
