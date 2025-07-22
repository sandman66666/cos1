"""
Authentication Middleware
========================

Middleware for handling authentication and authorization.
Extracted from main.py for better organization.
"""

import logging
from functools import wraps
from flask import session, jsonify
from chief_of_staff_ai.models.database import get_db_manager

logger = logging.getLogger(__name__)


def get_current_user():
    """
    Get current authenticated user with proper session isolation.
    
    Returns:
        dict: User information or None if not authenticated
    """
    if 'user_email' not in session or 'db_user_id' not in session:
        return None
    
    try:
        # Use the db_user_id from session for proper isolation
        user_id = session['db_user_id']
        
        # For this request context, we can trust the session's user_id
        # A full user object is not always needed here.
        # For simplicity, we'll return a lightweight object.
        current_user = {
            'id': user_id, 
            'email': session['user_email']
        }
        return current_user
        
    except Exception as e:
        logger.error(f"Error retrieving current user from session: {e}")
        session.clear()
        return None


def require_auth(f):
    """
    Decorator to require authentication for a route.
    
    Args:
        f: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_user_context(f):
    """
    Decorator that injects the current user into the function.
    
    Args:
        f: Function to wrap
        
    Returns:
        Wrapped function with user parameter
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        return f(user=user, *args, **kwargs)
    return decorated_function 