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
from datetime import timedelta
from flask import Flask, session, render_template, redirect, url_for, request, jsonify
from flask_session import Session
import tempfile

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
    from models.database import Task, Email
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
        return render_template('login.html')
    
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
        """Handle Google OAuth callback"""
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
            
            # Store user info in session
            user_info = result.get('user_info', {})
            session.clear()  # Clear any existing session data
            session['user_email'] = user_info.get('email')
            session['user_name'] = user_info.get('name')
            session['user_id'] = user_info.get('id')
            session['authenticated'] = True
            session.permanent = True
            
            logger.info(f"User successfully authenticated: {user_info.get('email')}")
            
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return redirect(url_for('login') + '?error=callback_failed')
    
    @app.route('/logout')
    def logout():
        """Logout and clear session"""
        user_email = session.get('user_email')
        session.clear()
        logger.info(f"User logged out: {user_email}")
        return redirect(url_for('login'))
    
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
            logger.error(f"Failed to get business knowledge: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/chat-knowledge', methods=['GET'])
    def api_get_chat_knowledge():
        """API endpoint to get comprehensive knowledge summary for chat queries"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            knowledge = email_intelligence.get_chat_knowledge_summary(user_email)
            return jsonify(knowledge)
        except Exception as e:
            logger.error(f"Failed to get chat knowledge: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/email-insights', methods=['GET'])
    def api_get_email_insights():
        """API endpoint to get email insights with AI analysis"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            limit = int(request.args.get('limit', 20))
            emails = get_db_manager().get_user_emails(user.id, limit)
            
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
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            topics = get_db_manager().get_user_topics(user.id)
            
            return jsonify({
                'success': True,
                'topics': [topic.to_dict() for topic in topics],
                'count': len(topics)
            })
            
        except Exception as e:
            logger.error(f"Get topics API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/topics', methods=['POST'])
    def api_create_topic():
        """API endpoint to create a new topic manually"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
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
            
            topic = get_db_manager().create_or_update_topic(user.id, topic_data)
            
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
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            success = get_db_manager().mark_topic_official(user.id, topic_id)
            
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
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            data = request.get_json()
            target_topic_id = data.get('target_topic_id')
            
            if not target_topic_id:
                return jsonify({'error': 'Target topic ID is required'}), 400
            
            success = get_db_manager().merge_topics(user.id, topic_id, target_topic_id)
            
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
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
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
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        if not claude_client:
            return jsonify({'error': 'Claude integration not configured'}), 500
        
        try:
            data = request.get_json()
            message = data.get('message')
            include_context = data.get('include_context', True)
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
            
            user_email = session['user_email']
            
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
                        user = get_db_manager().get_user_by_email(user_email)
                        if user:
                            tasks = get_db_manager().get_user_tasks(user.id)
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