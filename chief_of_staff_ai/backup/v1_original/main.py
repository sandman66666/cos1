# Main Flask application for AI Chief of Staff

import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import anthropic

from config.settings import settings
from auth.gmail_auth import gmail_auth
from ingest.gmail_fetcher import gmail_fetcher
from processors.email_normalizer import email_normalizer
from processors.task_extractor import task_extractor
from models.database import get_db_manager, Email, Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'

# Initialize Claude client for chat
claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

@app.route('/')
def index():
    """Main dashboard route"""
    user_email = session.get('user_email')
    
    if not user_email:
        return render_template('login.html')
    
    try:
        # Get user information
        user_info = gmail_auth.get_user_by_email(user_email)
        if not user_info:
            session.clear()
            return render_template('login.html')
        
        # Get user statistics
        user = get_db_manager().get_user_by_email(user_email)
        user_stats = {
            'total_emails': 0,
            'total_tasks': 0,
            'pending_tasks': 0,
            'completed_tasks': 0
        }
        
        if user:
            with get_db_manager().get_session() as db_session:
                user_stats['total_emails'] = db_session.query(Email).filter(
                    Email.user_id == user.id
                ).count()
                
                user_stats['total_tasks'] = db_session.query(Task).filter(
                    Task.user_id == user.id
                ).count()
                
                user_stats['pending_tasks'] = db_session.query(Task).filter(
                    Task.user_id == user.id,
                    Task.status == 'pending'
                ).count()
                
                user_stats['completed_tasks'] = db_session.query(Task).filter(
                    Task.user_id == user.id,
                    Task.status == 'completed'
                ).count()
        
        return render_template('dashboard.html', 
                             user_info=user_info, 
                             user_stats=user_stats)
    
    except Exception as e:
        logger.error(f"Dashboard error for {user_email}: {str(e)}")
        flash('An error occurred loading your dashboard. Please try again.', 'error')
        return render_template('dashboard.html', 
                             user_info={'email': user_email}, 
                             user_stats={'total_emails': 0, 'total_tasks': 0})

@app.route('/login')
def login():
    """Login page"""
    return render_template('login.html')

@app.route('/auth/google')
def auth_google():
    """Initiate Google OAuth flow"""
    try:
        auth_url, state = gmail_auth.get_authorization_url('user_session')
        session['oauth_state'] = state
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Google auth initiation error: {str(e)}")
        flash('Failed to initiate Google authentication. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth callback"""
    try:
        authorization_code = request.args.get('code')
        state = request.args.get('state')
        
        if not authorization_code:
            flash('Authorization failed. Please try again.', 'error')
            return redirect(url_for('login'))
        
        # Handle OAuth callback
        result = gmail_auth.handle_oauth_callback(authorization_code, state)
        
        if result['success']:
            session['user_email'] = result['user_email']
            session['authenticated'] = True
            flash(f'Successfully authenticated as {result["user_email"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash(f'Authentication failed: {result["error"]}', 'error')
            return redirect(url_for('login'))
    
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        flash('Authentication error occurred. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Logout user"""
    user_email = session.get('user_email')
    session.clear()
    
    if user_email:
        flash(f'Successfully logged out from {user_email}', 'success')
    
    return redirect(url_for('login'))

@app.route('/api/process-emails', methods=['POST'])
def api_process_emails():
    """API endpoint to fetch and process emails"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() or {}
        days_back = data.get('days_back', 7)
        limit = data.get('limit', 50)
        force_refresh = data.get('force_refresh', False)
        
        # Step 1: Fetch emails
        logger.info(f"Fetching emails for {user_email}")
        fetch_result = gmail_fetcher.fetch_recent_emails(
            user_email, 
            days_back=days_back, 
            limit=limit,
            force_refresh=force_refresh
        )
        
        if not fetch_result['success']:
            return jsonify({
                'success': False, 
                'error': f"Failed to fetch emails: {fetch_result.get('error')}"
            }), 400
        
        # Step 2: Normalize emails
        logger.info(f"Normalizing emails for {user_email}")
        normalize_result = email_normalizer.normalize_user_emails(user_email, limit)
        
        # Step 3: Extract tasks
        logger.info(f"Extracting tasks for {user_email}")
        task_result = task_extractor.extract_tasks_for_user(user_email, limit)
        
        return jsonify({
            'success': True,
            'fetch_result': fetch_result,
            'normalize_result': normalize_result,
            'task_result': task_result,
            'processed_at': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Email processing error for {user_email}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f"Processing failed: {str(e)}"
        }), 500

@app.route('/api/emails')
def api_get_emails():
    """API endpoint to get user emails"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        limit = request.args.get('limit', 50, type=int)
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        emails = get_db_manager().get_user_emails(user.id, limit)
        
        return jsonify({
            'success': True,
            'emails': [email.to_dict() for email in emails],
            'count': len(emails)
        })
    
    except Exception as e:
        logger.error(f"Get emails error for {user_email}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks')
def api_get_tasks():
    """API endpoint to get user tasks"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)
        
        result = task_extractor.get_user_tasks(user_email, status, limit)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Get tasks error for {user_email}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
def api_update_task_status(task_id):
    """API endpoint to update task status"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'in_progress', 'completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        result = task_extractor.update_task_status(user_email, task_id, new_status)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Update task status error for {user_email}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for Claude chat"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # Get user context for better responses
        user = get_db_manager().get_user_by_email(user_email)
        context_info = ""
        
        if user:
            with get_db_manager().get_session() as db_session:
                recent_tasks = db_session.query(Task).filter(
                    Task.user_id == user.id,
                    Task.status == 'pending'
                ).order_by(Task.created_at.desc()).limit(5).all()
                
                if recent_tasks:
                    task_list = "\n".join([f"- {task.description}" for task in recent_tasks])
                    context_info = f"\n\nYour recent pending tasks:\n{task_list}"
        
        # Build system prompt with context
        system_prompt = f"""You are an AI Chief of Staff assistant helping {user_email}. 
You have access to their email-derived tasks and can help with work organization, prioritization, and productivity.

Be helpful, professional, and concise. Focus on actionable advice related to their work and tasks.{context_info}"""
        
        # Call Claude
        response = claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1000,
            temperature=0.3,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": message
            }]
        )
        
        reply = response.content[0].text
        
        return jsonify({
            'success': True,
            'message': message,
            'reply': reply,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Chat error for {user_email}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': 'Failed to process chat message'
        }), 500

@app.route('/api/status')
def api_status():
    """API endpoint to get system status"""
    user_email = session.get('user_email')
    
    status = {
        'authenticated': bool(user_email),
        'user_email': user_email,
        'timestamp': datetime.utcnow().isoformat(),
        'database_connected': True,
        'gmail_auth_available': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        'claude_available': bool(settings.ANTHROPIC_API_KEY)
    }
    
    # Test database connection
    try:
        get_db_manager().get_session().close()
    except Exception as e:
        status['database_connected'] = False
        status['database_error'] = str(e)
    
    # Test Gmail auth if user is authenticated
    if user_email:
        try:
            auth_status = gmail_auth.get_authentication_status(user_email)
            status['gmail_auth_status'] = auth_status
        except Exception as e:
            status['gmail_auth_error'] = str(e)
    
    return jsonify(status)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Validate configuration
    config_errors = settings.validate_config()
    if config_errors:
        logger.error("Configuration errors:")
        for error in config_errors:
            logger.error(f"  - {error}")
        exit(1)
    
    logger.info("Starting AI Chief of Staff web application...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    logger.info(f"Environment: {'Production' if settings.is_production() else 'Development'}")
    
    # Initialize database
    try:
        get_db_manager().initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        exit(1)
    
    app.run(
        host='0.0.0.0',
        port=settings.PORT,
        debug=settings.DEBUG
    ) 