"""
Database Manager - Strategic Intelligence Platform Compatibility
==============================================================
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class User:
    """User model for compatibility"""
    id: int
    email: str
    name: str = None
    # OAuth credentials for Gmail integration
    access_token: str = None
    refresh_token: str = None
    token_expires_at: datetime = None
    scopes: List[str] = None
    google_id: str = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'scopes': self.scopes or [],
            'google_id': self.google_id
        }

@dataclass
class Task:
    """Task model for compatibility"""
    id: int
    user_id: int
    description: str
    status: str = 'pending'
    priority: str = 'medium'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'description': self.description,
            'status': self.status,
            'priority': self.priority
        }

@dataclass
class Email:
    """Email model for Gmail integration compatibility"""
    id: int
    user_id: int
    gmail_id: str
    subject: str = ""
    sender: str = ""
    sender_name: str = ""
    recipient_emails: str = ""  # JSON string of list
    email_date: datetime = None
    processed_at: datetime = None
    normalizer_version: str = ""
    body_text: str = ""
    body_html: str = ""
    has_attachments: bool = False
    is_read: bool = True
    is_important: bool = False
    is_starred: bool = False
    message_type: str = "received"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'gmail_id': self.gmail_id,
            'subject': self.subject,
            'sender': self.sender,
            'sender_name': self.sender_name,
            'recipient_emails': self.recipient_emails,
            'email_date': self.email_date.isoformat() if self.email_date else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'normalizer_version': self.normalizer_version,
            'body_text': self.body_text,
            'body_html': self.body_html,
            'has_attachments': self.has_attachments,
            'is_read': self.is_read,
            'is_important': self.is_important,
            'is_starred': self.is_starred,
            'message_type': self.message_type
        }

@dataclass
class TrustedContact:
    """Trusted contact model for contact strategy compatibility"""
    id: int
    user_id: int
    email_address: str
    name: str = ""
    engagement_score: float = 0.0
    first_sent_date: datetime = None
    last_sent_date: datetime = None
    total_sent_emails: int = 0
    total_received_emails: int = 0
    bidirectional_threads: int = 0
    topics_discussed: str = "[]"  # JSON string of list
    bidirectional_topics: str = "[]"  # JSON string of list
    relationship_strength: str = "low"
    communication_frequency: str = "occasional"
    last_analyzed: datetime = None
    
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
            'last_analyzed': self.last_analyzed.isoformat() if self.last_analyzed else None
        }

@dataclass
class Topic:
    """Topic model for knowledge tree compatibility"""
    id: int
    user_id: int
    name: str
    description: str = ""
    keywords: str = "[]"  # JSON string of list
    total_mentions: int = 0
    last_mentioned: datetime = None
    is_official: bool = False
    strategic_importance: float = 0.0
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'keywords': self.keywords,
            'total_mentions': self.total_mentions,
            'last_mentioned': self.last_mentioned.isoformat() if self.last_mentioned else None,
            'is_official': self.is_official,
            'strategic_importance': self.strategic_importance
        }

@dataclass  
class Person:
    """Person model for contact management compatibility"""
    id: int
    user_id: int
    name: str
    email_address: str = ""
    company: str = ""
    relationship_type: str = "contact"
    importance_level: float = 0.0
    last_interaction: datetime = None
    phone: str = ""
    title: str = ""
    notes: str = ""
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email_address': self.email_address,
            'company': self.company,
            'relationship_type': self.relationship_type,
            'importance_level': self.importance_level,
            'last_interaction': self.last_interaction.isoformat() if self.last_interaction else None,
            'phone': self.phone,
            'title': self.title,
            'notes': self.notes
        }

@dataclass
class Project:
    """Project model for project management compatibility"""
    id: int
    user_id: int
    name: str
    description: str = ""
    status: str = "active"
    priority: str = "medium"
    start_date: datetime = None
    end_date: datetime = None
    created_at: datetime = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class EntityRelationship:
    """Entity relationship model for knowledge graph compatibility"""
    id: int
    user_id: int
    entity_a_type: str
    entity_a_id: int
    entity_b_type: str
    entity_b_id: int
    relationship_type: str
    strength: float = 0.0
    created_at: datetime = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'entity_a_type': self.entity_a_type,
            'entity_a_id': self.entity_a_id,
            'entity_b_type': self.entity_b_type,
            'entity_b_id': self.entity_b_id,
            'relationship_type': self.relationship_type,
            'strength': self.strength,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class IntelligenceInsight:
    """Intelligence insight model for AI analysis compatibility"""
    id: int
    user_id: int
    insight_type: str
    title: str
    content: str
    confidence: float = 0.0
    source_type: str = ""
    source_id: str = ""
    created_at: datetime = None
    is_actionable: bool = False
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'insight_type': self.insight_type,
            'title': self.title,
            'content': self.content,
            'confidence': self.confidence,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_actionable': self.is_actionable
        }

@dataclass
class CalendarEvent:
    """Calendar event model for calendar integration compatibility"""
    id: int
    user_id: int
    title: str
    description: str = ""
    start_time: datetime = None
    end_time: datetime = None
    location: str = ""
    attendees: str = "[]"  # JSON string of list
    google_event_id: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'location': self.location,
            'attendees': self.attendees,
            'google_event_id': self.google_event_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DatabaseManager:
    """Minimal database manager for Strategic Intelligence Platform compatibility"""
    
    def __init__(self):
        self.initialized = False
        # In-memory storage for minimal functionality
        self.users = {}
        self.tasks = {}
        self.emails = {}
        self.trusted_contacts = {}
        self.topics = {}
        self.people = {}
        self.projects = {}
        self.entity_relationships = {}
        self.intelligence_insights = {}
        self.calendar_events = {}
        self.next_user_id = 1
        self.next_task_id = 1
        self.next_email_id = 1
        self.next_contact_id = 1
        self.next_topic_id = 1
        self.next_person_id = 1
        self.next_project_id = 1
        self.next_relationship_id = 1
        self.next_insight_id = 1
        self.next_event_id = 1
    
    def init_db(self):
        """Initialize database"""
        try:
            # Create some default users for testing
            test_users = [
                {'email': 'user@example.com', 'name': 'Test User'},
            ]
            
            for user_data in test_users:
                if user_data['email'] not in self.users:
                    user = User(
                        id=self.next_user_id,
                        email=user_data['email'],
                        name=user_data['name']
                    )
                    self.users[user_data['email']] = user
                    self.next_user_id += 1
            
            self.initialized = True
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        if email in self.users:
            return self.users[email]
        
        # Create user if doesn't exist (for OAuth users)
        user = User(
            id=self.next_user_id,
            email=email,
            name=email.split('@')[0].title()  # Simple name from email
        )
        self.users[email] = user
        self.next_user_id += 1
        
        logger.info(f"Created new user: {email}")
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None
    
    def get_user_tasks(self, user_id: int, limit: int = 50) -> List[Task]:
        """Get tasks for user"""
        user_tasks = []
        for task in self.tasks.values():
            if task.user_id == user_id:
                user_tasks.append(task)
                if len(user_tasks) >= limit:
                    break
        
        # If no tasks exist, create some sample tasks
        if not user_tasks:
            sample_tasks = [
                Task(
                    id=self.next_task_id,
                    user_id=user_id,
                    description="Set up Strategic Intelligence Platform",
                    status="completed",
                    priority="high"
                ),
                Task(
                    id=self.next_task_id + 1,
                    user_id=user_id,
                    description="Configure multi-database architecture",
                    status="completed",
                    priority="high"
                ),
                Task(
                    id=self.next_task_id + 2,
                    user_id=user_id,
                    description="Initialize Claude Opus 4 analysts",
                    status="pending",
                    priority="medium"
                )
            ]
            
            for task in sample_tasks:
                self.tasks[task.id] = task
                user_tasks.append(task)
                self.next_task_id += 1
        
        return user_tasks[:limit]
    
    def create_user(self, email: str, name: str = None) -> User:
        """Create a new user"""
        user = User(
            id=self.next_user_id,
            email=email,
            name=name or email.split('@')[0].title()
        )
        self.users[email] = user
        self.next_user_id += 1
        
        logger.info(f"Created user: {email}")
        return user
    
    def create_or_update_user(self, user_info: Dict, credentials: Dict) -> User:
        """Create or update user with OAuth credentials"""
        try:
            email = user_info['email']
            
            if email in self.users:
                # Update existing user with OAuth credentials
                user = self.users[email]
                user.name = user_info.get('name', user.name)
                user.google_id = user_info.get('id', user.google_id)
                user.access_token = credentials.get('access_token')
                user.refresh_token = credentials.get('refresh_token')
                user.token_expires_at = credentials.get('expires_at')
                user.scopes = credentials.get('scopes', [])
                
                logger.info(f"Updated user with OAuth credentials: {email}")
            else:
                # Create new user with OAuth credentials
                user = User(
                    id=self.next_user_id,
                    email=email,
                    name=user_info.get('name', email.split('@')[0].title()),
                    google_id=user_info.get('id'),
                    access_token=credentials.get('access_token'),
                    refresh_token=credentials.get('refresh_token'),
                    token_expires_at=credentials.get('expires_at'),
                    scopes=credentials.get('scopes', [])
                )
                
                self.users[email] = user
                self.next_user_id += 1
                
                logger.info(f"Created new user with OAuth credentials: {email}")
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to create/update user with OAuth credentials: {str(e)}")
            raise
    
    # ================================
    # EMAIL MANAGEMENT METHODS
    # ================================
    
    def save_email(self, user_id: int, email_data: Dict) -> Email:
        """Save email to database"""
        try:
            email = Email(
                id=self.next_email_id,
                user_id=user_id,
                gmail_id=email_data.get('id', ''),
                subject=email_data.get('subject', ''),
                sender=email_data.get('sender', ''),
                sender_name=email_data.get('sender_name', ''),
                recipient_emails=str(email_data.get('recipient_emails', [])),
                email_date=email_data.get('timestamp') or email_data.get('email_date') or datetime.utcnow(),
                processed_at=datetime.utcnow(),
                normalizer_version=email_data.get('normalizer_version', 'v1'),
                body_text=email_data.get('body_text', ''),
                body_html=email_data.get('body_html', ''),
                has_attachments=email_data.get('has_attachments', False),
                is_read=email_data.get('is_read', True),
                is_important=email_data.get('is_important', False),
                is_starred=email_data.get('is_starred', False),
                message_type=email_data.get('message_type', 'received')
            )
            
            self.emails[self.next_email_id] = email
            self.next_email_id += 1
            
            logger.info(f"Saved email: {email.subject}")
            return email
            
        except Exception as e:
            logger.error(f"Failed to save email: {str(e)}")
            raise
    
    def get_user_emails(self, user_id: int, limit: int = 100) -> List[Email]:
        """Get emails for user"""
        user_emails = []
        for email in self.emails.values():
            if email.user_id == user_id:
                user_emails.append(email)
                if len(user_emails) >= limit:
                    break
        
        return user_emails[:limit]
    
    def get_session(self):
        """Mock session context manager for compatibility"""
        class MockSession:
            def __init__(self, db_manager):
                self.db_manager = db_manager
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            
            def query(self, model_class):
                """Mock query method"""
                class MockQuery:
                    def __init__(self, model_class, db_manager):
                        self.model_class = model_class
                        self.db_manager = db_manager
                        self.filters = []
                    
                    def filter(self, *conditions):
                        self.filters.extend(conditions)
                        return self
                    
                    def first(self):
                        """Mock first() method with proper filter evaluation"""
                        if self.model_class == Email:
                            for email in self.db_manager.emails.values():
                                if self._evaluate_filters(email):
                                    return email
                        elif self.model_class == Topic:
                            for topic in self.db_manager.topics.values():
                                if self._evaluate_filters(topic):
                                    return topic
                        elif self.model_class == Person:
                            for person in self.db_manager.people.values():
                                if self._evaluate_filters(person):
                                    return person
                        elif self.model_class == Project:
                            for project in self.db_manager.projects.values():
                                if self._evaluate_filters(project):
                                    return project
                        elif self.model_class == CalendarEvent:
                            for event in self.db_manager.calendar_events.values():
                                if self._evaluate_filters(event):
                                    return event
                        return None
                    
                    def _evaluate_filters(self, obj):
                        """Evaluate SQLAlchemy-style filter conditions against an object"""
                        if not self.filters:
                            return True
                        
                        for condition in self.filters:
                            # Handle common SQLAlchemy filter patterns
                            if hasattr(condition, 'left') and hasattr(condition, 'right'):
                                # This is a comparison operation like Email.user_id == user_id
                                left_attr = self._extract_attribute_name(condition.left)
                                right_value = self._extract_value(condition.right)
                                
                                if left_attr and hasattr(obj, left_attr):
                                    obj_value = getattr(obj, left_attr)
                                    if not self._compare_values(obj_value, right_value, condition):
                                        return False
                            else:
                                # Simple boolean condition
                                if not condition:
                                    return False
                        
                        return True
                    
                    def _extract_attribute_name(self, attr_expr):
                        """Extract attribute name from SQLAlchemy expression"""
                        if hasattr(attr_expr, 'key'):
                            return attr_expr.key
                        elif hasattr(attr_expr, '__name__'):
                            return attr_expr.__name__
                        elif hasattr(attr_expr, 'name'):
                            return attr_expr.name
                        return None
                    
                    def _extract_value(self, value_expr):
                        """Extract actual value from SQLAlchemy expression"""
                        if hasattr(value_expr, 'value'):
                            return value_expr.value
                        elif hasattr(value_expr, 'val'):
                            return value_expr.val
                        else:
                            return value_expr
                    
                    def _compare_values(self, obj_value, filter_value, condition):
                        """Compare values based on the condition type"""
                        if hasattr(condition, 'operator'):
                            op = condition.operator
                        else:
                            # Default to equality
                            return obj_value == filter_value
                        
                        if op == '==':
                            return obj_value == filter_value
                        elif op == '!=':
                            return obj_value != filter_value
                        elif op == '>':
                            return obj_value > filter_value
                        elif op == '<':
                            return obj_value < filter_value
                        elif op == '>=':
                            return obj_value >= filter_value
                        elif op == '<=':
                            return obj_value <= filter_value
                        elif op == 'in':
                            return obj_value in filter_value
                        elif op == 'like':
                            return filter_value.lower() in str(obj_value).lower()
                        else:
                            # Default to equality
                            return obj_value == filter_value
                    
                    def count(self):
                        if self.model_class == Email:
                            return len(self.db_manager.emails)
                        elif self.model_class == Topic:
                            return len(self.db_manager.topics)
                        elif self.model_class == Person:
                            return len(self.db_manager.people)
                        elif self.model_class == Project:
                            return len(self.db_manager.projects)
                        elif self.model_class == CalendarEvent:
                            return len(self.db_manager.calendar_events)
                        return 0
                    
                    def all(self):
                        """Mock all() method for queries with filter evaluation"""
                        if self.model_class == Email:
                            return [email for email in self.db_manager.emails.values() if self._evaluate_filters(email)]
                        elif self.model_class == Topic:
                            return [topic for topic in self.db_manager.topics.values() if self._evaluate_filters(topic)]
                        elif self.model_class == Person:
                            return [person for person in self.db_manager.people.values() if self._evaluate_filters(person)]
                        elif self.model_class == Project:
                            return [project for project in self.db_manager.projects.values() if self._evaluate_filters(project)]
                        elif self.model_class == CalendarEvent:
                            return [event for event in self.db_manager.calendar_events.values() if self._evaluate_filters(event)]
                        return []
                    
                    def limit(self, count):
                        """Mock limit() method"""
                        return self
                    
                    def order_by(self, *args):
                        """Mock order_by() method"""
                        return self
                
                return MockQuery(model_class, self.db_manager)
            
            def add(self, obj):
                """Mock add method"""
                pass
            
            def commit(self):
                """Mock commit method"""
                pass
        
        return MockSession(self)
    
    # ================================
    # TRUSTED CONTACT MANAGEMENT METHODS
    # ================================
    
    def get_trusted_contacts(self, user_id: int, limit: int = 100) -> List[TrustedContact]:
        """Get trusted contacts for user"""
        user_contacts = []
        for contact in self.trusted_contacts.values():
            if contact.user_id == user_id:
                user_contacts.append(contact)
                if len(user_contacts) >= limit:
                    break
        
        # Sort by engagement score descending
        user_contacts.sort(key=lambda x: x.engagement_score, reverse=True)
        return user_contacts[:limit]
    
    def create_or_update_trusted_contact(self, user_id: int, contact_data: Dict) -> TrustedContact:
        """Create or update a trusted contact"""
        try:
            # Check if contact already exists
            existing_contact = None
            for contact in self.trusted_contacts.values():
                if contact.user_id == user_id and contact.email_address == contact_data['email_address']:
                    existing_contact = contact
                    break
            
            if existing_contact:
                # Update existing contact
                existing_contact.name = contact_data.get('name', existing_contact.name)
                existing_contact.engagement_score = contact_data.get('engagement_score', existing_contact.engagement_score)
                existing_contact.first_sent_date = contact_data.get('first_sent_date', existing_contact.first_sent_date)
                existing_contact.last_sent_date = contact_data.get('last_sent_date', existing_contact.last_sent_date)
                existing_contact.total_sent_emails = contact_data.get('total_sent_emails', existing_contact.total_sent_emails)
                existing_contact.total_received_emails = contact_data.get('total_received_emails', existing_contact.total_received_emails)
                existing_contact.bidirectional_threads = contact_data.get('bidirectional_threads', existing_contact.bidirectional_threads)
                existing_contact.topics_discussed = str(contact_data.get('topics_discussed', existing_contact.topics_discussed))
                existing_contact.bidirectional_topics = str(contact_data.get('bidirectional_topics', existing_contact.bidirectional_topics))
                existing_contact.relationship_strength = contact_data.get('relationship_strength', existing_contact.relationship_strength)
                existing_contact.communication_frequency = contact_data.get('communication_frequency', existing_contact.communication_frequency)
                existing_contact.last_analyzed = contact_data.get('last_analyzed', datetime.utcnow())
                
                logger.info(f"Updated trusted contact: {existing_contact.email_address}")
                return existing_contact
            else:
                # Create new contact
                contact = TrustedContact(
                    id=self.next_contact_id,
                    user_id=user_id,
                    email_address=contact_data['email_address'],
                    name=contact_data.get('name', ''),
                    engagement_score=contact_data.get('engagement_score', 0.0),
                    first_sent_date=contact_data.get('first_sent_date'),
                    last_sent_date=contact_data.get('last_sent_date'),
                    total_sent_emails=contact_data.get('total_sent_emails', 0),
                    total_received_emails=contact_data.get('total_received_emails', 0),
                    bidirectional_threads=contact_data.get('bidirectional_threads', 0),
                    topics_discussed=str(contact_data.get('topics_discussed', [])),
                    bidirectional_topics=str(contact_data.get('bidirectional_topics', [])),
                    relationship_strength=contact_data.get('relationship_strength', 'low'),
                    communication_frequency=contact_data.get('communication_frequency', 'occasional'),
                    last_analyzed=contact_data.get('last_analyzed', datetime.utcnow())
                )
                
                self.trusted_contacts[self.next_contact_id] = contact
                self.next_contact_id += 1
                
                logger.info(f"Created trusted contact: {contact.email_address}")
                return contact
                
        except Exception as e:
            logger.error(f"Failed to create/update trusted contact: {str(e)}")
            raise
    
    def find_trusted_contact_by_email(self, user_id: int, email_address: str) -> Optional[TrustedContact]:
        """Find trusted contact by email address"""
        for contact in self.trusted_contacts.values():
            if contact.user_id == user_id and contact.email_address.lower() == email_address.lower():
                return contact
        return None
    
    def find_person_by_email(self, user_id: int, email_address: str):
        """Find person by email - mock method for compatibility"""
        # In the real implementation, this would find a Person record
        # For now, return None since we don't have Person model
        return None
    
    def update_people_engagement_data(self, user_id: int, person_id: int, engagement_data: Dict):
        """Update people engagement data - mock method for compatibility"""
        # In the real implementation, this would update Person engagement data
        # For now, just log the call
        logger.info(f"Mock update_people_engagement_data called for user {user_id}, person {person_id}")
        pass
    
    def get_engagement_analytics(self, user_id: int) -> Dict:
        """Get engagement analytics for user"""
        user_contacts = self.get_trusted_contacts(user_id, limit=1000)
        
        if not user_contacts:
            return {
                'total_trusted_contacts': 0,
                'high_engagement_contacts': 0,
                'engagement_rate': 0.0
            }
        
        high_engagement_count = sum(1 for c in user_contacts if c.engagement_score > 0.7)
        
        return {
            'total_trusted_contacts': len(user_contacts),
            'high_engagement_contacts': high_engagement_count,
            'engagement_rate': high_engagement_count / len(user_contacts) if user_contacts else 0.0
        }

# Global database manager instance
_db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return _db_manager

# Mock association table for Person-Topic many-to-many relationships
# In a real SQLAlchemy setup, this would be a Table object
person_topic_association = {
    'table_name': 'person_topic_association',
    'description': 'Mock association table for Person-Topic relationships',
    'columns': ['person_id', 'topic_id', 'created_at']
} 