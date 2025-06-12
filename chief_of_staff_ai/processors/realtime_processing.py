# Real-Time Processing Pipeline - Continuous Intelligence
# This enables continuous intelligence vs. batch processing

import logging
import threading
import queue
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from processors.unified_entity_engine import entity_engine, EntityContext
from processors.enhanced_ai_pipeline import enhanced_ai_processor

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of events that can be processed"""
    NEW_EMAIL = "new_email"
    NEW_CALENDAR_EVENT = "new_calendar_event"
    USER_ACTION = "user_action"
    SYSTEM_TRIGGER = "system_trigger"

@dataclass
class ProcessingEvent:
    """Container for real-time processing events"""
    event_type: EventType
    data: Dict
    user_id: int
    priority: int = 5  # 1-10, lower number = higher priority
    timestamp: datetime = None
    retries: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class RealTimeProcessor:
    """
    Real-time processing pipeline for continuous intelligence generation.
    Processes events as they happen vs. batch processing.
    """
    
    def __init__(self):
        self.processing_queue = queue.PriorityQueue()
        self.worker_threads = []
        self.is_running = False
        self.stats = {
            'events_processed': 0,
            'events_failed': 0,
            'processing_times': [],
            'last_processed': None
        }
        self.num_workers = 3  # Configurable number of worker threads
        
    def start(self):
        """Start the real-time processing pipeline"""
        if self.is_running:
            logger.warning("Real-time processor already running")
            return
        
        self.is_running = True
        logger.info(f"Starting real-time processor with {self.num_workers} workers")
        
        # Start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"RealTimeWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
        
        logger.info("Real-time processor started successfully")
    
    def stop(self):
        """Stop the real-time processing pipeline"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping real-time processor...")
        
        # Add sentinel values to stop workers
        for _ in self.worker_threads:
            self.processing_queue.put((0, None))  # High priority sentinel
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=5.0)
        
        self.worker_threads.clear()
        logger.info("Real-time processor stopped")
    
    # =====================================================================
    # EVENT PROCESSING METHODS
    # =====================================================================
    
    def process_new_email(self, email_data: Dict, user_id: int, priority: int = 3):
        """Queue new email for real-time processing"""
        event = ProcessingEvent(
            event_type=EventType.NEW_EMAIL,
            data=email_data,
            user_id=user_id,
            priority=priority
        )
        
        self._queue_event(event)
        logger.info(f"Queued new email for processing: {email_data.get('subject', 'No subject')}")
    
    def process_new_calendar_event(self, event_data: Dict, user_id: int, priority: int = 4):
        """Queue new calendar event for real-time processing"""
        event = ProcessingEvent(
            event_type=EventType.NEW_CALENDAR_EVENT,
            data=event_data,
            user_id=user_id,
            priority=priority
        )
        
        self._queue_event(event)
        logger.info(f"Queued new calendar event for processing: {event_data.get('title', 'No title')}")
    
    def process_user_action(self, action_type: str, action_data: Dict, user_id: int, priority: int = 2):
        """Queue user action for real-time processing"""
        event = ProcessingEvent(
            event_type=EventType.USER_ACTION,
            data={'action_type': action_type, 'action_data': action_data},
            user_id=user_id,
            priority=priority
        )
        
        self._queue_event(event)
        logger.info(f"Queued user action for processing: {action_type}")
    
    def trigger_proactive_insights(self, user_id: int, priority: int = 6):
        """Trigger proactive insight generation"""
        event = ProcessingEvent(
            event_type=EventType.SYSTEM_TRIGGER,
            data={'trigger_type': 'proactive_insights'},
            user_id=user_id,
            priority=priority
        )
        
        self._queue_event(event)
        logger.info(f"Triggered proactive insights generation for user {user_id}")
    
    # =====================================================================
    # WORKER THREAD METHODS
    # =====================================================================
    
    def _worker_loop(self):
        """Main worker loop for processing events"""
        thread_name = threading.current_thread().name
        logger.info(f"Worker {thread_name} started")
        
        while self.is_running:
            try:
                # Get next event (blocking call with timeout)
                try:
                    priority, event = self.processing_queue.get(timeout=1.0)
                    
                    # Check for sentinel value (stop signal)
                    if event is None:
                        break
                    
                    # Process the event
                    self._process_event(event, thread_name)
                    
                    # Mark task as done
                    self.processing_queue.task_done()
                    
                except queue.Empty:
                    continue  # Timeout, check if still running
                    
            except Exception as e:
                logger.error(f"Worker {thread_name} error: {str(e)}")
                continue
        
        logger.info(f"Worker {thread_name} stopped")
    
    def _process_event(self, event: ProcessingEvent, worker_name: str):
        """Process a single event"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"[{worker_name}] Processing {event.event_type.value} for user {event.user_id}")
            
            # Route to appropriate processor
            if event.event_type == EventType.NEW_EMAIL:
                self._process_email_event(event)
            elif event.event_type == EventType.NEW_CALENDAR_EVENT:
                self._process_calendar_event(event)
            elif event.event_type == EventType.USER_ACTION:
                self._process_user_action_event(event)
            elif event.event_type == EventType.SYSTEM_TRIGGER:
                self._process_system_trigger_event(event)
            else:
                logger.warning(f"Unknown event type: {event.event_type}")
                return
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.stats['events_processed'] += 1
            self.stats['processing_times'].append(processing_time)
            self.stats['last_processed'] = datetime.utcnow()
            
            # Keep only last 100 processing times for memory efficiency
            if len(self.stats['processing_times']) > 100:
                self.stats['processing_times'] = self.stats['processing_times'][-100:]
            
            logger.info(f"[{worker_name}] Completed {event.event_type.value} in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"[{worker_name}] Failed to process event: {str(e)}")
            self.stats['events_failed'] += 1
            
            # Retry logic
            if event.retries < event.max_retries:
                event.retries += 1
                logger.info(f"Retrying event (attempt {event.retries}/{event.max_retries})")
                self._queue_event(event)
    
    # =====================================================================
    # EVENT PROCESSORS
    # =====================================================================
    
    def _process_email_event(self, event: ProcessingEvent):
        """Process new email event with enhanced AI pipeline"""
        email_data = event.data
        user_id = event.user_id
        
        # Process through enhanced AI pipeline
        result = enhanced_ai_processor.process_email_with_context(email_data, user_id)
        
        if result.success:
            logger.info(f"Email processed: {result.entities_created['people']} people, "
                       f"{result.entities_created['topics']} topics, "
                       f"{result.entities_created['tasks']} tasks created")
            
            # Generate proactive insights if significant entities were created
            total_entities = sum(result.entities_created.values())
            if total_entities > 2:  # Threshold for insight generation
                self.trigger_proactive_insights(user_id, priority=5)
        else:
            logger.error(f"Email processing failed: {result.error}")
    
    def _process_calendar_event(self, event: ProcessingEvent):
        """Process new calendar event with intelligence enhancement"""
        event_data = event.data
        user_id = event.user_id
        
        # Process through enhanced AI pipeline
        result = enhanced_ai_processor.enhance_calendar_event_with_intelligence(event_data, user_id)
        
        if result.success:
            logger.info(f"Calendar event enhanced: {result.entities_created['tasks']} prep tasks created")
        else:
            logger.error(f"Calendar enhancement failed: {result.error}")
    
    def _process_user_action_event(self, event: ProcessingEvent):
        """Process user action events"""
        action_type = event.data.get('action_type')
        action_data = event.data.get('action_data')
        user_id = event.user_id
        
        if action_type == 'insight_feedback':
            self._process_insight_feedback(action_data, user_id)
        elif action_type == 'task_completion':
            self._process_task_completion(action_data, user_id)
        elif action_type == 'manual_entity_creation':
            self._process_manual_entity_creation(action_data, user_id)
        else:
            logger.warning(f"Unknown user action type: {action_type}")
    
    def _process_system_trigger_event(self, event: ProcessingEvent):
        """Process system trigger events"""
        trigger_type = event.data.get('trigger_type')
        user_id = event.user_id
        
        if trigger_type == 'proactive_insights':
            # Generate proactive insights
            insights = entity_engine.generate_proactive_insights(user_id)
            logger.info(f"Generated {len(insights)} proactive insights for user {user_id}")
        elif trigger_type == 'scheduled_analysis':
            # Perform scheduled analysis (e.g., daily patterns)
            self._perform_scheduled_analysis(user_id)
        else:
            logger.warning(f"Unknown system trigger: {trigger_type}")
    
    # =====================================================================
    # SPECIFIC ACTION PROCESSORS
    # =====================================================================
    
    def _process_insight_feedback(self, feedback_data: Dict, user_id: int):
        """Process user feedback on insights"""
        try:
            from models.database import get_db_manager
            from models.enhanced_models import IntelligenceInsight
            
            insight_id = feedback_data.get('insight_id')
            feedback_type = feedback_data.get('feedback')
            
            with get_db_manager().get_session() as session:
                insight = session.query(IntelligenceInsight).get(insight_id)
                
                if insight and insight.user_id == user_id:
                    insight.user_feedback = feedback_type
                    insight.status = 'acted_on' if feedback_type == 'acted_on' else 'viewed'
                    insight.updated_at = datetime.utcnow()
                    session.commit()
                    
                    logger.info(f"Updated insight {insight_id} with feedback: {feedback_type}")
                
        except Exception as e:
            logger.error(f"Failed to process insight feedback: {str(e)}")
    
    def _process_task_completion(self, task_data: Dict, user_id: int):
        """Process task completion and generate follow-up insights"""
        try:
            from models.database import get_db_manager
            from models.enhanced_models import Task
            
            task_id = task_data.get('task_id')
            
            with get_db_manager().get_session() as session:
                task = session.query(Task).get(task_id)
                
                if task and task.user_id == user_id:
                    task.status = 'completed'
                    task.completed_at = datetime.utcnow()
                    task.updated_at = datetime.utcnow()
                    session.commit()
                    
                    logger.info(f"Marked task {task_id} as completed")
                    
                    # Generate follow-up insights based on task completion
                    # This could identify patterns or suggest next actions
                
        except Exception as e:
            logger.error(f"Failed to process task completion: {str(e)}")
    
    def _process_manual_entity_creation(self, entity_data: Dict, user_id: int):
        """Process manually created entities"""
        try:
            entity_type = entity_data.get('entity_type')
            
            context = EntityContext(
                source_type='manual',
                user_id=user_id,
                confidence=1.0  # High confidence for manual entries
            )
            
            if entity_type == 'person':
                entity_engine.create_or_update_person(
                    email=entity_data.get('email'),
                    name=entity_data.get('name'),
                    context=context
                )
            elif entity_type == 'topic':
                entity_engine.create_or_update_topic(
                    topic_name=entity_data.get('name'),
                    description=entity_data.get('description'),
                    keywords=entity_data.get('keywords', []),
                    context=context
                )
            elif entity_type == 'task':
                entity_engine.create_task_with_full_context(
                    description=entity_data.get('description'),
                    assignee_email=entity_data.get('assignee_email'),
                    topic_names=entity_data.get('topics', []),
                    context=context,
                    priority=entity_data.get('priority', 'medium')
                )
            
            logger.info(f"Created manual {entity_type} entity")
            
        except Exception as e:
            logger.error(f"Failed to process manual entity creation: {str(e)}")
    
    def _perform_scheduled_analysis(self, user_id: int):
        """Perform scheduled analysis like daily patterns, trends, etc."""
        try:
            # This would perform more sophisticated analysis
            # For now, just trigger insight generation
            insights = entity_engine.generate_proactive_insights(user_id)
            logger.info(f"Scheduled analysis generated {len(insights)} insights for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to perform scheduled analysis: {str(e)}")
    
    # =====================================================================
    # UTILITY METHODS
    # =====================================================================
    
    def _queue_event(self, event: ProcessingEvent):
        """Add event to processing queue"""
        if not self.is_running:
            logger.warning("Real-time processor not running, event ignored")
            return
        
        # Use priority as the sort key (lower number = higher priority)
        self.processing_queue.put((event.priority, event))
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        stats = self.stats.copy()
        
        # Calculate additional metrics
        if stats['processing_times']:
            stats['avg_processing_time'] = sum(stats['processing_times']) / len(stats['processing_times'])
            stats['max_processing_time'] = max(stats['processing_times'])
            stats['min_processing_time'] = min(stats['processing_times'])
        else:
            stats['avg_processing_time'] = 0.0
            stats['max_processing_time'] = 0.0
            stats['min_processing_time'] = 0.0
        
        stats['queue_size'] = self.processing_queue.qsize()
        stats['workers_active'] = len([t for t in self.worker_threads if t.is_alive()])
        stats['is_running'] = self.is_running
        
        return stats
    
    def clear_queue(self):
        """Clear the processing queue (emergency use)"""
        logger.warning("Clearing real-time processing queue")
        
        # Drain the queue
        while not self.processing_queue.empty():
            try:
                self.processing_queue.get_nowait()
                self.processing_queue.task_done()
            except queue.Empty:
                break
    
    def get_queue_status(self) -> Dict:
        """Get detailed queue status"""
        return {
            'queue_size': self.processing_queue.qsize(),
            'is_running': self.is_running,
            'worker_count': len(self.worker_threads),
            'active_workers': len([t for t in self.worker_threads if t.is_alive()]),
            'events_processed': self.stats['events_processed'],
            'events_failed': self.stats['events_failed'],
            'last_processed': self.stats['last_processed']
        }

# Global instance
realtime_processor = RealTimeProcessor() 