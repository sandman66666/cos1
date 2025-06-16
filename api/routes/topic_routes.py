"""
Topic Routes Blueprint
=====================

Topic management and knowledge base routes.
Extracted from main.py for better organization.
"""

import logging
from flask import Blueprint, request, jsonify
from ..middleware.auth_middleware import get_current_user, require_auth

logger = logging.getLogger(__name__)

topic_bp = Blueprint('topic', __name__, url_prefix='/api')


@topic_bp.route('/topics', methods=['GET'])
@require_auth
def api_get_topics():
    """Get all topics for a user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        topics = get_db_manager().get_user_topics(db_user.id)
        
        return jsonify({
            'success': True,
            'topics': [topic.to_dict() for topic in topics],
            'count': len(topics)
        })
        
    except Exception as e:
        logger.error(f"Get topics API error for user {user['email']}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@topic_bp.route('/topics', methods=['POST'])
@require_auth
def api_create_topic():
    """Create a new topic manually"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Topic name is required'}), 400
        
        topic_data = {
            'name': data['name'],
            'slug': data['name'].lower().replace(' ', '-'),
            'description': data.get('description', ''),
            'is_official': data.get('is_official', True),
            'keywords': data.get('keywords', [])
        }
        
        topic = get_db_manager().create_or_update_topic(db_user.id, topic_data)
        
        return jsonify({
            'success': True,
            'topic': topic.to_dict(),
            'message': f'Topic "{topic.name}" created successfully'
        })
        
    except Exception as e:
        logger.error(f"Create topic API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@topic_bp.route('/topics/<int:topic_id>/official', methods=['POST'])
@require_auth
def api_mark_topic_official(topic_id):
    """Mark a topic as official"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        success = get_db_manager().mark_topic_official(db_user.id, topic_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Topic marked as official'
            })
        else:
            return jsonify({'error': 'Topic not found or not authorized'}), 404
        
    except Exception as e:
        logger.error(f"Mark topic official API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@topic_bp.route('/topics/<int:topic_id>/merge', methods=['POST'])
@require_auth
def api_merge_topic(topic_id):
    """Merge one topic into another"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        target_topic_id = data.get('target_topic_id')
        
        if not target_topic_id:
            return jsonify({'error': 'Target topic ID is required'}), 400
        
        success = get_db_manager().merge_topics(db_user.id, topic_id, target_topic_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Topics merged successfully'
            })
        else:
            return jsonify({'error': 'Topics not found or merge failed'}), 404
        
    except Exception as e:
        logger.error(f"Merge topic API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@topic_bp.route('/topics/<int:topic_id>', methods=['PUT'])
@require_auth
def api_update_topic(topic_id):
    """Update a topic"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update topic data
        topic_data = {}
        if 'description' in data:
            topic_data['description'] = data['description']
        if 'keywords' in data:
            topic_data['keywords'] = data['keywords']
        if 'name' in data:
            topic_data['name'] = data['name']
        
        success = get_db_manager().update_topic(db_user.id, topic_id, topic_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Topic updated successfully'
            })
        else:
            return jsonify({'error': 'Topic not found or not authorized'}), 404
        
    except Exception as e:
        logger.error(f"Update topic API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@topic_bp.route('/topics/resync', methods=['POST'])
@require_auth
def api_resync_topics():
    """Resync all content with updated topics"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # This would trigger a resync of all emails with the updated topic definitions
        return jsonify({
            'success': True,
            'message': 'Topic resync initiated - this will re-categorize all content with updated topic definitions'
        })
        
    except Exception as e:
        logger.error(f"Resync topics API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@topic_bp.route('/sync-topics', methods=['POST'])
@require_auth
def api_sync_topics():
    """Sync topics from email content"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Placeholder for topic sync functionality
        return jsonify({
            'success': True,
            'message': 'Topic sync completed',
            'topics_processed': 0
        })
        
    except Exception as e:
        logger.error(f"Sync topics API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@topic_bp.route('/topics/ensure-default', methods=['POST'])
@require_auth
def api_ensure_default_topic():
    """Ensure default topics exist"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create default "General" topic if it doesn't exist
        default_topic_data = {
            'name': 'General',
            'slug': 'general',
            'description': 'General business communications and tasks',
            'is_official': True,
            'keywords': ['general', 'business', 'misc']
        }
        
        topic = get_db_manager().create_or_update_topic(db_user.id, default_topic_data)
        
        return jsonify({
            'success': True,
            'message': 'Default topic ensured',
            'topic': topic.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Ensure default topic API error: {str(e)}")
        return jsonify({'error': str(e)}), 500 