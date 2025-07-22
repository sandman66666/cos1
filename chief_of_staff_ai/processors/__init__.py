"""
Enhanced Processor Integration Manager
Coordinates all processing components as specified in the refactor
"""
from .unified_entity_engine import entity_engine
from .enhanced_ai_pipeline import enhanced_ai_processor  
from .realtime_processing import realtime_processor
from .analytics.predictive_analytics import predictive_analytics

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ProcessorManager:
    """Coordinates all processing components"""
    
    def __init__(self):
        self.entity_engine = entity_engine
        self.ai_processor = enhanced_ai_processor
        self.realtime_processor = realtime_processor
        self.predictive_analytics = predictive_analytics
        
    def start_all_processors(self):
        """Start all processing components"""
        try:
            # Start real-time processor
            if not self.realtime_processor.is_running:
                self.realtime_processor.start()
                logger.info("Started real-time processor")
            
            # Start predictive analytics
            if not self.predictive_analytics.running:
                self.predictive_analytics.start()
                logger.info("Started predictive analytics engine")
            
            logger.info("All enhanced processors started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start processors: {str(e)}")
    
    def stop_all_processors(self):
        """Stop all processing components"""
        try:
            self.realtime_processor.stop()
            self.predictive_analytics.stop()
            logger.info("All processors stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop processors: {str(e)}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        try:
            stats = {
                'success': True,
                'result': {
                    'real_time_processor': self.realtime_processor.get_stats(),
                    'predictive_analytics': {
                        'running': self.predictive_analytics.running,
                        'pattern_cache_size': len(self.predictive_analytics.pattern_cache),
                        'prediction_cache_size': len(self.predictive_analytics.prediction_cache)
                    },
                    'entity_engine': {
                        'available': True,
                        'methods': ['create_or_update_person', 'create_or_update_topic', 'create_task_with_full_context']
                    },
                    'ai_processor': {
                        'available': True,
                        'model': self.ai_processor.model
                    }
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get processing statistics: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'result': {}
            }
    
    def generate_user_insights(self, user_id: int, insight_type: str = 'comprehensive') -> Dict[str, Any]:
        """Generate comprehensive user insights using all processors"""
        try:
            insights_result = {
                'success': True,
                'result': {
                    'proactive_insights': [],
                    'predictive_analytics': {},
                    'entity_intelligence': {},
                    'processing_timestamp': datetime.utcnow().isoformat()
                }
            }
            
            # Get proactive insights from entity engine
            proactive_insights = self.entity_engine.generate_proactive_insights(user_id)
            insights_result['result']['proactive_insights'] = [
                {
                    'id': insight.id if hasattr(insight, 'id') else None,
                    'type': insight.insight_type if hasattr(insight, 'insight_type') else 'general',
                    'title': insight.title if hasattr(insight, 'title') else 'Insight',
                    'description': insight.description if hasattr(insight, 'description') else 'No description',
                    'priority': insight.priority if hasattr(insight, 'priority') else 'medium',
                    'confidence': insight.confidence if hasattr(insight, 'confidence') else 0.5
                }
                for insight in proactive_insights
            ]
            
            # Get predictive analytics if insight_type includes predictions
            if insight_type in ['comprehensive', 'predictive']:
                predictions = {
                    'relationship_opportunities': self.predictive_analytics.predict_relationship_opportunities(user_id),
                    'topic_trends': self.predictive_analytics.predict_topic_trends(user_id),
                    'business_opportunities': self.predictive_analytics.predict_business_opportunities(user_id)
                }
                
                # Convert predictions to serializable format
                serialized_predictions = {}
                for category, pred_list in predictions.items():
                    serialized_predictions[category] = [
                        {
                            'type': pred.prediction_type,
                            'confidence': pred.confidence,
                            'value': str(pred.predicted_value),
                            'reasoning': pred.reasoning,
                            'time_horizon': pred.time_horizon,
                            'data_points': pred.data_points_used,
                            'created_at': pred.created_at.isoformat()
                        }
                        for pred in pred_list
                    ]
                
                insights_result['result']['predictive_analytics'] = serialized_predictions
                
                # Add upcoming needs summary
                all_predictions = []
                for pred_list in predictions.values():
                    all_predictions.extend(pred_list)
                
                high_confidence_predictions = [p for p in all_predictions if p.confidence > 0.7]
                insights_result['result']['predictive_analytics']['upcoming_needs'] = [
                    {
                        'title': pred.predicted_value,
                        'confidence': pred.confidence,
                        'reasoning': pred.reasoning
                    }
                    for pred in high_confidence_predictions[:3]  # Top 3
                ]
            
            # Add entity intelligence if comprehensive
            if insight_type == 'comprehensive':
                insights_result['result']['entity_intelligence'] = self._generate_entity_intelligence_summary(user_id)
            
            return insights_result
            
        except Exception as e:
            logger.error(f"Failed to generate user insights: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'result': {}
            }
    
    def _generate_entity_intelligence_summary(self, user_id: int) -> Dict:
        """Generate entity intelligence summary"""
        try:
            from chief_of_staff_ai.models.database import get_db_manager
            from models.enhanced_models import Topic, Person, Task
            
            with get_db_manager().get_session() as session:
                # Entity counts
                topics_count = session.query(Topic).filter(Topic.user_id == user_id).count()
                people_count = session.query(Person).filter(Person.user_id == user_id).count()
                tasks_count = session.query(Task).filter(Task.user_id == user_id).count()
                
                return {
                    'entity_summary': {
                        'topics': topics_count,
                        'people': people_count,
                        'tasks': tasks_count,
                        'total_entities': topics_count + people_count + tasks_count
                    },
                    'intelligence_quality': {
                        'entity_density': (topics_count + people_count) / max(1, tasks_count),
                        'data_richness': 0.8  # Placeholder metric
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to generate entity intelligence summary: {str(e)}")
            return {}
    
    def process_unified_sync(self, user_id: int, sync_params: Dict) -> Dict[str, Any]:
        """Process unified intelligence sync"""
        try:
            result = {
                'success': True,
                'processing_stages': {},
                'entities_created': {'people': 0, 'topics': 0, 'tasks': 0},
                'entities_updated': {'people': 0, 'topics': 0, 'tasks': 0},
                'insights_generated': []
            }
            
            # Generate insights for this sync
            insights_result = self.generate_user_insights(user_id, 'comprehensive')
            
            if insights_result['success']:
                result['insights_generated'] = insights_result['result']['proactive_insights']
                result['predictive_analytics'] = insights_result['result'].get('predictive_analytics', {})
            
            # Trigger real-time analysis
            self.realtime_processor.trigger_proactive_insights(user_id, priority=3)
            
            result['processing_stages']['unified_sync'] = 'completed'
            result['processing_timestamp'] = datetime.utcnow().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process unified sync: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processing_stages': {},
                'entities_created': {},
                'entities_updated': {},
                'insights_generated': []
            }

# Global instance
processor_manager = ProcessorManager() 