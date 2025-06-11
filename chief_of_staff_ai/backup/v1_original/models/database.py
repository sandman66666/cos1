import os
import json
import logging
from datetime import datetime, timedelta
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
    
    # NEW: Smart Contact Strategy fields
    is_trusted_contact = Column(Boolean, default=False, index=True)
    engagement_score = Column(Float, default=0.0)
    bidirectional_topics = Column(JSONType)  # Topics with back-and-forth discussion
    
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
            'ai_version': self.ai_version,
            'is_trusted_contact': self.is_trusted_contact,
            'engagement_score': self.engagement_score,
            'bidirectional_topics': self.bidirectional_topics
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

class TrustedContact(Base):
    """Trusted Contact model for engagement-based contact database"""
    __tablename__ = 'trusted_contacts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Contact identification
    email_address = Column(String(255), nullable=False, index=True)
    name = Column(String(255))
    
    # Engagement metrics
    engagement_score = Column(Float, default=0.0, index=True)
    first_sent_date = Column(DateTime)
    last_sent_date = Column(DateTime, index=True)
    total_sent_emails = Column(Integer, default=0)
    total_received_emails = Column(Integer, default=0)
    bidirectional_threads = Column(Integer, default=0)
    
    # Topic analysis
    topics_discussed = Column(JSONType)  # List of topics from sent/received emails
    bidirectional_topics = Column(JSONType)  # Topics with back-and-forth discussion
    
    # Relationship assessment
    relationship_strength = Column(String(20), default='low', index=True)  # high, medium, low
    communication_frequency = Column(String(20))  # daily, weekly, monthly, occasional
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed = Column(DateTime)
    
    # Relationships
    user = relationship("User", backref="trusted_contacts")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_trusted_contact_user_email', 'user_id', 'email_address'),
        Index('idx_trusted_contact_engagement', 'user_id', 'engagement_score'),
        Index('idx_trusted_contact_strength', 'user_id', 'relationship_strength'),
    )
    
    def __repr__(self):
        return f"<TrustedContact(email='{self.email_address}', strength='{self.relationship_strength}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_address': self.email_address,
            'name': self.name,
            'engagement_score': self.engagement_score,
            'first_sent_date': self.first_sent_date.isoformat() if self.first_sent_date else None,
            'last_sent_date': self.last_sent_date.isoformat() if self.last_sent_date else None,
            'total_sent_emails': self.total_sent_emails,
            'total_received_emails': self.total_received_emails,
            'bidirectional_threads': self.bidirectional_threads,
            'topics_discussed': self.topics_discussed,
            'bidirectional_topics': self.bidirectional_topics,
            'relationship_strength': self.relationship_strength,
            'communication_frequency': self.communication_frequency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_analyzed': self.last_analyzed.isoformat() if self.last_analyzed else None
        }

class ContactContext(Base):
    """Rich context information for contacts"""
    __tablename__ = 'contact_contexts'
    
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Context details
    context_type = Column(String(50), nullable=False, index=True)  # communication_pattern, project_involvement, topic_expertise, relationship_notes
    title = Column(String(255), nullable=False)
    description = Column(Text)
    confidence_score = Column(Float, default=0.5)
    
    # Supporting evidence
    source_emails = Column(JSONType)  # List of email IDs that contributed to this context
    supporting_quotes = Column(JSONType)  # Relevant excerpts from emails
    tags = Column(JSONType)  # Flexible tagging system
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    person = relationship("Person", backref="contexts")
    user = relationship("User", backref="contact_contexts")
    
    # Indexes
    __table_args__ = (
        Index('idx_contact_context_person', 'person_id', 'context_type'),
        Index('idx_contact_context_user', 'user_id', 'context_type'),
    )
    
    def __repr__(self):
        return f"<ContactContext(type='{self.context_type}', title='{self.title}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'person_id': self.person_id,
            'user_id': self.user_id,
            'context_type': self.context_type,
            'title': self.title,
            'description': self.description,
            'confidence_score': self.confidence_score,
            'source_emails': self.source_emails,
            'supporting_quotes': self.supporting_quotes,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TaskContext(Base):
    """Rich context information for tasks"""
    __tablename__ = 'task_contexts'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Context details
    context_type = Column(String(50), nullable=False, index=True)  # background, stakeholders, timeline, business_impact
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Related entities
    related_people = Column(JSONType)  # List of person IDs
    related_projects = Column(JSONType)  # List of project IDs
    related_topics = Column(JSONType)  # List of relevant topics
    
    # Source information
    source_email_id = Column(Integer, ForeignKey('emails.id'))
    source_thread_id = Column(String(255))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", backref="contexts")
    user = relationship("User", backref="task_contexts")
    source_email = relationship("Email")
    
    # Indexes
    __table_args__ = (
        Index('idx_task_context_task', 'task_id', 'context_type'),
        Index('idx_task_context_user', 'user_id', 'context_type'),
    )
    
    def __repr__(self):
        return f"<TaskContext(type='{self.context_type}', title='{self.title}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'context_type': self.context_type,
            'title': self.title,
            'description': self.description,
            'related_people': self.related_people,
            'related_projects': self.related_projects,
            'related_topics': self.related_topics,
            'source_email_id': self.source_email_id,
            'source_thread_id': self.source_thread_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TopicKnowledgeBase(Base):
    """Comprehensive knowledge base for topics"""
    __tablename__ = 'topic_knowledge_base'
    
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Knowledge details
    knowledge_type = Column(String(50), nullable=False, index=True)  # methodology, key_people, challenges, success_patterns, tools, decisions
    title = Column(String(255), nullable=False)
    content = Column(Text)
    confidence_score = Column(Float, default=0.5)
    
    # Supporting evidence
    supporting_evidence = Column(JSONType)  # Email excerpts, patterns observed
    source_emails = Column(JSONType)  # List of email IDs that contributed
    patterns = Column(JSONType)  # Observed patterns and trends
    
    # Knowledge metadata
    relevance_score = Column(Float, default=0.5)  # How relevant this knowledge is
    engagement_weight = Column(Float, default=0.5)  # Weight based on user engagement
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topic = relationship("Topic", backref="knowledge_base")
    user = relationship("User", backref="topic_knowledge")
    
    # Indexes
    __table_args__ = (
        Index('idx_topic_knowledge_topic', 'topic_id', 'knowledge_type'),
        Index('idx_topic_knowledge_user', 'user_id', 'knowledge_type'),
        Index('idx_topic_knowledge_relevance', 'user_id', 'relevance_score'),
    )
    
    def __repr__(self):
        return f"<TopicKnowledgeBase(type='{self.knowledge_type}', title='{self.title}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'topic_id': self.topic_id,
            'user_id': self.user_id,
            'knowledge_type': self.knowledge_type,
            'title': self.title,
            'content': self.content,
            'confidence_score': self.confidence_score,
            'supporting_evidence': self.supporting_evidence,
            'source_emails': self.source_emails,
            'patterns': self.patterns,
            'relevance_score': self.relevance_score,
            'engagement_weight': self.engagement_weight,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class Calendar(Base):
    """Calendar model for storing Google Calendar events per user"""
    __tablename__ = 'calendar_events'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Google Calendar identifiers
    event_id = Column(String(255), nullable=False, index=True)
    calendar_id = Column(String(255), nullable=False, index=True)
    recurring_event_id = Column(String(255), index=True)
    
    # Event content
    title = Column(Text)
    description = Column(Text)
    location = Column(Text)
    status = Column(String(50))  # confirmed, tentative, cancelled
    
    # Event timing
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, index=True)
    timezone = Column(String(100))
    is_all_day = Column(Boolean, default=False)
    
    # Attendees and relationships
    organizer_email = Column(String(255), index=True)
    organizer_name = Column(String(255))
    attendees = Column(JSONType)  # List of attendee objects with email, name, status
    attendee_emails = Column(JSONType)  # List of attendee emails for quick lookup
    
    # Meeting metadata
    meeting_type = Column(String(100))  # in-person, video_call, phone, etc.
    conference_data = Column(JSONType)  # Google Meet, Zoom links, etc.
    visibility = Column(String(50))  # default, public, private
    
    # Event properties
    is_recurring = Column(Boolean, default=False)
    recurrence_rules = Column(JSONType)  # RRULE data
    is_busy = Column(Boolean, default=True)
    transparency = Column(String(20))  # opaque, transparent
    
    # AI analysis and insights
    ai_summary = Column(Text)  # Claude-generated meeting summary/purpose
    ai_category = Column(String(100))  # AI-determined category (business, personal, etc.)
    importance_score = Column(Float)  # AI-determined importance
    preparation_needed = Column(Boolean, default=False)
    follow_up_required = Column(Boolean, default=False)
    
    # Contact intelligence integration
    known_attendees = Column(JSONType)  # List of person IDs from People table
    unknown_attendees = Column(JSONType)  # Attendees not in contact database
    business_context = Column(Text)  # AI-generated business context based on attendees
    
    # Free time analysis
    is_free_time = Column(Boolean, default=False, index=True)  # For free time slot identification
    potential_duration = Column(Integer)  # Duration in minutes for free slots
    
    # Processing metadata
    fetched_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ai_processed_at = Column(DateTime)
    ai_version = Column(String(50))
    
    # Google Calendar metadata
    html_link = Column(Text)  # Link to event in Google Calendar
    hangout_link = Column(Text)  # Google Meet link
    ical_uid = Column(String(255))
    sequence = Column(Integer)  # For tracking updates
    
    # Relationships
    user = relationship("User", backref="calendar_events")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_calendar_user_event', 'user_id', 'event_id'),
        Index('idx_calendar_user_time', 'user_id', 'start_time'),
        Index('idx_calendar_user_organizer', 'user_id', 'organizer_email'),
        Index('idx_calendar_free_time', 'user_id', 'is_free_time'),
        Index('idx_calendar_status', 'user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Calendar(event_id='{self.event_id}', title='{self.title}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_id': self.event_id,
            'calendar_id': self.calendar_id,
            'recurring_event_id': self.recurring_event_id,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'timezone': self.timezone,
            'is_all_day': self.is_all_day,
            'organizer_email': self.organizer_email,
            'organizer_name': self.organizer_name,
            'attendees': self.attendees,
            'attendee_emails': self.attendee_emails,
            'meeting_type': self.meeting_type,
            'conference_data': self.conference_data,
            'visibility': self.visibility,
            'is_recurring': self.is_recurring,
            'recurrence_rules': self.recurrence_rules,
            'is_busy': self.is_busy,
            'transparency': self.transparency,
            'ai_summary': self.ai_summary,
            'ai_category': self.ai_category,
            'importance_score': self.importance_score,
            'preparation_needed': self.preparation_needed,
            'follow_up_required': self.follow_up_required,
            'known_attendees': self.known_attendees,
            'unknown_attendees': self.unknown_attendees,
            'business_context': self.business_context,
            'is_free_time': self.is_free_time,
            'potential_duration': self.potential_duration,
            'fetched_at': self.fetched_at.isoformat() if self.fetched_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'ai_processed_at': self.ai_processed_at.isoformat() if self.ai_processed_at else None,
            'ai_version': self.ai_version,
            'html_link': self.html_link,
            'hangout_link': self.hangout_link,
            'ical_uid': self.ical_uid,
            'sequence': self.sequence
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
        try:
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
                
                # Verify the task object is valid before returning
                if not task or not hasattr(task, 'id') or task.id is None:
                    raise ValueError("Failed to create task - invalid task object returned")
                
                return task
                
        except Exception as e:
            logger.error(f"Failed to save task to database: {str(e)}")
            logger.error(f"Task data: {task_data}")
            raise  # Re-raise the exception instead of returning a dict
    
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
                # Create new person - remove conflicting fields from person_data
                person_data_clean = person_data.copy()
                person_data_clean.pop('total_emails', None)  # Remove if present
                person_data_clean.pop('last_updated_by_ai', None)  # Remove if present
                
                person = Person(
                    user_id=user_id,
                    **person_data_clean,
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

    # ===== SMART CONTACT STRATEGY METHODS =====
    
    def create_or_update_trusted_contact(self, user_id: int, contact_data: Dict) -> TrustedContact:
        """Create or update a trusted contact record"""
        with self.get_session() as session:
            contact = session.query(TrustedContact).filter(
                TrustedContact.user_id == user_id,
                TrustedContact.email_address == contact_data['email_address']
            ).first()
            
            if contact:
                # Update existing contact
                for key, value in contact_data.items():
                    if hasattr(contact, key) and value is not None:
                        setattr(contact, key, value)
                contact.updated_at = datetime.utcnow()
            else:
                # Create new trusted contact
                contact = TrustedContact(
                    user_id=user_id,
                    **contact_data,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(contact)
            
            session.commit()
            session.refresh(contact)
            return contact
    
    def get_trusted_contacts(self, user_id: int, limit: int = 500) -> List[TrustedContact]:
        """Get trusted contacts for a user"""
        with self.get_session() as session:
            return session.query(TrustedContact).filter(
                TrustedContact.user_id == user_id
            ).order_by(TrustedContact.engagement_score.desc()).limit(limit).all()
    
    def find_trusted_contact_by_email(self, user_id: int, email_address: str) -> Optional[TrustedContact]:
        """Find trusted contact by email address"""
        with self.get_session() as session:
            return session.query(TrustedContact).filter(
                TrustedContact.user_id == user_id,
                TrustedContact.email_address == email_address
            ).first()
    
    def create_contact_context(self, user_id: int, person_id: int, context_data: Dict) -> ContactContext:
        """Create a new contact context record"""
        with self.get_session() as session:
            context = ContactContext(
                user_id=user_id,
                person_id=person_id,
                **context_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(context)
            session.commit()
            session.refresh(context)
            return context
    
    def get_contact_contexts(self, user_id: int, person_id: int = None, context_type: str = None) -> List[ContactContext]:
        """Get contact contexts for a user, optionally filtered by person or type"""
        with self.get_session() as session:
            query = session.query(ContactContext).filter(ContactContext.user_id == user_id)
            
            if person_id:
                query = query.filter(ContactContext.person_id == person_id)
            
            if context_type:
                query = query.filter(ContactContext.context_type == context_type)
            
            return query.order_by(ContactContext.created_at.desc()).all()
    
    def create_task_context(self, user_id: int, task_id: int, context_data: Dict) -> TaskContext:
        """Create a new task context record"""
        with self.get_session() as session:
            context = TaskContext(
                user_id=user_id,
                task_id=task_id,
                **context_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(context)
            session.commit()
            session.refresh(context)
            return context
    
    def get_task_contexts(self, user_id: int, task_id: int = None, context_type: str = None) -> List[TaskContext]:
        """Get task contexts for a user, optionally filtered by task or type"""
        with self.get_session() as session:
            query = session.query(TaskContext).filter(TaskContext.user_id == user_id)
            
            if task_id:
                query = query.filter(TaskContext.task_id == task_id)
            
            if context_type:
                query = query.filter(TaskContext.context_type == context_type)
            
            return query.order_by(TaskContext.created_at.desc()).all()
    
    def create_topic_knowledge(self, user_id: int, topic_id: int, knowledge_data: Dict) -> TopicKnowledgeBase:
        """Create a new topic knowledge record"""
        with self.get_session() as session:
            knowledge = TopicKnowledgeBase(
                user_id=user_id,
                topic_id=topic_id,
                **knowledge_data,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            session.add(knowledge)
            session.commit()
            session.refresh(knowledge)
            return knowledge
    
    def get_topic_knowledge(self, user_id: int, topic_id: int = None, knowledge_type: str = None) -> List[TopicKnowledgeBase]:
        """Get topic knowledge for a user, optionally filtered by topic or type"""
        with self.get_session() as session:
            query = session.query(TopicKnowledgeBase).filter(TopicKnowledgeBase.user_id == user_id)
            
            if topic_id:
                query = query.filter(TopicKnowledgeBase.topic_id == topic_id)
            
            if knowledge_type:
                query = query.filter(TopicKnowledgeBase.knowledge_type == knowledge_type)
            
            return query.order_by(TopicKnowledgeBase.relevance_score.desc()).all()
    
    def update_people_engagement_data(self, user_id: int, person_id: int, engagement_data: Dict) -> bool:
        """Update people table with engagement-based data"""
        with self.get_session() as session:
            person = session.query(Person).filter(
                Person.user_id == user_id,
                Person.id == person_id
            ).first()
            
            if not person:
                return False
            
            # Add engagement fields to person if they don't exist
            if 'is_trusted_contact' in engagement_data:
                person.is_trusted_contact = engagement_data['is_trusted_contact']
            
            if 'engagement_score' in engagement_data:
                person.engagement_score = engagement_data['engagement_score']
            
            if 'bidirectional_topics' in engagement_data:
                person.bidirectional_topics = engagement_data['bidirectional_topics']
            
            session.commit()
            return True
    
    def get_engagement_analytics(self, user_id: int) -> Dict:
        """Get engagement analytics for Smart Contact Strategy reporting"""
        with self.get_session() as session:
            total_contacts = session.query(TrustedContact).filter(TrustedContact.user_id == user_id).count()
            high_engagement = session.query(TrustedContact).filter(
                TrustedContact.user_id == user_id,
                TrustedContact.relationship_strength == 'high'
            ).count()
            
            recent_contacts = session.query(TrustedContact).filter(
                TrustedContact.user_id == user_id,
                TrustedContact.last_sent_date >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            return {
                'total_trusted_contacts': total_contacts,
                'high_engagement_contacts': high_engagement,
                'recent_active_contacts': recent_contacts,
                'engagement_rate': (high_engagement / total_contacts * 100) if total_contacts > 0 else 0
            }

    def save_calendar_event(self, user_id: int, event_data: Dict) -> Calendar:
        """Save or update a calendar event"""
        try:
            with self.get_session() as session:
                # Try to find existing event
                existing_event = session.query(Calendar).filter_by(
                    user_id=user_id,
                    event_id=event_data.get('event_id')
                ).first()
                
                if existing_event:
                    # Update existing event
                    for key, value in event_data.items():
                        if hasattr(existing_event, key):
                            setattr(existing_event, key, value)
                    event = existing_event
                else:
                    # Create new event
                    event = Calendar(user_id=user_id, **event_data)
                    session.add(event)
                
                session.commit()
                session.refresh(event)
                return event
                
        except Exception as e:
            logger.error(f"Failed to save calendar event: {str(e)}")
            raise

    def get_user_calendar_events(self, user_id: int, start_date: datetime = None, end_date: datetime = None, limit: int = 500) -> List[Calendar]:
        """Get calendar events for a user within a date range"""
        try:
            with self.get_session() as session:
                query = session.query(Calendar).filter_by(user_id=user_id)
                
                if start_date:
                    query = query.filter(Calendar.start_time >= start_date)
                if end_date:
                    query = query.filter(Calendar.start_time <= end_date)
                
                events = query.order_by(Calendar.start_time.asc()).limit(limit).all()
                return events
                
        except Exception as e:
            logger.error(f"Failed to get user calendar events: {str(e)}")
            return []

    def get_free_time_slots(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Identify free time slots between calendar events"""
        try:
            with self.get_session() as session:
                events = session.query(Calendar).filter(
                    Calendar.user_id == user_id,
                    Calendar.start_time >= start_date,
                    Calendar.start_time <= end_date,
                    Calendar.status.in_(['confirmed', 'tentative']),
                    Calendar.is_busy == True
                ).order_by(Calendar.start_time).all()
                
                free_slots = []
                current_time = start_date
                
                for event in events:
                    # If there's a gap before this event, it's free time
                    if event.start_time > current_time:
                        gap_duration = int((event.start_time - current_time).total_seconds() / 60)
                        if gap_duration >= 30:  # Minimum 30 minutes to be useful
                            free_slots.append({
                                'start_time': current_time,
                                'end_time': event.start_time,
                                'duration_minutes': gap_duration,
                                'type': 'free_time'
                            })
                    
                    # Update current time to end of this event
                    if event.end_time and event.end_time > current_time:
                        current_time = event.end_time
                
                # Check for free time after last event
                if current_time < end_date:
                    gap_duration = int((end_date - current_time).total_seconds() / 60)
                    if gap_duration >= 30:
                        free_slots.append({
                            'start_time': current_time,
                            'end_time': end_date,
                            'duration_minutes': gap_duration,
                            'type': 'free_time'
                        })
                
                return free_slots
                
        except Exception as e:
            logger.error(f"Failed to get free time slots: {str(e)}")
            return []

    def get_calendar_attendee_intelligence(self, user_id: int, event_id: str) -> Dict:
        """Get intelligence about calendar event attendees"""
        try:
            with self.get_session() as session:
                event = session.query(Calendar).filter_by(
                    user_id=user_id,
                    event_id=event_id
                ).first()
                
                if not event or not event.attendee_emails:
                    return {}
                
                # Find known attendees in People database
                known_people = []
                unknown_attendees = []
                
                for attendee_email in event.attendee_emails:
                    person = self.find_person_by_email(user_id, attendee_email)
                    if person:
                        known_people.append(person.to_dict())
                    else:
                        unknown_attendees.append(attendee_email)
                
                return {
                    'event_id': event_id,
                    'total_attendees': len(event.attendee_emails),
                    'known_attendees': known_people,
                    'unknown_attendees': unknown_attendees,
                    'known_percentage': len(known_people) / len(event.attendee_emails) * 100 if event.attendee_emails else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get calendar attendee intelligence: {str(e)}")
            return {}

    def update_calendar_ai_analysis(self, user_id: int, event_id: str, ai_data: Dict) -> bool:
        """Update calendar event with AI analysis"""
        try:
            with self.get_session() as session:
                event = session.query(Calendar).filter_by(
                    user_id=user_id,
                    event_id=event_id
                ).first()
                
                if not event:
                    return False
                
                # Update AI analysis fields
                if 'ai_summary' in ai_data:
                    event.ai_summary = ai_data['ai_summary']
                if 'ai_category' in ai_data:
                    event.ai_category = ai_data['ai_category']
                if 'importance_score' in ai_data:
                    event.importance_score = ai_data['importance_score']
                if 'business_context' in ai_data:
                    event.business_context = ai_data['business_context']
                if 'preparation_needed' in ai_data:
                    event.preparation_needed = ai_data['preparation_needed']
                if 'follow_up_required' in ai_data:
                    event.follow_up_required = ai_data['follow_up_required']
                
                event.ai_processed_at = datetime.utcnow()
                event.ai_version = ai_data.get('ai_version', 'claude-3.5-sonnet')
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update calendar AI analysis: {str(e)}")
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