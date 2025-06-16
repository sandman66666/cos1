"""
Knowledge Models - Core Knowledge-Centric Architecture
=====================================================

This module defines the enhanced knowledge models that form the foundation
of the Knowledge Replacement System. These models enable the system to:

1. Build hierarchical topic trees (auto-generated + user-managed)
2. Track multi-source knowledge ingestion (email, slack, dropbox, etc.)
3. Create bidirectional people-topic relationships
4. Maintain source traceability for all knowledge
5. Enable auto-response and decision-making capabilities

The goal: Store enough knowledge to replace the user (up to a certain level)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

Base = declarative_base()

# ==============================================================================
# ENUMS AND TYPE DEFINITIONS
# ==============================================================================

class TopicType(Enum):
    """Types of topics in the hierarchy"""
    COMPANY = "company"
    DEPARTMENT = "department"
    PRODUCT = "product"
    PROJECT = "project"
    FEATURE = "feature"
    INITIATIVE = "initiative"
    CAMPAIGN = "campaign"
    CUSTOM = "custom"

class SourceType(Enum):
    """Sources of knowledge ingestion"""
    EMAIL = "email"
    SLACK = "slack"
    DROPBOX = "dropbox"
    CALENDAR = "calendar"
    TASK_SYSTEM = "task_system"
    USER_INPUT = "user_input"
    MEETING_NOTES = "meeting_notes"
    DOCUMENTS = "documents"

class RelationshipType(Enum):
    """Types of person-topic relationships"""
    LEAD = "lead"                    # Project/topic leader
    CONTRIBUTOR = "contributor"       # Active contributor
    STAKEHOLDER = "stakeholder"      # Has interest/influence
    REVIEWER = "reviewer"            # Reviews/approves
    MENTOR = "mentor"                # Provides guidance
    OBSERVER = "observer"            # Stays informed
    DECISION_MAKER = "decision_maker" # Makes final decisions

class KnowledgeConfidence(Enum):
    """Confidence levels for knowledge extraction"""
    HIGH = "high"         # 0.8-1.0
    MEDIUM = "medium"     # 0.5-0.8  
    LOW = "low"          # 0.2-0.5
    UNCERTAIN = "uncertain" # 0.0-0.2

# ==============================================================================
# ASSOCIATION TABLES FOR MANY-TO-MANY RELATIONSHIPS
# ==============================================================================

# People-Topic relationships with metadata
person_topic_association = Table(
    'person_topic_relationships',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('person_id', Integer, ForeignKey('enhanced_people.id')),
    Column('topic_id', Integer, ForeignKey('topic_hierarchy.id')),
    Column('relationship_type', String(50)),  # RelationshipType enum
    Column('involvement_level', Float, default=0.5),  # 0.0 to 1.0
    Column('confidence', Float, default=0.5),
    Column('first_mentioned', DateTime, default=datetime.utcnow),
    Column('last_activity', DateTime, default=datetime.utcnow),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column('source_types', JSON),  # List of SourceType enums
    Column('evidence_count', Integer, default=1),  # Number of supporting evidence
    Column('metadata', JSON)  # Additional relationship data
)

# Source content references for traceability
knowledge_source_association = Table(
    'knowledge_source_references',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('knowledge_type', String(50)),  # topic/person/task/insight
    Column('knowledge_id', Integer),
    Column('source_type', String(50)),  # SourceType enum
    Column('source_id', String(255)),  # email_id, slack_message_id, file_path, etc.
    Column('source_content_snippet', Text),  # Relevant excerpt
    Column('confidence', Float, default=0.5),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('metadata', JSON)  # Source-specific data
)

# ==============================================================================
# CORE KNOWLEDGE MODELS
# ==============================================================================

class TopicHierarchy(Base):
    """
    Hierarchical topic tree that organizes all business knowledge.
    Auto-generated from content + user-managed structure.
    """
    __tablename__ = 'topic_hierarchy'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Hierarchy structure
    parent_topic_id = Column(Integer, ForeignKey('topic_hierarchy.id'))
    topic_type = Column(String(50), default=TopicType.CUSTOM.value)  # TopicType enum
    hierarchy_path = Column(String(1000))  # "/company/engineering/mobile_app/auth"
    depth_level = Column(Integer, default=0)  # 0=root, 1=department, 2=product, etc.
    
    # Knowledge attributes
    auto_generated = Column(Boolean, default=True)
    user_created = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.5)
    strategic_importance = Column(Float, default=0.5)
    
    # Activity tracking
    mention_count = Column(Integer, default=0)
    first_mentioned = Column(DateTime, default=datetime.utcnow)
    last_mentioned = Column(DateTime, default=datetime.utcnow)
    activity_trend = Column(String(20), default='stable')  # growing/stable/declining
    
    # Status and lifecycle
    status = Column(String(50), default='active')  # active/archived/completed/cancelled
    priority = Column(String(20), default='medium')  # high/medium/low
    
    # Knowledge metadata
    keywords = Column(JSON)  # List of related keywords/aliases
    related_entities = Column(JSON)  # Related people, projects, etc.
    source_distribution = Column(JSON)  # Distribution across source types
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("TopicHierarchy", remote_side=[id], backref='children')
    people = relationship("Person", secondary=person_topic_association, back_populates="topics")
    
    def __repr__(self):
        return f"<Topic({self.name}, type={self.topic_type}, depth={self.depth_level})>"
    
    def get_full_path(self) -> str:
        """Get full hierarchical path"""
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name
    
    def get_all_children(self) -> List['TopicHierarchy']:
        """Get all descendants recursively"""
        children = list(self.children)
        for child in list(self.children):
            children.extend(child.get_all_children())
        return children
    
    def get_related_people(self, relationship_types: List[str] = None) -> List['Person']:
        """Get people related to this topic with optional filtering"""
        if not relationship_types:
            return self.people
        
        # Would need to query the association table for filtered results
        return [p for p in self.people if p.get_relationship_type(self.id) in relationship_types]

class PersonTopicRelationship(Base):
    """
    Enhanced person-topic relationships with detailed metadata.
    This enables bidirectional knowledge queries.
    """
    __tablename__ = 'person_topic_relationships_detailed'
    
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('enhanced_people.id'), nullable=False)
    topic_id = Column(Integer, ForeignKey('topic_hierarchy.id'), nullable=False)
    
    # Relationship details
    relationship_type = Column(String(50), default=RelationshipType.CONTRIBUTOR.value)
    involvement_level = Column(Float, default=0.5)  # 0.0 to 1.0
    confidence = Column(String(20), default=KnowledgeConfidence.MEDIUM.value)
    
    # Activity tracking
    first_mentioned = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    evidence_count = Column(Integer, default=1)
    activity_frequency = Column(Float, default=0.0)  # mentions per week
    
    # Source attribution
    source_types = Column(JSON)  # List of SourceType enums that created this relationship
    primary_source = Column(String(50))  # Most common source type
    
    # Knowledge context
    context_summary = Column(Text)  # AI-generated summary of their involvement
    key_contributions = Column(JSON)  # List of specific contributions/mentions
    expertise_areas = Column(JSON)  # Specific areas within the topic they're expert in
    
    # Relationship strength indicators
    influence_score = Column(Float, default=0.5)  # How much influence they have on this topic
    dependency_score = Column(Float, default=0.5)  # How much this topic depends on them
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata for future extensibility
    metadata = Column(JSON)
    
    def __repr__(self):
        return f"<PersonTopic({self.person_id}-{self.topic_id}, {self.relationship_type})>"

class KnowledgeSource(Base):
    """
    Tracks all source content that feeds into the knowledge base.
    Enables complete traceability back to original content.
    """
    __tablename__ = 'knowledge_sources'
    
    id = Column(Integer, primary_key=True)
    
    # Source identification
    source_type = Column(String(50), nullable=False)  # SourceType enum
    source_id = Column(String(255), nullable=False)  # Unique ID within source type
    source_path = Column(String(1000))  # File path, thread ID, etc.
    
    # Content storage
    raw_content = Column(Text)  # Full original content
    processed_content = Column(Text)  # Cleaned/normalized content
    content_summary = Column(Text)  # AI-generated summary
    content_type = Column(String(100))  # email/slack_message/document/etc.
    
    # Metadata
    title = Column(String(500))
    author = Column(String(255))
    recipients = Column(JSON)  # List of recipients/participants
    timestamp = Column(DateTime)
    
    # Knowledge extraction results
    extracted_topics = Column(JSON)  # Topics identified in this content
    extracted_people = Column(JSON)  # People mentioned
    extracted_tasks = Column(JSON)  # Action items found
    extracted_insights = Column(JSON)  # Key insights generated
    
    # Processing metadata
    processing_version = Column(String(50))  # Version of AI that processed this
    confidence_scores = Column(JSON)  # Confidence in various extractions
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime)
    
    # Status
    processing_status = Column(String(50), default='pending')  # pending/processed/error
    
    def __repr__(self):
        return f"<KnowledgeSource({self.source_type}:{self.source_id})>"

class UnifiedKnowledgeGraph(Base):
    """
    Central knowledge graph that connects all entities and enables
    sophisticated queries across the entire knowledge base.
    """
    __tablename__ = 'unified_knowledge_graph'
    
    id = Column(Integer, primary_key=True)
    
    # Entity connections
    entity_type_1 = Column(String(50))  # person/topic/task/project/etc.
    entity_id_1 = Column(Integer)
    entity_type_2 = Column(String(50))
    entity_id_2 = Column(Integer)
    
    # Relationship details
    relationship_type = Column(String(100))  # works_on/reports_to/depends_on/etc.
    relationship_strength = Column(Float, default=0.5)
    confidence = Column(Float, default=0.5)
    
    # Supporting evidence
    evidence_sources = Column(JSON)  # List of KnowledgeSource IDs that support this relationship
    evidence_count = Column(Integer, default=1)
    
    # Temporal aspects
    first_observed = Column(DateTime, default=datetime.utcnow)
    last_observed = Column(DateTime, default=datetime.utcnow)
    relationship_duration = Column(Integer)  # Days active
    
    # Metadata
    metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<KnowledgeGraph({self.entity_type_1}:{self.entity_id_1} -> {self.entity_type_2}:{self.entity_id_2})>"

# ==============================================================================
# KNOWLEDGE INTELLIGENCE MODELS
# ==============================================================================

class ProactiveKnowledgeInsight(Base):
    """
    AI-generated insights that emerge from knowledge analysis.
    These power the auto-response and decision-making capabilities.
    """
    __tablename__ = 'proactive_knowledge_insights'
    
    id = Column(Integer, primary_key=True)
    
    # Insight content
    insight_type = Column(String(100))  # pattern/prediction/recommendation/anomaly
    title = Column(String(500))
    description = Column(Text)
    context = Column(Text)
    
    # Actionability
    action_required = Column(Boolean, default=False)
    suggested_actions = Column(JSON)  # List of recommended actions
    priority = Column(String(20), default='medium')
    urgency = Column(String(20), default='normal')
    
    # Evidence and confidence
    confidence = Column(Float, default=0.5)
    evidence_sources = Column(JSON)  # Supporting KnowledgeSource IDs
    related_entities = Column(JSON)  # People/topics/projects involved
    
    # Lifecycle
    status = Column(String(50), default='new')  # new/reviewed/acted_on/dismissed
    expires_at = Column(DateTime)
    
    # AI metadata
    generated_by = Column(String(100))  # AI model/version that generated this
    generation_context = Column(JSON)  # What triggered this insight
    
    # User interaction
    user_feedback = Column(String(20))  # helpful/not_helpful/inaccurate
    user_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ProactiveInsight({self.insight_type}: {self.title[:50]})>"

class KnowledgeEvolutionLog(Base):
    """
    Tracks how knowledge evolves over time.
    Critical for understanding knowledge quality and making decisions.
    """
    __tablename__ = 'knowledge_evolution_log'
    
    id = Column(Integer, primary_key=True)
    
    # What changed
    entity_type = Column(String(50))  # topic/person/relationship/etc.
    entity_id = Column(Integer)
    change_type = Column(String(50))  # created/updated/merged/split/deleted
    
    # Change details
    field_changed = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    change_reason = Column(String(200))  # auto_extraction/user_edit/ai_refinement
    
    # Context
    triggered_by_source = Column(Integer, ForeignKey('knowledge_sources.id'))
    confidence_before = Column(Float)
    confidence_after = Column(Float)
    
    # Metadata
    metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<KnowledgeEvolution({self.entity_type}:{self.entity_id}, {self.change_type})>"

# ==============================================================================
# HELPER DATACLASSES FOR API RESPONSES
# ==============================================================================

@dataclass
class TopicSummary:
    """Summary view of a topic with key metrics"""
    id: int
    name: str
    topic_type: str
    hierarchy_path: str
    people_count: int
    mention_count: int
    confidence_score: float
    last_activity: datetime
    status: str

@dataclass
class PersonTopicContext:
    """Person's relationship to a specific topic"""
    person_id: int
    topic_id: int
    topic_name: str
    relationship_type: str
    involvement_level: float
    expertise_areas: List[str]
    key_contributions: List[str]
    last_activity: datetime

@dataclass
class KnowledgeTraceability:
    """Traceability back to source content"""
    entity_type: str
    entity_id: int
    source_type: str
    source_id: str
    source_content_snippet: str
    confidence: float
    timestamp: datetime
    can_access_full_content: bool 