"""
Authentication Routes
====================

Routes for Google OAuth authentication, login, logout, and session management.
Extracted from main.py for better organization.
"""

import os
import uuid
import time
import logging
from datetime import datetime
from flask import Blueprint, session, render_template, redirect, url_for, request, jsonify, make_response

# Import necessary modules
from auth.gmail_auth import gmail_auth
from models.database import get_db_manager
from ..middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='')


@auth_bp.route('/')
def index():
    """Main index route"""
    user = get_current_user()
    if not user:
        return redirect('/auth/google')
    
    # Redirect to home page
    return redirect('/home')


@auth_bp.route('/home')
def home():
    """Home page route"""
    user = get_current_user()
    if not user:
        return redirect('/auth/google')
    
    return render_template('home.html', 
                           user_email=user['email'],
                           user_id=user.get('id'),
                           session_id=session.get('session_id'),
                           cache_buster=int(time.time()))


@auth_bp.route('/login')
def login():
    """Login page with Google OAuth"""
    # Check for logout/switching parameters
    logged_out = request.args.get('logged_out') == 'true'
    force_logout = request.args.get('force_logout') == 'true'
    
    context = {
        'logged_out': logged_out,
        'force_logout': force_logout,
        'switching_users': logged_out or force_logout
    }
    
    return render_template('login.html', **context)


@auth_bp.route('/auth/google')
def google_auth():
    """Initiate Google OAuth flow"""
    try:
        # Generate unique state for security
        state = f"cos_{session.get('csrf_token', 'temp')}"
        
        # Get authorization URL from our Gmail auth handler
        auth_url, state = gmail_auth.get_authorization_url(
            user_id=session.get('temp_user_id', 'anonymous'),
            state=state
        )
        
        # Store state in session for validation
        session['oauth_state'] = state
        
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Failed to initiate Google OAuth: {str(e)}")
        return redirect(url_for('auth.login') + '?error=oauth_init_failed')


@auth_bp.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback with enhanced session management"""
    try:
        # Get authorization code and state
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return redirect(url_for('auth.login') + f'?error={error}')
        
        if not code:
            logger.error("No authorization code received")
            return redirect(url_for('auth.login') + '?error=no_code')
        
        # Validate state (basic security check)
        expected_state = session.get('oauth_state')
        if state != expected_state:
            logger.error(f"OAuth state mismatch: {state} != {expected_state}")
            return redirect(url_for('auth.login') + '?error=state_mismatch')
        
        # Handle OAuth callback with our Gmail auth handler
        result = gmail_auth.handle_oauth_callback(
            authorization_code=code,
            state=state
        )
        
        if not result.get('success'):
            error_msg = result.get('error', 'Unknown OAuth error')
            logger.error(f"OAuth callback failed: {error_msg}")
            return redirect(url_for('auth.login') + f'?error=oauth_failed')
        
        # COMPLETE SESSION RESET - Critical for user isolation
        session.clear()
        
        # Extract user info from OAuth result
        user_info = result.get('user_info', {})
        user_email = user_info.get('email')
        
        if not user_email:
            logger.error("No email received from OAuth")
            return redirect(url_for('auth.login') + '?error=no_email')
        
        # Get or create user in database
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            logger.error(f"User not found in database: {user_email}")
            return redirect(url_for('auth.login') + '?error=user_not_found')
        
        # Set new session data with unique session ID
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        session['user_email'] = user_email
        session['user_name'] = user_info.get('name')
        session['google_id'] = user_info.get('id')  # Google ID
        session['authenticated'] = True
        session['db_user_id'] = user.id  # Database ID for queries - CRITICAL
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True
        
        logger.info(f"User authenticated successfully: {user_email} (DB ID: {user.id}, Session: {session_id})")
        
        # Create response with cache busting
        response = redirect(url_for('auth.index') + '?login_success=true&t=' + str(int(datetime.now().timestamp())))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        return response
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return redirect(url_for('auth.login') + '?error=callback_failed')


@auth_bp.route('/logout')
def logout():
    """Logout and clear session completely"""
    user_email = session.get('user_email')
    
    # Complete session cleanup
    session.clear()
    
    # Clear any persistent session files
    try:
        import shutil
        import tempfile
        session_dir = os.path.join(tempfile.gettempdir(), 'cos_flask_session')
        if os.path.exists(session_dir):
            # Clear old session files
            for filename in os.listdir(session_dir):
                if filename.startswith('flask_session_'):
                    try:
                        os.remove(os.path.join(session_dir, filename))
                    except:
                        pass
    except Exception as e:
        logger.warning(f"Could not clear session files: {e}")
    
    logger.info(f"User logged out completely: {user_email}")
    
    # Redirect to login with cache-busting parameter
    response = redirect(url_for('auth.login') + '?logged_out=true')
    
    # Clear all cookies
    response.set_cookie('session', '', expires=0)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@auth_bp.route('/force-logout')
def force_logout():
    """Force complete logout and session reset - use when switching users"""
    try:
        # Clear current session
        user_email = session.get('user_email', 'unknown')
        session.clear()
        
        # Clear all session files
        import tempfile
        session_dir = os.path.join(tempfile.gettempdir(), 'cos_flask_session')
        if os.path.exists(session_dir):
            for filename in os.listdir(session_dir):
                if filename.startswith('flask_session_'):
                    try:
                        os.remove(os.path.join(session_dir, filename))
                        logger.info(f"Cleared session file: {filename}")
                    except Exception as e:
                        logger.warning(f"Could not clear session file {filename}: {e}")
        
        logger.info(f"Force logout completed for: {user_email}")
        
        # Create response with aggressive cache clearing
        response = redirect(url_for('auth.login') + '?force_logout=true&t=' + str(int(datetime.now().timestamp())))
        
        # Clear all possible cookies and cache
        response.set_cookie('session', '', expires=0, path='/')
        response.set_cookie('flask-session', '', expires=0, path='/')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Clear-Site-Data'] = '"cache", "cookies", "storage"'
        
        return response
        
    except Exception as e:
        logger.error(f"Force logout error: {e}")
        return jsonify({'error': 'Force logout failed', 'details': str(e)}), 500


@auth_bp.route('/debug/session')
def debug_session():
    """Debug session information"""
    return jsonify({
        'session_data': dict(session),
        'user_email': session.get('user_email'),
        'authenticated': session.get('authenticated'),
        'session_keys': list(session.keys())
    })


# Additional page routes (can be moved to a separate blueprint later)
@auth_bp.route('/tasks')
def tasks():
    """Tasks page route"""
    user = get_current_user()
    if not user:
        return redirect('/auth/google')
    
    return render_template('tasks.html', 
                           user_email=user['email'],
                           user_id=user.get('id'),
                           session_id=session.get('session_id'),
                           cache_buster=int(time.time()))


@auth_bp.route('/people')
def people_page():
    """People management page"""
    user = get_current_user()
    if not user:
        return redirect('/login')
    return render_template('people.html')


@auth_bp.route('/knowledge')
def knowledge_page():
    """Knowledge management page"""
    user = get_current_user()
    if not user:
        return redirect('/login')
    return render_template('knowledge.html')


@auth_bp.route('/calendar')
def calendar_page():
    """Calendar management page"""
    user_email = session.get('user_email')
    
    if not user_email:
        return redirect(url_for('auth.login'))
    
    return render_template('calendar.html')


@auth_bp.route('/settings')
def settings_page():
    """Settings page for configuring email sync and other preferences"""
    user = get_current_user()
    if not user:
        return redirect('/login')
    return render_template('settings.html')


@auth_bp.route('/dashboard')
def dashboard():
    """Legacy dashboard route - redirect to home"""
    return redirect('/home') 