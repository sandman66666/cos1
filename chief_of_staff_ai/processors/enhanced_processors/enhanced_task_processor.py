# Enhanced Task Processor - Entity-Centric Task Management
# This replaces the old task_extractor.py with unified entity engine integration

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from processors.unified_entity_engine import entity_engine, EntityContext
from processors.enhanced_ai_pipeline import enhanced_ai_processor
from models.enhanced_models import Task, Person, Topic, Email, CalendarEvent

logger = logging.getLogger(__name__)

class EnhancedTaskProcessor:
    """
    Enhanced task processor that leverages the unified entity engine.
    This replaces the old task_extractor.py with context-aware, entity-integrated task management.
    """
    
    def __init__(self):
        self.entity_engine = entity_engine
        self.ai_processor = enhanced_ai_processor
        
    # =====================================================================
    # MAIN TASK PROCESSING METHODS
    # =====================================================================
    
    def process_tasks_from_email(self, email_data: Dict, user_id: int) -> Dict[str, Any]:
        """
        Process tasks from email using enhanced AI pipeline and entity context.
        This replaces the old scattered task extraction with unified processing.
        """
        try:
            logger.info(f"Processing tasks from email for user {user_id}")
            
            # Use enhanced AI pipeline for comprehensive processing
            context = EntityContext(
                source_type='email',
                source_id=email_data.get('id'),
                user_id=user_id,
                confidence=0.8
            )
            
            # Single AI call that handles tasks, entities, and relationships
            result = self.ai_processor.process_email_with_context(email_data, user_id)
            
            if result.success:
                # Extract task-specific information from the comprehensive result
                task_summary = {
                    'tasks_created': result.entities_created.get('tasks', 0),
                    'task_details': self._extract_task_details_from_result(result, user_id),
                    'related_entities': {
                        'people': result.entities_created.get('people', 0),
                        'topics': result.entities_created.get('topics', 0),
                        'projects': result.entities_created.get('projects', 0)
                    },
                    'processing_time': result.processing_time,
                    'insights': result.insights_generated
                }
                
                logger.info(f"Successfully processed {task_summary['tasks_created']} tasks with full context")
                return {'success': True, 'result': task_summary}
            else:
                logger.error(f"Failed to process email tasks: {result.error}")
                return {'success': False, 'error': result.error}
                
        except Exception as e:
            logger.error(f"Error in enhanced task processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_tasks_from_calendar_event(self, event_data: Dict, user_id: int) -> Dict[str, Any]:
        """
        Process preparation tasks from calendar events with attendee intelligence.
        """
        try:
            logger.info(f"Processing meeting prep tasks for user {user_id}")
            
            # Use enhanced AI pipeline for meeting preparation
            result = self.ai_processor.enhance_calendar_event_with_intelligence(event_data, user_id)
            
            if result.success:
                task_summary = {
                    'prep_tasks_created': result.entities_created.get('tasks', 0),
                    'task_details': self._extract_prep_task_details(result, event_data, user_id),
                    'meeting_intelligence': {
                        'attendee_analysis': result.entities_updated.get('people', 0),
                        'business_context': 'Meeting context enhanced with email intelligence'
                    },
                    'insights': result.insights_generated
                }
                
                logger.info(f"Created {task_summary['prep_tasks_created']} preparation tasks")
                return {'success': True, 'result': task_summary}
            else:
                return {'success': False, 'error': result.error}
                
        except Exception as e:
            logger.error(f"Error in calendar task processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_manual_task_with_context(self, task_description: str, 
                                      assignee_email: str = None,
                                      topic_names: List[str] = None,
                                      project_name: str = None,
                                      due_date: datetime = None,
                                      priority: str = 'medium',
                                      user_id: int = None) -> Dict[str, Any]:
        """
        Create manual task with full entity context and relationships.
        This provides the same functionality as the old system but with entity integration.
        """
        try:
            context = EntityContext(
                source_type='manual',
                user_id=user_id,
                confidence=1.0  # High confidence for manual tasks
            )
            
            # Use unified entity engine for task creation with full context
            task = entity_engine.create_task_with_full_context(
                description=task_description,
                assignee_email=assignee_email,
                topic_names=topic_names or [],
                context=context,
                due_date=due_date,
                priority=priority
            )
            
            if task:
                # Create project relationship if specified
                if project_name:
                    self._link_task_to_project(task, project_name, user_id)
                
                task_details = {
                    'task_id': task.id,
                    'description': task.description,
                    'context_story': task.context_story,
                    'assignee': assignee_email,
                    'priority': priority,
                    'due_date': due_date.isoformat() if due_date else None,
                    'related_topics': topic_names or [],
                    'related_project': project_name
                }
                
                logger.info(f"Created manual task with full context: {task.description[:50]}...")
                return {'success': True, 'result': task_details}
            else:
                return {'success': False, 'error': 'Failed to create task'}
                
        except Exception as e:
            logger.error(f"Error creating manual task: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # =====================================================================
    # TASK MANAGEMENT AND UPDATES
    # =====================================================================
    
    def update_task_status(self, task_id: int, new_status: str, user_id: int, 
                          completion_notes: str = None) -> Dict[str, Any]:
        """
        Update task status with intelligence propagation to related entities.
        """
        try:
            from models.database import get_db_manager
            
            with get_db_manager().get_session() as session:
                task = session.query(Task).filter(
                    Task.id == task_id,
                    Task.user_id == user_id
                ).first()
                
                if not task:
                    return {'success': False, 'error': 'Task not found'}
                
                old_status = task.status
                task.status = new_status
                task.updated_at = datetime.utcnow()
                
                if new_status == 'completed':
                    task.completed_at = datetime.utcnow()
                
                # Add completion notes if provided
                if completion_notes:
                    task.context_story = f"{task.context_story}. Completed: {completion_notes}"
                
                session.commit()
                
                # Propagate task completion intelligence to related entities
                self._propagate_task_status_update(task, old_status, new_status, user_id)
                
                # Generate insights from task completion patterns
                if new_status == 'completed':
                    self._analyze_task_completion_patterns(task, user_id)
                
                result = {
                    'task_id': task_id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'updated_at': task.updated_at.isoformat(),
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
                
                logger.info(f"Updated task {task_id} status: {old_status} -> {new_status}")
                return {'success': True, 'result': result}
                
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_user_tasks_with_context(self, user_id: int, 
                                  status_filter: str = None,
                                  priority_filter: str = None,
                                  limit: int = 100) -> Dict[str, Any]:
        """
        Get user tasks with full entity context and relationships.
        """
        try:
            from models.database import get_db_manager
            
            with get_db_manager().get_session() as session:
                query = session.query(Task).filter(Task.user_id == user_id)
                
                if status_filter:
                    query = query.filter(Task.status == status_filter)
                if priority_filter:
                    query = query.filter(Task.priority == priority_filter)
                
                tasks = query.order_by(Task.created_at.desc()).limit(limit).all()
                
                # Enrich tasks with entity context
                enriched_tasks = []
                for task in tasks:
                    task_data = {
                        'id': task.id,
                        'description': task.description,
                        'context_story': task.context_story,
                        'status': task.status,
                        'priority': task.priority,
                        'confidence': task.confidence,
                        'created_at': task.created_at.isoformat(),
                        'updated_at': task.updated_at.isoformat(),
                        'due_date': task.due_date.isoformat() if task.due_date else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        
                        # Entity relationships
                        'assignee': self._get_task_assignee_info(task),
                        'related_topics': self._get_task_topic_info(task),
                        'source_context': self._get_task_source_context(task),
                        'entity_relationships': self._get_task_entity_relationships(task)
                    }
                    enriched_tasks.append(task_data)
                
                result = {
                    'total_tasks': len(enriched_tasks),
                    'filtered_by': {
                        'status': status_filter,
                        'priority': priority_filter
                    },
                    'tasks': enriched_tasks
                }
                
                return {'success': True, 'result': result}
                
        except Exception as e:
            logger.error(f"Error getting user tasks: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def analyze_task_patterns(self, user_id: int, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze user task patterns for productivity insights.
        """
        try:
            from models.database import get_db_manager
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            with get_db_manager().get_session() as session:
                tasks = session.query(Task).filter(
                    Task.user_id == user_id,
                    Task.created_at > cutoff_date
                ).all()
                
                # Analyze patterns
                patterns = {
                    'total_tasks': len(tasks),
                    'completion_rate': self._calculate_completion_rate(tasks),
                    'priority_distribution': self._analyze_priority_distribution(tasks),
                    'topic_frequency': self._analyze_topic_frequency(tasks),
                    'source_breakdown': self._analyze_task_sources(tasks),
                    'productivity_trends': self._analyze_productivity_trends(tasks),
                    'insights': self._generate_productivity_insights(tasks, user_id)
                }
                
                return {'success': True, 'result': patterns}
                
        except Exception as e:
            logger.error(f"Error analyzing task patterns: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # =====================================================================
    # HELPER METHODS
    # =====================================================================
    
    def _extract_task_details_from_result(self, result: Any, user_id: int) -> List[Dict]:
        """Extract task details from enhanced AI processing result"""
        try:
            from models.database import get_db_manager
            
            # Get recently created tasks for this user
            with get_db_manager().get_session() as session:
                recent_tasks = session.query(Task).filter(
                    Task.user_id == user_id,
                    Task.created_at > datetime.utcnow() - timedelta(minutes=5)
                ).order_by(Task.created_at.desc()).limit(10).all()
                
                task_details = []
                for task in recent_tasks:
                    task_details.append({
                        'id': task.id,
                        'description': task.description,
                        'context_story': task.context_story,
                        'priority': task.priority,
                        'confidence': task.confidence,
                        'assignee_id': task.assignee_id,
                        'source_email_id': task.source_email_id,
                        'created_at': task.created_at.isoformat()
                    })
                
                return task_details
                
        except Exception as e:
            logger.error(f"Error extracting task details: {str(e)}")
            return []
    
    def _extract_prep_task_details(self, result: Any, event_data: Dict, user_id: int) -> List[Dict]:
        """Extract preparation task details from calendar event processing"""
        try:
            # Similar to above but filtered for preparation tasks
            return self._extract_task_details_from_result(result, user_id)
        except Exception as e:
            logger.error(f"Error extracting prep task details: {str(e)}")
            return []
    
    def _link_task_to_project(self, task: Task, project_name: str, user_id: int):
        """Link task to project through entity relationships"""
        try:
            # Find or create project
            project_topic = entity_engine.create_or_update_topic(
                topic_name=project_name,
                description=f"Project: {project_name}",
                context=EntityContext(source_type='manual', user_id=user_id)
            )
            
            if project_topic:
                # Create entity relationship
                entity_engine.create_entity_relationship(
                    'task', task.id,
                    'topic', project_topic.id,
                    'belongs_to_project',
                    EntityContext(source_type='manual', user_id=user_id)
                )
                
        except Exception as e:
            logger.error(f"Error linking task to project: {str(e)}")
    
    def _propagate_task_status_update(self, task: Task, old_status: str, new_status: str, user_id: int):
        """Propagate task status changes to related entities"""
        try:
            if new_status == 'completed':
                # Update related topic activity
                for topic in task.topics:
                    update_data = {'task_completed': True, 'completion_date': datetime.utcnow()}
                    entity_engine.augment_entity_from_source(
                        'topic', topic.id, update_data,
                        EntityContext(source_type='task_completion', user_id=user_id)
                    )
                
                # Update assignee activity if applicable
                if task.assignee:
                    update_data = {'task_completed': True}
                    entity_engine.augment_entity_from_source(
                        'person', task.assignee.id, update_data,
                        EntityContext(source_type='task_completion', user_id=user_id)
                    )
                    
        except Exception as e:
            logger.error(f"Error propagating task status update: {str(e)}")
    
    def _analyze_task_completion_patterns(self, task: Task, user_id: int):
        """Analyze task completion for productivity insights"""
        try:
            # Calculate completion time
            if task.created_at and task.completed_at:
                completion_time = task.completed_at - task.created_at
                
                # Store completion pattern data
                # This would feed into productivity analytics
                logger.debug(f"Task completed in {completion_time.days} days: {task.description[:50]}...")
                
        except Exception as e:
            logger.error(f"Error analyzing task completion patterns: {str(e)}")
    
    def _get_task_assignee_info(self, task: Task) -> Optional[Dict]:
        """Get assignee information for task"""
        if task.assignee:
            return {
                'id': task.assignee.id,
                'name': task.assignee.name,
                'email': task.assignee.email_address,
                'relationship': task.assignee.relationship_type
            }
        return None
    
    def _get_task_topic_info(self, task: Task) -> List[Dict]:
        """Get topic information for task"""
        topics = []
        for topic in task.topics:
            topics.append({
                'id': topic.id,
                'name': topic.name,
                'description': topic.description,
                'strategic_importance': topic.strategic_importance
            })
        return topics
    
    def _get_task_source_context(self, task: Task) -> Dict:
        """Get source context for task"""
        context = {'source_type': 'unknown'}
        
        if task.source_email_id:
            context = {'source_type': 'email', 'source_id': task.source_email_id}
        elif task.source_event_id:
            context = {'source_type': 'calendar', 'source_id': task.source_event_id}
        else:
            context = {'source_type': 'manual'}
            
        return context
    
    def _get_task_entity_relationships(self, task: Task) -> List[Dict]:
        """Get entity relationships for task"""
        relationships = []
        
        # Add topic relationships
        for topic in task.topics:
            relationships.append({
                'entity_type': 'topic',
                'entity_id': topic.id,
                'entity_name': topic.name,
                'relationship_type': 'related_to'
            })
        
        # Add assignee relationship
        if task.assignee:
            relationships.append({
                'entity_type': 'person',
                'entity_id': task.assignee.id,
                'entity_name': task.assignee.name,
                'relationship_type': 'assigned_to'
            })
        
        return relationships
    
    # =====================================================================
    # ANALYTICS METHODS
    # =====================================================================
    
    def _calculate_completion_rate(self, tasks: List[Task]) -> float:
        """Calculate task completion rate"""
        if not tasks:
            return 0.0
        
        completed = len([t for t in tasks if t.status == 'completed'])
        return completed / len(tasks) * 100
    
    def _analyze_priority_distribution(self, tasks: List[Task]) -> Dict:
        """Analyze priority distribution of tasks"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for task in tasks:
            priority = task.priority or 'medium'
            if priority in distribution:
                distribution[priority] += 1
        
        return distribution
    
    def _analyze_topic_frequency(self, tasks: List[Task]) -> List[Dict]:
        """Analyze which topics appear most frequently in tasks"""
        topic_counts = {}
        
        for task in tasks:
            for topic in task.topics:
                topic_name = topic.name
                if topic_name not in topic_counts:
                    topic_counts[topic_name] = 0
                topic_counts[topic_name] += 1
        
        # Sort by frequency
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [{'topic': topic, 'count': count} for topic, count in sorted_topics[:10]]
    
    def _analyze_task_sources(self, tasks: List[Task]) -> Dict:
        """Analyze where tasks come from"""
        sources = {'email': 0, 'calendar': 0, 'manual': 0}
        
        for task in tasks:
            if task.source_email_id:
                sources['email'] += 1
            elif task.source_event_id:
                sources['calendar'] += 1
            else:
                sources['manual'] += 1
        
        return sources
    
    def _analyze_productivity_trends(self, tasks: List[Task]) -> Dict:
        """Analyze productivity trends over time"""
        # Group tasks by week
        weekly_stats = {}
        
        for task in tasks:
            week_key = task.created_at.strftime('%Y-W%U')
            if week_key not in weekly_stats:
                weekly_stats[week_key] = {'created': 0, 'completed': 0}
            
            weekly_stats[week_key]['created'] += 1
            if task.status == 'completed':
                weekly_stats[week_key]['completed'] += 1
        
        return weekly_stats
    
    def _generate_productivity_insights(self, tasks: List[Task], user_id: int) -> List[str]:
        """Generate productivity insights from task patterns"""
        insights = []
        
        if not tasks:
            return insights
        
        completion_rate = self._calculate_completion_rate(tasks)
        
        if completion_rate > 80:
            insights.append("Excellent task completion rate! You're highly productive.")
        elif completion_rate > 60:
            insights.append("Good task completion rate. Consider prioritizing high-impact tasks.")
        else:
            insights.append("Task completion could be improved. Focus on fewer, high-priority tasks.")
        
        # Analyze overdue tasks
        overdue_tasks = [t for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status != 'completed']
        if overdue_tasks:
            insights.append(f"You have {len(overdue_tasks)} overdue tasks. Consider rescheduling or reprioritizing.")
        
        return insights

# Global instance for easy import
enhanced_task_processor = EnhancedTaskProcessor() 