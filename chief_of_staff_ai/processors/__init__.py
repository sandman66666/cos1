"""
Enhanced Processor Integration Manager
Coordinates all processing components as specified in the refactor
"""
from .unified_entity_engine import entity_engine
from .enhanced_ai_pipeline import enhanced_ai_processor  
from .realtime_processing import realtime_processor
from .analytics.predictive_analytics import predictive_analytics

import logging

logger = logging.getLogger(__name__)

class ProcessorManager:
    """Coordinates all processing components"""
    
    def __init__(self):
        self.entity_engine = entity_engine
        self.ai_processor = enhanced_ai_processor
        self.realtime_processor = realtime_processor
        self.predictive_analytics = predictive_analytics
        
        logger.info("ProcessorManager initialized with all enhanced components")
    
    def start_all_processors(self):
        """Start all processing components"""
        try:
            self.realtime_processor.start()
            self.predictive_analytics.start()
            
            logger.info("All processors started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start processors: {str(e)}")
            return False
    
    def stop_all_processors(self):
        """Stop all processing components"""
        try:
            self.realtime_processor.stop()
            self.predictive_analytics.stop()
            
            logger.info("All processors stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop processors: {str(e)}")
            return False
    
    def get_processing_statistics(self):
        """Get comprehensive processing statistics"""
        try:
            stats = {
                'success': True,
                'real_time_processing': {
                    'is_running': self.realtime_processor.is_running,
                    'queue_size': getattr(self.realtime_processor, 'queue_size', 0),
                    'workers_active': getattr(self.realtime_processor, 'workers_active', 0),
                    'events_processed': getattr(self.realtime_processor, 'events_processed', 0)
                },
                'predictive_analytics': {
                    'is_running': self.predictive_analytics.is_running,
                },
                'entity_engine': {
                    'available': self.entity_engine is not None
                },
                'ai_processor': {
                    'available': self.ai_processor is not None
                }
            }
            
            return {'success': True, 'result': stats}
            
        except Exception as e:
            logger.error(f"Failed to get processing statistics: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def generate_user_insights(self, user_id: int, insight_type: str = 'comprehensive'):
        """Generate comprehensive user insights using all processors"""
        try:
            insights = {
                'proactive_insights': [],
                'predictive_analytics': {},
                'entity_intelligence': {},
                'real_time_status': {}
            }
            
            # Generate proactive insights through entity engine
            if self.entity_engine:
                proactive_insights = self.entity_engine.generate_proactive_insights(user_id)
                insights['proactive_insights'] = [
                    {
                        'type': insight.insight_type,
                        'title': insight.title,
                        'description': insight.description,
                        'priority': insight.priority,
                        'confidence': insight.confidence
                    }
                    for insight in proactive_insights
                ]
            
            # Generate predictive analytics if available
            if self.predictive_analytics and self.predictive_analytics.is_running:
                insights['predictive_analytics'] = {
                    'communication_patterns': self.predictive_analytics.analyze_communication_patterns(user_id),
                    'upcoming_needs': self.predictive_analytics.predict_upcoming_needs(user_id),
                    'anomalies': self.predictive_analytics.detect_anomalies(user_id)
                }
            
            # Get real-time processing status
            if self.realtime_processor:
                insights['real_time_status'] = {
                    'is_running': self.realtime_processor.is_running,
                    'queue_size': getattr(self.realtime_processor, 'queue_size', 0)
                }
            
            return {'success': True, 'result': insights}
            
        except Exception as e:
            logger.error(f"Failed to generate user insights: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global instance
processor_manager = ProcessorManager() 