"""
Strategic Intelligence Platform - Multi-Database Storage Manager
================================================================
Orchestrates PostgreSQL, ChromaDB, Neo4j, Redis, and MinIO for the complete intelligence platform
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import os

# PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import psycopg2.sql as sql
    POSTGRESQL_AVAILABLE = True
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    sql = None
    POSTGRESQL_AVAILABLE = False

# Vector Database
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None
    Settings = None
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Graph Database
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    GraphDatabase = None
    NEO4J_AVAILABLE = False

# Cache
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

# Object Storage
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    Minio = None
    S3Error = None
    MINIO_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class Contact:
    """Enhanced contact with intelligence data"""
    id: Optional[int] = None
    user_id: int = None
    email: str = None
    name: str = None
    company: str = None
    linkedin_url: str = None
    twitter_handle: str = None
    enrichment_status: str = 'pending'  # pending, enriched, failed
    engagement_score: float = 0.0
    last_interaction: Optional[datetime] = None
    intelligence_data: Dict = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class KnowledgeNode:
    """Knowledge tree node with multi-dimensional insights"""
    id: str = None
    user_id: int = None
    node_type: str = None  # topic, person, decision, insight
    title: str = None
    content: Dict = None
    confidence: float = 0.0
    analyst_source: str = None
    evidence: List[str] = None
    relationships: List[str] = None
    created_at: Optional[datetime] = None

@dataclass
class IntelligenceTask:
    """Task tracking for async intelligence operations"""
    task_id: str = None
    user_id: int = None
    task_type: str = None
    status: str = 'pending'  # pending, running, completed, failed
    progress: int = 0
    result: Dict = None
    error: str = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class StrategicStorageManager:
    """
    Multi-Database Strategic Intelligence Storage Manager
    ====================================================
    Orchestrates all storage systems for the Strategic Intelligence Platform
    """
    
    def __init__(self):
        self.pg_conn = None
        self.chroma_client = None
        self.chroma_collections = {}
        self.neo4j_driver = None
        self.redis_client = None
        self.minio_client = None
        self.embedding_model = None
        self._initialized = False
        
        # In-memory storage fallback for testing
        self.use_memory_storage = False
        self.memory_contacts = {}
        self.memory_tasks = {}
        self.memory_knowledge_nodes = {}
        self.next_contact_id = 1
        self.next_task_id = 1
        self.next_node_id = 1
        
        # User context cache for background tasks
        self._user_context_cache = {}
    
    async def initialize(self):
        """Initialize all database connections"""
        if self._initialized:
            return
            
        try:
            logger.info("🔧 Initializing Strategic Storage Manager...")
            
            # Initialize PostgreSQL
            await self._init_postgresql()
            
            # Initialize ChromaDB (Vector Store) - optional
            if CHROMADB_AVAILABLE:
                await self._init_chromadb()
            else:
                logger.warning("ChromaDB not available - vector search disabled")
            
            # Initialize Neo4j (Graph Database) - optional
            if NEO4J_AVAILABLE:
                await self._init_neo4j()
            else:
                logger.warning("Neo4j not available - graph operations disabled")
            
            # Initialize Redis (Cache) - optional
            if REDIS_AVAILABLE:
                await self._init_redis()
            else:
                logger.warning("Redis not available - caching disabled")
            
            # Initialize MinIO (Object Storage) - optional
            if MINIO_AVAILABLE:
                await self._init_minio()
            else:
                logger.warning("MinIO not available - object storage disabled")
            
            # Initialize embedding model - optional
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            else:
                logger.warning("SentenceTransformers not available - embeddings disabled")
                self.embedding_model = None
            
            self._initialized = True
            logger.info("✅ Strategic Storage Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Storage initialization failed: {str(e)}")
            raise
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection and schema"""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - using in-memory storage for testing")
            self.use_memory_storage = True
            return
            
        try:
            self.pg_conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'chief_of_staff'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres')
            )
            self.pg_conn.autocommit = True
            
            # Create schema
            await self._create_postgresql_schema()
            logger.info("✅ PostgreSQL connected and schema ready")
            
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {str(e)} - using in-memory storage for testing")
            self.use_memory_storage = True
            self.pg_conn = None
    
    async def _create_postgresql_schema(self):
        """Create PostgreSQL tables for strategic intelligence"""
        with self.pg_conn.cursor() as cursor:
            # Enable pgvector extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    google_id VARCHAR(255) UNIQUE,
                    name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Enhanced contacts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    email VARCHAR(255) NOT NULL,
                    name VARCHAR(255),
                    company VARCHAR(255),
                    linkedin_url VARCHAR(500),
                    twitter_handle VARCHAR(100),
                    enrichment_status VARCHAR(50) DEFAULT 'pending',
                    engagement_score FLOAT DEFAULT 0.0,
                    last_interaction TIMESTAMP,
                    intelligence_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, email)
                );
            """)
            
            # Intelligence tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_tasks (
                    task_id VARCHAR(100) PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    task_type VARCHAR(100) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    result JSONB,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
            """)
            
            # Knowledge tree nodes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_nodes (
                    id VARCHAR(100) PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    node_type VARCHAR(50) NOT NULL,
                    title VARCHAR(500),
                    content JSONB,
                    confidence FLOAT DEFAULT 0.0,
                    analyst_source VARCHAR(100),
                    evidence JSONB,
                    relationships JSONB,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Emails table (enhanced)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    gmail_id VARCHAR(255) UNIQUE NOT NULL,
                    thread_id VARCHAR(255),
                    subject TEXT,
                    sender VARCHAR(255),
                    recipients JSONB,
                    cc_recipients JSONB,
                    bcc_recipients JSONB,
                    body_text TEXT,
                    body_html TEXT,
                    attachments JSONB,
                    labels JSONB,
                    email_date TIMESTAMP,
                    is_sent BOOLEAN DEFAULT FALSE,
                    intelligence_processed BOOLEAN DEFAULT FALSE,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indices for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user_email ON contacts(user_id, email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_user_type ON knowledge_nodes(user_id, node_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_user_date ON emails(user_id, email_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON intelligence_tasks(user_id, status);")
    
    async def _init_chromadb(self):
        """Initialize ChromaDB vector database"""
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available - skipping vector database initialization")
            return
            
        try:
            chroma_host = os.getenv('CHROMA_HOST', 'localhost')
            chroma_port = int(os.getenv('CHROMA_PORT', 8000))
            
            self.chroma_client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=Settings(
                    chroma_auth_token=os.getenv('CHROMA_AUTH_TOKEN', 'test-token')
                )
            )
            
            # Create collections for different data types
            collections = [
                'emails',
                'contacts', 
                'knowledge_nodes',
                'insights',
                'relationships'
            ]
            
            for collection_name in collections:
                try:
                    collection = self.chroma_client.get_or_create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"}
                    )
                    self.chroma_collections[collection_name] = collection
                except Exception as e:
                    logger.warning(f"ChromaDB collection {collection_name} setup issue: {str(e)}")
            
            logger.info("✅ ChromaDB vector store ready")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB initialization failed: {str(e)}")
            # Don't raise - allow system to work without vector search initially
    
    async def _init_neo4j(self):
        """Initialize Neo4j graph database"""
        if not NEO4J_AVAILABLE:
            logger.warning("Neo4j not available - skipping graph database initialization")
            return
            
        try:
            uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            user = os.getenv('NEO4J_USER', 'neo4j')
            password = os.getenv('NEO4J_PASSWORD', 'password')
            
            self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
            
            # Test connection and create constraints
            with self.neo4j_driver.session() as session:
                # Create constraints
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.email IS UNIQUE
                """)
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE
                """)
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE
                """)
            
            logger.info("✅ Neo4j graph database ready")
            
        except Exception as e:
            logger.error(f"❌ Neo4j initialization failed: {str(e)}")
            # Don't raise - allow system to work without graph initially
    
    async def _init_redis(self):
        """Initialize Redis cache"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - skipping cache initialization")
            return
            
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD', ''),
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis cache ready")
            
        except Exception as e:
            logger.error(f"❌ Redis initialization failed: {str(e)}")
            # Don't raise - allow system to work without caching initially
    
    async def _init_minio(self):
        """Initialize MinIO object storage"""
        if not MINIO_AVAILABLE:
            logger.warning("MinIO not available - skipping object storage initialization")
            return
            
        try:
            self.minio_client = Minio(
                os.getenv('S3_ENDPOINT', 'localhost:9000').replace('http://', ''),
                access_key=os.getenv('S3_ACCESS_KEY', 'minioadmin'),
                secret_key=os.getenv('S3_SECRET_KEY', 'minioadmin'),
                secure=False
            )
            
            # Create bucket if not exists
            bucket_name = os.getenv('S3_BUCKET', 'chief-of-staff')
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
            
            logger.info("✅ MinIO object storage ready")
            
        except Exception as e:
            logger.error(f"❌ MinIO initialization failed: {str(e)}")
            # Don't raise - allow system to work without object storage initially
    
    # ==================== CONTACT MANAGEMENT ====================
    
    async def save_contact(self, contact: Contact) -> Contact:
        """Save or update contact with intelligence data"""
        if not self._initialized:
            await self.initialize()
        
        if self.use_memory_storage:
            # In-memory storage fallback
            if not contact.id:
                contact.id = self.next_contact_id
                self.next_contact_id += 1
            
            contact.updated_at = datetime.utcnow()
            if not contact.created_at:
                contact.created_at = datetime.utcnow()
            
            self.memory_contacts[contact.id] = contact
            logger.info(f"Saved contact to memory: {contact.email}")
            return contact
        
        try:
            with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if contact.id:
                    # Update existing
                    cursor.execute("""
                        UPDATE contacts SET
                            name = %s, company = %s, linkedin_url = %s, twitter_handle = %s,
                            enrichment_status = %s, engagement_score = %s, 
                            last_interaction = %s, intelligence_data = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s RETURNING *;
                    """, (
                        contact.name, contact.company, contact.linkedin_url, 
                        contact.twitter_handle, contact.enrichment_status,
                        contact.engagement_score, contact.last_interaction,
                        json.dumps(contact.intelligence_data or {}), contact.id
                    ))
                else:
                    # Create new
                    cursor.execute("""
                        INSERT INTO contacts (
                            user_id, email, name, company, linkedin_url, twitter_handle,
                            enrichment_status, engagement_score, last_interaction, intelligence_data
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, email) DO UPDATE SET
                            name = COALESCE(EXCLUDED.name, contacts.name),
                            company = COALESCE(EXCLUDED.company, contacts.company),
                            enrichment_status = EXCLUDED.enrichment_status,
                            engagement_score = EXCLUDED.engagement_score,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING *;
                    """, (
                        contact.user_id, contact.email, contact.name, contact.company,
                        contact.linkedin_url, contact.twitter_handle, contact.enrichment_status,
                        contact.engagement_score, contact.last_interaction,
                        json.dumps(contact.intelligence_data or {})
                    ))
                
                result = cursor.fetchone()
                if result:
                    return Contact(**dict(result))
                    
        except Exception as e:
            logger.error(f"Contact save error: {str(e)}")
            raise
    
    async def get_contacts_for_enrichment(self, user_id: int, limit: int = 50) -> List[Contact]:
        """Get contacts that need web intelligence enrichment"""
        if not self._initialized:
            await self.initialize()
        
        if self.use_memory_storage:
            # In-memory storage fallback - return actual contacts only
            contacts = []
            for contact in self.memory_contacts.values():
                if contact.user_id == user_id and contact.enrichment_status == 'pending':
                    contacts.append(contact)
                    if len(contacts) >= limit:
                        break
            
            logger.info(f"Found {len(contacts)} real contacts for enrichment")
            return contacts
        
        try:
            with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM contacts 
                    WHERE user_id = %s AND enrichment_status = 'pending'
                    ORDER BY engagement_score DESC, last_interaction DESC NULLS LAST
                    LIMIT %s;
                """, (user_id, limit))
                
                results = cursor.fetchall()
                return [Contact(**dict(row)) for row in results]
                
        except Exception as e:
            logger.error(f"Get contacts for enrichment error: {str(e)}")
            return []
    
    # ==================== INTELLIGENCE TASK MANAGEMENT ====================
    
    async def create_intelligence_task(self, user_id: int, task_type: str) -> IntelligenceTask:
        """Create new intelligence processing task"""
        if not self._initialized:
            await self.initialize()
        
        task = IntelligenceTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            task_type=task_type,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        if self.use_memory_storage:
            # In-memory storage fallback
            self.memory_tasks[task.task_id] = task
            logger.info(f"Created task in memory: {task.task_id}")
            return task
        
        try:
            with self.pg_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO intelligence_tasks (task_id, user_id, task_type, status, created_at)
                    VALUES (%s, %s, %s, %s, %s);
                """, (task.task_id, task.user_id, task.task_type, task.status, task.created_at))
            
            # Cache in Redis for real-time updates
            if self.redis_client:
                self.redis_client.hset(
                    f"task:{task.task_id}",
                    mapping=asdict(task)
                )
                self.redis_client.expire(f"task:{task.task_id}", 3600)  # 1 hour TTL
            
            return task
            
        except Exception as e:
            logger.error(f"Create intelligence task error: {str(e)}")
            raise
    
    async def update_task_progress(self, task_id: str, progress: int, status: str = None):
        """Update task progress and status"""
        if self.use_memory_storage:
            # In-memory storage fallback
            if task_id in self.memory_tasks:
                task = self.memory_tasks[task_id]
                task.progress = progress
                if status:
                    task.status = status
                if status == 'completed':
                    task.completed_at = datetime.utcnow()
                logger.info(f"Updated task progress in memory: {task_id} -> {progress}%")
            return
        
        try:
            updates = {"progress": progress}
            if status:
                updates["status"] = status
            if status == 'completed':
                updates["completed_at"] = datetime.utcnow()
            
            # Update PostgreSQL
            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            values = list(updates.values()) + [task_id]
            
            with self.pg_conn.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE intelligence_tasks SET {set_clause} 
                    WHERE task_id = %s;
                """, values)
            
            # Update Redis cache
            if self.redis_client:
                self.redis_client.hset(f"task:{task_id}", mapping=updates)
            
        except Exception as e:
            logger.error(f"Update task progress error: {str(e)}")
    
    async def get_task_status(self, task_id: str) -> Dict:
        """Get current task status"""
        if self.use_memory_storage:
            # In-memory storage fallback
            if task_id in self.memory_tasks:
                task = self.memory_tasks[task_id]
                return {
                    'task_id': task.task_id,
                    'user_id': task.user_id,
                    'task_type': task.task_type,
                    'status': task.status,
                    'progress': task.progress,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
            return {"status": "not_found"}
        
        try:
            # Try Redis first
            if self.redis_client:
                task_data = self.redis_client.hgetall(f"task:{task_id}")
                if task_data:
                    return task_data
            
            # Fallback to PostgreSQL
            with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM intelligence_tasks WHERE task_id = %s;
                """, (task_id,))
                
                result = cursor.fetchone()
                if result:
                    return dict(result)
            
            return {"status": "not_found"}
            
        except Exception as e:
            logger.error(f"Get task status error: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    # ==================== KNOWLEDGE TREE MANAGEMENT ====================
    
    async def save_knowledge_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Save knowledge tree node with vector embedding"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate embedding for the node content
            content_text = f"{node.title} {json.dumps(node.content or {})}"
            
            if self.embedding_model:
                embedding = self.embedding_model.encode(content_text).tolist()
            else:
                # Create a dummy embedding when sentence-transformers not available
                embedding = [0.0] * 384  # Match the expected vector size
            
            # Save to PostgreSQL
            with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO knowledge_nodes (
                        id, user_id, node_type, title, content, confidence,
                        analyst_source, evidence, relationships, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        confidence = EXCLUDED.confidence,
                        evidence = EXCLUDED.evidence,
                        relationships = EXCLUDED.relationships,
                        embedding = EXCLUDED.embedding
                    RETURNING *;
                """, (
                    node.id or str(uuid.uuid4()), node.user_id, node.node_type,
                    node.title, json.dumps(node.content or {}), node.confidence,
                    node.analyst_source, json.dumps(node.evidence or []),
                    json.dumps(node.relationships or []), embedding
                ))
                
                result = cursor.fetchone()
                if result:
                    saved_node = KnowledgeNode(**dict(result))
                    
                    # Add to vector database if available
                    if CHROMADB_AVAILABLE and 'knowledge_nodes' in self.chroma_collections:
                        self.chroma_collections['knowledge_nodes'].add(
                            ids=[saved_node.id],
                            embeddings=[embedding],
                            documents=[content_text],
                            metadatas=[{
                                'user_id': saved_node.user_id,
                                'node_type': saved_node.node_type,
                                'analyst_source': saved_node.analyst_source,
                                'confidence': saved_node.confidence
                            }]
                        )
                    
                    return saved_node
                    
        except Exception as e:
            logger.error(f"Save knowledge node error: {str(e)}")
            raise
    
    # ==================== VECTOR SEARCH ====================
    
    async def semantic_search(self, user_id: int, query: str, collection: str = 'knowledge_nodes', limit: int = 10) -> List[Dict]:
        """Perform semantic search across vector collections"""
        if not self._initialized:
            await self.initialize()
        
        # Return empty if ChromaDB or embedding model not available
        if not CHROMADB_AVAILABLE or not self.embedding_model:
            logger.warning("Semantic search not available - ChromaDB or SentenceTransformers missing")
            return []
        
        try:
            if collection not in self.chroma_collections:
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search in ChromaDB
            results = self.chroma_collections[collection].query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where={"user_id": user_id}
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search error: {str(e)}")
            return []
    
    # ==================== GRAPH OPERATIONS ====================
    
    async def add_relationship(self, from_entity: str, to_entity: str, relationship_type: str, properties: Dict = None):
        """Add relationship to knowledge graph"""
        if not self.neo4j_driver:
            return
            
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (a:Entity {id: $from_id})
                    MERGE (b:Entity {id: $to_id})
                    MERGE (a)-[r:RELATED {type: $rel_type}]->(b)
                    SET r += $props
                """, from_id=from_entity, to_id=to_entity, rel_type=relationship_type, props=properties or {})
                
        except Exception as e:
            logger.error(f"Add relationship error: {str(e)}")
    
    async def get_user(self, email: str) -> Optional[Dict]:
        """Get user by email - compatibility method"""
        if not self._initialized:
            await self.initialize()
            
        try:
            with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s;", (email,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID - compatibility method"""
        if not self._initialized:
            await self.initialize()
        
        if self.use_memory_storage:
            # First check user context cache (for background tasks)
            if user_id in self._user_context_cache:
                logger.info(f"Using cached user context for user {user_id}")
                return self._user_context_cache[user_id]
            
            # In-memory storage fallback - get real user from Flask session
            try:
                from flask import session
                if 'user_email' in session and 'db_user_id' in session:
                    if session['db_user_id'] == user_id:
                        return {
                            'id': user_id,
                            'email': session['user_email'],
                            'name': session.get('user_name', 'User'),
                            'google_id': session.get('google_id', '')
                        }
                
                # Fallback: try to get from old database manager
                from models.database import get_db_manager
                user = get_db_manager().get_user_by_id(user_id)
                if user:
                    return {
                        'id': user.id,
                        'email': user.email,
                        'name': getattr(user, 'name', ''),
                        'google_id': getattr(user, 'google_id', '')
                    }
                    
            except Exception as e:
                logger.warning(f"Could not get real user data: {str(e)}")
            
            # Last resort fallback
            return {
                'id': user_id,
                'email': f'user{user_id}@strategic-intel.local',
                'name': f'Strategic User {user_id}',
                'google_id': f'google_id_{user_id}'
            }
            
        try:
            with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Get user by ID error: {str(e)}")
            return None
    
    async def close(self):
        """Close all database connections"""
        if self.pg_conn:
            self.pg_conn.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.redis_client:
            self.redis_client.close()

# Global storage manager instance
storage_manager = StrategicStorageManager() 