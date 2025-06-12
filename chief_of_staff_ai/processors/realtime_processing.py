# Real-Time Processing Pipeline - Proactive Intelligence
# This transforms the system from batch processing to continuous intelligence

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time

from processors.enhanced_ai_pipeline import enhanced_ai_processor
from processors.unified_entity_engine import entity_engine, EntityContext
from models.enhanced_models import IntelligenceInsight, Person, Topic, Task, CalendarEvent

logger = logging.getLogger(__name__)

class EventType(Enum):
    NEW_EMAIL = "new_email"
    NEW_CALENDAR_EVENT = "new_calendar_event"
    ENTITY_UPDATE = "entity_update"
    USER_ACTION = "user_action"
    SCHEDULED_ANALYSIS = "scheduled_analysis"

@dataclass
class ProcessingEvent:
    event_type: EventType
    user_id: int
    data: Dict
    timestamp: datetime
    priority: int = 5  # 1-10, 1 = highest priority
    correlation_id: Optional[str] = None

class RealTimeProcessor:
    """
    Real-time processing engine that provides continuous intelligence.
    This is what transforms your system from reactive to proactive.
    """
    
    def __init__(self):
        self.processing_queue = queue.PriorityQueue()
        self.running = False
        self.worker_threads = []
        self.user_contexts = {}  # Cache user contexts for efficiency
        self.insight_callbacks = {}  # User-specific insight delivery callbacks
        
    def start(self, num_workers: int = 3):
        """Start the real-time processing engine"""
        self.running = True
        
        # Start worker threads
        for i in range(num_workers):
            worker = threading.Thread(target=self._process_events_worker, name=f"RTProcessor-{i}")
            worker.daemon = True
            worker.start()
            self.worker_threads.append(worker)
        
        # Start periodic analysis thread
        scheduler = threading.Thread(target=self._scheduled_analysis_worker, name="RTScheduler")
        scheduler.daemon = True
        scheduler.start()
        self.worker_threads.append(scheduler)
        
        logger.info(f"Started real-time processor with {num_workers} workers")
    
    def stop(self):
        """Stop the real-time processing engine"""
        self.running = False
        for worker in self.worker_threads:
            worker.join(timeout=5)
        logger.info("Stopped real-time processor")
    
    # =====================================================================
    # EVENT INGESTION METHODS
    # =====================================================================
    
    def process_new_email(self, email_data: Dict, user_id: int, priority: int = 5):
        """Process new email in real-time"""
        event = ProcessingEvent(
            event_type=EventType.NEW_EMAIL,
            user_id=user_id,
            data=email_data,
            timestamp=datetime.utcnow(),
            priority=priority
        )
        self._queue_event(event)
    
    def process_new_calendar_event(self, event_data: Dict, user_id: int, priority: int = 5):
        """Process new calendar event in real-time"""
        event = ProcessingEvent(
            event_type=EventType.NEW_CALENDAR_EVENT,
            user_id=user_id,
            data=event_data,
            timestamp=datetime.utcnow(),
            priority=priority
        )
        self._queue_event(event)
    
    def process_entity_update(self, entity_type: str, entity_id: int, update_data: Dict, user_id: int):
        """Process entity update and trigger related intelligence updates"""
        event = ProcessingEvent(
            event_type=EventType.ENTITY_UPDATE,
            user_id=user_id,
            data={
                'entity_type': entity_type,
                'entity_id': entity_id,
                'update_data': update_data
            },
            timestamp=datetime.utcnow(),
            priority=3  # Higher priority for entity updates
        )
        self._queue_event(event)
    
    def process_user_action(self, action_type: str, action_data: Dict, user_id: int):
        """Process user action and learn from feedback"""
        event = ProcessingEvent(
            event_type=EventType.USER_ACTION,
            user_id=user_id,
            data={
                'action_type': action_type,
                'action_data': action_data
            },
            timestamp=datetime.utcnow(),
            priority=4
        )
        self._queue_event(event)
    
    # =====================================================================
    # CORE PROCESSING WORKERS
    # =====================================================================
    
    def _process_events_worker(self):
        """Main event processing worker"""
        while self.running:
            try:
                # Get event from queue (blocks until available or timeout)
                try:
                    priority, event = self.processing_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                logger.debug(f"Processing {event.event_type.value} for user {event.user_id}")
                
                # Process based on event type
                if event.event_type == EventType.NEW_EMAIL:
                    self._process_new_email_event(event)
                elif event.event_type == EventType.NEW_CALENDAR_EVENT:
                    self._process_new_calendar_event(event)
                elif event.event_type == EventType.ENTITY_UPDATE:
                    self._process_entity_update_event(event)
                elif event.event_type == EventType.USER_ACTION:
                    self._process_user_action_event(event)
                elif event.event_type == EventType.SCHEDULED_ANALYSIS:
                    self._process_scheduled_analysis_event(event)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in event processing worker: {str(e)}")
                time.sleep(0.1)  # Brief pause on error
    
    def _scheduled_analysis_worker(self):
        """Worker for periodic intelligence analysis"""
        while self.running:
            try:
                # Run scheduled analysis every 15 minutes
                time.sleep(900)  # 15 minutes
                
                # Get active users (those with recent activity)
                active_users = self._get_active_users_for_analysis()
                
                for user_id in active_users:
                    event = ProcessingEvent(
                        event_type=EventType.SCHEDULED_ANALYSIS,
                        user_id=user_id,
                        data={'analysis_type': 'proactive_insights'},
                        timestamp=datetime.utcnow(),
                        priority=7  # Lower priority for scheduled analysis
                    )
                    self._queue_event(event)
                
            except Exception as e:
                logger.error(f"Error in scheduled analysis worker: {str(e)}")
    
    # =====================================================================
    # EVENT PROCESSING METHODS
    # =====================================================================
    
    def _process_new_email_event(self, event: ProcessingEvent):
        """Process new email with real-time intelligence generation"""
        try:
            email_data = event.data
            user_id = event.user_id
            
            # Get cached user context for efficiency
            context = self._get_cached_user_context(user_id)
            
            # Process email with enhanced AI pipeline
            result = enhanced_ai_processor.process_email_with_context(email_data, user_id, context)
            
            if result.success:
                # Update cached context with new information
                self._update_cached_context(user_id, result)
                
                # Generate immediate insights
                immediate_insights = self._generate_immediate_insights(email_data, result, user_id)
                
                # Deliver insights to user
                self._deliver_insights_to_user(user_id, immediate_insights)
                
                # Check for entity cross-references and augmentations
                self._check_cross_entity_augmentations(result, user_id)
                
                logger.info(f"Processed new email in real-time for user {user_id}: "
                           f"{result.entities_created} entities created, {len(immediate_insights)} insights")
            
        except Exception as e:
            logger.error(f"Failed to process new email event: {str(e)}")
    
    def _process_new_calendar_event(self, event: ProcessingEvent):
        """Process new calendar event with intelligence enhancement"""
        try:
            event_data = event.data
            user_id = event.user_id
            
            # Enhance calendar event with email intelligence
            result = enhanced_ai_processor.enhance_calendar_event_with_intelligence(event_data, user_id)
            
            if result.success:
                # Generate meeting preparation insights
                prep_insights = self._generate_meeting_prep_insights(event_data, result, user_id)
                
                # Deliver insights to user
                self._deliver_insights_to_user(user_id, prep_insights)
                
                # Update cached context
                self._update_cached_context(user_id, result)
                
                logger.info(f"Enhanced calendar event in real-time for user {user_id}: "
                           f"{result.entities_created['tasks']} prep tasks created")
            
        except Exception as e:
            logger.error(f"Failed to process new calendar event: {str(e)}")
    
    def _process_entity_update_event(self, event: ProcessingEvent):
        """Process entity updates and propagate intelligence"""
        try:
            entity_type = event.data['entity_type']
            entity_id = event.data['entity_id']
            update_data = event.data['update_data']
            user_id = event.user_id
            
            # Create entity context
            context = EntityContext(
                source_type='update',
                user_id=user_id,
                confidence=0.9
            )
            
            # Augment entity with new data
            entity_engine.augment_entity_from_source(entity_type, entity_id, update_data, context)
            
            # Find related entities that might need updates
            related_entities = self._find_related_entities(entity_type, entity_id, user_id)
            
            # Propagate intelligence to related entities
            for related_entity in related_entities:
                self._propagate_intelligence_update(
                    related_entity['type'], 
                    related_entity['id'], 
                    entity_type, 
                    entity_id, 
                    update_data, 
                    user_id
                )
            
            # Generate insights from entity updates
            update_insights = self._generate_entity_update_insights(entity_type, entity_id, update_data, user_id)
            self._deliver_insights_to_user(user_id, update_insights)
            
            logger.info(f"Processed entity update for {entity_type}:{entity_id}, "
                       f"propagated to {len(related_entities)} related entities")
            
        except Exception as e:
            logger.error(f"Failed to process entity update event: {str(e)}")
    
    def _process_user_action_event(self, event: ProcessingEvent):
        """Process user actions and learn from feedback"""
        try:
            action_type = event.data['action_type']
            action_data = event.data['action_data']
            user_id = event.user_id
            
            # Learning from user feedback
            if action_type == 'insight_feedback':
                self._learn_from_insight_feedback(action_data, user_id)
            elif action_type == 'task_completion':
                self._learn_from_task_completion(action_data, user_id)
            elif action_type == 'topic_management':
                self._learn_from_topic_management(action_data, user_id)
            elif action_type == 'relationship_update':
                self._learn_from_relationship_update(action_data, user_id)
            
            logger.debug(f"Processed user action: {action_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process user action event: {str(e)}")
    
    def _process_scheduled_analysis_event(self, event: ProcessingEvent):
        """Process scheduled proactive analysis"""
        try:
            user_id = event.user_id
            analysis_type = event.data.get('analysis_type', 'proactive_insights')
            
            if analysis_type == 'proactive_insights':
                # Generate proactive insights
                insights = entity_engine.generate_proactive_insights(user_id)
                
                if insights:
                    self._deliver_insights_to_user(user_id, insights)
                    logger.info(f"Generated {len(insights)} proactive insights for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process scheduled analysis: {str(e)}")
    
    # =====================================================================
    # INTELLIGENCE GENERATION METHODS
    # =====================================================================
    
    def _generate_immediate_insights(self, email_data: Dict, processing_result: Any, user_id: int) -> List[IntelligenceInsight]:
        """Generate immediate insights from new email processing"""
        insights = []
        
        try:
            # Insight 1: Important person contact
            sender = email_data.get('sender', '')
            if sender and self._is_important_person(sender, user_id):
                insight = IntelligenceInsight(
                    user_id=user_id,
                    insight_type='important_contact',
                    title=f"New email from important contact",
                    description=f"Received email from {email_data.get('sender_name', sender)}. "
                               f"Subject: {email_data.get('subject', 'No subject')}",
                    priority='high',
                    confidence=0.9,
                    related_entity_type='person',
                    status='new'
                )
                insights.append(insight)
            
            # Insight 2: Urgent task detection
            if hasattr(processing_result, 'entities_created') and processing_result.entities_created.get('tasks', 0) > 0:
                # Check if any high-priority tasks were created
                insight = IntelligenceInsight(
                    user_id=user_id,
                    insight_type='urgent_task',
                    title=f"New tasks extracted from email",
                    description=f"Created {processing_result.entities_created['tasks']} tasks from recent email. "
                               f"Review and prioritize action items.",
                    priority='medium',
                    confidence=0.8,
                    related_entity_type='task',
                    status='new'
                )
                insights.append(insight)
            
            # Insight 3: Topic momentum detection
            if hasattr(processing_result, 'entities_created') and (processing_result.entities_created.get('topics', 0) > 0 or processing_result.entities_updated.get('topics', 0) > 0):
                insight = IntelligenceInsight(
                    user_id=user_id,
                    insight_type='topic_momentum',
                    title=f"Business topic activity detected",
                    description=f"Recent email activity relates to your business topics. "
                               f"Consider scheduling focused time for strategic planning.",
                    priority='medium',
                    confidence=0.7,
                    related_entity_type='topic',
                    status='new'
                )
                insights.append(insight)
            
        except Exception as e:
            logger.error(f"Failed to generate immediate insights: {str(e)}")
        
        return insights
    
    def _generate_meeting_prep_insights(self, event_data: Dict, processing_result: Any, user_id: int) -> List[IntelligenceInsight]:
        """Generate meeting preparation insights"""
        insights = []
        
        try:
            meeting_title = event_data.get('title', 'Unknown Meeting')
            meeting_time = event_data.get('start_time')
            
            # Calculate time until meeting
            if meeting_time:
                if isinstance(meeting_time, str):
                    from dateutil import parser
                    meeting_time = parser.parse(meeting_time)
                
                time_until = meeting_time - datetime.utcnow()
                
                if time_until.total_seconds() > 0 and time_until.days <= 2:  # Within 48 hours
                    # High-priority preparation insight
                    insight = IntelligenceInsight(
                        user_id=user_id,
                        insight_type='meeting_prep',
                        title=f"Prepare for '{meeting_title}'",
                        description=f"Meeting in {time_until.days} days, {time_until.seconds // 3600} hours. "
                                   f"AI has generated preparation tasks based on attendee intelligence.",
                        priority='high' if time_until.days == 0 else 'medium',
                        confidence=0.9,
                        related_entity_type='event',
                        status='new',
                        expires_at=meeting_time
                    )
                    insights.append(insight)
            
            # Insight about preparation tasks created
            if hasattr(processing_result, 'entities_created') and processing_result.entities_created.get('tasks', 0) > 0:
                insight = IntelligenceInsight(
                    user_id=user_id,
                    insight_type='prep_tasks_generated',
                    title=f"Meeting preparation tasks created",
                    description=f"Generated {processing_result.entities_created['tasks']} preparation tasks "
                               f"for '{meeting_title}' based on your email history with attendees.",
                    priority='medium',
                    confidence=0.8,
                    related_entity_type='task',
                    status='new'
                )
                insights.append(insight)
            
        except Exception as e:
            logger.error(f"Failed to generate meeting prep insights: {str(e)}")
        
        return insights
    
    def _generate_entity_update_insights(self, entity_type: str, entity_id: int, update_data: Dict, user_id: int) -> List[IntelligenceInsight]:
        """Generate insights from entity updates"""
        insights = []
        
        try:
            if entity_type == 'topic' and update_data.get('mentions', 0) > 0:
                # Topic becoming hot
                insight = IntelligenceInsight(
                    user_id=user_id,
                    insight_type='topic_momentum',
                    title=f"Topic gaining momentum",
                    description=f"Business topic receiving increased attention. "
                               f"Consider preparing materials or scheduling focused discussion.",
                    priority='medium',
                    confidence=0.7,
                    related_entity_type='topic',
                    related_entity_id=entity_id,
                    status='new'
                )
                insights.append(insight)
            
            elif entity_type == 'person' and update_data.get('interaction'):
                # Relationship activity
                insight = IntelligenceInsight(
                    user_id=user_id,
                    insight_type='relationship_activity',
                    title=f"Recent contact activity",
                    description=f"Ongoing communication with important contact. "
                               f"Relationship engagement is active.",
                    priority='low',
                    confidence=0.6,
                    related_entity_type='person',
                    related_entity_id=entity_id,
                    status='new'
                )
                insights.append(insight)
            
        except Exception as e:
            logger.error(f"Failed to generate entity update insights: {str(e)}")
        
        return insights
    
    # =====================================================================
    # CONTEXT MANAGEMENT AND CACHING
    # =====================================================================
    
    def _get_cached_user_context(self, user_id: int) -> Dict:
        """Get cached user context for efficient processing"""
        if user_id not in self.user_contexts:
            # Load context from enhanced AI processor
            context = enhanced_ai_processor._gather_user_context(user_id)
            self.user_contexts[user_id] = {
                'context': context,
                'last_updated': datetime.utcnow(),
                'version': 1
            }
        else:
            # Check if context needs refresh (every 30 minutes)
            cached = self.user_contexts[user_id]
            if datetime.utcnow() - cached['last_updated'] > timedelta(minutes=30):
                context = enhanced_ai_processor._gather_user_context(user_id)
                cached['context'] = context
                cached['last_updated'] = datetime.utcnow()
                cached['version'] += 1
        
        return self.user_contexts[user_id]['context']
    
    def _update_cached_context(self, user_id: int, processing_result: Any):
        """Update cached context with new processing results"""
        if user_id not in self.user_contexts:
            return
        
        cached = self.user_contexts[user_id]
        
        # Update context with new entities
        if hasattr(processing_result, 'entities_created'):
            # This would update the cached context with newly created entities
            # Implementation would depend on the specific structure
            cached['last_updated'] = datetime.utcnow()
            cached['version'] += 1
    
    def _find_related_entities(self, entity_type: str, entity_id: int, user_id: int) -> List[Dict]:
        """Find entities related to the updated entity"""
        related_entities = []
        
        try:
            from models.database import get_db_manager
            from models.enhanced_models import EntityRelationship
            
            with get_db_manager().get_session() as session:
                # Find direct relationships
                relationships = session.query(EntityRelationship).filter(
                    EntityRelationship.user_id == user_id,
                    ((EntityRelationship.entity_type_a == entity_type) & (EntityRelationship.entity_id_a == entity_id)) |
                    ((EntityRelationship.entity_type_b == entity_type) & (EntityRelationship.entity_id_b == entity_id))
                ).all()
                
                for rel in relationships:
                    if rel.entity_type_a == entity_type and rel.entity_id_a == entity_id:
                        related_entities.append({
                            'type': rel.entity_type_b,
                            'id': rel.entity_id_b,
                            'relationship': rel.relationship_type
                        })
                    else:
                        related_entities.append({
                            'type': rel.entity_type_a,
                            'id': rel.entity_id_a,
                            'relationship': rel.relationship_type
                        })
            
        except Exception as e:
            logger.error(f"Failed to find related entities: {str(e)}")
        
        return related_entities
    
    def _propagate_intelligence_update(self, target_entity_type: str, target_entity_id: int, 
                                     source_entity_type: str, source_entity_id: int, 
                                     update_data: Dict, user_id: int):
        """Propagate intelligence updates to related entities"""
        try:
            # Create propagation context
            context = EntityContext(
                source_type='propagation',
                user_id=user_id,
                confidence=0.7,
                processing_metadata={
                    'source_entity': f"{source_entity_type}:{source_entity_id}",
                    'propagation_data': update_data
                }
            )
            
            # Determine what intelligence to propagate based on entity types
            propagation_data = {}
            
            if source_entity_type == 'topic' and target_entity_type == 'person':
                # Topic update affecting person
                propagation_data = {
                    'topic_activity': True,
                    'related_topic_update': update_data
                }
            elif source_entity_type == 'person' and target_entity_type == 'topic':
                # Person update affecting topic
                propagation_data = {
                    'person_interaction': True,
                    'related_person_update': update_data
                }
            
            if propagation_data:
                entity_engine.augment_entity_from_source(
                    target_entity_type, target_entity_id, propagation_data, context
                )
            
        except Exception as e:
            logger.error(f"Failed to propagate intelligence update: {str(e)}")
    
    def _check_cross_entity_augmentations(self, processing_result: Any, user_id: int):
        """Check for opportunities to augment existing entities with new information"""
        try:
            # This would analyze the processing result and find opportunities to
            # augment existing entities with new information from the processing
            pass
            
        except Exception as e:
            logger.error(f"Failed to check cross-entity augmentations: {str(e)}")
    
    # =====================================================================
    # USER FEEDBACK AND LEARNING
    # =====================================================================
    
    def _learn_from_insight_feedback(self, feedback_data: Dict, user_id: int):
        """Learn from user feedback on insights"""
        try:
            insight_id = feedback_data.get('insight_id')
            feedback_type = feedback_data.get('feedback')  # helpful, not_helpful, etc.
            
            from models.database import get_db_manager
            
            with get_db_manager().get_session() as session:
                insight = session.query(IntelligenceInsight).filter(
                    IntelligenceInsight.id == insight_id,
                    IntelligenceInsight.user_id == user_id
                ).first()
                
                if insight:
                    insight.user_feedback = feedback_type
                    insight.updated_at = datetime.utcnow()
                    session.commit()
                    
                    # Adjust future insight generation based on feedback
                    self._adjust_insight_generation(insight.insight_type, feedback_type, user_id)
            
        except Exception as e:
            logger.error(f"Failed to learn from insight feedback: {str(e)}")
    
    def _learn_from_task_completion(self, completion_data: Dict, user_id: int):
        """Learn from task completion patterns"""
        try:
            task_id = completion_data.get('task_id')
            completion_time = completion_data.get('completion_time')
            
            # This would analyze task completion patterns to improve future task extraction
            # For example: tasks that take longer than estimated, tasks that are never completed, etc.
            
        except Exception as e:
            logger.error(f"Failed to learn from task completion: {str(e)}")
    
    def _learn_from_topic_management(self, topic_data: Dict, user_id: int):
        """Learn from user topic management actions"""
        try:
            action = topic_data.get('action')  # create, merge, delete, etc.
            
            # This would learn user preferences for topic organization
            # and improve future topic extraction and categorization
            
        except Exception as e:
            logger.error(f"Failed to learn from topic management: {str(e)}")
    
    def _learn_from_relationship_update(self, relationship_data: Dict, user_id: int):
        """Learn from relationship updates"""
        try:
            # Learn how users categorize and prioritize relationships
            # to improve future relationship intelligence
            pass
            
        except Exception as e:
            logger.error(f"Failed to learn from relationship update: {str(e)}")
    
    def _adjust_insight_generation(self, insight_type: str, feedback: str, user_id: int):
        """Adjust future insight generation based on user feedback"""
        # This would implement adaptive insight generation
        # For example: if user consistently marks "relationship_alert" as not helpful,
        # reduce frequency or adjust criteria for that insight type
        pass
    
    # =====================================================================
    # UTILITY METHODS
    # =====================================================================
    
    def _queue_event(self, event: ProcessingEvent):
        """Queue event for processing"""
        # Priority queue uses tuple (priority, item)
        self.processing_queue.put((event.priority, event))
    
    def _get_active_users_for_analysis(self) -> List[int]:
        """Get users with recent activity for scheduled analysis"""
        try:
            from models.database import get_db_manager
            
            # Users with activity in last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            with get_db_manager().get_session() as session:
                # This would query for users with recent email processing or other activity
                # For now, return empty list - would be implemented with proper user activity tracking
                return []
            
        except Exception as e:
            logger.error(f"Failed to get active users: {str(e)}")
            return []
    
    def _is_important_person(self, email: str, user_id: int) -> bool:
        """Check if person is marked as important"""
        try:
            from models.database import get_db_manager
            
            with get_db_manager().get_session() as session:
                person = session.query(Person).filter(
                    Person.user_id == user_id,
                    Person.email_address == email.lower(),
                    Person.importance_level > 0.7
                ).first()
                
                return person is not None
                
        except Exception as e:
            logger.error(f"Failed to check person importance: {str(e)}")
            return False
    
    def _deliver_insights_to_user(self, user_id: int, insights: List[IntelligenceInsight]):
        """Deliver insights to user through registered callbacks"""
        if not insights:
            return
        
        try:
            # Store insights in database
            from models.database import get_db_manager
            
            with get_db_manager().get_session() as session:
                for insight in insights:
                    session.add(insight)
                session.commit()
            
            # Deliver through callbacks (WebSocket, push notifications, etc.)
            if user_id in self.insight_callbacks:
                callback = self.insight_callbacks[user_id]
                callback(insights)
            
            logger.info(f"Delivered {len(insights)} insights to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to deliver insights to user: {str(e)}")
    
    def register_insight_callback(self, user_id: int, callback):
        """Register callback for delivering insights to specific user"""
        self.insight_callbacks[user_id] = callback
    
    def unregister_insight_callback(self, user_id: int):
        """Unregister insight callback for user"""
        if user_id in self.insight_callbacks:
            del self.insight_callbacks[user_id]

# Global instance
realtime_processor = RealTimeProcessor() 