# Entity Management API Endpoints - CRUD and Relationship Management
# These endpoints provide comprehensive entity management for the entity-centric system

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
import json

# Import the integration manager and models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'chief_of_staff_ai'))

from processors.integration_manager import integration_manager
from processors.unified_entity_engine import entity_engine, EntityContext
from chief_of_staff_ai.models.database import get_db_manager
from models.enhanced_models import (
    Person, Topic, Task, CalendarEvent, Email, Project,
    EntityRelationship, IntelligenceInsight
)

logger = logging.getLogger(__name__)

# Create Blueprint
entity_api_bp = Blueprint('entity_api', __name__, url_prefix='/api/entities')

# =====================================================================
# AUTHENTICATION AND UTILITIES
# =====================================================================

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session or 'db_user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        g.user_id = session['db_user_id']
        g.user_email = session['user_email']
        
        return f(*args, **kwargs)
    return decorated_function

def success_response(data: Any, message: str = None) -> tuple:
    """Create standardized success response"""
    response = {
        'success': True,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    }
    if message:
        response['message'] = message
    return jsonify(response), 200

def error_response(error: str, code: str = None, status_code: int = 400) -> tuple:
    """Create standardized error response"""
    response = {
        'success': False,
        'error': error,
        'timestamp': datetime.utcnow().isoformat()
    }
    if code:
        response['code'] = code
    return jsonify(response), status_code

# =====================================================================
# PERSON ENTITY ENDPOINTS
# =====================================================================

@entity_api_bp.route('/people', methods=['GET'])
@require_auth
def get_people():
    """
    Get all people entities with optional filtering and relationship data.
    """
    try:
        # Query parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search')
        company_filter = request.args.get('company')
        importance_min = float(request.args.get('importance_min', 0.0))
        include_relationships = request.args.get('include_relationships', 'false').lower() == 'true'
        
        with get_db_manager().get_session() as session:
            query = session.query(Person).filter(Person.user_id == g.user_id)
            
            # Apply filters
            if search:
                query = query.filter(
                    (Person.name.ilike(f'%{search}%')) |
                    (Person.email_address.ilike(f'%{search}%')) |
                    (Person.company.ilike(f'%{search}%'))
                )
            
            if company_filter:
                query = query.filter(Person.company.ilike(f'%{company_filter}%'))
            
            if importance_min > 0:
                query = query.filter(Person.importance_level >= importance_min)
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination
            people = query.order_by(Person.importance_level.desc(), Person.name)\
                          .offset(offset).limit(limit).all()
            
            # Format response
            people_data = []
            for person in people:
                person_data = {
                    'id': person.id,
                    'name': person.name,
                    'email_address': person.email_address,
                    'company': person.company,
                    'title': person.title,
                    'relationship_type': person.relationship_type,
                    'importance_level': person.importance_level,
                    'bio': person.bio,
                    'linkedin_url': person.linkedin_url,
                    'last_interaction': person.last_interaction.isoformat() if person.last_interaction else None,
                    'interaction_count': person.interaction_count,
                    'created_at': person.created_at.isoformat() if person.created_at else None,
                    'updated_at': person.updated_at.isoformat() if person.updated_at else None
                }
                
                # Include relationships if requested
                if include_relationships:
                    person_data['relationships'] = _get_person_relationships(person.id, session)
                
                people_data.append(person_data)
            
            return success_response({
                'people': people_data,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting people: {str(e)}")
        return error_response(f"Failed to get people: {str(e)}", "PEOPLE_FETCH_ERROR", 500)

@entity_api_bp.route('/people/<int:person_id>', methods=['GET'])
@require_auth
def get_person(person_id: int):
    """
    Get detailed information about a specific person including relationships.
    """
    try:
        with get_db_manager().get_session() as session:
            person = session.query(Person).filter(
                Person.id == person_id,
                Person.user_id == g.user_id
            ).first()
            
            if not person:
                return error_response("Person not found", "PERSON_NOT_FOUND", 404)
            
            # Get comprehensive person data
            person_data = {
                'id': person.id,
                'name': person.name,
                'email_address': person.email_address,
                'company': person.company,
                'title': person.title,
                'relationship_type': person.relationship_type,
                'importance_level': person.importance_level,
                'bio': person.bio,
                'linkedin_url': person.linkedin_url,
                'last_interaction': person.last_interaction.isoformat() if person.last_interaction else None,
                'interaction_count': person.interaction_count,
                'created_at': person.created_at.isoformat() if person.created_at else None,
                'updated_at': person.updated_at.isoformat() if person.updated_at else None,
                
                # Comprehensive relationships
                'relationships': _get_person_relationships(person.id, session),
                'interaction_history': _get_person_interaction_history(person, session),
                'related_topics': _get_person_topics(person, session),
                'related_tasks': _get_person_tasks(person, session),
                'related_projects': _get_person_projects(person, session)
            }
            
            return success_response(person_data)
            
    except Exception as e:
        logger.error(f"Error getting person {person_id}: {str(e)}")
        return error_response(f"Failed to get person: {str(e)}", "PERSON_FETCH_ERROR", 500)

@entity_api_bp.route('/people', methods=['POST'])
@require_auth
def create_person():
    """
    Create a new person entity with relationships.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return error_response("Person name is required", "MISSING_NAME")
        
        # Create entity context
        context = EntityContext(
            source_type='manual',
            user_id=g.user_id,
            confidence=1.0
        )
        
        # Use entity engine to create person
        person = entity_engine.create_or_update_person(
            email=data.get('email_address', ''),
            name=data['name'],
            company=data.get('company', ''),
            context=context,
            bio=data.get('bio', ''),
            title=data.get('title', ''),
            linkedin_url=data.get('linkedin_url', '')
        )
        
        if person:
            # Create relationships if specified
            if data.get('related_topics'):
                for topic_name in data['related_topics']:
                    topic = entity_engine.create_or_update_topic(topic_name, context=context)
                    if topic:
                        entity_engine.create_entity_relationship(
                            'person', person.id,
                            'topic', topic.id,
                            'discusses',
                            context
                        )
            
            return success_response({
                'id': person.id,
                'name': person.name,
                'email_address': person.email_address,
                'created_at': person.created_at.isoformat() if person.created_at else None
            }, "Person created successfully")
        else:
            return error_response("Failed to create person", "CREATION_ERROR")
            
    except Exception as e:
        logger.error(f"Error creating person: {str(e)}")
        return error_response(f"Failed to create person: {str(e)}", "PERSON_CREATE_ERROR", 500)

@entity_api_bp.route('/people/<int:person_id>', methods=['PUT'])
@require_auth
def update_person(person_id: int):
    """
    Update person entity information.
    """
    try:
        data = request.get_json()
        
        with get_db_manager().get_session() as session:
            person = session.query(Person).filter(
                Person.id == person_id,
                Person.user_id == g.user_id
            ).first()
            
            if not person:
                return error_response("Person not found", "PERSON_NOT_FOUND", 404)
            
            # Update fields
            if 'name' in data:
                person.name = data['name']
            if 'company' in data:
                person.company = data['company']
            if 'title' in data:
                person.title = data['title']
            if 'relationship_type' in data:
                person.relationship_type = data['relationship_type']
            if 'importance_level' in data:
                person.importance_level = float(data['importance_level'])
            if 'bio' in data:
                person.bio = data['bio']
            if 'linkedin_url' in data:
                person.linkedin_url = data['linkedin_url']
            
            person.updated_at = datetime.utcnow()
            session.commit()
            
            return success_response({
                'id': person.id,
                'updated_at': person.updated_at.isoformat()
            }, "Person updated successfully")
            
    except Exception as e:
        logger.error(f"Error updating person {person_id}: {str(e)}")
        return error_response(f"Failed to update person: {str(e)}", "PERSON_UPDATE_ERROR", 500)

@entity_api_bp.route('/people/<int:person_id>', methods=['DELETE'])
@require_auth
def delete_person(person_id: int):
    """
    Delete person entity and its relationships.
    """
    try:
        with get_db_manager().get_session() as session:
            person = session.query(Person).filter(
                Person.id == person_id,
                Person.user_id == g.user_id
            ).first()
            
            if not person:
                return error_response("Person not found", "PERSON_NOT_FOUND", 404)
            
            # Delete relationships first
            session.query(EntityRelationship).filter(
                ((EntityRelationship.entity_type_a == 'person') & (EntityRelationship.entity_id_a == person_id)) |
                ((EntityRelationship.entity_type_b == 'person') & (EntityRelationship.entity_id_b == person_id))
            ).delete()
            
            # Delete person
            session.delete(person)
            session.commit()
            
            return success_response({'deleted': True}, "Person deleted successfully")
            
    except Exception as e:
        logger.error(f"Error deleting person {person_id}: {str(e)}")
        return error_response(f"Failed to delete person: {str(e)}", "PERSON_DELETE_ERROR", 500)

# =====================================================================
# TOPIC ENTITY ENDPOINTS
# =====================================================================

@entity_api_bp.route('/topics', methods=['GET'])
@require_auth
def get_topics():
    """
    Get all topic entities with optional filtering.
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search')
        is_official = request.args.get('is_official')
        strategic_min = float(request.args.get('strategic_min', 0.0))
        include_relationships = request.args.get('include_relationships', 'false').lower() == 'true'
        
        with get_db_manager().get_session() as session:
            query = session.query(Topic).filter(Topic.user_id == g.user_id)
            
            # Apply filters
            if search:
                query = query.filter(
                    (Topic.name.ilike(f'%{search}%')) |
                    (Topic.description.ilike(f'%{search}%'))
                )
            
            if is_official is not None:
                query = query.filter(Topic.is_official == (is_official.lower() == 'true'))
            
            if strategic_min > 0:
                query = query.filter(Topic.strategic_importance >= strategic_min)
            
            total_count = query.count()
            topics = query.order_by(Topic.strategic_importance.desc(), Topic.email_count.desc())\
                          .offset(offset).limit(limit).all()
            
            # Format response
            topics_data = []
            for topic in topics:
                topic_data = {
                    'id': topic.id,
                    'name': topic.name,
                    'description': topic.description,
                    'is_official': topic.is_official,
                    'strategic_importance': topic.strategic_importance,
                    'email_count': topic.email_count,
                    'created_at': topic.created_at.isoformat() if topic.created_at else None,
                    'updated_at': topic.updated_at.isoformat() if topic.updated_at else None
                }
                
                if include_relationships:
                    topic_data['relationships'] = _get_topic_relationships(topic.id, session)
                
                topics_data.append(topic_data)
            
            return success_response({
                'topics': topics_data,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting topics: {str(e)}")
        return error_response(f"Failed to get topics: {str(e)}", "TOPICS_FETCH_ERROR", 500)

@entity_api_bp.route('/topics/<int:topic_id>', methods=['GET'])
@require_auth
def get_topic(topic_id: int):
    """
    Get detailed information about a specific topic.
    """
    try:
        with get_db_manager().get_session() as session:
            topic = session.query(Topic).filter(
                Topic.id == topic_id,
                Topic.user_id == g.user_id
            ).first()
            
            if not topic:
                return error_response("Topic not found", "TOPIC_NOT_FOUND", 404)
            
            topic_data = {
                'id': topic.id,
                'name': topic.name,
                'description': topic.description,
                'is_official': topic.is_official,
                'strategic_importance': topic.strategic_importance,
                'email_count': topic.email_count,
                'created_at': topic.created_at.isoformat() if topic.created_at else None,
                'updated_at': topic.updated_at.isoformat() if topic.updated_at else None,
                
                # Comprehensive relationships
                'relationships': _get_topic_relationships(topic.id, session),
                'related_people': _get_topic_people(topic, session),
                'related_tasks': _get_topic_tasks(topic, session),
                'related_emails': _get_topic_emails(topic, session),
                'trend_analysis': _analyze_topic_trends(topic, session)
            }
            
            return success_response(topic_data)
            
    except Exception as e:
        logger.error(f"Error getting topic {topic_id}: {str(e)}")
        return error_response(f"Failed to get topic: {str(e)}", "TOPIC_FETCH_ERROR", 500)

@entity_api_bp.route('/topics', methods=['POST'])
@require_auth
def create_topic():
    """
    Create a new topic entity.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return error_response("Topic name is required", "MISSING_NAME")
        
        context = EntityContext(
            source_type='manual',
            user_id=g.user_id,
            confidence=1.0
        )
        
        topic = entity_engine.create_or_update_topic(
            topic_name=data['name'],
            description=data.get('description', ''),
            context=context
        )
        
        if topic:
            # Mark as official if specified
            if data.get('is_official', False):
                with get_db_manager().get_session() as session:
                    topic_obj = session.query(Topic).filter(Topic.id == topic.id).first()
                    if topic_obj:
                        topic_obj.is_official = True
                        session.commit()
            
            return success_response({
                'id': topic.id,
                'name': topic.name,
                'created_at': topic.created_at.isoformat() if topic.created_at else None
            }, "Topic created successfully")
        else:
            return error_response("Failed to create topic", "CREATION_ERROR")
            
    except Exception as e:
        logger.error(f"Error creating topic: {str(e)}")
        return error_response(f"Failed to create topic: {str(e)}", "TOPIC_CREATE_ERROR", 500)

# =====================================================================
# TASK ENTITY ENDPOINTS
# =====================================================================

@entity_api_bp.route('/tasks', methods=['GET'])
@require_auth
def get_tasks():
    """
    Get all task entities with filtering and relationship data.
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status')
        priority = request.args.get('priority')
        assignee_id = request.args.get('assignee_id')
        include_relationships = request.args.get('include_relationships', 'false').lower() == 'true'
        
        with get_db_manager().get_session() as session:
            query = session.query(Task).filter(Task.user_id == g.user_id)
            
            # Apply filters
            if status:
                query = query.filter(Task.status == status)
            if priority:
                query = query.filter(Task.priority == priority)
            if assignee_id:
                query = query.filter(Task.assignee_id == int(assignee_id))
            
            total_count = query.count()
            tasks = query.order_by(Task.created_at.desc())\
                         .offset(offset).limit(limit).all()
            
            # Format response
            tasks_data = []
            for task in tasks:
                task_data = {
                    'id': task.id,
                    'description': task.description,
                    'context_story': task.context_story,
                    'status': task.status,
                    'priority': task.priority,
                    'confidence': task.confidence,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                    'assignee_id': task.assignee_id,
                    'source_email_id': task.source_email_id,
                    'source_event_id': task.source_event_id
                }
                
                if include_relationships:
                    task_data['relationships'] = _get_task_relationships(task.id, session)
                    task_data['assignee'] = _get_task_assignee(task, session)
                    task_data['related_topics'] = _get_task_topics(task, session)
                
                tasks_data.append(task_data)
            
            return success_response({
                'tasks': tasks_data,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        return error_response(f"Failed to get tasks: {str(e)}", "TASKS_FETCH_ERROR", 500)

# =====================================================================
# ENTITY RELATIONSHIP ENDPOINTS
# =====================================================================

@entity_api_bp.route('/relationships', methods=['GET'])
@require_auth
def get_entity_relationships():
    """
    Get entity relationships with filtering and analysis.
    """
    try:
        entity_type_a = request.args.get('entity_type_a')
        entity_id_a = request.args.get('entity_id_a')
        entity_type_b = request.args.get('entity_type_b')
        relationship_type = request.args.get('relationship_type')
        limit = int(request.args.get('limit', 100))
        
        with get_db_manager().get_session() as session:
            query = session.query(EntityRelationship).filter(
                EntityRelationship.user_id == g.user_id
            )
            
            # Apply filters
            if entity_type_a:
                query = query.filter(EntityRelationship.entity_type_a == entity_type_a)
            if entity_id_a:
                query = query.filter(EntityRelationship.entity_id_a == int(entity_id_a))
            if entity_type_b:
                query = query.filter(EntityRelationship.entity_type_b == entity_type_b)
            if relationship_type:
                query = query.filter(EntityRelationship.relationship_type == relationship_type)
            
            relationships = query.order_by(EntityRelationship.strength.desc())\
                                 .limit(limit).all()
            
            # Format response
            relationships_data = []
            for rel in relationships:
                rel_data = {
                    'id': rel.id,
                    'entity_a': {
                        'type': rel.entity_type_a,
                        'id': rel.entity_id_a
                    },
                    'entity_b': {
                        'type': rel.entity_type_b,
                        'id': rel.entity_id_b
                    },
                    'relationship_type': rel.relationship_type,
                    'strength': rel.strength,
                    'confidence': rel.confidence,
                    'created_at': rel.created_at.isoformat() if rel.created_at else None,
                    'metadata': rel.metadata
                }
                
                relationships_data.append(rel_data)
            
            # Add relationship analysis
            analysis = _analyze_relationship_patterns(relationships)
            
            return success_response({
                'relationships': relationships_data,
                'analysis': analysis,
                'total_count': len(relationships_data)
            })
            
    except Exception as e:
        logger.error(f"Error getting relationships: {str(e)}")
        return error_response(f"Failed to get relationships: {str(e)}", "RELATIONSHIPS_FETCH_ERROR", 500)

@entity_api_bp.route('/relationships', methods=['POST'])
@require_auth
def create_relationship():
    """
    Create a new entity relationship.
    """
    try:
        data = request.get_json()
        
        required_fields = ['entity_type_a', 'entity_id_a', 'entity_type_b', 'entity_id_b', 'relationship_type']
        for field in required_fields:
            if field not in data:
                return error_response(f"Missing required field: {field}", "MISSING_FIELD")
        
        context = EntityContext(
            source_type='manual',
            user_id=g.user_id,
            confidence=data.get('confidence', 1.0)
        )
        
        relationship = entity_engine.create_entity_relationship(
            data['entity_type_a'], data['entity_id_a'],
            data['entity_type_b'], data['entity_id_b'],
            data['relationship_type'],
            context,
            strength=data.get('strength', 1.0)
        )
        
        if relationship:
            return success_response({
                'id': relationship.id,
                'created_at': relationship.created_at.isoformat() if relationship.created_at else None
            }, "Relationship created successfully")
        else:
            return error_response("Failed to create relationship", "CREATION_ERROR")
            
    except Exception as e:
        logger.error(f"Error creating relationship: {str(e)}")
        return error_response(f"Failed to create relationship: {str(e)}", "RELATIONSHIP_CREATE_ERROR", 500)

# =====================================================================
# ENTITY SEARCH AND DISCOVERY ENDPOINTS
# =====================================================================

@entity_api_bp.route('/search', methods=['GET'])
@require_auth
def search_entities():
    """
    Search across all entity types.
    """
    try:
        query_text = request.args.get('q', '').strip()
        entity_types = request.args.getlist('types')  # Can specify types to search
        limit = int(request.args.get('limit', 50))
        
        if not query_text:
            return error_response("Search query is required", "MISSING_QUERY")
        
        if not entity_types:
            entity_types = ['people', 'topics', 'tasks', 'projects']
        
        search_results = {}
        
        with get_db_manager().get_session() as session:
            # Search people
            if 'people' in entity_types:
                people = session.query(Person).filter(
                    Person.user_id == g.user_id,
                    (Person.name.ilike(f'%{query_text}%')) |
                    (Person.email_address.ilike(f'%{query_text}%')) |
                    (Person.company.ilike(f'%{query_text}%'))
                ).limit(limit).all()
                
                search_results['people'] = [
                    {
                        'id': p.id,
                        'name': p.name,
                        'email_address': p.email_address,
                        'company': p.company,
                        'importance_level': p.importance_level
                    }
                    for p in people
                ]
            
            # Search topics
            if 'topics' in entity_types:
                topics = session.query(Topic).filter(
                    Topic.user_id == g.user_id,
                    (Topic.name.ilike(f'%{query_text}%')) |
                    (Topic.description.ilike(f'%{query_text}%'))
                ).limit(limit).all()
                
                search_results['topics'] = [
                    {
                        'id': t.id,
                        'name': t.name,
                        'description': t.description,
                        'strategic_importance': t.strategic_importance,
                        'is_official': t.is_official
                    }
                    for t in topics
                ]
            
            # Search tasks
            if 'tasks' in entity_types:
                tasks = session.query(Task).filter(
                    Task.user_id == g.user_id,
                    Task.description.ilike(f'%{query_text}%')
                ).limit(limit).all()
                
                search_results['tasks'] = [
                    {
                        'id': t.id,
                        'description': t.description,
                        'status': t.status,
                        'priority': t.priority,
                        'confidence': t.confidence
                    }
                    for t in tasks
                ]
        
        return success_response({
            'query': query_text,
            'results': search_results,
            'total_results': sum(len(results) for results in search_results.values())
        })
        
    except Exception as e:
        logger.error(f"Error searching entities: {str(e)}")
        return error_response(f"Failed to search entities: {str(e)}", "SEARCH_ERROR", 500)

# =====================================================================
# ENTITY ANALYTICS AND INSIGHTS
# =====================================================================

@entity_api_bp.route('/analytics/overview', methods=['GET'])
@require_auth
def get_entity_overview():
    """
    Get comprehensive overview of all entities and their relationships.
    """
    try:
        with get_db_manager().get_session() as session:
            # Get entity counts
            entity_counts = {
                'people': session.query(Person).filter(Person.user_id == g.user_id).count(),
                'topics': session.query(Topic).filter(Topic.user_id == g.user_id).count(),
                'tasks': session.query(Task).filter(Task.user_id == g.user_id).count(),
                'emails': session.query(Email).filter(Email.user_id == g.user_id).count(),
                'events': session.query(CalendarEvent).filter(CalendarEvent.user_id == g.user_id).count(),
                'relationships': session.query(EntityRelationship).filter(EntityRelationship.user_id == g.user_id).count()
            }
            
            # Get top entities by various metrics
            top_people = session.query(Person).filter(Person.user_id == g.user_id)\
                               .order_by(Person.importance_level.desc()).limit(5).all()
            
            top_topics = session.query(Topic).filter(Topic.user_id == g.user_id)\
                               .order_by(Topic.strategic_importance.desc()).limit(5).all()
            
            pending_tasks = session.query(Task).filter(
                Task.user_id == g.user_id,
                Task.status.in_(['pending', 'open'])
            ).count()
            
            # Calculate relationship density
            total_entities = sum(entity_counts[k] for k in ['people', 'topics', 'tasks'] if k in entity_counts)
            relationship_density = entity_counts['relationships'] / max(total_entities, 1)
            
            overview = {
                'entity_counts': entity_counts,
                'top_people': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'company': p.company,
                        'importance_level': p.importance_level
                    }
                    for p in top_people
                ],
                'top_topics': [
                    {
                        'id': t.id,
                        'name': t.name,
                        'strategic_importance': t.strategic_importance,
                        'email_count': t.email_count
                    }
                    for t in top_topics
                ],
                'task_summary': {
                    'total': entity_counts['tasks'],
                    'pending': pending_tasks,
                    'completion_rate': (entity_counts['tasks'] - pending_tasks) / max(entity_counts['tasks'], 1) * 100
                },
                'relationship_metrics': {
                    'total_relationships': entity_counts['relationships'],
                    'relationship_density': relationship_density,
                    'avg_relationships_per_entity': relationship_density * 2  # Each relationship connects 2 entities
                }
            }
            
            return success_response(overview)
            
    except Exception as e:
        logger.error(f"Error getting entity overview: {str(e)}")
        return error_response(f"Failed to get entity overview: {str(e)}", "OVERVIEW_ERROR", 500)

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def _get_person_relationships(person_id: int, session) -> List[Dict]:
    """Get relationships for a person"""
    relationships = session.query(EntityRelationship).filter(
        ((EntityRelationship.entity_type_a == 'person') & (EntityRelationship.entity_id_a == person_id)) |
        ((EntityRelationship.entity_type_b == 'person') & (EntityRelationship.entity_id_b == person_id))
    ).all()
    
    return [
        {
            'id': rel.id,
            'related_entity': {
                'type': rel.entity_type_b if rel.entity_type_a == 'person' else rel.entity_type_a,
                'id': rel.entity_id_b if rel.entity_type_a == 'person' else rel.entity_id_a
            },
            'relationship_type': rel.relationship_type,
            'strength': rel.strength
        }
        for rel in relationships
    ]

def _get_person_interaction_history(person: Person, session) -> List[Dict]:
    """Get interaction history for a person"""
    emails = session.query(Email).filter(
        Email.user_id == person.user_id,
        Email.sender == person.email_address
    ).order_by(Email.email_date.desc()).limit(10).all()
    
    return [
        {
            'type': 'email',
            'date': email.email_date.isoformat() if email.email_date else None,
            'subject': email.subject,
            'summary': email.ai_summary[:100] if email.ai_summary else None
        }
        for email in emails
    ]

def _get_person_topics(person: Person, session) -> List[Dict]:
    """Get topics related to a person"""
    # This would join through relationships
    return []  # Simplified for now

def _get_person_tasks(person: Person, session) -> List[Dict]:
    """Get tasks related to a person"""
    tasks = session.query(Task).filter(Task.assignee_id == person.id).limit(5).all()
    
    return [
        {
            'id': task.id,
            'description': task.description,
            'status': task.status,
            'priority': task.priority
        }
        for task in tasks
    ]

def _get_person_projects(person: Person, session) -> List[Dict]:
    """Get projects related to a person"""
    # This would need to be implemented based on project relationships
    return []  # Simplified for now

def _get_topic_relationships(topic_id: int, session) -> List[Dict]:
    """Get relationships for a topic"""
    relationships = session.query(EntityRelationship).filter(
        ((EntityRelationship.entity_type_a == 'topic') & (EntityRelationship.entity_id_a == topic_id)) |
        ((EntityRelationship.entity_type_b == 'topic') & (EntityRelationship.entity_id_b == topic_id))
    ).all()
    
    return [
        {
            'id': rel.id,
            'related_entity': {
                'type': rel.entity_type_b if rel.entity_type_a == 'topic' else rel.entity_type_a,
                'id': rel.entity_id_b if rel.entity_type_a == 'topic' else rel.entity_id_a
            },
            'relationship_type': rel.relationship_type,
            'strength': rel.strength
        }
        for rel in relationships
    ]

def _get_topic_people(topic: Topic, session) -> List[Dict]:
    """Get people related to a topic"""
    # This would join through relationships
    return []  # Simplified for now

def _get_topic_tasks(topic: Topic, session) -> List[Dict]:
    """Get tasks related to a topic"""
    # This would join through relationships or topic assignments
    return []  # Simplified for now

def _get_topic_emails(topic: Topic, session) -> List[Dict]:
    """Get emails related to a topic"""
    # This would need topic-email relationships
    return []  # Simplified for now

def _analyze_topic_trends(topic: Topic, session) -> Dict:
    """Analyze trends for a topic"""
    return {
        'email_trend': 'increasing',  # Would calculate based on actual data
        'mention_frequency': topic.email_count,
        'strategic_trajectory': 'growing'
    }

def _get_task_relationships(task_id: int, session) -> List[Dict]:
    """Get relationships for a task"""
    relationships = session.query(EntityRelationship).filter(
        ((EntityRelationship.entity_type_a == 'task') & (EntityRelationship.entity_id_a == task_id)) |
        ((EntityRelationship.entity_type_b == 'task') & (EntityRelationship.entity_id_b == task_id))
    ).all()
    
    return [
        {
            'id': rel.id,
            'related_entity': {
                'type': rel.entity_type_b if rel.entity_type_a == 'task' else rel.entity_type_a,
                'id': rel.entity_id_b if rel.entity_type_a == 'task' else rel.entity_id_a
            },
            'relationship_type': rel.relationship_type,
            'strength': rel.strength
        }
        for rel in relationships
    ]

def _get_task_assignee(task: Task, session) -> Optional[Dict]:
    """Get assignee information for a task"""
    if task.assignee_id:
        assignee = session.query(Person).filter(Person.id == task.assignee_id).first()
        if assignee:
            return {
                'id': assignee.id,
                'name': assignee.name,
                'email_address': assignee.email_address
            }
    return None

def _get_task_topics(task: Task, session) -> List[Dict]:
    """Get topics related to a task"""
    # This would join through relationships
    return []  # Simplified for now

def _analyze_relationship_patterns(relationships: List[EntityRelationship]) -> Dict:
    """Analyze patterns in entity relationships"""
    from collections import Counter
    
    relationship_types = Counter(rel.relationship_type for rel in relationships)
    entity_type_pairs = Counter(f"{rel.entity_type_a}-{rel.entity_type_b}" for rel in relationships)
    
    return {
        'most_common_relationships': dict(relationship_types.most_common(5)),
        'most_common_entity_pairs': dict(entity_type_pairs.most_common(5)),
        'average_strength': sum(rel.strength for rel in relationships) / len(relationships) if relationships else 0,
        'total_relationships': len(relationships)
    }

# Export the blueprint
__all__ = ['entity_api_bp'] 