# Integration Manager - Unified Processor Coordination
# This coordinates between all enhanced processors and provides unified interfaces

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass

# Import enhanced processors
from processors.enhanced_processors.enhanced_task_processor import enhanced_task_processor
from processors.enhanced_processors.enhanced_email_processor import enhanced_email_processor
from processors.enhanced_processors.enhanced_data_normalizer import enhanced_data_normalizer

# Import unified processors
from processors.unified_entity_engine import entity_engine, EntityContext
from processors.enhanced_ai_pipeline import enhanced_ai_processor
from processors.realtime_processor import realtime_processor

# Import adapter layer for backward compatibility
from processors.adapter_layer import task_extractor, email_intelligence, email_normalizer

logger = logging.getLogger(__name__)

@dataclass
class ProcessingPlan:
    """Plan for processing various types of data"""
    data_type: str
    processing_steps: List[str]
    expected_entities: List[str]
    real_time: bool
    priority: int

class IntegrationManager:
    """
    Central integration manager that coordinates all processors.
    This is the main interface for the application to interact with processors.
    """
    
    def __init__(self):
        # Enhanced processors
        self.task_processor = enhanced_task_processor
        self.email_processor = enhanced_email_processor
        self.data_normalizer = enhanced_data_normalizer
        
        # Unified processors
        self.entity_engine = entity_engine
        self.ai_processor = enhanced_ai_processor
        self.realtime_processor = realtime_processor
        
        # Adapter layer for backward compatibility
        self.legacy_task_extractor = task_extractor
        self.legacy_email_intelligence = email_intelligence
        self.legacy_email_normalizer = email_normalizer
        
        # Processing statistics
        self.processing_stats = {
            'emails_processed': 0,
            'tasks_created': 0,
            'entities_created': 0,
            'insights_generated': 0,
            'processing_time_total': 0.0
        }
        
        logger.info("Integration Manager initialized with enhanced processor architecture")
    
    # =====================================================================
    # UNIFIED PROCESSING INTERFACES
    # =====================================================================
    
    def process_email_complete(self, email_data: Dict, user_id: int, 
                             real_time: bool = True, 
                             legacy_mode: bool = False) -> Dict[str, Any]:
        """
        Complete email processing with full entity creation and intelligence.
        This is the main email processing interface.
        """
        try:
            start_time = datetime.utcnow()
            
            if legacy_mode:
                # Use legacy adapters for backward compatibility
                logger.info(f"Processing email in legacy mode for user {user_id}")
                result = self._process_email_legacy_mode(email_data, user_id)
            else:
                # Use enhanced processors
                logger.info(f"Processing email with enhanced processors for user {user_id}")
                result = self._process_email_enhanced_mode(email_data, user_id, real_time)
            
            # Update processing statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_processing_stats('email', result, processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in complete email processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processing_mode': 'legacy' if legacy_mode else 'enhanced'
            }
    
    def process_calendar_event_complete(self, event_data: Dict, user_id: int,
                                      real_time: bool = True) -> Dict[str, Any]:
        """
        Complete calendar event processing with meeting preparation.
        """
        try:
            start_time = datetime.utcnow()
            
            # Step 1: Normalize calendar data
            logger.info(f"Processing calendar event for user {user_id}")
            normalization_result = self.data_normalizer.normalize_calendar_data(event_data)
            
            if not normalization_result.success:
                return {
                    'success': False,
                    'error': f"Calendar normalization failed: {normalization_result.issues_found}"
                }
            
            normalized_event = normalization_result.normalized_data
            
            # Step 2: Process with enhanced processors
            if real_time:
                # Queue for real-time processing
                self.realtime_processor.process_new_calendar_event(normalized_event, user_id)
                result = {
                    'success': True,
                    'status': 'queued_for_realtime',
                    'event_id': normalized_event.get('google_event_id'),
                    'message': 'Calendar event queued for real-time processing'
                }
            else:
                # Process immediately
                ai_result = self.ai_processor.enhance_calendar_event_with_intelligence(
                    normalized_event, user_id
                )
                
                # Create preparation tasks
                task_result = self.task_processor.process_tasks_from_calendar_event(
                    normalized_event, user_id
                )
                
                result = {
                    'success': True,
                    'event_processing': ai_result,
                    'task_processing': task_result,
                    'normalized_event': normalized_event
                }
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_processing_stats('calendar', result, processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in calendar event processing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_manual_task_complete(self, task_description: str, user_id: int,
                                  assignee_email: str = None,
                                  topic_names: List[str] = None,
                                  project_name: str = None,
                                  due_date: datetime = None,
                                  priority: str = 'medium') -> Dict[str, Any]:
        """
        Complete manual task creation with entity relationships.
        """
        try:
            result = self.task_processor.create_manual_task_with_context(
                task_description=task_description,
                assignee_email=assignee_email,
                topic_names=topic_names,
                project_name=project_name,
                due_date=due_date,
                priority=priority,
                user_id=user_id
            )
            
            # Update statistics
            if result['success']:
                self.processing_stats['tasks_created'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error in manual task creation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # =====================================================================
    # BATCH PROCESSING INTERFACES
    # =====================================================================
    
    def process_email_batch(self, email_list: List[Dict], user_id: int,
                           batch_size: int = 10,
                           real_time: bool = False) -> Dict[str, Any]:
        """
        Process multiple emails in optimized batches.
        """
        try:
            logger.info(f"Processing email batch of {len(email_list)} emails for user {user_id}")
            
            # Use enhanced email processor for batch processing
            result = self.email_processor.process_email_batch(email_list, user_id, batch_size)
            
            # Update statistics
            if result['success']:
                batch_result = result['result']
                self.processing_stats['emails_processed'] += batch_result['processed']
                self.processing_stats['processing_time_total'] += batch_result['batch_summary']['processing_time']
                
                # Update entity stats
                entities_created = batch_result['batch_summary']['total_entities_created']
                for entity_type, count in entities_created.items():
                    if entity_type == 'tasks':
                        self.processing_stats['tasks_created'] += count
                    self.processing_stats['entities_created'] += count
            
            return result
            
        except Exception as e:
            logger.error(f"Error in email batch processing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # =====================================================================
    # ANALYTICS AND INSIGHTS
    # =====================================================================
    
    def generate_user_insights(self, user_id: int, analysis_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Generate comprehensive user insights from all data sources.
        """
        try:
            insights = {
                'user_id': user_id,
                'analysis_type': analysis_type,
                'generated_at': datetime.utcnow().isoformat(),
                'insights': {}
            }
            
            if analysis_type in ['comprehensive', 'email']:
                # Email pattern analysis
                email_insights = self.email_processor.analyze_email_patterns(user_id)
                if email_insights['success']:
                    insights['insights']['email_patterns'] = email_insights['result']
            
            if analysis_type in ['comprehensive', 'tasks']:
                # Task pattern analysis
                task_insights = self.task_processor.analyze_task_patterns(user_id)
                if task_insights['success']:
                    insights['insights']['task_patterns'] = task_insights['result']
            
            if analysis_type in ['comprehensive', 'proactive']:
                # Proactive insights from entity engine
                proactive_insights = self.entity_engine.generate_proactive_insights(user_id)
                insights['insights']['proactive_insights'] = [
                    {
                        'type': insight.insight_type,
                        'title': insight.title,
                        'description': insight.description,
                        'priority': insight.priority,
                        'confidence': insight.confidence
                    }
                    for insight in proactive_insights
                ]
            
            return {
                'success': True,
                'result': insights
            }
            
        except Exception as e:
            logger.error(f"Error generating user insights: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing statistics.
        """
        return {
            'success': True,
            'result': {
                'processing_stats': self.processing_stats.copy(),
                'processor_status': {
                    'enhanced_processors_active': True,
                    'legacy_adapters_available': True,
                    'real_time_processing': self.realtime_processor.running,
                    'entity_engine_active': True
                },
                'performance_metrics': {
                    'avg_processing_time': (
                        self.processing_stats['processing_time_total'] / 
                        max(1, self.processing_stats['emails_processed'])
                    ),
                    'entities_per_email': (
                        self.processing_stats['entities_created'] / 
                        max(1, self.processing_stats['emails_processed'])
                    )
                }
            }
        }
    
    # =====================================================================
    # LEGACY COMPATIBILITY METHODS
    # =====================================================================
    
    def get_legacy_task_extractor(self):
        """Get legacy task extractor for backward compatibility"""
        return self.legacy_task_extractor
    
    def get_legacy_email_intelligence(self):
        """Get legacy email intelligence for backward compatibility"""
        return self.legacy_email_intelligence
    
    def get_legacy_email_normalizer(self):
        """Get legacy email normalizer for backward compatibility"""
        return self.legacy_email_normalizer
    
    # =====================================================================
    # REAL-TIME PROCESSING CONTROL
    # =====================================================================
    
    def start_realtime_processing(self, num_workers: int = 3):
        """Start real-time processing"""
        try:
            self.realtime_processor.start(num_workers)
            logger.info(f"Started real-time processing with {num_workers} workers")
            return {'success': True, 'message': 'Real-time processing started'}
        except Exception as e:
            logger.error(f"Failed to start real-time processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def stop_realtime_processing(self):
        """Stop real-time processing"""
        try:
            self.realtime_processor.stop()
            logger.info("Stopped real-time processing")
            return {'success': True, 'message': 'Real-time processing stopped'}
        except Exception as e:
            logger.error(f"Failed to stop real-time processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def register_insight_callback(self, user_id: int, callback_function):
        """Register callback for real-time insight delivery"""
        self.realtime_processor.register_insight_callback(user_id, callback_function)
        logger.info(f"Registered insight callback for user {user_id}")
    
    # =====================================================================
    # PRIVATE HELPER METHODS
    # =====================================================================
    
    def _process_email_enhanced_mode(self, email_data: Dict, user_id: int, real_time: bool) -> Dict[str, Any]:
        """Process email using enhanced processors"""
        # Step 1: Normalize email data
        normalization_result = self.data_normalizer.normalize_email_data(email_data)
        
        if not normalization_result.success:
            return {
                'success': False,
                'error': f"Email normalization failed: {normalization_result.issues_found}",
                'processing_mode': 'enhanced'
            }
        
        normalized_email = normalization_result.normalized_data
        
        # Step 2: Process with enhanced email processor
        processing_result = self.email_processor.process_email_comprehensive(
            normalized_email, user_id, real_time
        )
        
        # Add normalization info to result
        if processing_result['success']:
            processing_result['normalization'] = {
                'quality_score': normalization_result.quality_score,
                'issues_found': normalization_result.issues_found
            }
        
        processing_result['processing_mode'] = 'enhanced'
        return processing_result
    
    def _process_email_legacy_mode(self, email_data: Dict, user_id: int) -> Dict[str, Any]:
        """Process email using legacy adapters"""
        # Step 1: Normalize with legacy adapter
        normalized_email = self.legacy_email_normalizer.normalize_gmail_email(email_data)
        
        if normalized_email.get('error'):
            return {
                'success': False,
                'error': normalized_email.get('error_message'),
                'processing_mode': 'legacy'
            }
        
        # Step 2: Extract tasks
        task_result = self.legacy_task_extractor.extract_tasks_from_email(normalized_email, user_id)
        
        # Step 3: Process with email intelligence
        intelligence_result = self.legacy_email_intelligence.process_email(normalized_email, user_id)
        
        # Combine results
        combined_result = {
            'success': True,
            'processing_mode': 'legacy',
            'normalized_email': normalized_email,
            'task_extraction': task_result,
            'email_intelligence': intelligence_result
        }
        
        return combined_result
    
    def _update_processing_stats(self, data_type: str, result: Dict, processing_time: float):
        """Update internal processing statistics"""
        self.processing_stats['processing_time_total'] += processing_time
        
        if data_type == 'email' and result.get('success'):
            self.processing_stats['emails_processed'] += 1
            
            # Count entities if available
            if 'processing_summary' in result.get('result', {}):
                entities_created = result['result']['processing_summary'].get('entities_created', {})
                for entity_type, count in entities_created.items():
                    if entity_type == 'tasks':
                        self.processing_stats['tasks_created'] += count
                    self.processing_stats['entities_created'] += count
                
                insights_count = result['result']['processing_summary'].get('insights_generated', 0)
                self.processing_stats['insights_generated'] += insights_count

# =====================================================================
# GLOBAL INTEGRATION MANAGER INSTANCE
# =====================================================================

# Create global integration manager instance
integration_manager = IntegrationManager()

# Export for easy import
__all__ = ['integration_manager', 'IntegrationManager', 'ProcessingPlan']

logger.info("Integration Manager module loaded - unified processor coordination active") 