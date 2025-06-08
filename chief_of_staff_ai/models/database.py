import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.types import TypeDecorator

from config.settings import settings

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()

# Custom JSON type that works with both SQLite and PostgreSQL
class JSONType(TypeDecorator):
    impl = Text
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value

class User(Base):
    """User model for multi-tenant authentication"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    google_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    
    # OAuth credentials (encrypted in production)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    scopes = Column(JSONType)
    
    # Account metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Processing preferences
    email_fetch_limit = Column(Integer, default=50)
    email_days_back = Column(Integer, default=30)
    auto_process_emails = Column(Boolean, default=True)
    
    # Relationships
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    people = relationship("Person", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.name}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'google_id': self.google_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'email_fetch_limit': self.email_fetch_limit,
            'email_days_back': self.email_days_back,
            'auto_process_emails': self.auto_process_emails
        }

class Email(Base):
    """Email model for storing processed emails per user"""
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Gmail identifiers
    gmail_id = Column(String(255), nullable=False, index=True)
    thread_id = Column(String(255), index=True)
    
    # Email content
    sender = Column(String(255), index=True)
    sender_name = Column(String(255))
    subject = Column(Text)
    body_text = Column(Text)
    body_html = Column(Text)
    body_clean = Column(Text)
    body_preview = Column(Text)
    snippet = Column(Text)
    
    # Email metadata
    recipients = Column(JSONType)  # List of recipient emails
    cc = Column(JSONType)  # List of CC emails
    bcc = Column(JSONType)  # List of BCC emails
    labels = Column(JSONType)  # Gmail labels
    attachments = Column(JSONType)  # Attachment metadata
    entities = Column(JSONType)  # Extracted entities
    
    # Email properties
    email_date = Column(DateTime, index=True)
    size_estimate = Column(Integer)
    message_type = Column(String(50), index=True)  # regular, meeting, newsletter, etc.
    priority_score = Column(Float, index=True)
    
    # Email status
    is_read = Column(Boolean, default=False)
    is_important = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    has_attachments = Column(Boolean, default=False)
    
    # Email classification and AI insights
    project_id = Column(Integer, ForeignKey('projects.id'), index=True)
    mentioned_people = Column(JSONType)  # List of person IDs mentioned in email
    ai_summary = Column(Text)  # Claude-generated summary
    ai_category = Column(String(100))  # AI-determined category
    sentiment_score = Column(Float)  # Sentiment analysis score
    urgency_score = Column(Float)  # AI-determined urgency
    key_insights = Column(JSONType)  # Key insights extracted by Claude
    topics = Column(JSONType)  # Main topics/themes identified
    action_required = Column(Boolean, default=False)  # Whether action is needed
    follow_up_required = Column(Boolean, default=False)  # Whether follow-up needed
    
    # Processing metadata
    processed_at = Column(DateTime, default=datetime.utcnow)
    normalizer_version = Column(String(50))
    has_errors = Column(Boolean, default=False)
    error_message = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="emails")
    tasks = relationship("Task", back_populates="email", cascade="all, delete-orphan")
    
    # Indexes for performance - Fixed naming to avoid conflicts
    __table_args__ = (
        Index('idx_email_user_gmail', 'user_id', 'gmail_id'),
        Index('idx_email_user_date', 'user_id', 'email_date'),
        Index('idx_email_user_type', 'user_id', 'message_type'),
        Index('idx_email_user_priority', 'user_id', 'priority_score'),
    )
    
    def __repr__(self):
        return f"<Email(gmail_id='{self.gmail_id}', subject='{self.subject[:50]}...')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'gmail_id': self.gmail_id,
            'thread_id': self.thread_id,
            'sender': self.sender,
            'sender_name': self.sender_name,
            'subject': self.subject,
            'body_preview': self.body_preview,
            'snippet': self.snippet,
            'recipients': self.recipients,
            'email_date': self.email_date.isoformat() if self.email_date else None,
            'message_type': self.message_type,
            'priority_score': self.priority_score,
            'is_read': self.is_read,
            'is_important': self.is_important,
            'is_starred': self.is_starred,
            'has_attachments': self.has_attachments,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'project_id': self.project_id,
            'mentioned_people': self.mentioned_people,
            'ai_summary': self.ai_summary,
            'ai_category': self.ai_category,
            'sentiment_score': self.sentiment_score,
            'urgency_score': self.urgency_score,
            'key_insights': self.key_insights,
            'topics': self.topics,
            'action_required': self.action_required,
            'follow_up_required': self.follow_up_required
        }

class Task(Base):
    """Task model for storing extracted tasks per user"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=True, index=True)
    
    # Task content
    description = Column(Text, nullable=False)
    assignee = Column(String(255))
    due_date = Column(DateTime, index=True)
    due_date_text = Column(String(255))
    
    # Task metadata
    priority = Column(String(20), default='medium', index=True)  # high, medium, low
    category = Column(String(50), index=True)  # follow-up, deadline, meeting, etc.
    confidence = Column(Float)  # AI confidence score
    source_text = Column(Text)  # Original text from email
    
    # Task status
    status = Column(String(20), default='pending', index=True)  # pending, in_progress, completed, cancelled
    completed_at = Column(DateTime)
    
    # Extraction metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extractor_version = Column(String(50))
    model_used = Column(String(100))
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    email = relationship("Email", back_populates="tasks")
    
    # Indexes for performance - Fixed naming to avoid conflicts
    __table_args__ = (
        Index('idx_task_user_status', 'user_id', 'status'),
        Index('idx_task_user_priority_unique', 'user_id', 'priority'),
        Index('idx_task_user_due_date', 'user_id', 'due_date'),
        Index('idx_task_user_category', 'user_id', 'category'),
    )
    
    def __repr__(self):
        return f"<Task(description='{self.description[:50]}...', priority='{self.priority}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_id': self.email_id,
            'description': self.description,
            'assignee': self.assignee,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'due_date_text': self.due_date_text,
            'priority': self.priority,
            'category': self.category,
            'confidence': self.confidence,
            'source_text': self.source_text,
            'status': self.status,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'extractor_version': self.extractor_version,
            'model_used': self.model_used
        }

class Person(Base):
    """Person model for tracking individuals mentioned in emails"""
    __tablename__ = 'people'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Person identification
    email_address = Column(String(255), index=True)
    name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    
    # Person details (extracted and augmented by Claude)
    title = Column(String(255))
    company = Column(String(255))
    role = Column(String(255))
    department = Column(String(255))
    
    # Relationship and context
    relationship_type = Column(String(100))  # colleague, client, vendor, etc.
    communication_frequency = Column(String(50))  # high, medium, low
    importance_level = Column(Float)  # 0.0 to 1.0
    
    # Knowledge base (JSON fields for flexible data)
    skills = Column(JSONType)  # List of skills/expertise
    interests = Column(JSONType)  # Personal/professional interests
    projects_involved = Column(JSONType)  # List of project IDs
    communication_style = Column(Text)  # Claude's analysis of communication style
    key_topics = Column(JSONType)  # Main topics discussed with this person
    
    # Extracted insights
    personality_traits = Column(JSONType)  # Claude-extracted personality insights
    preferences = Column(JSONType)  # Communication preferences, etc.
    notes = Column(Text)  # Accumulated notes about this person
    
    # Metadata
    first_mentioned = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    total_emails = Column(Integer, default=0)
    
    # AI processing metadata
    knowledge_confidence = Column(Float, default=0.5)  # Confidence in extracted data
    last_updated_by_ai = Column(DateTime)
    ai_version = Column(String(50))
    
    # Relationships
    user = relationship("User", back_populates="people")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_person_user_email', 'user_id', 'email_address'),
        Index('idx_person_user_name', 'user_id', 'name'),
        Index('idx_person_company', 'user_id', 'company'),
    )
    
    def __repr__(self):
        return f"<Person(name='{self.name}', email='{self.email_address}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_address': self.email_address,
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'title': self.title,
            'company': self.company,
            'role': self.role,
            'department': self.department,
            'relationship_type': self.relationship_type,
            'communication_frequency': self.communication_frequency,
            'importance_level': self.importance_level,
            'skills': self.skills,
            'interests': self.interests,
            'projects_involved': self.projects_involved,
            'communication_style': self.communication_style,
            'key_topics': self.key_topics,
            'personality_traits': self.personality_traits,
            'preferences': self.preferences,
            'notes': self.notes,
            'first_mentioned': self.first_mentioned.isoformat() if self.first_mentioned else None,
            'last_interaction': self.last_interaction.isoformat() if self.last_interaction else None,
            'total_emails': self.total_emails,
            'knowledge_confidence': self.knowledge_confidence,
            'last_updated_by_ai': self.last_updated_by_ai.isoformat() if self.last_updated_by_ai else None,
            'ai_version': self.ai_version
        }

class Project(Base):
    """Project model for categorizing emails and tracking project-related information"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Project identification
    name = Column(String(255), nullable=False)
    slug = Column(String(255), index=True)  # URL-friendly name
    description = Column(Text)
    
    # Project details
    status = Column(String(50), default='active')  # active, completed, paused, cancelled
    priority = Column(String(20), default='medium')  # high, medium, low
    category = Column(String(100))  # business, personal, client work, etc.
    
    # Timeline
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    deadline = Column(DateTime)
    
    # People and relationships
    stakeholders = Column(JSONType)  # List of person IDs involved
    team_members = Column(JSONType)  # List of person IDs
    
    # Project insights (extracted by Claude)
    key_topics = Column(JSONType)  # Main topics/themes
    objectives = Column(JSONType)  # Project goals and objectives
    challenges = Column(JSONType)  # Identified challenges
    progress_indicators = Column(JSONType)  # Metrics and milestones
    
    # Communication patterns
    communication_frequency = Column(String(50))
    last_activity = Column(DateTime)
    total_emails = Column(Integer, default=0)
    
    # AI analysis
    sentiment_trend = Column(Float)  # Overall sentiment about project
    urgency_level = Column(Float)  # How urgent this project appears
    confidence_score = Column(Float)  # AI confidence in project categorization
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ai_version = Column(String(50))
    
    # Relationships
    user = relationship("User", back_populates="projects")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_project_user_status', 'user_id', 'status'),
        Index('idx_project_user_priority', 'user_id', 'priority'),
        Index('idx_project_user_category', 'user_id', 'category'),
    )
    
    def __repr__(self):
        return f"<Project(name='{self.name}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'category': self.category,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'stakeholders': self.stakeholders,
            'team_members': self.team_members,
            'key_topics': self.key_topics,
            'objectives': self.objectives,
            'challenges': self.challenges,
            'progress_indicators': self.progress_indicators,
            'communication_frequency': self.communication_frequency,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'total_emails': self.total_emails,
            'sentiment_trend': self.sentiment_trend,
            'urgency_level': self.urgency_level,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'ai_version': self.ai_version
        }

class Topic(Base):
    """Topic model for organizing and categorizing content"""
    __tablename__ = 'topics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Topic identification
    name = Column(String(255), nullable=False)
    slug = Column(String(255), index=True)  # URL-friendly name
    description = Column(Text)
    
    # Topic properties
    is_official = Column(Boolean, default=False, index=True)  # Official vs AI-discovered
    parent_topic_id = Column(Integer, ForeignKey('topics.id'), index=True)  # For hierarchical topics
    merged_topics = Column(Text)  # JSON string of merged topic names
    keywords = Column(Text)  # JSON string of keywords for matching (changed from JSONType for compatibility)
    email_count = Column(Integer, default=0)  # Number of emails with this topic
    
    # Usage tracking
    last_used = Column(DateTime)
    usage_frequency = Column(Float)
    confidence_threshold = Column(Float)
    
    # AI analysis
    confidence_score = Column(Float, default=0.5)  # AI confidence in topic classification
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ai_version = Column(String(50))
    
    # Relationships
    user = relationship("User", back_populates="topics")
    parent_topic = relationship("Topic", remote_side=[id], backref="child_topics")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_topic_user_official', 'user_id', 'is_official'),
        Index('idx_topic_user_name', 'user_id', 'name'),
        Index('idx_topic_slug', 'user_id', 'slug'),
        Index('idx_topic_parent', 'parent_topic_id'),
    )
    
    def __repr__(self):
        return f"<Topic(name='{self.name}', is_official={self.is_official})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'is_official': self.is_official,
            'keywords': json.loads(self.keywords) if self.keywords else [],
            'email_count': self.email_count,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'ai_version': self.ai_version,
            'parent_topic_id': self.parent_topic_id,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }

class DatabaseManager:
    """Database manager for handling connections and sessions"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            # Use DATABASE_URL from environment or default to SQLite
            database_url = settings.DATABASE_URL
            
            # Handle PostgreSQL URL for Heroku
            if database_url and database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            # Create engine with appropriate settings
            if database_url.startswith('postgresql://'):
                # PostgreSQL settings for Heroku
                self.engine = create_engine(
                    database_url,
                    echo=settings.DEBUG,
                    pool_pre_ping=True,
                    pool_recycle=300
                )
            else:
                # SQLite settings for local development
                self.engine = create_engine(
                    database_url,
                    echo=settings.DEBUG,
                    connect_args={"check_same_thread": False}
                )
            
            # Create session factory
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        with self.get_session() as session:
            return session.query(User).filter(User.email == email).first()
    
    def create_or_update_user(self, user_info: Dict, credentials: Dict) -> User:
        """Create or update user with OAuth info"""
        with self.get_session() as session:
            user = session.query(User).filter(User.email == user_info['email']).first()
            
            if user:
                # Update existing user
                user.name = user_info.get('name', user.name)
                user.last_login = datetime.utcnow()
                user.access_token = credentials.get('access_token')
                user.refresh_token = credentials.get('refresh_token')
                user.token_expires_at = credentials.get('expires_at')
                user.scopes = credentials.get('scopes', [])
            else:
                # Create new user
                user = User(
                    email=user_info['email'],
                    google_id=user_info['id'],
                    name=user_info.get('name', ''),
                    access_token=credentials.get('access_token'),
                    refresh_token=credentials.get('refresh_token'),
                    token_expires_at=credentials.get('expires_at'),
                    scopes=credentials.get('scopes', [])
                )
                session.add(user)
            
            session.commit()
            session.refresh(user)
            return user
    
    def save_email(self, user_id: int, email_data: Dict) -> Email:
        """Save processed email to database"""
        with self.get_session() as session:
            # Check if email already exists
            existing = session.query(Email).filter(
                Email.user_id == user_id,
                Email.gmail_id == email_data['id']
            ).first()
            
            if existing:
                return existing
            
            # Create new email record
            email = Email(
                user_id=user_id,
                gmail_id=email_data['id'],
                thread_id=email_data.get('thread_id'),
                sender=email_data.get('sender'),
                sender_name=email_data.get('sender_name'),
                subject=email_data.get('subject'),
                body_text=email_data.get('body_text'),
                body_html=email_data.get('body_html'),
                body_clean=email_data.get('body_clean'),
                body_preview=email_data.get('body_preview'),
                snippet=email_data.get('snippet'),
                recipients=email_data.get('recipients', []),
                cc=email_data.get('cc', []),
                bcc=email_data.get('bcc', []),
                labels=email_data.get('labels', []),
                attachments=email_data.get('attachments', []),
                entities=email_data.get('entities', {}),
                email_date=email_data.get('timestamp'),
                size_estimate=email_data.get('size_estimate'),
                message_type=email_data.get('message_type'),
                priority_score=email_data.get('priority_score'),
                is_read=email_data.get('is_read', False),
                is_important=email_data.get('is_important', False),
                is_starred=email_data.get('is_starred', False),
                has_attachments=email_data.get('has_attachments', False),
                normalizer_version=email_data.get('processing_metadata', {}).get('normalizer_version'),
                has_errors=email_data.get('error', False),
                error_message=email_data.get('error_message')
            )
            
            session.add(email)
            session.commit()
            session.refresh(email)
            return email
    
    def save_task(self, user_id: int, email_id: Optional[int], task_data: Dict) -> Task:
        """Save extracted task to database"""
        with self.get_session() as session:
            task = Task(
                user_id=user_id,
                email_id=email_id,
                description=task_data['description'],
                assignee=task_data.get('assignee'),
                due_date=task_data.get('due_date'),
                due_date_text=task_data.get('due_date_text'),
                priority=task_data.get('priority', 'medium'),
                category=task_data.get('category'),
                confidence=task_data.get('confidence'),
                source_text=task_data.get('source_text'),
                status=task_data.get('status', 'pending'),
                extractor_version=task_data.get('extractor_version'),
                model_used=task_data.get('model_used')
            )
            
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
    
    def get_user_emails(self, user_id: int, limit: int = 50) -> List[Email]:
        """Get emails for a user"""
        with self.get_session() as session:
            return session.query(Email).filter(
                Email.user_id == user_id
            ).order_by(Email.email_date.desc()).limit(limit).all()
    
    def get_user_tasks(self, user_id: int, status: str = None, limit: int = 500) -> List[Task]:
        """Get tasks for a user"""
        with self.get_session() as session:
            query = session.query(Task).filter(Task.user_id == user_id)
            if status:
                query = query.filter(Task.status == status)
            return query.order_by(Task.created_at.desc()).limit(limit).all()

    def create_or_update_person(self, user_id: int, person_data: Dict) -> Person:
        """Create or update a person record"""
        with self.get_session() as session:
            # Try to find existing person by email or name
            person = session.query(Person).filter(
                Person.user_id == user_id,
                Person.email_address == person_data.get('email_address')
            ).first()
            
            if not person and person_data.get('name'):
                # Try by name if email not found
                person = session.query(Person).filter(
                    Person.user_id == user_id,
                    Person.name == person_data.get('name')
                ).first()
            
            if person:
                # Update existing person
                for key, value in person_data.items():
                    if hasattr(person, key) and value is not None:
                        setattr(person, key, value)
                person.last_interaction = datetime.utcnow()
                person.total_emails += 1
                person.last_updated_by_ai = datetime.utcnow()
            else:
                # Create new person
                person = Person(
                    user_id=user_id,
                    **person_data,
                    total_emails=1,
                    last_updated_by_ai=datetime.utcnow()
                )
                session.add(person)
            
            session.commit()
            session.refresh(person)
            return person
    
    def create_or_update_project(self, user_id: int, project_data: Dict) -> Project:
        """Create or update a project record"""
        with self.get_session() as session:
            # Try to find existing project by name or slug
            project = session.query(Project).filter(
                Project.user_id == user_id,
                Project.name == project_data.get('name')
            ).first()
            
            if project:
                # Update existing project
                for key, value in project_data.items():
                    if hasattr(project, key) and value is not None:
                        setattr(project, key, value)
                project.last_activity = datetime.utcnow()
                project.total_emails += 1
                project.updated_at = datetime.utcnow()
            else:
                # Create new project
                project = Project(
                    user_id=user_id,
                    **project_data,
                    total_emails=1,
                    updated_at=datetime.utcnow()
                )
                session.add(project)
            
            session.commit()
            session.refresh(project)
            return project
    
    def get_user_people(self, user_id: int, limit: int = 500) -> List[Person]:
        """Get people for a user"""
        with self.get_session() as session:
            query = session.query(Person).filter(Person.user_id == user_id)
            query = query.order_by(Person.last_interaction.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_user_projects(self, user_id: int, status: str = None, limit: int = 200) -> List[Project]:
        """Get projects for a user"""
        with self.get_session() as session:
            query = session.query(Project).filter(Project.user_id == user_id)
            if status:
                query = query.filter(Project.status == status)
            query = query.order_by(Project.last_activity.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def find_person_by_email(self, user_id: int, email: str) -> Optional[Person]:
        """Find person by email address"""
        with self.get_session() as session:
            return session.query(Person).filter(
                Person.user_id == user_id,
                Person.email_address == email
            ).first()
    
    def find_project_by_keywords(self, user_id: int, keywords: List[str]) -> Optional[Project]:
        """Find project by matching keywords against name, description, or topics - FIXED to prevent memory issues"""
        with self.get_session() as session:
            # CRITICAL FIX: Add limit to prevent loading too many projects
            projects = session.query(Project).filter(Project.user_id == user_id).limit(50).all()
            
            for project in projects:
                # Check name and description
                if any(keyword.lower() in (project.name or '').lower() for keyword in keywords):
                    return project
                if any(keyword.lower() in (project.description or '').lower() for keyword in keywords):
                    return project
                
                # Check key topics
                if project.key_topics:
                    project_topics = [topic.lower() for topic in project.key_topics]
                    if any(keyword.lower() in project_topics for keyword in keywords):
                        return project
            
            return None

    def get_user_topics(self, user_id: int, limit: int = 1000) -> List[Topic]:
        """Get all topics for a user"""
        with self.get_session() as session:
            return session.query(Topic).filter(
                Topic.user_id == user_id
            ).order_by(Topic.is_official.desc(), Topic.name.asc()).limit(limit).all()
    
    def create_or_update_topic(self, user_id: int, topic_data: Dict) -> Topic:
        """Create or update a topic record"""
        with self.get_session() as session:
            # Try to find existing topic by name
            topic = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.name == topic_data.get('name')
            ).first()
            
            # Handle keywords conversion to JSON string
            topic_data_copy = topic_data.copy()
            if 'keywords' in topic_data_copy and isinstance(topic_data_copy['keywords'], list):
                topic_data_copy['keywords'] = json.dumps(topic_data_copy['keywords'])
            
            if topic:
                # Update existing topic
                for key, value in topic_data_copy.items():
                    if hasattr(topic, key) and key != 'id':
                        setattr(topic, key, value)
                topic.updated_at = datetime.now()
            else:
                # Create new topic
                topic_data_copy['user_id'] = user_id
                topic_data_copy['created_at'] = datetime.now()
                topic_data_copy['updated_at'] = datetime.now()
                
                # Set default values for optional fields
                if 'slug' not in topic_data_copy:
                    topic_data_copy['slug'] = topic_data_copy['name'].lower().replace(' ', '-').replace('_', '-')
                
                if 'is_official' not in topic_data_copy:
                    topic_data_copy['is_official'] = False
                    
                if 'confidence_score' not in topic_data_copy:
                    topic_data_copy['confidence_score'] = 0.5
                    
                if 'email_count' not in topic_data_copy:
                    topic_data_copy['email_count'] = 0
                
                topic = Topic(**topic_data_copy)
                session.add(topic)
            
            session.commit()
            session.refresh(topic)
            return topic

    def update_topic(self, user_id: int, topic_id: int, topic_data: Dict) -> bool:
        """Update a specific topic by ID"""
        with self.get_session() as session:
            topic = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.id == topic_id
            ).first()
            
            if not topic:
                return False
            
            # Handle keywords conversion to JSON string
            for key, value in topic_data.items():
                if hasattr(topic, key) and value is not None:
                    if key == 'keywords' and isinstance(value, list):
                        setattr(topic, key, json.dumps(value))
                    else:
                        setattr(topic, key, value)
            
            topic.updated_at = datetime.utcnow()
            session.commit()
            return True

    def mark_topic_official(self, user_id: int, topic_id: int) -> bool:
        """Mark a topic as official"""
        with self.get_session() as session:
            topic = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.id == topic_id
            ).first()
            
            if not topic:
                return False
            
            topic.is_official = True
            topic.updated_at = datetime.utcnow()
            session.commit()
            return True

    def merge_topics(self, user_id: int, source_topic_id: int, target_topic_id: int) -> bool:
        """Merge one topic into another"""
        with self.get_session() as session:
            source_topic = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.id == source_topic_id
            ).first()
            
            target_topic = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.id == target_topic_id
            ).first()
            
            if not source_topic or not target_topic:
                return False
            
            try:
                # Update all emails that reference the source topic
                # This is a simplified version - in practice, you'd need to update
                # the topics JSON array in emails to replace source with target
                
                # For now, we'll merge the email counts and keywords
                target_topic.email_count = (target_topic.email_count or 0) + (source_topic.email_count or 0)
                
                # Merge keywords
                source_keywords = json.loads(source_topic.keywords) if source_topic.keywords else []
                target_keywords = json.loads(target_topic.keywords) if target_topic.keywords else []
                merged_keywords = list(set(source_keywords + target_keywords))
                target_topic.keywords = json.dumps(merged_keywords)
                
                # Update merge tracking
                merged_topics = json.loads(target_topic.merged_topics) if target_topic.merged_topics else []
                merged_topics.append(source_topic.name)
                target_topic.merged_topics = json.dumps(merged_topics)
                
                target_topic.updated_at = datetime.utcnow()
                
                # Delete the source topic
                session.delete(source_topic)
                session.commit()
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to merge topics: {str(e)}")
                return False

# Global database manager instance - Initialize lazily
_db_manager = None

def get_db_manager():
    """Get the global database manager instance (lazy initialization)"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

# Export as db_manager for compatibility, but don't instantiate during import
db_manager = None  # Will be set by get_db_manager() when first called 