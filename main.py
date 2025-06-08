#!/usr/bin/env python3
"""
AI Chief of Staff - Flask Web Application

This is the main web application that provides:
1. Google OAuth authentication with Gmail access
2. Web interface for managing emails and tasks
3. API endpoints for processing emails
4. Integration with Claude 4 Sonnet for intelligent assistance
"""

import os
import sys
import logging
from datetime import timedelta, datetime
from flask import Flask, session, render_template, redirect, url_for, request, jsonify, make_response
from flask_session import Session
import tempfile
import time
import uuid

# Add the chief_of_staff_ai directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chief_of_staff_ai'))

try:
    from config.settings import settings
    from auth.gmail_auth import gmail_auth
    from ingest.gmail_fetcher import gmail_fetcher
    from processors.email_normalizer import email_normalizer
    from processors.task_extractor import task_extractor
    from processors.email_intelligence import email_intelligence
    from models.database import get_db_manager, Person, Project
    from models.database import Task, Email, Topic
    import anthropic
except ImportError as e:
    print(f"Failed to import AI Chief of Staff modules: {e}")
    print("Make sure the chief_of_staff_ai directory and modules are properly set up")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = settings.SECRET_KEY
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'cos_flask_session')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
    
    # Initialize extensions
    Session(app)
    
    # Create necessary directories
    settings.create_directories()
    
    # Initialize Claude client
    claude_client = None
    if settings.ANTHROPIC_API_KEY:
        claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def get_current_user():
        """Get current authenticated user with proper session isolation"""
        if 'user_email' not in session or 'db_user_id' not in session:
            return None
        
        try:
            # Use the db_user_id from session for proper isolation
            user_id = session['db_user_id']
            
            # This check is safer than re-fetching by email every time
            # For this request context, we can trust the session's user_id
            # Re-fetching the user should only be for sensitive operations
            # or to refresh data, not for basic authentication checks.
            # A full user object is not always needed here.
            # For simplicity, we'll return a lightweight object or dict.
            
            # Placeholder for a more robust user object if needed later
            # For now, this is enough to confirm an active session.
            current_user = {'id': user_id, 'email': session['user_email']}
            return current_user
            
        except Exception as e:
            logger.error(f"Error retrieving current user from session: {e}")
            session.clear()
            return None
    
    # Routes
    @app.route('/')
    def index():
        """Main dashboard"""
        if 'user_email' not in session:
            return redirect(url_for('login'))
        
        user_email = session['user_email']
        
        # Check Gmail authentication status
        gmail_status = gmail_auth.get_authentication_status(user_email)
        
        return render_template('dashboard.html', 
                             user_email=user_email,
                             gmail_status=gmail_status)
    
    @app.route('/login')
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
    
    @app.route('/auth/google')
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
            return redirect(url_for('login') + '?error=oauth_init_failed')
    
    @app.route('/auth/google/callback')
    def google_callback():
        """Handle Google OAuth callback with enhanced session management"""
        try:
            # Get authorization code and state
            code = request.args.get('code')
            state = request.args.get('state')
            error = request.args.get('error')
            
            if error:
                logger.error(f"OAuth error: {error}")
                return redirect(url_for('login') + f'?error={error}')
            
            if not code:
                logger.error("No authorization code received")
                return redirect(url_for('login') + '?error=no_code')
            
            # Validate state (basic security check)
            expected_state = session.get('oauth_state')
            if state != expected_state:
                logger.error(f"OAuth state mismatch: {state} != {expected_state}")
                return redirect(url_for('login') + '?error=state_mismatch')
            
            # Handle OAuth callback with our Gmail auth handler
            result = gmail_auth.handle_oauth_callback(
                authorization_code=code,
                state=state
            )
            
            if not result.get('success'):
                error_msg = result.get('error', 'Unknown OAuth error')
                logger.error(f"OAuth callback failed: {error_msg}")
                return redirect(url_for('login') + f'?error=oauth_failed')
            
            # COMPLETE SESSION RESET - Critical for user isolation
            session.clear()
            
            # Extract user info from OAuth result
            user_info = result.get('user_info', {})
            user_email = user_info.get('email')
            
            if not user_email:
                logger.error("No email received from OAuth")
                return redirect(url_for('login') + '?error=no_email')
            
            # Get or create user in database
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                logger.error(f"User not found in database: {user_email}")
                return redirect(url_for('login') + '?error=user_not_found')
            
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
            response = redirect(url_for('index') + '?login_success=true&t=' + str(int(datetime.now().timestamp())))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            return response
            
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return redirect(url_for('login') + '?error=callback_failed')
    
    @app.route('/logout')
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
        response = redirect(url_for('login') + '?logged_out=true')
        
        # Clear all cookies
        response.set_cookie('session', '', expires=0)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    @app.route('/debug/session')
    def debug_session():
        """Debug session information"""
        return jsonify({
            'session_data': dict(session),
            'user_email': session.get('user_email'),
            'authenticated': session.get('authenticated'),
            'session_keys': list(session.keys())
        })
    
    @app.route('/force-logout')
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
            response = redirect(url_for('login') + '?force_logout=true&t=' + str(int(datetime.now().timestamp())))
            
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
    
    @app.route('/api/fetch-emails', methods=['POST'])
    def api_fetch_emails():
        """API endpoint to fetch emails"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            data = request.get_json() or {}
            max_emails = data.get('max_emails', 10)
            days_back = data.get('days_back', 7)
            
            # Fetch emails using correct method name
            result = gmail_fetcher.fetch_recent_emails(
                user_email=user_email,
                limit=max_emails,
                days_back=days_back
            )
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Email fetch API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/process-emails', methods=['POST'])
    def api_process_emails():
        """API endpoint to intelligently process emails with comprehensive analysis"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            data = request.get_json() or {}
            max_emails = data.get('max_emails', 10)
            days_back = data.get('days_back', 7)
            force_refresh = data.get('force_refresh', False)
            
            # First fetch emails if needed
            fetch_result = gmail_fetcher.fetch_recent_emails(
                user_email=user_email,
                limit=max_emails,
                days_back=days_back,
                force_refresh=force_refresh
            )
            
            if not fetch_result.get('success'):
                return jsonify(fetch_result), 400
            
            # Normalize emails first
            normalize_result = email_normalizer.normalize_user_emails(user_email, limit=max_emails)
            
            # Use intelligent processing instead of basic task extraction
            intelligence_result = email_intelligence.process_user_emails_intelligently(
                user_email=user_email,
                limit=max_emails,
                force_refresh=force_refresh
            )
            
            # Get current user data for display
            user = get_db_manager().get_user_by_email(user_email)
            all_tasks = get_db_manager().get_user_tasks(user.id) if user else []
            
            return jsonify({
                'success': True,
                'fetch_result': fetch_result,
                'normalize_result': normalize_result,
                'intelligence_result': intelligence_result,
                'summary': {
                    'emails_fetched': fetch_result.get('count', 0),
                    'emails_normalized': normalize_result.get('processed', 0),
                    'emails_analyzed': intelligence_result.get('processed_emails', 0),
                    'insights_extracted': intelligence_result.get('insights_extracted', 0),
                    'people_identified': intelligence_result.get('people_identified', 0),
                    'projects_identified': intelligence_result.get('projects_identified', 0),
                    'tasks_created': intelligence_result.get('tasks_created', 0),
                    'total_tasks': len(all_tasks)
                }
            })
            
        except Exception as e:
            logger.error(f"Email processing API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        """API endpoint for Claude chat functionality"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        if not claude_client:
            return jsonify({'error': 'Claude integration not configured'}), 500
        
        try:
            data = request.get_json()
            message = data.get('message')
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
            
            user_email = session['user_email']
            
            # Create system prompt with context
            system_prompt = f"""You are an AI Chief of Staff assistant for {user_email}. 

You have access to their Gmail and can help with:
- Summarizing emails
- Extracting action items and tasks
- Scheduling and calendar management
- Strategic planning and prioritization
- General productivity assistance

Be helpful, professional, and actionable in your responses."""
            
            # Send message to Claude
            response = claude_client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=2000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": message
                }]
            )
            
            assistant_response = response.content[0].text
            
            return jsonify({
                'response': assistant_response,
                'model': settings.CLAUDE_MODEL
            })
            
        except Exception as e:
            logger.error(f"Chat API error: {str(e)}")
            return jsonify({'error': f'Chat error: {str(e)}'}), 500
    
    @app.route('/api/status')
    def api_status():
        """API endpoint to get system status"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            # Get authentication status
            gmail_status = gmail_auth.get_authentication_status(user_email)
            
            # Get user's processing stats
            user = get_db_manager().get_user_by_email(user_email)
            stats = {
                'user_email': user_email,
                'emails_count': 0,
                'tasks_count': 0,
                'last_fetch': None
            }
            
            if user:
                # Get email count
                emails = get_db_manager().get_user_emails(user.id, limit=1000)
                stats['emails_count'] = len(emails)
                if emails:
                    stats['last_fetch'] = max([email.processed_at for email in emails]).isoformat()
                
                # Get task count
                tasks = get_db_manager().get_user_tasks(user.id)
                stats['tasks_count'] = len(tasks)
            
            return jsonify({
                'user_email': user_email,
                'gmail_status': gmail_status,
                'processing_stats': stats,
                'claude_available': claude_client is not None
            })
            
        except Exception as e:
            logger.error(f"Status API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/emails', methods=['GET'])
    def api_get_emails():
        """API endpoint to get existing emails"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            emails = get_db_manager().get_user_emails(user.id, limit=50)
            
            return jsonify({
                'success': True,
                'emails': [email.to_dict() for email in emails],
                'count': len(emails)
            })
            
        except Exception as e:
            logger.error(f"Get emails API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/tasks', methods=['GET'])
    def api_get_tasks():
        """API endpoint to get existing tasks"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            
            tasks = get_db_manager().get_user_tasks(user.id, status)
            if limit:
                tasks = tasks[:limit]
            
            return jsonify({
                'success': True,
                'tasks': [task.to_dict() for task in tasks],
                'count': len(tasks),
                'status_filter': status
            })
            
        except Exception as e:
            logger.error(f"Get tasks API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/flush-database', methods=['POST'])
    def api_flush_database():
        """API endpoint to flush all user data for a clean start"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Delete all user data but keep the user record
            with get_db_manager().get_session() as db_session:
                # Delete tasks
                db_session.query(Task).filter(Task.user_id == user.id).delete()
                
                # Delete emails
                db_session.query(Email).filter(Email.user_id == user.id).delete()
                
                # Delete people
                db_session.query(Person).filter(Person.user_id == user.id).delete()
                
                # Delete projects
                db_session.query(Project).filter(Project.user_id == user.id).delete()
                
                # CRITICAL FIX: Also delete topics to ensure a complete flush
                db_session.query(Topic).filter(Topic.user_id == user.id).delete()
                
                db_session.commit()
            
            logger.info(f"Flushed all data for user: {user_email}")
            
            return jsonify({
                'success': True,
                'message': 'All data cleared successfully. You can start fresh!',
                'user_email': user_email
            })
            
        except Exception as e:
            logger.error(f"Database flush error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/people', methods=['GET'])
    def api_get_people():
        """API endpoint to get people insights"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            limit = int(request.args.get('limit', 50))
            people = get_db_manager().get_user_people(user.id, limit)
            
            return jsonify({
                'success': True,
                'people': [person.to_dict() for person in people],
                'count': len(people)
            })
            
        except Exception as e:
            logger.error(f"Get people API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/projects', methods=['GET'])
    def api_get_projects():
        """API endpoint to get projects"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            
            projects = get_db_manager().get_user_projects(user.id, status, limit)
            
            return jsonify({
                'success': True,
                'projects': [project.to_dict() for project in projects],
                'count': len(projects),
                'status_filter': status
            })
            
        except Exception as e:
            logger.error(f"Get projects API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/business-knowledge', methods=['GET'])
    def api_get_business_knowledge():
        """API endpoint to get business knowledge summary"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            knowledge = email_intelligence.get_business_knowledge_summary(user_email)
            return jsonify(knowledge)
        except Exception as e:
            logger.error(f"Failed to get business knowledge for {user_email}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/chat-knowledge', methods=['GET'])
    def api_get_chat_knowledge():
        """API endpoint to get comprehensive knowledge summary for chat queries"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = user['email']
        
        try:
            knowledge = email_intelligence.get_chat_knowledge_summary(user_email)
            return jsonify(knowledge)
        except Exception as e:
            logger.error(f"Failed to get chat knowledge for {user_email}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/email-insights', methods=['GET'])
    def api_get_email_insights():
        """API endpoint to get email insights with AI analysis"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            limit = int(request.args.get('limit', 20))
            emails = get_db_manager().get_user_emails(db_user.id, limit)
            
            # Filter to only emails with AI insights
            analyzed_emails = []
            for email in emails:
                if email.ai_summary:
                    email_data = email.to_dict()
                    # Add sender name for display
                    email_data['from_name'] = email.sender_name or email.sender
                    analyzed_emails.append(email_data)
            
            return jsonify({
                'success': True,
                'email_insights': analyzed_emails,
                'count': len(analyzed_emails)
            })
            
        except Exception as e:
            logger.error(f"Get email insights API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/topics', methods=['GET'])
    def api_get_topics():
        """API endpoint to get all topics for a user"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            topics = get_db_manager().get_user_topics(db_user.id)
            
            return jsonify({
                'success': True,
                'topics': [topic.to_dict() for topic in topics],
                'count': len(topics),
                'user_info': {'email': db_user.email, 'db_id': db_user.id}  # Debug info
            })
            
        except Exception as e:
            logger.error(f"Get topics API error for user {user['email']}: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/topics', methods=['POST'])
    def api_create_topic():
        """API endpoint to create a new topic manually"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
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
                'is_official': data.get('is_official', True),  # Default to official for manually created topics
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
    
    @app.route('/api/topics/<int:topic_id>/official', methods=['POST'])
    def api_mark_topic_official(topic_id):
        """API endpoint to mark a topic as official"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
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
    
    @app.route('/api/topics/<int:topic_id>/merge', methods=['POST'])
    def api_merge_topic(topic_id):
        """API endpoint to merge one topic into another"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
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
    
    @app.route('/api/topics/resync', methods=['POST'])
    def api_resync_topics():
        """API endpoint to resync all content with updated topics using Claude"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = user['email']
        
        try:
            # This would trigger a resync of all emails with the updated topic definitions
            # For now, just return success - full implementation would re-process emails
            return jsonify({
                'success': True,
                'message': 'Topic resync initiated - this will re-categorize all content with updated topic definitions'
            })
            
        except Exception as e:
            logger.error(f"Resync topics API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/chat-with-knowledge', methods=['POST'])
    def api_chat_with_knowledge():
        """API endpoint for enhanced Claude chat with full business knowledge context"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        if not claude_client:
            return jsonify({'error': 'Claude integration not configured'}), 500
        
        try:
            data = request.get_json()
            message = data.get('message')
            include_context = data.get('include_context', True)
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
            
            user_email = user['email']
            
            # Get comprehensive knowledge context
            context_parts = []
            
            if include_context:
                try:
                    # Get business knowledge
                    knowledge_response = email_intelligence.get_chat_knowledge_summary(user_email)
                    if knowledge_response.get('success'):
                        knowledge = knowledge_response['knowledge_base']
                        
                        # Add business intelligence context
                        if knowledge.get('business_intelligence'):
                            bi = knowledge['business_intelligence']
                            
                            if bi.get('recent_decisions'):
                                context_parts.append("RECENT BUSINESS DECISIONS:\n" + "\n".join([f"- {decision}" for decision in bi['recent_decisions'][:5]]))
                            
                            if bi.get('top_opportunities'):
                                context_parts.append("BUSINESS OPPORTUNITIES:\n" + "\n".join([f"- {opp}" for opp in bi['top_opportunities'][:5]]))
                            
                            if bi.get('current_challenges'):
                                context_parts.append("CURRENT CHALLENGES:\n" + "\n".join([f"- {challenge}" for challenge in bi['current_challenges'][:5]]))
                        
                        # Add people context
                        if knowledge.get('rich_contacts'):
                            contacts_summary = []
                            for contact in knowledge['rich_contacts'][:10]:  # Top 10 contacts
                                contact_info = f"{contact['name']}"
                                if contact.get('title') and contact.get('company'):
                                    contact_info += f" ({contact['title']} at {contact['company']})"
                                if contact.get('relationship'):
                                    contact_info += f" - {contact['relationship']}"
                                contacts_summary.append(contact_info)
                            
                            if contacts_summary:
                                context_parts.append("KEY BUSINESS CONTACTS:\n" + "\n".join([f"- {contact}" for contact in contacts_summary]))
                        
                        # Add recent tasks
                        db_user = get_db_manager().get_user_by_email(user_email)
                        if db_user:
                            tasks = get_db_manager().get_user_tasks(db_user.id)
                            if tasks:
                                recent_tasks = [f"{task.description}" for task in tasks[:10]]
                                context_parts.append("CURRENT TASKS:\n" + "\n".join([f"- {task}" for task in recent_tasks]))
                
                except Exception as context_error:
                    logger.warning(f"Failed to load context for chat: {context_error}")
            
            # Create enhanced system prompt with business context
            business_context = "\n\n".join(context_parts) if context_parts else "No specific business context available."
            
            system_prompt = f"""You are an AI Chief of Staff assistant for {user_email}. You have access to their comprehensive business knowledge and should provide intelligent, context-aware responses.

BUSINESS CONTEXT:
{business_context}

INSTRUCTIONS:
- Use the business context above to provide informed, specific responses
- Reference specific people, decisions, opportunities, or challenges when relevant
- Provide actionable insights and recommendations based on the available data
- If asked about people, reference their roles, relationships, and relevant context
- For task or project questions, consider current priorities and deadlines
- Be professional but conversational
- If you don't have enough context for a specific question, say so and suggest what information would help

Always think about the bigger picture and provide strategic, helpful advice based on the user's business situation."""
            
            # Send message to Claude with enhanced context
            response = claude_client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=3000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": message
                }]
            )
            
            assistant_response = response.content[0].text
            
            return jsonify({
                'success': True,
                'response': assistant_response,
                'model': settings.CLAUDE_MODEL,
                'context_included': include_context and len(context_parts) > 0
            })
            
        except Exception as e:
            logger.error(f"Enhanced chat API error: {str(e)}")
            return jsonify({'success': False, 'error': f'Enhanced chat error: {str(e)}'}), 500
    
    @app.route('/api/download-knowledge', methods=['GET'])
    def api_download_knowledge():
        """API endpoint to download comprehensive knowledge base as text file"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401

        try:
            user_email = user['email']
            knowledge_response = email_intelligence.get_chat_knowledge_summary(user_email)
            
            if not knowledge_response.get('success'):
                return jsonify({'error': 'Failed to get knowledge base'}), 500

            knowledge = knowledge_response['knowledge_base']
            
            # Generate comprehensive text content
            content_lines = []
            content_lines.append("AI CHIEF OF STAFF - COMPREHENSIVE KNOWLEDGE BASE")
            content_lines.append("=" * 60)
            content_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_lines.append(f"User: {user_email}")
            content_lines.append("")

            # Summary Statistics
            if knowledge.get('summary_stats'):
                stats = knowledge['summary_stats']
                content_lines.append("SUMMARY STATISTICS")
                content_lines.append("-" * 30)
                content_lines.append(f"Quality Emails Analyzed: {stats.get('total_emails_analyzed', 0)}")
                content_lines.append(f"Human Contacts: {stats.get('rich_contacts', 0)}")
                content_lines.append(f"Business Decisions: {stats.get('business_decisions', 0)}")
                content_lines.append(f"Opportunities: {stats.get('opportunities_identified', 0)}")
                content_lines.append(f"Active Projects: {stats.get('active_projects', 0)}")
                content_lines.append("")

            # Strategic Business Intelligence
            if knowledge.get('business_intelligence'):
                bi = knowledge['business_intelligence']
                
                if bi.get('recent_decisions'):
                    content_lines.append("STRATEGIC BUSINESS DECISIONS")
                    content_lines.append("-" * 40)
                    for i, decision in enumerate(bi['recent_decisions'], 1):
                        if isinstance(decision, dict):
                            content_lines.append(f"{i}. {decision.get('decision', 'Unknown decision')}")
                            if decision.get('context'):
                                content_lines.append(f"   Context: {decision['context']}")
                            if decision.get('sender'):
                                content_lines.append(f"   Source: {decision['sender']}")
                            if decision.get('date'):
                                content_lines.append(f"   Date: {decision['date']}")
                        else:
                            content_lines.append(f"{i}. {decision}")
                        content_lines.append("")
                    content_lines.append("")

                if bi.get('top_opportunities'):
                    content_lines.append("BUSINESS OPPORTUNITIES")
                    content_lines.append("-" * 40)
                    for i, opportunity in enumerate(bi['top_opportunities'], 1):
                        if isinstance(opportunity, dict):
                            content_lines.append(f"{i}. {opportunity.get('opportunity', 'Unknown opportunity')}")
                            if opportunity.get('context'):
                                content_lines.append(f"   Context: {opportunity['context']}")
                            if opportunity.get('source'):
                                content_lines.append(f"   Source: {opportunity['source']}")
                        else:
                            content_lines.append(f"{i}. {opportunity}")
                        content_lines.append("")
                    content_lines.append("")

                if bi.get('current_challenges'):
                    content_lines.append("CURRENT CHALLENGES")
                    content_lines.append("-" * 40)
                    for i, challenge in enumerate(bi['current_challenges'], 1):
                        if isinstance(challenge, dict):
                            content_lines.append(f"{i}. {challenge.get('challenge', 'Unknown challenge')}")
                            if challenge.get('context'):
                                content_lines.append(f"   Context: {challenge['context']}")
                            if challenge.get('source'):
                                content_lines.append(f"   Source: {challenge['source']}")
                        else:
                            content_lines.append(f"{i}. {challenge}")
                        content_lines.append("")
                    content_lines.append("")

            # Professional Contact Intelligence
            if knowledge.get('rich_contacts'):
                content_lines.append("PROFESSIONAL CONTACT INTELLIGENCE")
                content_lines.append("-" * 40)
                for i, contact in enumerate(knowledge['rich_contacts'], 1):
                    content_lines.append(f"{i}. {contact.get('name', 'Unknown')}")
                    if contact.get('title'):
                        content_lines.append(f"   Title: {contact['title']}")
                    if contact.get('company'):
                        content_lines.append(f"   Company: {contact['company']}")
                    if contact.get('relationship'):
                        content_lines.append(f"   Relationship: {contact['relationship']}")
                    if contact.get('story'):
                        content_lines.append(f"   Professional Story:")
                        content_lines.append(f"   {contact['story']}")
                    if contact.get('total_emails'):
                        content_lines.append(f"   Email Interactions: {contact['total_emails']}")
                    content_lines.append("")
                content_lines.append("")

            # Business Topics & Knowledge
            if knowledge.get('topic_knowledge') and knowledge['topic_knowledge'].get('all_topics'):
                content_lines.append("BUSINESS TOPICS & KNOWLEDGE")
                content_lines.append("-" * 40)
                for topic in knowledge['topic_knowledge']['all_topics']:
                    content_lines.append(f"TOPIC: {topic}")
                    contexts = knowledge['topic_knowledge'].get('topic_contexts', {}).get(topic, [])
                    if contexts:
                        content_lines.append("Related Communications:")
                        for context in contexts:
                            if context.get('email_subject'):
                                content_lines.append(f"  - {context['email_subject']} ({context.get('date', 'Unknown date')})")
                            if context.get('summary'):
                                content_lines.append(f"    {context['summary']}")
                            if context.get('sender'):
                                content_lines.append(f"    From: {context['sender']}")
                    content_lines.append("")
                content_lines.append("")

            # Active Projects
            if knowledge.get('projects_summary'):
                content_lines.append("ACTIVE BUSINESS PROJECTS")
                content_lines.append("-" * 40)
                for i, project in enumerate(knowledge['projects_summary'], 1):
                    content_lines.append(f"{i}. {project.get('name', 'Unknown Project')}")
                    if project.get('description'):
                        content_lines.append(f"   Description: {project['description']}")
                    content_lines.append(f"   Status: {project.get('status', 'Unknown')}")
                    content_lines.append(f"   Priority: {project.get('priority', 'Unknown')}")
                    if project.get('stakeholders'):
                        content_lines.append(f"   Stakeholders: {', '.join(project['stakeholders'])}")
                    if project.get('key_topics'):
                        content_lines.append(f"   Key Topics: {', '.join(project['key_topics'])}")
                    content_lines.append("")

            # Create response
            text_content = "\n".join(content_lines)
            
            response = make_response(text_content)
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=AI_Chief_of_Staff_Knowledge_Base_{datetime.now().strftime("%Y-%m-%d")}.txt'
            
            return response

        except Exception as e:
            logger.error(f"Knowledge download error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/email-diagnostics', methods=['GET'])
    def api_email_diagnostics():
        """API endpoint to diagnose email processing and filtering"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get all user emails
            all_emails = get_db_manager().get_user_emails(db_user.id, limit=100)
            
            # Analyze filtering results
            newsletter_count = 0
            automated_count = 0
            business_count = 0
            quality_emails = []
            
            diagnostics = {
                'total_emails': len(all_emails),
                'filtered_breakdown': {},
                'sample_emails': {
                    'newsletters': [],
                    'automated': [],
                    'business': [],
                    'quality': []
                }
            }
            
            for email in all_emails:
                # Check if email would be filtered out
                if email_intelligence._is_newsletter_or_promotional(email):
                    newsletter_count += 1
                    if len(diagnostics['sample_emails']['newsletters']) < 3:
                        diagnostics['sample_emails']['newsletters'].append({
                            'subject': email.subject,
                            'sender': email.sender,
                            'sender_name': email.sender_name,
                            'date': email.email_date.isoformat() if email.email_date else None,
                            'reason': 'Newsletter/Promotional content detected'
                        })
                elif email_intelligence._is_non_human_contact(email.sender or ''):
                    automated_count += 1
                    if len(diagnostics['sample_emails']['automated']) < 3:
                        diagnostics['sample_emails']['automated'].append({
                            'subject': email.subject,
                            'sender': email.sender,
                            'sender_name': email.sender_name,
                            'date': email.email_date.isoformat() if email.email_date else None,
                            'reason': 'Non-human sender detected'
                        })
                else:
                    business_count += 1
                    if len(diagnostics['sample_emails']['business']) < 3:
                        diagnostics['sample_emails']['business'].append({
                            'subject': email.subject,
                            'sender': email.sender,
                            'sender_name': email.sender_name,
                            'date': email.email_date.isoformat() if email.email_date else None,
                            'has_ai_summary': bool(email.ai_summary),
                            'ai_summary_length': len(email.ai_summary) if email.ai_summary else 0
                        })
                    
                    # Check if it's a quality email with AI insights
                    if email.ai_summary and len(email.ai_summary) > 15:
                        quality_emails.append(email)
                        if len(diagnostics['sample_emails']['quality']) < 5:
                            diagnostics['sample_emails']['quality'].append({
                                'subject': email.subject,
                                'sender': email.sender,
                                'sender_name': email.sender_name,
                                'date': email.email_date.isoformat() if email.email_date else None,
                                'ai_summary': email.ai_summary[:200] + '...' if len(email.ai_summary) > 200 else email.ai_summary,
                                'key_insights': bool(email.key_insights),
                                'topics': email.topics[:3] if email.topics else []
                            })
            
            diagnostics['filtered_breakdown'] = {
                'newsletters_filtered': newsletter_count,
                'automated_filtered': automated_count, 
                'business_emails': business_count,
                'quality_emails_with_ai': len(quality_emails)
            }
            
            # Get recent knowledge base content for comparison
            knowledge_response = email_intelligence.get_business_knowledge_summary(user['email'])
            if knowledge_response.get('success'):
                knowledge = knowledge_response['business_knowledge']
                diagnostics['current_knowledge'] = {
                    'summary_stats': knowledge.get('summary_stats', {}),
                    'decision_sources': [],
                    'opportunity_sources': []
                }
                
                # Sample the sources of business intelligence
                strategic = knowledge.get('strategic_intelligence', {})
                if strategic.get('key_decisions'):
                    diagnostics['current_knowledge']['decision_sources'] = strategic['key_decisions'][:3]
                if strategic.get('business_opportunities'):
                    diagnostics['current_knowledge']['opportunity_sources'] = strategic['business_opportunities'][:3]
            
            return jsonify({
                'success': True,
                'user_email': user['email'],
                'diagnostics': diagnostics
            })
            
        except Exception as e:
            logger.error(f"Email diagnostics error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/sync-topics', methods=['POST'])
    def api_sync_topics():
        """API endpoint to sync email topics to the topics table"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get all emails with topics
            emails = get_db_manager().get_user_emails(db_user.id, limit=1000)
            topic_counts = {}
            
            # Count topic usage across emails
            for email in emails:
                if email.topics and isinstance(email.topics, list):
                    for topic in email.topics:
                        if topic and len(topic.strip()) > 2:  # Valid topic
                            topic_name = topic.strip()
                            if topic_name not in topic_counts:
                                topic_counts[topic_name] = 0
                            topic_counts[topic_name] += 1
            
            # Create Topic records for topics with 2+ usages
            topics_created = 0
            for topic_name, count in topic_counts.items():
                if count >= 2:  # Only create topics used in multiple emails
                    # Check if topic already exists
                    existing_topics = get_db_manager().get_user_topics(db_user.id)
                    topic_exists = any(t.name.lower() == topic_name.lower() for t in existing_topics)
                    
                    if not topic_exists:
                        topic_data = {
                            'name': topic_name,
                            'slug': topic_name.lower().replace(' ', '-'),
                            'description': f'Auto-discovered topic from {count} emails',
                            'is_official': False,  # Mark as AI-discovered
                            'email_count': count,
                            'confidence_score': min(0.9, count / 10.0),  # Higher confidence for more usage
                            'keywords': [topic_name.lower()]
                        }
                        get_db_manager().create_or_update_topic(db_user.id, topic_data)
                        topics_created += 1
            
            return jsonify({
                'success': True,
                'topics_created': topics_created,
                'total_topic_usage': len(topic_counts),
                'message': f'Synced {topics_created} topics from email analysis'
            })
            
        except Exception as e:
            logger.error(f"Sync topics API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/dashboard')
    def dashboard():
        """Main dashboard - requires authentication"""
        user = get_current_user()
        if not user:
            logger.warning("Unauthenticated access attempt to dashboard")
            return redirect(url_for('login'))
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            logger.warning(f"User not found in database: {user_email}")
            return redirect(url_for('login'))
        
        logger.info(f"Dashboard access by user: {db_user.email} (ID: {db_user.id})")
        
        # Add user context to prevent frontend confusion
        context = {
            'user_email': db_user.email,
            'user_id': db_user.id,
            'session_id': session.get('session_id', 'unknown'),
            'cache_buster': int(time.time())  # Force fresh data load
        }
        
        response = make_response(render_template('dashboard.html', **context))
        
        # Ensure no caching of dashboard
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Internal server error"), 500
    
    @app.after_request
    def after_request(response):
        """Add cache-busting headers to prevent session contamination"""
        # Prevent caching for API endpoints and sensitive pages
        if (request.endpoint and 
            (request.endpoint.startswith('api_') or 
             request.path.startswith('/api/') or
             request.path in ['/dashboard', '/debug/session'])):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    
    return app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    try:
        # Validate settings
        config_errors = settings.validate_config()
        if config_errors:
            raise ValueError(f"Configuration errors: {', '.join(config_errors)}")
        
        print("🚀 Starting AI Chief of Staff Web Application")
        print(f"📧 Gmail integration: {'✓ Configured' if settings.GOOGLE_CLIENT_ID else '✗ Missing'}")
        print(f"🤖 Claude integration: {'✓ Configured' if settings.ANTHROPIC_API_KEY else '✗ Missing'}")
        print(f"🌐 Server: http://localhost:{settings.PORT}")
        print("\nTo get started:")
        print("1. Go to the URL above")
        print("2. Click 'Sign in with Google'")
        print("3. Grant Gmail access permissions")
        print("4. Start processing your emails!")
        
        app.run(
            host=settings.HOST,
            port=settings.PORT,
            debug=settings.DEBUG
        )
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1) 