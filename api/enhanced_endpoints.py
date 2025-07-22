# Enhanced API Endpoints - Main Business Logic APIs
# These endpoints leverage the integration manager and enhanced processor architecture

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
import json
import asyncio
import traceback

# Import the integration manager and enhanced processors
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'chief_of_staff_ai'))

from processors.integration_manager import integration_manager
from chief_of_staff_ai.models.database import get_db_manager
from config.settings import settings

logger = logging.getLogger(__name__)

# Create Blueprint
enhanced_api_bp = Blueprint('enhanced_api', __name__, url_prefix='/api/v2')

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
        
        # Store user info in g for easy access
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
# EMAIL PROCESSING ENDPOINTS
# =====================================================================

@enhanced_api_bp.route('/emails/process', methods=['POST'])
@require_auth
def process_emails():
    """
    Process emails with comprehensive entity creation and intelligence.
    This is the main email processing endpoint using enhanced processors.
    """
    try:
        data = request.get_json() or {}
        
        # Configuration options
        real_time = data.get('real_time', True)
        batch_size = data.get('batch_size', 10)
        legacy_mode = data.get('legacy_mode', False)
        email_limit = data.get('limit', 50)
        
        logger.info(f"Processing emails for user {g.user_id} - realtime: {real_time}, legacy: {legacy_mode}")
        
        # Get email data (this would normally come from Gmail fetcher)
        # For now, we'll get from database or fetch new emails
        if 'email_data' in data:
            # Process specific emails provided in request
            email_list = data['email_data']
            if isinstance(email_list, dict):
                email_list = [email_list]
            
            # Process single email or batch
            if len(email_list) == 1:
                result = integration_manager.process_email_complete(
                    email_list[0], g.user_id, real_time, legacy_mode
                )
            else:
                result = integration_manager.process_email_batch(
                    email_list, g.user_id, batch_size, real_time
                )
        else:
            # Fetch and process recent emails
            from ingest.gmail_fetcher import gmail_fetcher
            
            # Get Gmail credentials from session
            gmail_creds = session.get('gmail_credentials')
            if not gmail_creds:
                return error_response("Gmail credentials not found", "GMAIL_AUTH_REQUIRED", 401)
            
            # Fetch recent emails
            fetch_result = gmail_fetcher.fetch_recent_emails(
                gmail_creds, limit=email_limit
            )
            
            if not fetch_result['success']:
                return error_response(f"Failed to fetch emails: {fetch_result['error']}", "GMAIL_FETCH_ERROR")
            
            emails = fetch_result['emails']
            if not emails:
                return success_response({
                    'processed': 0,
                    'message': 'No new emails to process'
                })
            
            # Process emails in batch
            result = integration_manager.process_email_batch(
                emails, g.user_id, batch_size, real_time
            )
        
        if result['success']:
            return success_response(result['result'], "Emails processed successfully")
        else:
            return error_response(result['error'], "EMAIL_PROCESSING_ERROR")
            
    except Exception as e:
        logger.error(f"Error in enhanced email processing: {str(e)}")
        logger.error(traceback.format_exc())
        return error_response(f"Internal processing error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/emails/normalize', methods=['POST'])
@require_auth
def normalize_email():
    """
    Normalize email data using enhanced data normalizer.
    """
    try:
        data = request.get_json()
        
        if not data or 'email_data' not in data:
            return error_response("Email data required", "MISSING_EMAIL_DATA")
        
        # Use integration manager's normalizer
        result = integration_manager.data_normalizer.normalize_email_data(data['email_data'])
        
        if result.success:
            response_data = {
                'normalized_data': result.normalized_data,
                'quality_score': result.quality_score,
                'issues_found': result.issues_found,
                'processing_notes': result.processing_notes
            }
            return success_response(response_data, "Email normalized successfully")
        else:
            return error_response(f"Normalization failed: {result.issues_found}", "NORMALIZATION_ERROR")
            
    except Exception as e:
        logger.error(f"Error in email normalization: {str(e)}")
        return error_response(f"Normalization error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/emails/intelligence', methods=['POST'])
@require_auth
def extract_email_intelligence():
    """
    Extract comprehensive business intelligence from email.
    """
    try:
        data = request.get_json()
        
        if not data or 'email_data' not in data:
            return error_response("Email data required", "MISSING_EMAIL_DATA")
        
        # Extract business context
        context_result = integration_manager.email_processor.extract_business_context(
            data['email_data'], g.user_id
        )
        
        # Extract meeting requests
        meeting_result = integration_manager.email_processor.extract_meeting_requests(
            data['email_data'], g.user_id
        )
        
        # Enhance with historical context
        history_result = integration_manager.email_processor.enhance_with_historical_context(
            data['email_data'], g.user_id
        )
        
        intelligence_data = {
            'business_context': context_result['result'] if context_result['success'] else None,
            'meeting_requests': meeting_result['result'] if meeting_result['success'] else None,
            'historical_context': history_result['result'] if history_result['success'] else None
        }
        
        return success_response(intelligence_data, "Email intelligence extracted")
        
    except Exception as e:
        logger.error(f"Error in email intelligence extraction: {str(e)}")
        return error_response(f"Intelligence extraction error: {str(e)}", "INTERNAL_ERROR", 500)

# =====================================================================
# TASK MANAGEMENT ENDPOINTS  
# =====================================================================

@enhanced_api_bp.route('/tasks', methods=['GET'])
@require_auth
def get_tasks():
    """
    Get user tasks with full entity context and relationships.
    """
    try:
        # Get query parameters
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        limit = int(request.args.get('limit', 100))
        
        result = integration_manager.task_processor.get_user_tasks_with_context(
            g.user_id, status_filter, priority_filter, limit
        )
        
        if result['success']:
            return success_response(result['result'])
        else:
            return error_response(result['error'], "TASK_FETCH_ERROR")
            
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        return error_response(f"Task retrieval error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/tasks', methods=['POST'])
@require_auth
def create_task():
    """
    Create manual task with full entity context and relationships.
    """
    try:
        data = request.get_json()
        
        if not data or 'description' not in data:
            return error_response("Task description required", "MISSING_DESCRIPTION")
        
        result = integration_manager.create_manual_task_complete(
            task_description=data['description'],
            user_id=g.user_id,
            assignee_email=data.get('assignee_email'),
            topic_names=data.get('topic_names', []),
            project_name=data.get('project_name'),
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            priority=data.get('priority', 'medium')
        )
        
        if result['success']:
            return success_response(result['result'], "Task created successfully")
        else:
            return error_response(result['error'], "TASK_CREATION_ERROR")
            
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return error_response(f"Task creation error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
@require_auth
def update_task_status(task_id: int):
    """
    Update task status with intelligence propagation.
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return error_response("New status required", "MISSING_STATUS")
        
        result = integration_manager.task_processor.update_task_status(
            task_id, data['status'], g.user_id, data.get('completion_notes')
        )
        
        if result['success']:
            return success_response(result['result'], "Task status updated")
        else:
            return error_response(result['error'], "TASK_UPDATE_ERROR")
            
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        return error_response(f"Task update error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/tasks/from-email', methods=['POST'])
@require_auth
def extract_tasks_from_email():
    """
    Extract tasks from email using enhanced processor.
    """
    try:
        data = request.get_json()
        
        if not data or 'email_data' not in data:
            return error_response("Email data required", "MISSING_EMAIL_DATA")
        
        result = integration_manager.task_processor.process_tasks_from_email(
            data['email_data'], g.user_id
        )
        
        if result['success']:
            return success_response(result['result'], "Tasks extracted from email")
        else:
            return error_response(result['error'], "TASK_EXTRACTION_ERROR")
            
    except Exception as e:
        logger.error(f"Error extracting tasks from email: {str(e)}")
        return error_response(f"Task extraction error: {str(e)}", "INTERNAL_ERROR", 500)

# =====================================================================
# CALENDAR AND MEETING ENDPOINTS
# =====================================================================

@enhanced_api_bp.route('/calendar/process', methods=['POST'])
@require_auth
def process_calendar_event():
    """
    Process calendar event with meeting preparation and intelligence.
    """
    try:
        data = request.get_json()
        
        if not data or 'event_data' not in data:
            return error_response("Calendar event data required", "MISSING_EVENT_DATA")
        
        real_time = data.get('real_time', True)
        
        result = integration_manager.process_calendar_event_complete(
            data['event_data'], g.user_id, real_time
        )
        
        if result['success']:
            return success_response(result['result'], "Calendar event processed")
        else:
            return error_response(result['error'], "CALENDAR_PROCESSING_ERROR")
            
    except Exception as e:
        logger.error(f"Error processing calendar event: {str(e)}")
        return error_response(f"Calendar processing error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/calendar/prep-tasks', methods=['POST'])
@require_auth
def generate_meeting_prep_tasks():
    """
    Generate meeting preparation tasks from calendar event.
    """
    try:
        data = request.get_json()
        
        if not data or 'event_data' not in data:
            return error_response("Calendar event data required", "MISSING_EVENT_DATA")
        
        result = integration_manager.task_processor.process_tasks_from_calendar_event(
            data['event_data'], g.user_id
        )
        
        if result['success']:
            return success_response(result['result'], "Meeting preparation tasks generated")
        else:
            return error_response(result['error'], "PREP_TASK_ERROR")
            
    except Exception as e:
        logger.error(f"Error generating prep tasks: {str(e)}")
        return error_response(f"Prep task error: {str(e)}", "INTERNAL_ERROR", 500)

# =====================================================================
# ANALYTICS AND INSIGHTS ENDPOINTS
# =====================================================================

@enhanced_api_bp.route('/analytics/insights', methods=['GET'])
@require_auth
def get_user_insights():
    """
    Generate comprehensive user insights from all data sources.
    """
    try:
        analysis_type = request.args.get('type', 'comprehensive')
        
        result = integration_manager.generate_user_insights(g.user_id, analysis_type)
        
        if result['success']:
            return success_response(result['result'])
        else:
            return error_response(result['error'], "INSIGHTS_ERROR")
            
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        return error_response(f"Insights error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/analytics/task-patterns', methods=['GET'])
@require_auth
def get_task_patterns():
    """
    Analyze user task patterns for productivity insights.
    """
    try:
        days_back = int(request.args.get('days', 30))
        
        result = integration_manager.task_processor.analyze_task_patterns(g.user_id, days_back)
        
        if result['success']:
            return success_response(result['result'])
        else:
            return error_response(result['error'], "TASK_ANALYSIS_ERROR")
            
    except Exception as e:
        logger.error(f"Error analyzing task patterns: {str(e)}")
        return error_response(f"Task analysis error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/analytics/email-patterns', methods=['GET'])
@require_auth
def get_email_patterns():
    """
    Analyze email communication patterns and generate insights.
    """
    try:
        days_back = int(request.args.get('days', 30))
        
        result = integration_manager.email_processor.analyze_email_patterns(g.user_id, days_back)
        
        if result['success']:
            return success_response(result['result'])
        else:
            return error_response(result['error'], "EMAIL_ANALYSIS_ERROR")
            
    except Exception as e:
        logger.error(f"Error analyzing email patterns: {str(e)}")
        return error_response(f"Email analysis error: {str(e)}", "INTERNAL_ERROR", 500)

# =====================================================================
# SYSTEM STATUS AND MONITORING
# =====================================================================

@enhanced_api_bp.route('/status', methods=['GET'])
@require_auth
def get_system_status():
    """
    Get comprehensive system status and processing statistics.
    """
    try:
        result = integration_manager.get_processing_statistics()
        
        if result['success']:
            return success_response(result['result'])
        else:
            return error_response(result['error'], "STATUS_ERROR")
            
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return error_response(f"Status error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring.
    """
    try:
        health_status = {
            'status': 'healthy',
            'version': '2.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'integration_manager': True,
                'entity_engine': True,
                'enhanced_processors': True,
                'database': True
            }
        }
        
        # Test database connection
        try:
            get_db_manager().get_session().execute('SELECT 1')
        except Exception as e:
            health_status['components']['database'] = False
            health_status['status'] = 'degraded'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# =====================================================================
# LEGACY COMPATIBILITY ENDPOINTS
# =====================================================================

@enhanced_api_bp.route('/legacy/task-extract', methods=['POST'])
@require_auth 
def legacy_task_extract():
    """
    Legacy task extraction endpoint for backward compatibility.
    """
    try:
        data = request.get_json()
        
        if not data or 'email_data' not in data:
            return error_response("Email data required", "MISSING_EMAIL_DATA")
        
        # Use legacy adapter
        legacy_extractor = integration_manager.get_legacy_task_extractor()
        result = legacy_extractor.extract_tasks_from_email(data['email_data'], g.user_id)
        
        return success_response(result, "Tasks extracted (legacy mode)")
        
    except Exception as e:
        logger.error(f"Error in legacy task extraction: {str(e)}")
        return error_response(f"Legacy extraction error: {str(e)}", "INTERNAL_ERROR", 500)

@enhanced_api_bp.route('/legacy/email-intelligence', methods=['POST'])
@require_auth
def legacy_email_intelligence():
    """
    Legacy email intelligence endpoint for backward compatibility.
    """
    try:
        data = request.get_json()
        
        if not data or 'email_data' not in data:
            return error_response("Email data required", "MISSING_EMAIL_DATA")
        
        # Use legacy adapter
        legacy_intelligence = integration_manager.get_legacy_email_intelligence()
        result = legacy_intelligence.process_email(data['email_data'], g.user_id)
        
        return success_response(result, "Email processed (legacy mode)")
        
    except Exception as e:
        logger.error(f"Error in legacy email intelligence: {str(e)}")
        return error_response(f"Legacy intelligence error: {str(e)}", "INTERNAL_ERROR", 500) 