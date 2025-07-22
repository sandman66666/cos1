# Unified Entity Engine - Central Intelligence Hub
# This replaces the scattered entity creation across multiple files

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import json
import hashlib
from sqlalchemy.orm import Session
from dataclasses import dataclass
import re

from chief_of_staff_ai.models.database import get_db_manager
from config.settings import settings
from chief_of_staff_ai.models.database import (
    Topic, Person, Task, Email, CalendarEvent, Project,
    EntityRelationship, IntelligenceInsight, 
    person_topic_association, task_topic_association, event_topic_association
)

logger = logging.getLogger(__name__)

@dataclass
class EntityContext:
    """Container for entity creation context"""
    source_type: str  # email, calendar, manual
    source_id: Optional[int] = None
    confidence: float = 0.8
    user_id: int = None
    processing_metadata: Dict = None

class UnifiedEntityEngine:
    """
    Central hub for all entity creation, updating, and relationship management.
    This is the brain that ensures consistency across all data sources.
    """
    
    def __init__(self):
        self.db_manager = get_db_manager()
        
    # =====================================================================
    # CORE ENTITY CREATION METHODS
    # =====================================================================
    
    def create_or_update_person(self, 
                               email: str, 
                               name: str = None, 
                               context: EntityContext = None) -> Person:
        """
        Unified person creation from ANY source (email, calendar, manual).
        This solves the asymmetry problem you identified.
        """
        try:
            with self.db_manager.get_session() as session:
                # Always check for existing person first
                existing_person = session.query(Person).filter(
                    Person.user_id == context.user_id,
                    Person.email_address == email.lower()
                ).first()
                
                if existing_person:
                    # Update existing person with new information
                    updated = self._update_person_intelligence(existing_person, name, context, session)
                    if updated:
                        session.commit()
                        logger.info(f"Updated existing person: {existing_person.name} ({email})")
                    return existing_person
                
                # Create new person
                person = Person(
                    user_id=context.user_id,
                    email_address=email.lower(),
                    name=name or self._extract_name_from_email(email),
                    created_at=datetime.utcnow()
                )
                
                # Add source-specific intelligence
                self._enrich_person_from_context(person, context)
                
                session.add(person)
                session.commit()
                
                logger.info(f"Created new person: {person.name} ({email}) from {context.source_type}")
                return person
                
        except Exception as e:
            logger.error(f"Failed to create/update person {email}: {str(e)}")
            return None
    
    def create_or_update_topic(self, 
                              topic_name: str, 
                              description: str = None,
                              keywords: List[str] = None,
                              context: EntityContext = None) -> Topic:
        """
        Topics as the central brain - always check existing first, then augment.
        This solves your topic duplication concern.
        """
        try:
            with self.db_manager.get_session() as session:
                # Intelligent topic matching - exact name or similar
                existing_topic = self._find_matching_topic(topic_name, context.user_id, session)
                
                if existing_topic:
                    # Augment existing topic with new intelligence
                    updated = self._augment_topic_intelligence(existing_topic, description, keywords, context, session)
                    if updated:
                        existing_topic.updated_at = datetime.utcnow()
                        existing_topic.version += 1
                        session.commit()
                        logger.info(f"Augmented existing topic: {existing_topic.name}")
                    return existing_topic
                
                # Create new topic
                topic = Topic(
                    user_id=context.user_id,
                    name=topic_name.strip().title(),
                    description=description,
                    keywords=','.join(keywords) if keywords else None,
                    confidence_score=context.confidence,
                    total_mentions=1,
                    last_mentioned=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                
                # Generate AI intelligence summary for new topic
                topic.intelligence_summary = self._generate_topic_intelligence_summary(topic_name, description, keywords)
                
                session.add(topic)
                session.commit()
                
                logger.info(f"Created new topic: {topic_name}")
                return topic
                
        except Exception as e:
            logger.error(f"Failed to create/update topic {topic_name}: {str(e)}")
            return None
    
    def create_task_with_full_context(self,
                                    description: str,
                                    assignee_email: str = None,
                                    topic_names: List[str] = None,
                                    context: EntityContext = None,
                                    due_date: datetime = None,
                                    priority: str = 'medium') -> Task:
        """
        Create tasks with full context story and entity relationships.
        This addresses your concern about tasks existing "in the air".
        """
        try:
            with self.db_manager.get_session() as session:
                # Create the task
                task = Task(
                    user_id=context.user_id,
                    description=description,
                    priority=priority,
                    due_date=due_date,
                    confidence=context.confidence,
                    created_at=datetime.utcnow()
                )
                
                # Generate context story - WHY this task exists
                task.context_story = self._generate_task_context_story(
                    description, assignee_email, topic_names, context
                )
                
                # Link to assignee if provided
                if assignee_email:
                    assignee = self.create_or_update_person(assignee_email, context=context)
                    if assignee:
                        task.assignee_id = assignee.id
                
                # Link to topics
                if topic_names:
                    topic_ids = []
                    for topic_name in topic_names:
                        topic = self.create_or_update_topic(topic_name, context=context)
                        if topic:
                            topic_ids.append(topic.id)
                    task.topics = topic_ids  # Store as JSON list of topic IDs
                
                # Link to source
                if context.source_type == 'email' and context.source_id:
                    task.source_email_id = context.source_id
                elif context.source_type == 'calendar' and context.source_id:
                    task.source_event_id = context.source_id
                
                session.add(task)
                session.commit()
                
                logger.info(f"Created task with full context: {description[:50]}...")
                return task
                
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            return None
    
    # =====================================================================
    # RELATIONSHIP INTELLIGENCE METHODS
    # =====================================================================
    
    def create_entity_relationship(self, 
                                 entity_a_type: str, entity_a_id: int,
                                 entity_b_type: str, entity_b_id: int,
                                 relationship_type: str,
                                 context: EntityContext) -> EntityRelationship:
        """Create intelligent relationships between any entities"""
        try:
            with self.db_manager.get_session() as session:
                # Check if relationship already exists
                existing = session.query(EntityRelationship).filter(
                    EntityRelationship.user_id == context.user_id,
                    EntityRelationship.entity_type_a == entity_a_type,
                    EntityRelationship.entity_id_a == entity_a_id,
                    EntityRelationship.entity_type_b == entity_b_type,
                    EntityRelationship.entity_id_b == entity_b_id
                ).first()
                
                if existing:
                    # Strengthen existing relationship
                    existing.total_interactions += 1
                    existing.last_interaction = datetime.utcnow()
                    existing.strength = min(1.0, existing.strength + 0.1)
                    session.commit()
                    return existing
                
                # Create new relationship
                relationship = EntityRelationship(
                    user_id=context.user_id,
                    entity_type_a=entity_a_type,
                    entity_id_a=entity_a_id,
                    entity_type_b=entity_b_type,
                    entity_id_b=entity_b_id,
                    relationship_type=relationship_type,
                    strength=0.5,
                    last_interaction=datetime.utcnow(),
                    total_interactions=1
                )
                
                # Generate context summary
                relationship.context_summary = self._generate_relationship_context(
                    entity_a_type, entity_a_id, entity_b_type, entity_b_id, session
                )
                
                session.add(relationship)
                session.commit()
                
                logger.info(f"Created relationship: {entity_a_type}:{entity_a_id} -> {entity_b_type}:{entity_b_id}")
                return relationship
                
        except Exception as e:
            logger.error(f"Failed to create entity relationship: {str(e)}")
            return None
    
    def generate_proactive_insights(self, user_id: int) -> List[IntelligenceInsight]:
        """
        Generate proactive insights based on entity patterns and relationships.
        This is where the predictive intelligence happens.
        """
        insights = []
        
        try:
            with self.db_manager.get_session() as session:
                # Insight 1: Relationship gaps (haven't contacted important people)
                relationship_insights = self._detect_relationship_gaps(user_id, session)
                insights.extend(relationship_insights)
                
                # Insight 2: Topic momentum (topics getting hot)
                topic_insights = self._detect_topic_momentum(user_id, session)
                insights.extend(topic_insights)
                
                # Insight 3: Meeting preparation needs
                meeting_prep_insights = self._detect_meeting_prep_needs(user_id, session)
                insights.extend(meeting_prep_insights)
                
                # Insight 4: Project attention needed
                project_insights = self._detect_project_attention_needs(user_id, session)
                insights.extend(project_insights)
                
                # Save insights to database
                for insight in insights:
                    session.add(insight)
                
                session.commit()
                logger.info(f"Generated {len(insights)} proactive insights for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to generate proactive insights: {str(e)}")
            
        return insights
    
    # =====================================================================
    # HELPER METHODS
    # =====================================================================
    
    def _find_matching_topic(self, topic_name: str, user_id: int, session: Session) -> Optional[Topic]:
        """Intelligent topic matching using exact name, keywords, or similarity"""
        # Exact match first
        exact_match = session.query(Topic).filter(
            Topic.user_id == user_id,
            Topic.name.ilike(f"%{topic_name}%")
        ).first()
        
        if exact_match:
            return exact_match
        
        # Keyword matching
        topics = session.query(Topic).filter(Topic.user_id == user_id).all()
        for topic in topics:
            if topic.keywords:
                keywords = [k.strip().lower() for k in topic.keywords.split(',')]
                if topic_name.lower() in keywords:
                    return topic
        
        return None
    
    def _generate_task_context_story(self, description: str, assignee_email: str, 
                                   topic_names: List[str], context: EntityContext) -> str:
        """Generate WHY this task exists - the narrative context"""
        story_parts = []
        
        # Source context
        if context.source_type == 'email':
            story_parts.append(f"Task extracted from email communication")
        elif context.source_type == 'calendar':
            story_parts.append(f"Task generated for meeting preparation")
        
        # Topic context
        if topic_names:
            story_parts.append(f"Related to: {', '.join(topic_names)}")
        
        # Assignee context
        if assignee_email:
            story_parts.append(f"Assigned to: {assignee_email}")
        
        # Confidence context
        confidence_level = "high" if context.confidence > 0.8 else "medium" if context.confidence > 0.5 else "low"
        story_parts.append(f"Confidence: {confidence_level}")
        
        return ". ".join(story_parts)
    
    def _generate_topic_intelligence_summary(self, name: str, description: str, keywords: List[str]) -> str:
        """Generate AI summary of what we know about this topic"""
        # This would call Claude for intelligence generation
        # For now, return a structured summary
        parts = [f"Topic: {name}"]
        if description:
            parts.append(f"Description: {description}")
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}")
        return ". ".join(parts)
    
    def _detect_relationship_gaps(self, user_id: int, session: Session) -> List[IntelligenceInsight]:
        """Detect important people user hasn't contacted recently"""
        insights = []
        
        # Find high-importance people with no recent contact
        important_people = session.query(Person).filter(
            Person.user_id == user_id,
            Person.importance_level > 0.7,
            Person.last_interaction < datetime.utcnow() - timedelta(days=14)
        ).limit(5).all()
        
        for person in important_people:
            insight = IntelligenceInsight(
                user_id=user_id,
                insight_type='relationship_alert',
                title=f"Haven't connected with {person.name} recently",
                description=f"Last contact was {person.last_interaction.strftime('%Y-%m-%d') if person.last_interaction else 'unknown'}. "
                           f"Consider reaching out about relevant topics.",
                priority='medium',
                confidence=0.8,
                related_entity_type='person',
                related_entity_id=person.id
            )
            insights.append(insight)
        
        return insights
    
    def _detect_topic_momentum(self, user_id: int, session: Session) -> List[IntelligenceInsight]:
        """Detect topics that are gaining momentum"""
        insights = []
        
        # Topics mentioned frequently in recent emails (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        hot_topics = session.query(Topic).filter(
            Topic.user_id == user_id,
            Topic.last_mentioned > week_ago,
            Topic.total_mentions > 3
        ).order_by(Topic.total_mentions.desc()).limit(3).all()
        
        for topic in hot_topics:
            insight = IntelligenceInsight(
                user_id=user_id,
                insight_type='topic_momentum',
                title=f"'{topic.name}' is trending in your communications",
                description=f"Mentioned {topic.total_mentions} times recently. "
                           f"Consider preparing materials or scheduling focused time.",
                priority='medium',
                confidence=0.7,
                related_entity_type='topic',
                related_entity_id=topic.id
            )
            insights.append(insight)
        
        return insights
    
    def _detect_meeting_prep_needs(self, user_id: int, session: Session) -> List[IntelligenceInsight]:
        """Detect upcoming meetings that need preparation"""
        insights = []
        
        # Meetings in next 48 hours with high prep priority
        tomorrow = datetime.utcnow() + timedelta(hours=48)
        
        upcoming_meetings = session.query(CalendarEvent).filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time.between(datetime.utcnow(), tomorrow),
            CalendarEvent.preparation_priority > 0.7
        ).all()
        
        for meeting in upcoming_meetings:
            insight = IntelligenceInsight(
                user_id=user_id,
                insight_type='meeting_prep',
                title=f"Prepare for '{meeting.title}'",
                description=f"High-priority meeting on {meeting.start_time.strftime('%Y-%m-%d %H:%M')}. "
                           f"{meeting.business_context or 'No context available.'}",
                priority='high',
                confidence=0.9,
                related_entity_type='event',
                related_entity_id=meeting.id,
                expires_at=meeting.start_time
            )
            insights.append(insight)
        
        return insights
    
    def _detect_project_attention_needs(self, user_id: int, session: Session) -> List[IntelligenceInsight]:
        """Detect projects that need attention"""
        insights = []
        
        # Projects with no recent activity
        stale_projects = session.query(Project).filter(
            Project.user_id == user_id,
            Project.status == 'active',
            Project.updated_at < datetime.utcnow() - timedelta(days=7)
        ).limit(3).all()
        
        for project in stale_projects:
            insight = IntelligenceInsight(
                user_id=user_id,
                insight_type='project_attention',
                title=f"Project '{project.name}' needs attention",
                description=f"No recent activity since {project.updated_at.strftime('%Y-%m-%d')}. "
                           f"Consider checking in with stakeholders.",
                priority='medium',
                confidence=0.6,
                related_entity_type='project',
                related_entity_id=project.id
            )
            insights.append(insight)
        
        return insights
    
    def _update_person_intelligence(self, person: Person, name: str, context: EntityContext, session: Session) -> bool:
        """Update existing person with new intelligence"""
        updated = False
        
        # Update name if we have a better one
        if name and name != person.name and len(name) > len(person.name or ""):
            person.name = name
            updated = True
        
        # Update interaction tracking
        person.total_interactions += 1
        person.last_interaction = datetime.utcnow()
        person.updated_at = datetime.utcnow()
        updated = True
        
        # Add any signature data from processing metadata
        if context.processing_metadata and context.processing_metadata.get('signature'):
            sig_data = context.processing_metadata['signature']
            if sig_data.get('company') and not person.company:
                person.company = sig_data['company']
                updated = True
            if sig_data.get('title') and not person.title:
                person.title = sig_data['title']
                updated = True
            if sig_data.get('phone') and not person.phone:
                person.phone = sig_data['phone']
                updated = True
        
        return updated
    
    def _extract_name_from_email(self, email: str) -> str:
        """Extract a reasonable name from email address"""
        local_part = email.split('@')[0]
        # Handle common formats like first.last, first_last, firstlast
        if '.' in local_part:
            parts = local_part.split('.')
            return ' '.join(part.capitalize() for part in parts)
        elif '_' in local_part:
            parts = local_part.split('_')
            return ' '.join(part.capitalize() for part in parts)
        else:
            return local_part.capitalize()
    
    def _enrich_person_from_context(self, person: Person, context: EntityContext):
        """Enrich person with context-specific information"""
        if context.source_type == 'email':
            person.relationship_type = 'email_contact'
        elif context.source_type == 'calendar':
            person.relationship_type = 'meeting_attendee'
        
        # Set initial importance based on context
        person.importance_level = context.confidence * 0.6  # Scale down initial importance
        person.total_interactions = 1
        person.last_interaction = datetime.utcnow()
    
    def _augment_topic_intelligence(self, topic: Topic, description: str, keywords: List[str], 
                                   context: EntityContext, session: Session) -> bool:
        """Augment existing topic with new intelligence"""
        updated = False
        
        # Update mention tracking
        topic.total_mentions += 1
        topic.last_mentioned = datetime.utcnow()
        updated = True
        
        # Add new description if we don't have one
        if description and not topic.description:
            topic.description = description
            updated = True
        
        # Merge keywords
        if keywords:
            existing_keywords = set(topic.keywords.split(',')) if topic.keywords else set()
            new_keywords = set(keywords)
            merged_keywords = existing_keywords.union(new_keywords)
            topic.keywords = ','.join(merged_keywords)
            updated = True
        
        return updated
    
    def _generate_relationship_context(self, entity_a_type: str, entity_a_id: int, 
                                     entity_b_type: str, entity_b_id: int, session: Session) -> str:
        """Generate context summary for entity relationships"""
        try:
            # Get entity names for context
            entity_a_name = self._get_entity_name(entity_a_type, entity_a_id, session)
            entity_b_name = self._get_entity_name(entity_b_type, entity_b_id, session)
            
            return f"{entity_a_type.title()} '{entity_a_name}' connected to {entity_b_type} '{entity_b_name}'"
        except:
            return f"Relationship between {entity_a_type}:{entity_a_id} and {entity_b_type}:{entity_b_id}"
    
    def _get_entity_name(self, entity_type: str, entity_id: int, session: Session) -> str:
        """Get display name for any entity"""
        if entity_type == 'person':
            person = session.query(Person).get(entity_id)
            return person.name if person else f"Person {entity_id}"
        elif entity_type == 'topic':
            topic = session.query(Topic).get(entity_id)
            return topic.name if topic else f"Topic {entity_id}"
        elif entity_type == 'project':
            project = session.query(Project).get(entity_id)
            return project.name if project else f"Project {entity_id}"
        else:
            return f"{entity_type.title()} {entity_id}"
    
    def _extract_from_signature(self, signature_text: str) -> Dict[str, str]:
        """Extract structured data from email signature"""
        info = {}
        
        # Extract title (common patterns)
        title_patterns = [
            r'(?:CEO|CTO|CFO|President|Director|Manager|VP|Vice President)',
            r'(?:Senior|Lead|Principal|Head of|Chief)\s+[A-Za-z\s]+',
            r'(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\n|$)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, signature_text, re.IGNORECASE)
            if match:
                info['title'] = match.group(0).strip()
                break
        
        # Extract company (usually follows title)
        company_patterns = [
            r'(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+Inc\.?|\s+LLC|\s+Corp\.?|\s+Co\.?))\s*(?:\n|$)',
            r'(?:@\s*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\n|$)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, signature_text)
            if match:
                potential_company = match.group(1).strip()
                if potential_company and len(potential_company) > 2:
                    info['company'] = potential_company
                    break
        
        # Extract phone with improved pattern
        phone_pattern = r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
        phone_match = re.search(phone_pattern, signature_text)
        if phone_match:
            info['phone'] = phone_match.group(1).strip()
        
        # Extract LinkedIn with robust pattern
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/pub/)([a-zA-Z0-9-]+)'
        linkedin_match = re.search(linkedin_pattern, signature_text, re.IGNORECASE)
        if linkedin_match:
            info['linkedin'] = f"https://linkedin.com/in/{linkedin_match.group(1)}"
        
        # Extract email if different from sender
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, signature_text)
        if emails:
            info['additional_emails'] = emails
        
        return info

# Global instance
entity_engine = UnifiedEntityEngine() 