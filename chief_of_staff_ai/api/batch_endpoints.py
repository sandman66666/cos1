# Batch Processing API Endpoints - Bulk Operations and Efficient Processing
# These endpoints provide batch processing capabilities for high-volume operations

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Import the integration manager and enhanced processors
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'chief_of_staff_ai'))

from processors.integration_manager import integration_manager
from chief_of_staff_ai.models.database import get_db_manager
from config.settings import settings

logger = logging.getLogger(__name__)

# Create Blueprint
batch_api_bp = Blueprint('batch_api', __name__, url_prefix='/api/batch')

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
# BATCH EMAIL PROCESSING ENDPOINTS
# =====================================================================

@batch_api_bp.route('/emails/process', methods=['POST'])
@require_auth
def batch_process_emails():
    """
    Process multiple emails in batch with configurable concurrency and options.
    """
    try:
        data = request.get_json() or {}
        
        # Batch configuration
        emails_data = data.get('emails', [])
        batch_size = data.get('batch_size', 10)
        max_workers = data.get('max_workers', 3)
        real_time = data.get('real_time', False)
        legacy_mode = data.get('legacy_mode', False)
        priority = data.get('priority', 5)
        
        if not emails_data:
            return error_response("No emails provided for batch processing", "NO_EMAILS")
        
        if len(emails_data) > 1000:
            return error_response("Batch size too large. Maximum 1000 emails per batch.", "BATCH_TOO_LARGE")
        
        logger.info(f"Starting batch email processing: {len(emails_data)} emails, batch_size={batch_size}, workers={max_workers}")
        
        # Process emails in batches
        start_time = time.time()
        batch_results = []
        total_processed = 0
        total_errors = 0
        
        # Split emails into batches
        email_batches = [emails_data[i:i + batch_size] for i in range(0, len(emails_data), batch_size)]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit batch processing jobs
            future_to_batch = {
                executor.submit(
                    _process_email_batch_worker,
                    batch, g.user_id, real_time, legacy_mode, batch_idx
                ): batch_idx
                for batch_idx, batch in enumerate(email_batches)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_result = future.result()
                    batch_results.append({
                        'batch_index': batch_idx,
                        'result': batch_result,
                        'processing_time': batch_result.get('processing_time', 0)
                    })
                    
                    total_processed += batch_result.get('processed_count', 0)
                    total_errors += batch_result.get('error_count', 0)
                    
                except Exception as e:
                    logger.error(f"Error in batch {batch_idx}: {str(e)}")
                    batch_results.append({
                        'batch_index': batch_idx,
                        'error': str(e)
                    })
                    total_errors += len(email_batches[batch_idx])
        
        total_time = time.time() - start_time
        
        # Compile comprehensive results
        batch_summary = {
            'total_emails': len(emails_data),
            'total_processed': total_processed,
            'total_errors': total_errors,
            'success_rate': (total_processed / len(emails_data)) * 100 if emails_data else 0,
            'total_processing_time': total_time,
            'avg_emails_per_second': len(emails_data) / total_time if total_time > 0 else 0,
            'batch_results': batch_results,
            'configuration': {
                'batch_size': batch_size,
                'max_workers': max_workers,
                'real_time': real_time,
                'legacy_mode': legacy_mode
            }
        }
        
        return success_response(batch_summary, f"Batch processing completed: {total_processed}/{len(emails_data)} emails processed")
        
    except Exception as e:
        logger.error(f"Error in batch email processing: {str(e)}")
        return error_response(f"Batch processing error: {str(e)}", "BATCH_ERROR", 500)

@batch_api_bp.route('/emails/normalize', methods=['POST'])
@require_auth
def batch_normalize_emails():
    """
    Normalize multiple emails in batch.
    """
    try:
        data = request.get_json() or {}
        emails_data = data.get('emails', [])
        batch_size = data.get('batch_size', 20)
        
        if not emails_data:
            return error_response("No emails provided for normalization", "NO_EMAILS")
        
        logger.info(f"Starting batch email normalization: {len(emails_data)} emails")
        
        # Process in batches for memory efficiency
        normalized_results = []
        error_results = []
        
        for i in range(0, len(emails_data), batch_size):
            batch = emails_data[i:i + batch_size]
            
            for email_data in batch:
                try:
                    result = integration_manager.data_normalizer.normalize_email_data(email_data)
                    normalized_results.append({
                        'original_index': i + batch.index(email_data),
                        'success': result.success,
                        'normalized_data': result.normalized_data if result.success else None,
                        'quality_score': result.quality_score,
                        'issues_found': result.issues_found
                    })
                except Exception as e:
                    error_results.append({
                        'original_index': i + batch.index(email_data),
                        'error': str(e)
                    })
        
        normalization_summary = {
            'total_emails': len(emails_data),
            'successfully_normalized': len([r for r in normalized_results if r['success']]),
            'normalization_errors': len(error_results),
            'processing_errors': len([r for r in normalized_results if not r['success']]),
            'average_quality_score': sum(r['quality_score'] for r in normalized_results if r['success']) / max(len([r for r in normalized_results if r['success']]), 1),
            'results': normalized_results,
            'errors': error_results
        }
        
        return success_response(normalization_summary, "Batch normalization completed")
        
    except Exception as e:
        logger.error(f"Error in batch email normalization: {str(e)}")
        return error_response(f"Batch normalization error: {str(e)}", "BATCH_NORMALIZE_ERROR", 500)

# =====================================================================
# BATCH TASK PROCESSING ENDPOINTS
# =====================================================================

@batch_api_bp.route('/tasks/create', methods=['POST'])
@require_auth
def batch_create_tasks():
    """
    Create multiple tasks in batch with entity relationships.
    """
    try:
        data = request.get_json() or {}
        tasks_data = data.get('tasks', [])
        
        if not tasks_data:
            return error_response("No tasks provided for creation", "NO_TASKS")
        
        if len(tasks_data) > 500:
            return error_response("Batch size too large. Maximum 500 tasks per batch.", "BATCH_TOO_LARGE")
        
        logger.info(f"Starting batch task creation: {len(tasks_data)} tasks")
        
        created_tasks = []
        error_tasks = []
        
        for idx, task_data in enumerate(tasks_data):
            try:
                if 'description' not in task_data:
                    error_tasks.append({
                        'index': idx,
                        'error': 'Missing required field: description',
                        'task_data': task_data
                    })
                    continue
                
                result = integration_manager.create_manual_task_complete(
                    task_description=task_data['description'],
                    user_id=g.user_id,
                    assignee_email=task_data.get('assignee_email'),
                    topic_names=task_data.get('topic_names', []),
                    project_name=task_data.get('project_name'),
                    due_date=datetime.fromisoformat(task_data['due_date']) if task_data.get('due_date') else None,
                    priority=task_data.get('priority', 'medium')
                )
                
                if result['success']:
                    created_tasks.append({
                        'index': idx,
                        'task_id': result['result']['task']['id'],
                        'description': result['result']['task']['description']
                    })
                else:
                    error_tasks.append({
                        'index': idx,
                        'error': result['error'],
                        'task_data': task_data
                    })
                    
            except Exception as e:
                error_tasks.append({
                    'index': idx,
                    'error': str(e),
                    'task_data': task_data
                })
        
        task_creation_summary = {
            'total_tasks': len(tasks_data),
            'successfully_created': len(created_tasks),
            'creation_errors': len(error_tasks),
            'success_rate': (len(created_tasks) / len(tasks_data)) * 100 if tasks_data else 0,
            'created_tasks': created_tasks,
            'errors': error_tasks
        }
        
        return success_response(task_creation_summary, f"Batch task creation completed: {len(created_tasks)}/{len(tasks_data)} tasks created")
        
    except Exception as e:
        logger.error(f"Error in batch task creation: {str(e)}")
        return error_response(f"Batch task creation error: {str(e)}", "BATCH_TASK_ERROR", 500)

@batch_api_bp.route('/tasks/update-status', methods=['POST'])
@require_auth
def batch_update_task_status():
    """
    Update status of multiple tasks in batch.
    """
    try:
        data = request.get_json() or {}
        task_updates = data.get('task_updates', [])
        
        if not task_updates:
            return error_response("No task updates provided", "NO_UPDATES")
        
        logger.info(f"Starting batch task status updates: {len(task_updates)} tasks")
        
        updated_tasks = []
        error_updates = []
        
        for idx, update_data in enumerate(task_updates):
            try:
                if 'task_id' not in update_data or 'status' not in update_data:
                    error_updates.append({
                        'index': idx,
                        'error': 'Missing required fields: task_id and status',
                        'update_data': update_data
                    })
                    continue
                
                result = integration_manager.task_processor.update_task_status(
                    update_data['task_id'],
                    update_data['status'],
                    g.user_id,
                    update_data.get('completion_notes')
                )
                
                if result['success']:
                    updated_tasks.append({
                        'index': idx,
                        'task_id': update_data['task_id'],
                        'new_status': update_data['status']
                    })
                else:
                    error_updates.append({
                        'index': idx,
                        'error': result['error'],
                        'update_data': update_data
                    })
                    
            except Exception as e:
                error_updates.append({
                    'index': idx,
                    'error': str(e),
                    'update_data': update_data
                })
        
        update_summary = {
            'total_updates': len(task_updates),
            'successfully_updated': len(updated_tasks),
            'update_errors': len(error_updates),
            'success_rate': (len(updated_tasks) / len(task_updates)) * 100 if task_updates else 0,
            'updated_tasks': updated_tasks,
            'errors': error_updates
        }
        
        return success_response(update_summary, f"Batch task updates completed: {len(updated_tasks)}/{len(task_updates)} tasks updated")
        
    except Exception as e:
        logger.error(f"Error in batch task updates: {str(e)}")
        return error_response(f"Batch task update error: {str(e)}", "BATCH_UPDATE_ERROR", 500)

# =====================================================================
# BATCH CALENDAR PROCESSING ENDPOINTS
# =====================================================================

@batch_api_bp.route('/calendar/process', methods=['POST'])
@require_auth
def batch_process_calendar_events():
    """
    Process multiple calendar events in batch.
    """
    try:
        data = request.get_json() or {}
        events_data = data.get('events', [])
        max_workers = data.get('max_workers', 2)  # Calendar processing is more intensive
        real_time = data.get('real_time', False)
        
        if not events_data:
            return error_response("No calendar events provided", "NO_EVENTS")
        
        if len(events_data) > 200:
            return error_response("Batch size too large. Maximum 200 events per batch.", "BATCH_TOO_LARGE")
        
        logger.info(f"Starting batch calendar processing: {len(events_data)} events")
        
        processed_events = []
        error_events = []
        
        # Process events with limited concurrency due to AI processing intensity
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_event = {
                executor.submit(
                    _process_calendar_event_worker,
                    event_data, g.user_id, real_time, idx
                ): idx
                for idx, event_data in enumerate(events_data)
            }
            
            for future in as_completed(future_to_event):
                idx = future_to_event[future]
                try:
                    result = future.result()
                    if result['success']:
                        processed_events.append({
                            'index': idx,
                            'event_id': result['result'].get('event_id'),
                            'title': result['result'].get('title')
                        })
                    else:
                        error_events.append({
                            'index': idx,
                            'error': result['error']
                        })
                except Exception as e:
                    error_events.append({
                        'index': idx,
                        'error': str(e)
                    })
        
        calendar_summary = {
            'total_events': len(events_data),
            'successfully_processed': len(processed_events),
            'processing_errors': len(error_events),
            'success_rate': (len(processed_events) / len(events_data)) * 100 if events_data else 0,
            'processed_events': processed_events,
            'errors': error_events
        }
        
        return success_response(calendar_summary, f"Batch calendar processing completed: {len(processed_events)}/{len(events_data)} events processed")
        
    except Exception as e:
        logger.error(f"Error in batch calendar processing: {str(e)}")
        return error_response(f"Batch calendar processing error: {str(e)}", "BATCH_CALENDAR_ERROR", 500)

# =====================================================================
# BATCH ANALYTICS ENDPOINTS
# =====================================================================

@batch_api_bp.route('/analytics/generate-insights', methods=['POST'])
@require_auth
def batch_generate_insights():
    """
    Generate analytics and insights for multiple users or time periods.
    """
    try:
        data = request.get_json() or {}
        analysis_requests = data.get('requests', [])
        
        if not analysis_requests:
            # Default to current user comprehensive analysis
            analysis_requests = [{'type': 'comprehensive', 'user_id': g.user_id}]
        
        logger.info(f"Starting batch analytics generation: {len(analysis_requests)} requests")
        
        analytics_results = []
        error_results = []
        
        for idx, request_data in enumerate(analysis_requests):
            try:
                analysis_type = request_data.get('type', 'comprehensive')
                target_user_id = request_data.get('user_id', g.user_id)
                
                # Ensure user can only analyze their own data (security check)
                if target_user_id != g.user_id:
                    error_results.append({
                        'index': idx,
                        'error': 'Cannot analyze data for other users',
                        'request': request_data
                    })
                    continue
                
                result = integration_manager.generate_user_insights(target_user_id, analysis_type)
                
                if result['success']:
                    analytics_results.append({
                        'index': idx,
                        'analysis_type': analysis_type,
                        'insights_count': len(result['result'].get('insights', [])),
                        'summary': result['result'].get('summary', {})
                    })
                else:
                    error_results.append({
                        'index': idx,
                        'error': result['error'],
                        'request': request_data
                    })
                    
            except Exception as e:
                error_results.append({
                    'index': idx,
                    'error': str(e),
                    'request': request_data
                })
        
        analytics_summary = {
            'total_requests': len(analysis_requests),
            'successfully_generated': len(analytics_results),
            'generation_errors': len(error_results),
            'success_rate': (len(analytics_results) / len(analysis_requests)) * 100 if analysis_requests else 0,
            'analytics_results': analytics_results,
            'errors': error_results
        }
        
        return success_response(analytics_summary, f"Batch analytics generation completed: {len(analytics_results)}/{len(analysis_requests)} analyses generated")
        
    except Exception as e:
        logger.error(f"Error in batch analytics generation: {str(e)}")
        return error_response(f"Batch analytics error: {str(e)}", "BATCH_ANALYTICS_ERROR", 500)

# =====================================================================
# BATCH ENTITY MANAGEMENT ENDPOINTS
# =====================================================================

@batch_api_bp.route('/entities/create', methods=['POST'])
@require_auth
def batch_create_entities():
    """
    Create multiple entities and their relationships in batch.
    """
    try:
        data = request.get_json() or {}
        entities_data = data.get('entities', [])
        create_relationships = data.get('create_relationships', True)
        
        if not entities_data:
            return error_response("No entities provided for creation", "NO_ENTITIES")
        
        logger.info(f"Starting batch entity creation: {len(entities_data)} entities")
        
        created_entities = []
        error_entities = []
        
        from processors.unified_entity_engine import EntityContext
        
        context = EntityContext(
            source_type='batch_manual',
            user_id=g.user_id,
            confidence=1.0
        )
        
        for idx, entity_data in enumerate(entities_data):
            try:
                entity_type = entity_data.get('type')
                
                if entity_type == 'person':
                    entity = integration_manager.entity_engine.create_or_update_person(
                        email=entity_data.get('email', ''),
                        name=entity_data.get('name', ''),
                        company=entity_data.get('company', ''),
                        context=context,
                        bio=entity_data.get('bio', ''),
                        title=entity_data.get('title', ''),
                        linkedin_url=entity_data.get('linkedin_url', '')
                    )
                    
                elif entity_type == 'topic':
                    entity = integration_manager.entity_engine.create_or_update_topic(
                        topic_name=entity_data.get('name', ''),
                        description=entity_data.get('description', ''),
                        context=context
                    )
                    
                else:
                    error_entities.append({
                        'index': idx,
                        'error': f'Unsupported entity type: {entity_type}',
                        'entity_data': entity_data
                    })
                    continue
                
                if entity:
                    created_entities.append({
                        'index': idx,
                        'entity_type': entity_type,
                        'entity_id': entity.id,
                        'name': getattr(entity, 'name', 'Unknown')
                    })
                else:
                    error_entities.append({
                        'index': idx,
                        'error': 'Failed to create entity',
                        'entity_data': entity_data
                    })
                    
            except Exception as e:
                error_entities.append({
                    'index': idx,
                    'error': str(e),
                    'entity_data': entity_data
                })
        
        entity_creation_summary = {
            'total_entities': len(entities_data),
            'successfully_created': len(created_entities),
            'creation_errors': len(error_entities),
            'success_rate': (len(created_entities) / len(entities_data)) * 100 if entities_data else 0,
            'created_entities': created_entities,
            'errors': error_entities
        }
        
        return success_response(entity_creation_summary, f"Batch entity creation completed: {len(created_entities)}/{len(entities_data)} entities created")
        
    except Exception as e:
        logger.error(f"Error in batch entity creation: {str(e)}")
        return error_response(f"Batch entity creation error: {str(e)}", "BATCH_ENTITY_ERROR", 500)

# =====================================================================
# BATCH STATUS AND MONITORING ENDPOINTS
# =====================================================================

@batch_api_bp.route('/status', methods=['GET'])
@require_auth
def get_batch_processing_status():
    """
    Get current status of all batch processing operations.
    """
    try:
        # This would integrate with a job queue system in production
        # For now, return static status information
        status_info = {
            'batch_processing_available': True,
            'max_batch_sizes': {
                'emails': 1000,
                'tasks': 500,
                'calendar_events': 200,
                'entities': 500
            },
            'default_batch_sizes': {
                'emails': 10,
                'tasks': 20,
                'calendar_events': 5,
                'entities': 25
            },
            'max_workers': {
                'emails': 3,
                'tasks': 4,
                'calendar_events': 2,
                'entities': 3
            },
            'processing_statistics': integration_manager.get_processing_statistics()['result'] if integration_manager.get_processing_statistics()['success'] else {}
        }
        
        return success_response(status_info, "Batch processing status retrieved")
        
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        return error_response(f"Status error: {str(e)}", "STATUS_ERROR", 500)

@batch_api_bp.route('/health', methods=['GET'])
def batch_health_check():
    """
    Health check for batch processing endpoints.
    """
    try:
        health_status = {
            'status': 'healthy',
            'batch_endpoints': 'available',
            'integration_manager': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test integration manager connection
        try:
            integration_manager.get_processing_statistics()
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['integration_manager'] = f'error: {str(e)}'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# =====================================================================
# WORKER FUNCTIONS FOR BATCH PROCESSING
# =====================================================================

def _process_email_batch_worker(email_batch: List[Dict], user_id: int, real_time: bool, legacy_mode: bool, batch_idx: int) -> Dict:
    """
    Worker function to process a batch of emails.
    """
    try:
        start_time = time.time()
        
        result = integration_manager.process_email_batch(
            email_batch, user_id, len(email_batch), real_time
        )
        
        processing_time = time.time() - start_time
        
        return {
            'batch_index': batch_idx,
            'success': result['success'],
            'processed_count': len(email_batch) if result['success'] else 0,
            'error_count': 0 if result['success'] else len(email_batch),
            'processing_time': processing_time,
            'details': result['result'] if result['success'] else result['error']
        }
        
    except Exception as e:
        logger.error(f"Error in email batch worker {batch_idx}: {str(e)}")
        return {
            'batch_index': batch_idx,
            'success': False,
            'processed_count': 0,
            'error_count': len(email_batch),
            'processing_time': 0,
            'error': str(e)
        }

def _process_calendar_event_worker(event_data: Dict, user_id: int, real_time: bool, idx: int) -> Dict:
    """
    Worker function to process a single calendar event.
    """
    try:
        result = integration_manager.process_calendar_event_complete(
            event_data, user_id, real_time
        )
        
        return {
            'index': idx,
            'success': result['success'],
            'result': result['result'] if result['success'] else None,
            'error': result['error'] if not result['success'] else None
        }
        
    except Exception as e:
        logger.error(f"Error in calendar event worker {idx}: {str(e)}")
        return {
            'index': idx,
            'success': False,
            'result': None,
            'error': str(e)
        }

# Export the blueprint
__all__ = ['batch_api_bp'] 