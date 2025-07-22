# Real-Time API Endpoints - WebSocket and Live Processing
# These endpoints provide real-time intelligence and proactive insights

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session, g
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from functools import wraps
import json
import asyncio
import threading
import time

# Import the integration manager and real-time processor
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'chief_of_staff_ai'))

from processors.integration_manager import integration_manager
from processors.realtime_processor import realtime_processor
from chief_of_staff_ai.models.database import get_db_manager

logger = logging.getLogger(__name__)

# Create Blueprint
realtime_api_bp = Blueprint('realtime_api', __name__, url_prefix='/api/realtime')

# Global SocketIO instance (will be initialized by main app)
socketio = None

def init_socketio(app_socketio):
    """Initialize SocketIO instance"""
    global socketio
    socketio = app_socketio

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

def require_socketio_auth(f):
    """Decorator to require authentication for SocketIO events"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # SocketIO auth check - session should be available
        if not hasattr(session, 'get') or not session.get('user_email'):
            emit('error', {
                'message': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            })
            return
        
        return f(*args, **kwargs)
    return decorated_function

# =====================================================================
# REAL-TIME PROCESSING CONTROL
# =====================================================================

@realtime_api_bp.route('/start', methods=['POST'])
@require_auth
def start_realtime_processing():
    """
    Start real-time processing engine for the user.
    """
    try:
        data = request.get_json() or {}
        num_workers = data.get('workers', 3)
        
        # Start real-time processing
        result = integration_manager.start_realtime_processing(num_workers)
        
        if result['success']:
            # Register user for real-time insights
            user_insight_callback = create_user_insight_callback(g.user_id)
            integration_manager.register_insight_callback(g.user_id, user_insight_callback)
            
            return jsonify({
                'success': True,
                'message': f'Real-time processing started with {num_workers} workers',
                'user_id': g.user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting real-time processing: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@realtime_api_bp.route('/stop', methods=['POST'])
@require_auth
def stop_realtime_processing():
    """
    Stop real-time processing engine.
    """
    try:
        result = integration_manager.stop_realtime_processing()
        
        # Unregister user callbacks
        realtime_processor.unregister_insight_callback(g.user_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error stopping real-time processing: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@realtime_api_bp.route('/status', methods=['GET'])
@require_auth
def get_realtime_status():
    """
    Get real-time processing status.
    """
    try:
        status = {
            'success': True,
            'data': {
                'is_running': realtime_processor.running,
                'worker_count': len(realtime_processor.worker_threads),
                'queue_size': realtime_processor.processing_queue.qsize(),
                'user_contexts_cached': len(realtime_processor.user_contexts),
                'registered_callbacks': len(realtime_processor.insight_callbacks),
                'user_registered': g.user_id in realtime_processor.insight_callbacks
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting real-time status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================================
# LIVE DATA STREAMING ENDPOINTS
# =====================================================================

@realtime_api_bp.route('/stream/emails', methods=['POST'])
@require_auth
def stream_email_processing():
    """
    Stream email for real-time processing.
    """
    try:
        data = request.get_json()
        
        if not data or 'email_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Email data required'
            }), 400
        
        priority = data.get('priority', 5)
        
        # Queue email for real-time processing
        realtime_processor.process_new_email(data['email_data'], g.user_id, priority)
        
        return jsonify({
            'success': True,
            'message': 'Email queued for real-time processing',
            'user_id': g.user_id,
            'priority': priority,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error streaming email: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@realtime_api_bp.route('/stream/calendar', methods=['POST'])
@require_auth
def stream_calendar_event():
    """
    Stream calendar event for real-time processing.
    """
    try:
        data = request.get_json()
        
        if not data or 'event_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Calendar event data required'
            }), 400
        
        priority = data.get('priority', 5)
        
        # Queue calendar event for real-time processing
        realtime_processor.process_new_calendar_event(data['event_data'], g.user_id, priority)
        
        return jsonify({
            'success': True,
            'message': 'Calendar event queued for real-time processing',
            'user_id': g.user_id,
            'priority': priority,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error streaming calendar event: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@realtime_api_bp.route('/trigger/user-action', methods=['POST'])
@require_auth
def trigger_user_action():
    """
    Trigger user action for learning and feedback.
    """
    try:
        data = request.get_json()
        
        if not data or 'action_type' not in data:
            return jsonify({
                'success': False,
                'error': 'Action type required'
            }), 400
        
        action_type = data['action_type']
        action_data = data.get('action_data', {})
        
        # Process user action for learning
        realtime_processor.process_user_action(action_type, action_data, g.user_id)
        
        return jsonify({
            'success': True,
            'message': f'User action {action_type} processed',
            'user_id': g.user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing user action: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================================
# WEBSOCKET EVENT HANDLERS
# =====================================================================

def register_socketio_events(socketio_instance):
    """Register SocketIO event handlers"""
    global socketio
    socketio = socketio_instance
    
    @socketio.on('connect')
    @require_socketio_auth
    def handle_connect():
        """Handle client connection"""
        user_id = session.get('db_user_id')
        user_email = session.get('user_email')
        
        if user_id:
            # Join user-specific room
            join_room(f'user_{user_id}')
            
            logger.info(f"User {user_email} connected to real-time channel")
            
            emit('connected', {
                'message': 'Connected to real-time intelligence',
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Send current status
            emit('status_update', {
                'realtime_processing': realtime_processor.running,
                'user_registered': user_id in realtime_processor.insight_callbacks
            })
    
    @socketio.on('disconnect')
    @require_socketio_auth
    def handle_disconnect():
        """Handle client disconnection"""
        user_id = session.get('db_user_id')
        user_email = session.get('user_email')
        
        if user_id:
            leave_room(f'user_{user_id}')
            logger.info(f"User {user_email} disconnected from real-time channel")
    
    @socketio.on('subscribe_insights')
    @require_socketio_auth
    def handle_subscribe_insights():
        """Subscribe to real-time insights"""
        user_id = session.get('db_user_id')
        
        if user_id:
            # Register callback for this user
            user_insight_callback = create_user_insight_callback(user_id)
            integration_manager.register_insight_callback(user_id, user_insight_callback)
            
            emit('insight_subscription', {
                'subscribed': True,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    @socketio.on('unsubscribe_insights')
    @require_socketio_auth
    def handle_unsubscribe_insights():
        """Unsubscribe from real-time insights"""
        user_id = session.get('db_user_id')
        
        if user_id:
            realtime_processor.unregister_insight_callback(user_id)
            
            emit('insight_subscription', {
                'subscribed': False,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    @socketio.on('request_proactive_insights')
    @require_socketio_auth
    def handle_request_proactive_insights():
        """Request immediate proactive insights"""
        user_id = session.get('db_user_id')
        
        if user_id:
            try:
                # Generate proactive insights
                insights = integration_manager.entity_engine.generate_proactive_insights(user_id)
                
                # Send insights directly
                emit('proactive_insights', {
                    'insights': [
                        {
                            'type': insight.insight_type,
                            'title': insight.title,
                            'description': insight.description,
                            'priority': insight.priority,
                            'confidence': insight.confidence,
                            'created_at': insight.created_at.isoformat() if insight.created_at else None
                        }
                        for insight in insights
                    ],
                    'count': len(insights),
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error generating proactive insights: {str(e)}")
                emit('error', {
                    'message': f'Failed to generate insights: {str(e)}',
                    'code': 'INSIGHT_ERROR'
                })
    
    @socketio.on('feedback')
    @require_socketio_auth
    def handle_feedback(data):
        """Handle user feedback on insights"""
        user_id = session.get('db_user_id')
        
        if user_id and data:
            try:
                # Process feedback through real-time processor
                feedback_data = {
                    'insight_id': data.get('insight_id'),
                    'feedback': data.get('feedback'),
                    'additional_notes': data.get('notes')
                }
                
                realtime_processor.process_user_action('insight_feedback', feedback_data, user_id)
                
                emit('feedback_received', {
                    'insight_id': feedback_data['insight_id'],
                    'feedback': feedback_data['feedback'],
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error processing feedback: {str(e)}")
                emit('error', {
                    'message': f'Failed to process feedback: {str(e)}',
                    'code': 'FEEDBACK_ERROR'
                })

# =====================================================================
# INSIGHT DELIVERY SYSTEM
# =====================================================================

def create_user_insight_callback(user_id: int):
    """
    Create a callback function for delivering insights to a specific user via WebSocket.
    """
    def insight_callback(insights):
        """Callback function to deliver insights via WebSocket"""
        try:
            if not socketio:
                logger.warning("SocketIO not initialized, cannot deliver insights")
                return
            
            # Format insights for WebSocket delivery
            formatted_insights = []
            for insight in insights:
                formatted_insight = {
                    'id': insight.id if hasattr(insight, 'id') else None,
                    'type': insight.insight_type,
                    'title': insight.title,
                    'description': insight.description,
                    'priority': insight.priority,
                    'confidence': insight.confidence,
                    'related_entity_type': insight.related_entity_type,
                    'related_entity_id': insight.related_entity_id,
                    'status': insight.status,
                    'created_at': insight.created_at.isoformat() if insight.created_at else datetime.utcnow().isoformat(),
                    'expires_at': insight.expires_at.isoformat() if hasattr(insight, 'expires_at') and insight.expires_at else None
                }
                formatted_insights.append(formatted_insight)
            
            # Emit to user's room
            socketio.emit('new_insights', {
                'insights': formatted_insights,
                'count': len(formatted_insights),
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{user_id}')
            
            logger.info(f"Delivered {len(formatted_insights)} insights to user {user_id} via WebSocket")
            
        except Exception as e:
            logger.error(f"Error delivering insights via WebSocket: {str(e)}")
    
    return insight_callback

# =====================================================================
# REAL-TIME ANALYTICS ENDPOINTS
# =====================================================================

@realtime_api_bp.route('/analytics/live', methods=['GET'])
@require_auth
def get_live_analytics():
    """
    Get live analytics and processing statistics.
    """
    try:
        # Get processing statistics
        stats_result = integration_manager.get_processing_statistics()
        
        if not stats_result['success']:
            return jsonify({
                'success': False,
                'error': stats_result['error']
            }), 500
        
        stats = stats_result['result']
        
        # Add real-time specific metrics
        live_metrics = {
            'processing_stats': stats['processing_stats'],
            'processor_status': stats['processor_status'],
            'performance_metrics': stats['performance_metrics'],
            'realtime_metrics': {
                'queue_size': realtime_processor.processing_queue.qsize(),
                'cached_contexts': len(realtime_processor.user_contexts),
                'active_callbacks': len(realtime_processor.insight_callbacks),
                'worker_threads': len(realtime_processor.worker_threads),
                'is_running': realtime_processor.running
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': live_metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting live analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@realtime_api_bp.route('/queue/status', methods=['GET'])
@require_auth
def get_queue_status():
    """
    Get real-time processing queue status.
    """
    try:
        queue_status = {
            'queue_size': realtime_processor.processing_queue.qsize(),
            'is_running': realtime_processor.running,
            'worker_count': len(realtime_processor.worker_threads),
            'user_has_callback': g.user_id in realtime_processor.insight_callbacks,
            'user_context_cached': g.user_id in realtime_processor.user_contexts,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': queue_status
        })
        
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================================
# TESTING AND DEBUG ENDPOINTS
# =====================================================================

@realtime_api_bp.route('/test/insight', methods=['POST'])
@require_auth
def test_insight_delivery():
    """
    Test insight delivery system (for development/testing).
    """
    try:
        from models.enhanced_models import IntelligenceInsight
        
        # Create test insight
        test_insight = IntelligenceInsight(
            user_id=g.user_id,
            insight_type='test',
            title='Test Insight Delivery',
            description='This is a test insight to verify real-time delivery works.',
            priority='medium',
            confidence=1.0,
            status='new'
        )
        
        # Deliver test insight
        if g.user_id in realtime_processor.insight_callbacks:
            callback = realtime_processor.insight_callbacks[g.user_id]
            callback([test_insight])
            
            return jsonify({
                'success': True,
                'message': 'Test insight delivered',
                'user_id': g.user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No insight callback registered for user'
            }), 400
            
    except Exception as e:
        logger.error(f"Error testing insight delivery: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Export SocketIO event registration function
__all__ = ['realtime_api_bp', 'register_socketio_events', 'init_socketio'] 