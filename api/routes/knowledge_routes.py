"""
Knowledge Routes Blueprint
=========================

API routes for the Knowledge-Centric Architecture that enable:
1. Hierarchical topic tree management (auto-generated + user-managed)
2. Bidirectional people-topic relationship queries
3. Source content traceability and verification
4. Knowledge building and evolution
5. Multi-source ingestion endpoints (for future Slack, Dropbox, etc.)

This is the API layer for the Knowledge Replacement System.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from ..middleware.auth_middleware import get_current_user, require_auth

logger = logging.getLogger(__name__)

# Create blueprint
knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/api/knowledge')

# =============================================================================
# TOPIC HIERARCHY ENDPOINTS
# =============================================================================

@knowledge_bp.route('/topics/hierarchy', methods=['GET'])
@require_auth
def get_topic_hierarchy():
    """Get the complete topic hierarchy for the user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.models.knowledge_models import TopicHierarchy
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get all topics organized by hierarchy
        with get_db_manager().get_session() as session:
            all_topics = session.query(TopicHierarchy).filter(
                TopicHierarchy.user_id == db_user.id
            ).order_by(TopicHierarchy.depth_level, TopicHierarchy.name).all()
            
            # Build hierarchical structure
            hierarchy = _build_topic_tree(all_topics)
            
            # Get statistics
            stats = {
                'total_topics': len(all_topics),
                'max_depth': max([t.depth_level for t in all_topics]) if all_topics else 0,
                'auto_generated': len([t for t in all_topics if t.auto_generated]),
                'user_created': len([t for t in all_topics if t.user_created]),
                'by_type': _count_by_type(all_topics),
                'recent_activity': len([t for t in all_topics if t.last_mentioned and (datetime.utcnow() - t.last_mentioned).days <= 7])
            }
            
            return jsonify({
                'success': True,
                'hierarchy': hierarchy,
                'stats': stats,
                'total_count': len(all_topics)
            })
            
    except Exception as e:
        logger.error(f"Get topic hierarchy error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/topics/build-from-emails', methods=['POST'])
@require_auth
def build_topics_from_emails():
    """Build topic hierarchy from existing emails"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.knowledge_engine import knowledge_engine
        from chief_of_staff_ai.models.knowledge_models import SourceType
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's emails to analyze
        with get_db_manager().get_session() as session:
            emails = get_db_manager().get_user_emails(db_user.id, limit=1000)
            
            # Convert to knowledge engine format
            email_content = []
            for email in emails:
                if email.ai_summary:  # Only process emails with AI analysis
                    email_content.append({
                        'id': email.gmail_id,
                        'source_type': 'email',
                        'content': email.ai_summary,
                        'body_text': email.body_text or '',
                        'subject': email.subject or '',
                        'sender': email.sender,
                        'timestamp': email.email_date.isoformat() if email.email_date else datetime.utcnow().isoformat()
                    })
            
            if not email_content:
                return jsonify({
                    'success': False,
                    'error': 'No processed emails found. Please sync emails first.'
                }), 400
            
            # Build topic hierarchy
            result = knowledge_engine.build_topic_hierarchy_from_content(db_user.id, email_content)
            
            return jsonify({
                'success': result.get('success', True),
                'message': f"Built topic hierarchy from {len(email_content)} emails",
                'result': result
            })
            
    except Exception as e:
        logger.error(f"Build topics from emails error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/foundation/build-from-bulk-emails', methods=['POST'])
@require_auth
def build_foundation_from_bulk_emails():
    """
    Build comprehensive knowledge foundation from bulk historical emails.
    This creates the business context skeleton for accurate content categorization.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.knowledge_engine import knowledge_engine
        
        data = request.get_json() or {}
        months_back = data.get('months_back', 6)  # Default to 6 months
        
        # Validate months_back parameter
        if not isinstance(months_back, int) or months_back < 1 or months_back > 24:
            return jsonify({
                'error': 'Invalid months_back parameter. Must be between 1-24.'
            }), 400
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"🏗️  Starting knowledge foundation build for {user_email} - {months_back} months back")
        
        # Build comprehensive knowledge foundation
        result = knowledge_engine.build_knowledge_foundation_from_bulk_emails(
            user_id=db_user.id,
            months_back=months_back
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f"Built knowledge foundation from {months_back} months of historical data",
                'foundation_stats': {
                    'emails_analyzed': result.get('emails_analyzed', 0),
                    'topics_created': result.get('topics_created', 0),
                    'hierarchy_depth': result.get('hierarchy_depth', 0),
                    'business_areas': result.get('business_areas_identified', 0),
                    'projects': result.get('projects_identified', 0),
                    'people_connected': result.get('people_connected', 0),
                    'foundation_quality': result.get('foundation_quality_score', 0.0)
                },
                'next_steps': [
                    'Your knowledge foundation is now ready',
                    'Future email processing will use this context',
                    'You can now create manual topics that integrate with this foundation',
                    'All new content will be categorized using this business structure'
                ]
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Foundation building failed'),
                'recommendation': result.get('recommendation', 'Try the manual interview approach instead')
            }), 400
            
    except Exception as e:
        logger.error(f"Build foundation from bulk emails error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/foundation/status', methods=['GET'])
@require_auth
def get_foundation_status():
    """Check if user has a knowledge foundation and its quality"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.models.knowledge_models import TopicHierarchy
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            # Check existing topics
            topics = session.query(TopicHierarchy).filter(
                TopicHierarchy.user_id == db_user.id
            ).all()
            
            if not topics:
                return jsonify({
                    'has_foundation': False,
                    'recommendation': 'build_foundation',
                    'message': 'No knowledge foundation found. Build one from historical emails or manual interview.',
                    'available_approaches': ['bulk_email_analysis', 'manual_interview']
                })
            
            # Analyze foundation quality
            foundation_quality = {
                'total_topics': len(topics),
                'max_depth': max([t.depth_level for t in topics]) if topics else 0,
                'topic_types': len(set([t.topic_type for t in topics])),
                'auto_generated': len([t for t in topics if t.auto_generated]),
                'user_created': len([t for t in topics if t.user_created]),
                'avg_confidence': sum([t.confidence_score for t in topics]) / len(topics) if topics else 0
            }
            
            # Determine if foundation is comprehensive enough
            is_comprehensive = (
                foundation_quality['total_topics'] >= 5 and
                foundation_quality['max_depth'] >= 2 and
                foundation_quality['topic_types'] >= 3
            )
            
            return jsonify({
                'has_foundation': True,
                'is_comprehensive': is_comprehensive,
                'foundation_quality': foundation_quality,
                'recommendation': 'foundation_ready' if is_comprehensive else 'enhance_foundation',
                'message': 'Knowledge foundation ready for content processing' if is_comprehensive 
                          else 'Foundation exists but could be enhanced with more historical data'
            })
            
    except Exception as e:
        logger.error(f"Get foundation status error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/topics', methods=['POST'])
@require_auth
def create_topic():
    """Create a new topic manually"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.models.knowledge_models import TopicHierarchy, TopicType
        
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Topic name is required'}), 400
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            # Check if topic already exists
            existing = session.query(TopicHierarchy).filter(
                TopicHierarchy.name.ilike(data['name']),
                TopicHierarchy.user_id == db_user.id
            ).first()
            
            if existing:
                return jsonify({'error': 'Topic already exists'}), 400
            
            # Find parent if specified
            parent_topic = None
            if data.get('parent_id'):
                parent_topic = session.query(TopicHierarchy).filter(
                    TopicHierarchy.id == data['parent_id'],
                    TopicHierarchy.user_id == db_user.id
                ).first()
                
                if not parent_topic:
                    return jsonify({'error': 'Parent topic not found'}), 404
            
            # Create topic
            topic = TopicHierarchy(
                name=data['name'],
                description=data.get('description', ''),
                topic_type=data.get('topic_type', TopicType.CUSTOM.value),
                parent_topic_id=parent_topic.id if parent_topic else None,
                depth_level=(parent_topic.depth_level + 1) if parent_topic else 0,
                hierarchy_path=f"{parent_topic.hierarchy_path}/{data['name']}" if parent_topic else data['name'],
                user_created=True,
                auto_generated=False,
                confidence_score=1.0,
                priority=data.get('priority', 'medium'),
                keywords=data.get('keywords', [])
            )
            
            session.add(topic)
            session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Topic created successfully',
                'topic': {
                    'id': topic.id,
                    'name': topic.name,
                    'description': topic.description,
                    'topic_type': topic.topic_type,
                    'hierarchy_path': topic.hierarchy_path,
                    'depth_level': topic.depth_level
                }
            })
            
    except Exception as e:
        logger.error(f"Create topic error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/topics/<int:topic_id>', methods=['PUT'])
@require_auth
def update_topic(topic_id):
    """Update an existing topic"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.models.knowledge_models import TopicHierarchy
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            topic = session.query(TopicHierarchy).filter(
                TopicHierarchy.id == topic_id,
                TopicHierarchy.user_id == db_user.id
            ).first()
            
            if not topic:
                return jsonify({'error': 'Topic not found'}), 404
            
            # Update fields
            if 'name' in data:
                topic.name = data['name']
            if 'description' in data:
                topic.description = data['description']
            if 'topic_type' in data:
                topic.topic_type = data['topic_type']
            if 'priority' in data:
                topic.priority = data['priority']
            if 'status' in data:
                topic.status = data['status']
            if 'keywords' in data:
                topic.keywords = data['keywords']
            
            topic.updated_at = datetime.utcnow()
            session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Topic updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Update topic error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# PEOPLE-TOPIC RELATIONSHIP ENDPOINTS
# =============================================================================

@knowledge_bp.route('/topics/<int:topic_id>/people', methods=['GET'])
@require_auth
def get_topic_people(topic_id):
    """Get all people related to a specific topic"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.models.knowledge_models import TopicHierarchy, PersonTopicRelationship
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            # Verify topic exists and belongs to user
            topic = session.query(TopicHierarchy).filter(
                TopicHierarchy.id == topic_id,
                TopicHierarchy.user_id == db_user.id
            ).first()
            
            if not topic:
                return jsonify({'error': 'Topic not found'}), 404
            
            # Get all people related to this topic
            relationships = session.query(PersonTopicRelationship).filter(
                PersonTopicRelationship.topic_id == topic_id
            ).all()
            
            people_data = []
            for rel in relationships:
                person = rel.person  # Assuming relationship is set up
                people_data.append({
                    'person_id': rel.person_id,
                    'name': person.name if person else 'Unknown',
                    'email': person.email_address if person else 'Unknown',
                    'company': person.company if person else None,
                    'relationship_type': rel.relationship_type,
                    'involvement_level': rel.involvement_level,
                    'confidence': rel.confidence,
                    'last_activity': rel.last_activity.isoformat() if rel.last_activity else None,
                    'evidence_count': rel.evidence_count,
                    'expertise_areas': rel.expertise_areas or [],
                    'key_contributions': rel.key_contributions or [],
                    'context_summary': rel.context_summary
                })
            
            return jsonify({
                'success': True,
                'topic': {
                    'id': topic.id,
                    'name': topic.name,
                    'hierarchy_path': topic.hierarchy_path
                },
                'people': people_data,
                'total_count': len(people_data)
            })
            
    except Exception as e:
        logger.error(f"Get topic people error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/people/<int:person_id>/topics', methods=['GET'])
@require_auth
def get_person_topics(person_id):
    """Get all topics related to a specific person"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.models.knowledge_models import PersonTopicRelationship, TopicHierarchy
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            # Get person
            person = get_db_manager().get_person_by_id(person_id)
            if not person or person.user_id != db_user.id:
                return jsonify({'error': 'Person not found'}), 404
            
            # Get all topics this person is related to
            relationships = session.query(PersonTopicRelationship).filter(
                PersonTopicRelationship.person_id == person_id
            ).all()
            
            topics_data = []
            for rel in relationships:
                topic = session.query(TopicHierarchy).filter(
                    TopicHierarchy.id == rel.topic_id
                ).first()
                
                if topic:
                    topics_data.append({
                        'topic_id': rel.topic_id,
                        'topic_name': topic.name,
                        'topic_type': topic.topic_type,
                        'hierarchy_path': topic.hierarchy_path,
                        'depth_level': topic.depth_level,
                        'relationship_type': rel.relationship_type,
                        'involvement_level': rel.involvement_level,
                        'confidence': rel.confidence,
                        'last_activity': rel.last_activity.isoformat() if rel.last_activity else None,
                        'evidence_count': rel.evidence_count,
                        'expertise_areas': rel.expertise_areas or [],
                        'key_contributions': rel.key_contributions or [],
                        'context_summary': rel.context_summary
                    })
            
            return jsonify({
                'success': True,
                'person': {
                    'id': person.id,
                    'name': person.name,
                    'email': person.email_address,
                    'company': person.company
                },
                'topics': topics_data,
                'total_count': len(topics_data)
            })
            
    except Exception as e:
        logger.error(f"Get person topics error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SOURCE TRACEABILITY ENDPOINTS
# =============================================================================

@knowledge_bp.route('/sources/<source_type>/<source_id>', methods=['GET'])
@require_auth
def get_source_content(source_type, source_id):
    """Get full source content for traceability"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.knowledge_engine import knowledge_engine
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get source content
        content = knowledge_engine.get_source_content(source_type, source_id, db_user.id)
        
        if not content:
            return jsonify({'error': 'Source content not found'}), 404
        
        return jsonify({
            'success': True,
            'source': content
        })
        
    except Exception as e:
        logger.error(f"Get source content error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/traceability/<entity_type>/<int:entity_id>', methods=['GET'])
@require_auth
def get_knowledge_traceability(entity_type, entity_id):
    """Get traceability for any knowledge entity"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.knowledge_engine import knowledge_engine
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get traceability
        traceability = knowledge_engine.get_knowledge_traceability(entity_type, entity_id, db_user.id)
        
        return jsonify({
            'success': True,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'sources': [
                {
                    'source_type': t.source_type,
                    'source_id': t.source_id,
                    'snippet': t.source_content_snippet,
                    'confidence': t.confidence,
                    'timestamp': t.timestamp.isoformat() if t.timestamp else None,
                    'can_access_full': t.can_access_full_content
                }
                for t in traceability
            ],
            'total_sources': len(traceability)
        })
        
    except Exception as e:
        logger.error(f"Get knowledge traceability error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# KNOWLEDGE MANAGEMENT ENDPOINTS
# =============================================================================

@knowledge_bp.route('/ingest', methods=['POST'])
@require_auth
def ingest_knowledge():
    """Ingest knowledge from various sources (future: Slack, Dropbox, etc.)"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.knowledge_engine import knowledge_engine
        from chief_of_staff_ai.models.knowledge_models import SourceType
        
        data = request.get_json()
        if not data or not data.get('source_type') or not data.get('content'):
            return jsonify({'error': 'Source type and content are required'}), 400
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Parse source type
        try:
            source_type = SourceType(data['source_type'])
        except ValueError:
            return jsonify({'error': f"Unsupported source type: {data['source_type']}"}), 400
        
        # Ingest knowledge
        result = knowledge_engine.ingest_knowledge_from_source(
            source_type=source_type,
            content=data['content'],
            user_id=db_user.id
        )
        
        return jsonify({
            'success': True,
            'message': f"Knowledge ingested from {source_type.value}",
            'extraction_results': {
                'topics_found': len(result.topics),
                'people_found': len(result.people),
                'relationships_found': len(result.relationships),
                'tasks_found': len(result.tasks),
                'insights_generated': len(result.insights),
                'confidence': result.confidence
            }
        })
        
    except Exception as e:
        logger.error(f"Ingest knowledge error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/stats', methods=['GET'])
@require_auth
def get_knowledge_stats():
    """Get comprehensive knowledge base statistics"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.models.knowledge_models import TopicHierarchy, PersonTopicRelationship, KnowledgeSource
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            # Get comprehensive stats
            topics = session.query(TopicHierarchy).filter(
                TopicHierarchy.user_id == db_user.id
            ).all()
            
            relationships = session.query(PersonTopicRelationship).join(
                TopicHierarchy
            ).filter(
                TopicHierarchy.user_id == db_user.id
            ).all()
            
            sources = session.query(KnowledgeSource).filter(
                KnowledgeSource.user_id == db_user.id
            ).all()
            
            stats = {
                'knowledge_base': {
                    'total_topics': len(topics),
                    'topic_hierarchy_depth': max([t.depth_level for t in topics]) if topics else 0,
                    'auto_generated_topics': len([t for t in topics if t.auto_generated]),
                    'user_created_topics': len([t for t in topics if t.user_created]),
                    'active_topics': len([t for t in topics if t.status == 'active'])
                },
                'relationships': {
                    'total_people_topic_relationships': len(relationships),
                    'high_confidence_relationships': len([r for r in relationships if r.confidence == 'high']),
                    'relationship_types': _count_relationship_types(relationships)
                },
                'sources': {
                    'total_sources': len(sources),
                    'by_type': _count_sources_by_type(sources),
                    'processed_sources': len([s for s in sources if s.processing_status == 'processed']),
                    'recent_sources': len([s for s in sources if s.created_at and (datetime.utcnow() - s.created_at).days <= 7])
                },
                'knowledge_quality': {
                    'avg_topic_confidence': sum([t.confidence_score for t in topics]) / len(topics) if topics else 0,
                    'topics_with_people': len(set([r.topic_id for r in relationships])),
                    'coverage_percentage': (len(set([r.topic_id for r in relationships])) / len(topics) * 100) if topics else 0
                }
            }
            
            return jsonify({
                'success': True,
                'stats': stats,
                'last_updated': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Get knowledge stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_topic_tree(topics):
    """Build hierarchical topic tree structure"""
    topic_map = {t.id: {
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'topic_type': t.topic_type,
        'depth_level': t.depth_level,
        'hierarchy_path': t.hierarchy_path,
        'confidence_score': t.confidence_score,
        'mention_count': t.mention_count,
        'auto_generated': t.auto_generated,
        'user_created': t.user_created,
        'status': t.status,
        'priority': t.priority,
        'last_mentioned': t.last_mentioned.isoformat() if t.last_mentioned else None,
        'children': []
    } for t in topics}
    
    root_topics = []
    
    for topic in topics:
        topic_data = topic_map[topic.id]
        
        if topic.parent_topic_id and topic.parent_topic_id in topic_map:
            topic_map[topic.parent_topic_id]['children'].append(topic_data)
        else:
            root_topics.append(topic_data)
    
    return root_topics

def _count_by_type(topics):
    """Count topics by type"""
    counts = {}
    for topic in topics:
        topic_type = topic.topic_type
        counts[topic_type] = counts.get(topic_type, 0) + 1
    return counts

def _count_relationship_types(relationships):
    """Count relationships by type"""
    counts = {}
    for rel in relationships:
        rel_type = rel.relationship_type
        counts[rel_type] = counts.get(rel_type, 0) + 1
    return counts

def _count_sources_by_type(sources):
    """Count sources by type"""
    counts = {}
    for source in sources:
        source_type = source.source_type
        counts[source_type] = counts.get(source_type, 0) + 1
    return counts 