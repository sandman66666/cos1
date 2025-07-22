"""
Enhanced API endpoints for entity-centric intelligence
Provides advanced endpoints for unified entities, relationships, and insights
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from typing import Dict, List, Optional

from chief_of_staff_ai.models.database import get_db_manager
from models.enhanced_models import Topic, Person, Task, EntityRelationship, IntelligenceInsight
from processors.realtime_processing import realtime_processor, EventType
from processors.enhanced_ai_pipeline import enhanced_ai_processor
from processors.unified_entity_engine import entity_engine, EntityContext

logger = logging.getLogger(__name__)

# Create blueprint for enhanced endpoints
enhanced_api_bp = Blueprint('enhanced_api', __name__, url_prefix='/api/enhanced')

def require_auth_session():
    """Simple session-based auth check"""
    user_email = session.get('user_email')
    if not user_email:
        return None
    
    user = get_db_manager().get_user_by_email(user_email)
    return user

@enhanced_api_bp.route('/unified-sync', methods=['POST'])
def enhanced_unified_sync():
    """
    Enhanced unified sync with entity-centric processing
    Triggers comprehensive data sync with real-time processing
    """
    try:
        user = require_auth_session()
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = user.id
        
        # Check if real-time processor is running
        if not realtime_processor.is_running:
            logger.info("Starting real-time processor for enhanced sync")
            realtime_processor.start()
        
        # Trigger comprehensive sync event
        realtime_processor.trigger_comprehensive_sync(user_id, priority=1)
        
        # Get current processing status
        status = realtime_processor.get_processing_status()
        
        return jsonify({
            'success': True,
            'message': 'Enhanced unified sync initiated',
            'real_time_processing': True,
            'processing_status': status,
            'enhanced_features_active': True,
            'sync_time': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Enhanced unified sync failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'enhanced_features_active': False
        }), 500

@enhanced_api_bp.route('/entities/topics', methods=['GET'])
def get_enhanced_topics():
    """Get topics with enhanced intelligence accumulation"""
    try:
        user = require_auth_session()
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = user.id
        limit = request.args.get('limit', 50, type=int)
        include_relationships = request.args.get('relationships', False, type=bool)
        
        db_manager = get_db_manager()
        
        with db_manager.get_session() as db_session:
            # Get topics with enhanced metrics
            topics_query = db_session.query(Topic).filter(Topic.user_id == user_id)
            
            # Order by strategic importance and mentions
            topics_query = topics_query.order_by(
                Topic.strategic_importance.desc(),
                Topic.total_mentions.desc()
            ).limit(limit)
            
            topics = topics_query.all()
            
            topics_data = []
            for topic in topics:
                topic_dict = {
                    'id': topic.id,
                    'name': topic.name,
                    'description': topic.description,
                    'keywords': topic.keywords.split(',') if topic.keywords else [],
                    'strategic_importance': topic.strategic_importance,
                    'total_mentions': topic.total_mentions,
                    'last_mentioned': topic.last_mentioned.isoformat() if topic.last_mentioned else None,
                    'intelligence_summary': topic.intelligence_summary,
                    'version': topic.version,
                    'created_at': topic.created_at.isoformat() if topic.created_at else None
                }
                
                # Include relationships if requested
                if include_relationships:
                    relationships = db_session.query(EntityRelationship).filter(
                        ((EntityRelationship.entity_type_a == 'topic') & (EntityRelationship.entity_id_a == topic.id)) |
                        ((EntityRelationship.entity_type_b == 'topic') & (EntityRelationship.entity_id_b == topic.id))
                    ).all()
                    
                    topic_dict['relationships'] = [
                        {
                            'type': rel.relationship_type,
                            'strength': rel.strength,
                            'context': rel.context_summary,
                            'related_entity': {
                                'type': rel.entity_type_b if rel.entity_type_a == 'topic' else rel.entity_type_a,
                                'id': rel.entity_id_b if rel.entity_type_a == 'topic' else rel.entity_id_a
                            }
                        }
                        for rel in relationships
                    ]
                
                topics_data.append(topic_dict)
        
        return jsonify({
            'success': True,
            'topics': topics_data,
            'count': len(topics_data),
            'enhanced_features': True,
            'fetched_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get enhanced topics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/entities/people', methods=['GET'])
def get_enhanced_people():
    """Get people with comprehensive relationship intelligence"""
    try:
        user = require_auth_session()
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = user.id
        limit = request.args.get('limit', 50, type=int)
        include_relationships = request.args.get('relationships', False, type=bool)
        
        db_manager = get_db_manager()
        
        with db_manager.get_session() as db_session:
            # Get people with enhanced metrics
            people_query = db_session.query(Person).filter(Person.user_id == user_id)
            
            # Order by importance and interactions
            people_query = people_query.order_by(
                Person.importance_level.desc(),
                Person.total_interactions.desc()
            ).limit(limit)
            
            people = people_query.all()
            
            people_data = []
            for person in people:
                person_dict = {
                    'id': person.id,
                    'name': person.name,
                    'email_address': person.email_address,
                    'company': person.company,
                    'title': person.title,
                    'relationship_type': person.relationship_type,
                    'importance_level': person.importance_level,
                    'total_interactions': person.total_interactions,
                    'last_contact': person.last_contact.isoformat() if person.last_contact else None,
                    'professional_story': person.professional_story,
                    'key_topics': person.key_topics.split(',') if person.key_topics else [],
                    'created_at': person.created_at.isoformat() if person.created_at else None
                }
                
                # Include relationships if requested
                if include_relationships:
                    relationships = db_session.query(EntityRelationship).filter(
                        ((EntityRelationship.entity_type_a == 'person') & (EntityRelationship.entity_id_a == person.id)) |
                        ((EntityRelationship.entity_type_b == 'person') & (EntityRelationship.entity_id_b == person.id))
                    ).all()
                    
                    person_dict['relationships'] = [
                        {
                            'type': rel.relationship_type,
                            'strength': rel.strength,
                            'context': rel.context_summary,
                            'total_interactions': rel.total_interactions,
                            'last_interaction': rel.last_interaction.isoformat() if rel.last_interaction else None,
                            'related_entity': {
                                'type': rel.entity_type_b if rel.entity_type_a == 'person' else rel.entity_type_a,
                                'id': rel.entity_id_b if rel.entity_type_a == 'person' else rel.entity_id_a
                            }
                        }
                        for rel in relationships
                    ]
                
                people_data.append(person_dict)
        
        return jsonify({
            'success': True,
            'people': people_data,
            'count': len(people_data),
            'enhanced_features': True,
            'fetched_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get enhanced people: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/intelligence/insights', methods=['GET'])
def get_intelligence_insights():
    """Get proactive intelligence insights"""
    try:
        user = require_auth_session()
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = user.id
        status = request.args.get('status', 'new')
        insight_type = request.args.get('type')
        limit = request.args.get('limit', 20, type=int)
        
        db_manager = get_db_manager()
        
        with db_manager.get_session() as db_session:
            insights_query = db_session.query(IntelligenceInsight).filter(
                IntelligenceInsight.user_id == user_id
            )
            
            if status:
                insights_query = insights_query.filter(IntelligenceInsight.status == status)
            
            if insight_type:
                insights_query = insights_query.filter(IntelligenceInsight.insight_type == insight_type)
            
            # Order by priority and creation date
            insights_query = insights_query.order_by(
                IntelligenceInsight.priority.desc(),
                IntelligenceInsight.created_at.desc()
            ).limit(limit)
            
            insights = insights_query.all()
            
            insights_data = [
                {
                    'id': insight.id,
                    'type': insight.insight_type,
                    'title': insight.title,
                    'description': insight.description,
                    'priority': insight.priority,
                    'confidence': insight.confidence,
                    'status': insight.status,
                    'related_entity': {
                        'type': insight.related_entity_type,
                        'id': insight.related_entity_id
                    } if insight.related_entity_type else None,
                    'action_taken': insight.action_taken,
                    'created_at': insight.created_at.isoformat() if insight.created_at else None,
                    'expires_at': insight.expires_at.isoformat() if insight.expires_at else None
                }
                for insight in insights
            ]
        
        return jsonify({
            'success': True,
            'insights': insights_data,
            'count': len(insights_data),
            'enhanced_intelligence': True,
            'fetched_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get intelligence insights: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/intelligence/trigger-insights', methods=['POST'])
def trigger_proactive_insights():
    """Manually trigger proactive insights generation"""
    try:
        user = require_auth_session()
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = user.id
        
        # Trigger insights through real-time processor if running
        if realtime_processor.is_running:
            realtime_processor.trigger_proactive_insights(user_id, priority=2)
            return jsonify({
                'success': True,
                'message': 'Proactive insights generation triggered via real-time processor',
                'real_time_processing': True
            })
        else:
            # Generate insights directly through entity engine
            insights = entity_engine.generate_proactive_insights(user_id)
            
            return jsonify({
                'success': True,
                'message': 'Proactive insights generated directly',
                'insights_generated': len(insights),
                'real_time_processing': False,
                'insights': [
                    {
                        'type': insight.insight_type,
                        'title': insight.title,
                        'description': insight.description,
                        'priority': insight.priority,
                        'confidence': insight.confidence
                    }
                    for insight in insights
                ]
            })
        
    except Exception as e:
        logger.error(f"Failed to trigger proactive insights: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/real-time/status', methods=['GET'])
def get_realtime_status():
    """Get real-time processing status and performance metrics"""
    try:
        user = require_auth_session()
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        status = {
            'is_running': realtime_processor.is_running,
            'enhanced_features_active': True,
            'processors_available': {
                'real_time_processor': realtime_processor is not None,
                'enhanced_ai_pipeline': enhanced_ai_processor is not None,
                'unified_entity_engine': entity_engine is not None
            }
        }
        
        if realtime_processor.is_running:
            processing_status = realtime_processor.get_processing_status()
            status.update(processing_status)
        else:
            status.update({
                'queue_size': 0,
                'workers_active': 0,
                'processing_rate': 0,
                'total_processed': 0
            })
        
        return jsonify({
            'success': True,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get real-time status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/real-time/start', methods=['POST'])
def start_realtime_processing():
    """Start the real-time processing system"""
    try:
        if not realtime_processor.is_running:
            realtime_processor.start()
            
            return jsonify({
                'success': True,
                'message': 'Real-time processor started successfully',
                'is_running': realtime_processor.is_running
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Real-time processor already running',
                'is_running': True
            })
        
    except Exception as e:
        logger.error(f"Failed to start real-time processor: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/real-time/stop', methods=['POST'])
def stop_realtime_processing():
    """Stop the real-time processing system"""
    try:
        if realtime_processor.is_running:
            realtime_processor.stop()
            
            return jsonify({
                'success': True,
                'message': 'Real-time processor stopped successfully',
                'is_running': realtime_processor.is_running
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Real-time processor already stopped',
                'is_running': False
            })
        
    except Exception as e:
        logger.error(f"Failed to stop real-time processor: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Helper functions for enhanced endpoints

def get_entity_intelligence_summary(user_id: int, entity_type: str, entity_id: int) -> Dict:
    """Get comprehensive intelligence summary for an entity"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            # Get entity relationships
            relationships = session.query(EntityRelationship).filter(
                EntityRelationship.user_id == user_id,
                ((EntityRelationship.entity_type_a == entity_type) & (EntityRelationship.entity_id_a == entity_id)) |
                ((EntityRelationship.entity_type_b == entity_type) & (EntityRelationship.entity_id_b == entity_id))
            ).all()
            
            # Get related insights
            insights = session.query(IntelligenceInsight).filter(
                IntelligenceInsight.user_id == user_id,
                IntelligenceInsight.related_entity_type == entity_type,
                IntelligenceInsight.related_entity_id == entity_id
            ).all()
            
            return {
                'entity_type': entity_type,
                'entity_id': entity_id,
                'total_relationships': len(relationships),
                'relationship_strength_avg': sum(r.strength for r in relationships) / len(relationships) if relationships else 0,
                'related_insights': len(insights),
                'last_activity': max(r.last_interaction for r in relationships) if relationships else None
            }
            
    except Exception as e:
        logger.error(f"Failed to get entity intelligence summary: {str(e)}")
        return {'error': str(e)}

def calculate_relationship_analysis(user_id: int) -> Dict:
    """Calculate comprehensive relationship analysis for user"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            # Get all relationships
            relationships = session.query(EntityRelationship).filter(
                EntityRelationship.user_id == user_id
            ).all()
            
            # Analyze relationship patterns
            analysis = {
                'total_relationships': len(relationships),
                'strong_relationships': len([r for r in relationships if r.strength > 0.7]),
                'relationship_types': {},
                'entity_connectivity': {},
                'average_strength': sum(r.strength for r in relationships) / len(relationships) if relationships else 0
            }
            
            # Count by type
            for rel in relationships:
                rel_type = rel.relationship_type
                analysis['relationship_types'][rel_type] = analysis['relationship_types'].get(rel_type, 0) + 1
                
                # Track entity connectivity
                entity_a = f"{rel.entity_type_a}:{rel.entity_id_a}"
                entity_b = f"{rel.entity_type_b}:{rel.entity_id_b}"
                
                analysis['entity_connectivity'][entity_a] = analysis['entity_connectivity'].get(entity_a, 0) + 1
                analysis['entity_connectivity'][entity_b] = analysis['entity_connectivity'].get(entity_b, 0) + 1
            
            return analysis
            
    except Exception as e:
        logger.error(f"Failed to calculate relationship analysis: {str(e)}")
        return {'error': str(e)}

def get_intelligence_quality_metrics(user_id: int) -> Dict:
    """Get quality metrics for user's intelligence data"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            # Get counts for different entity types
            topics_count = session.query(Topic).filter(Topic.user_id == user_id).count()
            people_count = session.query(Person).filter(Person.user_id == user_id).count()
            insights_count = session.query(IntelligenceInsight).filter(IntelligenceInsight.user_id == user_id).count()
            relationships_count = session.query(EntityRelationship).filter(EntityRelationship.user_id == user_id).count()
            
            # Calculate confidence scores
            topics = session.query(Topic).filter(Topic.user_id == user_id).all()
            avg_topic_importance = sum(t.strategic_importance for t in topics) / len(topics) if topics else 0
            
            people = session.query(Person).filter(Person.user_id == user_id).all()
            avg_person_importance = sum(p.importance_level for p in people) / len(people) if people else 0
            
            insights = session.query(IntelligenceInsight).filter(IntelligenceInsight.user_id == user_id).all()
            avg_insight_confidence = sum(i.confidence for i in insights) / len(insights) if insights else 0
            
            return {
                'entity_counts': {
                    'topics': topics_count,
                    'people': people_count,
                    'insights': insights_count,
                    'relationships': relationships_count
                },
                'quality_metrics': {
                    'avg_topic_importance': avg_topic_importance,
                    'avg_person_importance': avg_person_importance,
                    'avg_insight_confidence': avg_insight_confidence,
                    'relationship_density': relationships_count / (topics_count + people_count) if (topics_count + people_count) > 0 else 0
                },
                'intelligence_score': (avg_topic_importance + avg_person_importance + avg_insight_confidence) / 3
            }
            
    except Exception as e:
        logger.error(f"Failed to get intelligence quality metrics: {str(e)}")
        return {'error': str(e)} 