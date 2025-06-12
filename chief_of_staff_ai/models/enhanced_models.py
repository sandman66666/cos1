# Enhanced Database Models for Entity-Centric Intelligence

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Table, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()

# Association Tables for Many-to-Many Relationships
person_topic_association = Table(
    'person_topics',
    Base.metadata,
    Column('person_id', Integer, ForeignKey('people.id')),
    Column('topic_id', Integer, ForeignKey('topics.id')),
    Column('affinity_score', Float, default=0.5),  # How connected this person is to this topic
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('last_interaction', DateTime, default=datetime.utcnow)
)

task_topic_association = Table(
    'task_topics',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id')),
    Column('topic_id', Integer, ForeignKey('topics.id')),
    Column('relevance_score', Float, default=0.5),
    Column('created_at', DateTime, default=datetime.utcnow)
)

event_topic_association = Table(
    'event_topics', 
    Base.metadata,
    Column('event_id', Integer, ForeignKey('calendar_events.id')),
    Column('topic_id', Integer, ForeignKey('topics.id')),
    Column('relevance_score', Float, default=0.5),
    Column('created_at', DateTime, default=datetime.utcnow)
)

class Topic(Base):
    """Topics as the central brain - persistent memory containers"""
    __tablename__ = 'topics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    keywords = Column(Text)  # Comma-separated for now, can be normalized later
    is_official = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.5)
    
    # Intelligence accumulation fields
    total_mentions = Column(Integer, default=0)
    last_mentioned = Column(DateTime)
    intelligence_summary = Column(Text)  # AI-generated summary of what we know about this topic
    strategic_importance = Column(Float, default=0.5)  # How important this topic is to the user
    
    # Topic evolution tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)  # Track topic evolution
    
    # Relationships - Topics as the central hub
    people = relationship("Person", secondary=person_topic_association, back_populates="topics")
    tasks = relationship("Task", secondary=task_topic_association, back_populates="topics")
    events = relationship("CalendarEvent", secondary=event_topic_association, back_populates="topics")
    
    # Direct content relationships
    emails = relationship("Email", back_populates="primary_topic")
    projects = relationship("Project", back_populates="primary_topic")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'keywords': json.loads(self.keywords) if self.keywords else [],
            'is_official': self.is_official,
            'confidence_score': self.confidence_score,
            'total_mentions': self.total_mentions,
            'last_mentioned': self.last_mentioned.isoformat() if self.last_mentioned else None,
            'intelligence_summary': self.intelligence_summary,
            'strategic_importance': self.strategic_importance,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }

class Person(Base):
    """Enhanced Person model with relationship intelligence"""
    __tablename__ = 'people'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(200), nullable=False)
    email_address = Column(String(255))
    phone = Column(String(50))
    company = Column(String(200))
    title = Column(String(200))
    
    # Relationship intelligence
    relationship_type = Column(String(100))  # colleague, client, partner, etc.
    importance_level = Column(Float, default=0.5)
    communication_frequency = Column(String(50))  # daily, weekly, monthly, etc.
    last_contact = Column(DateTime)
    total_interactions = Column(Integer, default=0)
    
    # Professional context (extracted from signatures, etc.)
    linkedin_url = Column(String(255))
    bio = Column(Text)
    professional_story = Column(Text)  # AI-generated summary of professional relationship
    
    # Intelligence accumulation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topics = relationship("Topic", secondary=person_topic_association, back_populates="people")
    tasks_assigned = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    tasks_mentioned = relationship("Task", foreign_keys="Task.mentioned_person_id", back_populates="mentioned_person")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email_address': self.email_address,
            'phone': self.phone,
            'company': self.company,
            'title': self.title,
            'relationship_type': self.relationship_type,
            'importance_level': self.importance_level,
            'communication_frequency': self.communication_frequency,
            'last_contact': self.last_contact.isoformat() if self.last_contact else None,
            'total_interactions': self.total_interactions,
            'linkedin_url': self.linkedin_url,
            'bio': self.bio,
            'professional_story': self.professional_story,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Task(Base):
    """Enhanced Task model with full context"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    description = Column(Text, nullable=False)
    context_story = Column(Text)  # WHY this task exists - the narrative context
    
    # Assignments and ownership
    assignee_id = Column(Integer, ForeignKey('people.id'))
    mentioned_person_id = Column(Integer, ForeignKey('people.id'))  # Person mentioned in task
    
    # Task metadata
    priority = Column(String(20), default='medium')
    status = Column(String(20), default='pending')
    category = Column(String(100))
    confidence = Column(Float, default=0.8)
    
    # Source tracking
    source_email_id = Column(Integer, ForeignKey('emails.id'))
    source_event_id = Column(Integer, ForeignKey('calendar_events.id'))
    
    # Temporal information
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    topics = relationship("Topic", secondary=task_topic_association, back_populates="tasks")
    assignee = relationship("Person", foreign_keys=[assignee_id], back_populates="tasks_assigned")
    mentioned_person = relationship("Person", foreign_keys=[mentioned_person_id], back_populates="tasks_mentioned")
    source_email = relationship("Email", back_populates="generated_tasks")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'description': self.description,
            'context_story': self.context_story,
            'assignee_id': self.assignee_id,
            'mentioned_person_id': self.mentioned_person_id,
            'priority': self.priority,
            'status': self.status,
            'category': self.category,
            'confidence': self.confidence,
            'source_email_id': self.source_email_id,
            'source_event_id': self.source_event_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class Email(Base):
    """Streamlined Email model focused on intelligence, not storage"""
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    gmail_id = Column(String(255), unique=True, nullable=False)
    
    # Essential metadata only
    subject = Column(String(500))
    sender = Column(String(255))
    sender_name = Column(String(255))
    recipient_emails = Column(Text)  # JSON array of recipients
    email_date = Column(DateTime)
    
    # Intelligence fields
    ai_summary = Column(Text)  # Concise summary for display
    business_category = Column(String(100))  # meeting, project, decision, etc.
    sentiment = Column(String(50))
    urgency_score = Column(Float, default=0.5)
    strategic_importance = Column(Float, default=0.5)
    
    # Content storage strategy: metadata in DB, content in blob storage
    content_hash = Column(String(64))  # SHA-256 of content for deduplication
    blob_storage_key = Column(String(255))  # Reference to external content storage
    
    # Primary topic assignment (Topics as brain concept)
    primary_topic_id = Column(Integer, ForeignKey('topics.id'))
    
    # Processing metadata
    processed_at = Column(DateTime)
    processing_version = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    primary_topic = relationship("Topic", back_populates="emails")
    generated_tasks = relationship("Task", back_populates="source_email")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'gmail_id': self.gmail_id,
            'subject': self.subject,
            'sender': self.sender,
            'sender_name': self.sender_name,
            'recipient_emails': json.loads(self.recipient_emails) if self.recipient_emails else [],
            'email_date': self.email_date.isoformat() if self.email_date else None,
            'ai_summary': self.ai_summary,
            'business_category': self.business_category,
            'sentiment': self.sentiment,
            'urgency_score': self.urgency_score,
            'strategic_importance': self.strategic_importance,
            'content_hash': self.content_hash,
            'blob_storage_key': self.blob_storage_key,
            'primary_topic_id': self.primary_topic_id,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processing_version': self.processing_version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CalendarEvent(Base):
    """Enhanced Calendar model with business intelligence"""
    __tablename__ = 'calendar_events'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    google_event_id = Column(String(255), unique=True, nullable=False)
    
    # Event basics
    title = Column(String(500))
    description = Column(Text)
    location = Column(String(500))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    # Business intelligence
    business_context = Column(Text)  # AI-generated context about meeting purpose
    attendee_intelligence = Column(Text)  # Summary of known attendees and relationships
    preparation_priority = Column(Float, default=0.5)  # How important prep is for this meeting
    
    # Meeting outcome tracking
    outcome_summary = Column(Text)  # Post-meeting AI analysis
    follow_up_needed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topics = relationship("Topic", secondary=event_topic_association, back_populates="events")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'google_event_id': self.google_event_id,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'business_context': self.business_context,
            'attendee_intelligence': self.attendee_intelligence,
            'preparation_priority': self.preparation_priority,
            'outcome_summary': self.outcome_summary,
            'follow_up_needed': self.follow_up_needed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Project(Base):
    """Projects as coherent business initiatives"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='active')
    priority = Column(String(20), default='medium')
    
    # Project intelligence
    stakeholder_summary = Column(Text)  # AI summary of key people involved
    objective = Column(Text)
    current_phase = Column(String(100))
    challenges = Column(Text)
    opportunities = Column(Text)
    
    # Primary topic assignment
    primary_topic_id = Column(Integer, ForeignKey('topics.id'))
    
    # Timeline
    start_date = Column(DateTime)
    target_completion = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    primary_topic = relationship("Topic", back_populates="projects")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'stakeholder_summary': self.stakeholder_summary,
            'objective': self.objective,
            'current_phase': self.current_phase,
            'challenges': self.challenges,
            'opportunities': self.opportunities,
            'primary_topic_id': self.primary_topic_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'target_completion': self.target_completion.isoformat() if self.target_completion else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class EntityRelationship(Base):
    """Track relationships between any entities for advanced intelligence"""
    __tablename__ = 'entity_relationships'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Generic entity references
    entity_type_a = Column(String(50), nullable=False)  # person, topic, project, etc.
    entity_id_a = Column(Integer, nullable=False)
    entity_type_b = Column(String(50), nullable=False)
    entity_id_b = Column(Integer, nullable=False)
    
    # Relationship metadata
    relationship_type = Column(String(100))  # collaborates_on, leads, discusses, etc.
    strength = Column(Float, default=0.5)  # How strong this relationship is
    frequency = Column(String(50))  # How often they interact
    
    # Intelligence context
    context_summary = Column(Text)  # AI summary of this relationship
    last_interaction = Column(DateTime)
    total_interactions = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'entity_type_a': self.entity_type_a,
            'entity_id_a': self.entity_id_a,
            'entity_type_b': self.entity_type_b,
            'entity_id_b': self.entity_id_b,
            'relationship_type': self.relationship_type,
            'strength': self.strength,
            'frequency': self.frequency,
            'context_summary': self.context_summary,
            'last_interaction': self.last_interaction.isoformat() if self.last_interaction else None,
            'total_interactions': self.total_interactions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class IntelligenceInsight(Base):
    """Capture proactive insights generated by the system"""
    __tablename__ = 'intelligence_insights'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Insight metadata
    insight_type = Column(String(100), nullable=False)  # relationship_alert, opportunity, decision_needed
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default='medium')
    confidence = Column(Float, default=0.8)
    
    # Entity connections
    related_entity_type = Column(String(50))  # What entity triggered this insight
    related_entity_id = Column(Integer)
    
    # User interaction
    status = Column(String(50), default='new')  # new, viewed, acted_on, dismissed
    user_feedback = Column(String(50))  # helpful, not_helpful, etc.
    
    # Temporal
    expires_at = Column(DateTime)  # Some insights are time-sensitive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'insight_type': self.insight_type,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'confidence': self.confidence,
            'related_entity_type': self.related_entity_type,
            'related_entity_id': self.related_entity_id,
            'status': self.status,
            'user_feedback': self.user_feedback,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Migration strategy: Create these tables alongside existing ones,
# then populate with data transformation scripts 