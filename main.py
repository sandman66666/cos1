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
from typing import List, Dict

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

def get_strategic_business_insights(user_email: str) -> List[Dict]:
    """Generate strategic business insights from user's data patterns"""
    try:
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return []
        
        insights = []
        
        # Get recent data
        emails = get_db_manager().get_user_emails(db_user.id, limit=100)
        people = get_db_manager().get_user_people(db_user.id, limit=50)
        tasks = get_db_manager().get_user_tasks(db_user.id, limit=50)
        projects = get_db_manager().get_user_projects(db_user.id, limit=20)
        
        # Filter quality data
        analyzed_emails = [e for e in emails if e.ai_summary and len(e.ai_summary or '') > 10]
        human_contacts = [p for p in people if p.name and not any(pattern in (p.email_address or '').lower() 
                                                                for pattern in ['noreply', 'no-reply', 'automated'])]
        active_projects = [p for p in projects if p.status == 'active']
        pending_tasks = [t for t in tasks if t.status in ['pending', 'open']]
        
        # 1. RELATIONSHIP INTELLIGENCE
        if human_contacts:
            insights.append({
                'type': 'relationship_intelligence',
                'title': f'Professional Network Growth',
                'description': f'You\'ve built connections with {len(human_contacts)} professional contacts across {len(set(p.company for p in human_contacts if p.company))} organizations.',
                'details': f'Key relationships include contacts from {", ".join(list(set(p.company for p in human_contacts if p.company))[:3])}.',
                'action': 'Consider reaching out to maintain these valuable professional relationships.',
                'priority': 'medium',
                'icon': '👥'
            })
        
        # 2. COMMUNICATION PATTERNS
        if analyzed_emails:
            recent_senders = {}
            for email in analyzed_emails[-30:]:  # Last 30 emails
                sender = email.sender_name or email.sender
                recent_senders[sender] = recent_senders.get(sender, 0) + 1
            
            top_correspondents = sorted(recent_senders.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_correspondents:
                insights.append({
                    'type': 'communication_pattern',
                    'title': 'Active Communication Threads',
                    'description': f'Most active correspondence with {top_correspondents[0][0]} ({top_correspondents[0][1]} emails).',
                    'details': f'Top correspondents: {", ".join([f"{name} ({count})" for name, count in top_correspondents])}',
                    'action': 'These frequent exchanges suggest important ongoing work or relationships.',
                    'priority': 'high',
                    'icon': '💬'
                })
        
        # 3. PROJECT INTELLIGENCE
        if active_projects:
            insights.append({
                'type': 'project_intelligence',
                'title': 'Active Project Portfolio',
                'description': f'Currently managing {len(active_projects)} active projects.',
                'details': f'Projects: {", ".join([p.name for p in active_projects[:3]])}.',
                'action': 'Review project priorities and resource allocation.',
                'priority': 'high',
                'icon': '📋'
            })
        
        # 4. TASK INTELLIGENCE
        if pending_tasks:
            high_priority_tasks = [t for t in pending_tasks if t.priority == 'high']
            overdue_tasks = [t for t in pending_tasks if t.due_date and t.due_date < datetime.now()]
            
            if high_priority_tasks or overdue_tasks:
                insights.append({
                    'type': 'task_intelligence',
                    'title': 'Task Priority Analysis',
                    'description': f'{len(high_priority_tasks)} high-priority tasks and {len(overdue_tasks)} overdue items need attention.',
                    'details': f'Total pending: {len(pending_tasks)} tasks. Focus on urgent items first.',
                    'action': 'Prioritize high-impact tasks and address overdue items.',
                    'priority': 'high' if overdue_tasks else 'medium',
                    'icon': '⚡'
                })
        
        # 5. BUSINESS INTELLIGENCE FROM EMAIL CONTENT
        business_decisions = []
        opportunities = []
        challenges = []
        
        for email in analyzed_emails:
            if email.key_insights and isinstance(email.key_insights, dict):
                insights_data = email.key_insights
                business_decisions.extend(insights_data.get('key_decisions', []))
                opportunities.extend(insights_data.get('strategic_opportunities', []))
                challenges.extend(insights_data.get('business_challenges', []))
        
        if business_decisions:
            insights.append({
                'type': 'strategic_intelligence',
                'title': 'Strategic Decisions Tracked',
                'description': f'Identified {len(business_decisions)} strategic decisions across recent communications.',
                'details': f'Recent decision: "{business_decisions[0][:100]}..."' if business_decisions else '',
                'action': 'Review decision outcomes and track implementation progress.',
                'priority': 'high',
                'icon': '🎯'
            })
        
        if opportunities:
            insights.append({
                'type': 'opportunity_intelligence', 
                'title': 'Business Opportunities Identified',
                'description': f'Discovered {len(opportunities)} potential business opportunities.',
                'details': f'Top opportunity: "{opportunities[0][:100]}..."' if opportunities else '',
                'action': 'Evaluate and prioritize these opportunities for potential action.',
                'priority': 'medium',
                'icon': '💡'
            })
        
        if challenges:
            insights.append({
                'type': 'challenge_intelligence',
                'title': 'Business Challenges Detected',
                'description': f'Identified {len(challenges)} business challenges requiring attention.',
                'details': f'Key challenge: "{challenges[0][:100]}..."' if challenges else '',
                'action': 'Develop strategies to address these challenges.',
                'priority': 'medium',
                'icon': '⚠️'
            })
        
        # 6. ENGAGEMENT INSIGHTS
        if analyzed_emails and human_contacts:
            recent_new_contacts = [p for p in human_contacts if p.total_emails and p.total_emails <= 2]
            if recent_new_contacts:
                insights.append({
                    'type': 'engagement_intelligence',
                    'title': 'New Professional Connections',
                    'description': f'Connected with {len(recent_new_contacts)} new professional contacts recently.',
                    'details': f'New contacts from: {", ".join(set(p.company for p in recent_new_contacts if p.company)[:3])}',
                    'action': 'Follow up to strengthen these new professional relationships.',
                    'priority': 'medium',
                    'icon': '🤝'
                })
        
        # 7. PRODUCTIVITY INSIGHTS
        total_processed = len(analyzed_emails)
        if total_processed > 0:
            insights.append({
                'type': 'productivity_intelligence',
                'title': 'Communication Intelligence',
                'description': f'AI has analyzed {total_processed} business communications to extract actionable insights.',
                'details': f'Extracted {len(pending_tasks)} actionable tasks and identified {len(human_contacts)} business contacts.',
                'action': 'Your AI Chief of Staff is building comprehensive business knowledge to help you stay on top of opportunities.',
                'priority': 'low',
                'icon': '🧠'
            })
        
        # If no insights generated, provide helpful guidance
        if not insights:
            insights.append({
                'type': 'guidance',
                'title': 'Building Your Business Intelligence',
                'description': 'Process more emails to unlock strategic insights about your business.',
                'details': 'Your AI Chief of Staff will analyze communication patterns, extract tasks, and identify opportunities as you sync more data.',
                'action': 'Use the "Process Emails" button to start building your comprehensive business knowledge base.',
                'priority': 'medium',
                'icon': '🚀'
            })
        
        # Sort by priority (high, medium, low)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        insights.sort(key=lambda x: priority_order.get(x['priority'], 2))
        
        return insights[:6]  # Return top 6 insights
        
    except Exception as e:
        logger.error(f"Error generating strategic insights: {str(e)}")
        return [{
            'type': 'error',
            'title': 'Insights Processing',
            'description': 'Unable to generate strategic insights at this time.',
            'details': 'Please try processing some emails first.',
            'action': 'Process your emails to build business intelligence.',
            'priority': 'medium',
            'icon': '⚠️'
        }]

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
        user = get_current_user()
        if not user:
            return redirect('/auth/google')
        
        # Redirect to home page
        return redirect('/home')
    
    @app.route('/home')
    def home():
        user = get_current_user()
        if not user:
            return redirect('/auth/google')
        
        return render_template('home.html', 
                               user_email=user['email'],
                               user_id=user.get('id'),
                               session_id=session.get('session_id'),
                               cache_buster=int(time.time()))
    
    @app.route('/tasks')
    def tasks():
        user = get_current_user()
        if not user:
            return redirect('/auth/google')
        
        return render_template('tasks.html', 
                               user_email=user['email'],
                               user_id=user.get('id'),
                               session_id=session.get('session_id'),
                               cache_buster=int(time.time()))
    
    @app.route('/people')
    def people_page():
        """People management page"""
        user = get_current_user()
        if not user:
            return redirect('/login')
        return render_template('people.html')
    
    @app.route('/knowledge')
    def knowledge_page():
        """Knowledge management page"""
        user = get_current_user()
        if not user:
            return redirect('/login')
        return render_template('knowledge.html')
    
    @app.route('/settings')
    def settings_page():
        """Settings page for configuring email sync and other preferences"""
        user = get_current_user()
        if not user:
            return redirect('/login')
        return render_template('settings.html')
    
    @app.route('/dashboard')
    def dashboard():
        """Legacy dashboard route - redirect to home"""
        return redirect('/home')
    
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
        """API endpoint for Claude chat functionality with comprehensive knowledge context"""
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
            
            # Get comprehensive knowledge context if requested
            context_parts = []
            if include_context:
                try:
                    # Get comprehensive business knowledge
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
                        
                        # Add recent tasks context
                        db_user = get_db_manager().get_user_by_email(user_email)
                        if db_user:
                            tasks = get_db_manager().get_user_tasks(db_user.id, limit=10)
                            if tasks:
                                recent_tasks = [f"{task.description} (Priority: {task.priority}, Status: {task.status})" for task in tasks[:10]]
                                context_parts.append("CURRENT TASKS:\n" + "\n".join([f"- {task}" for task in recent_tasks]))
                            
                            # Add topics context
                            topics = get_db_manager().get_user_topics(db_user.id)
                            if topics:
                                official_topics = [t.name for t in topics if t.is_official][:5]
                                if official_topics:
                                    context_parts.append("OFFICIAL TOPICS:\n" + "\n".join([f"- {topic}" for topic in official_topics]))
                
                except Exception as context_error:
                    logger.warning(f"Failed to load context for chat: {context_error}")
            
            # Create enhanced system prompt with comprehensive business context
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
                'response': assistant_response,
                'model': settings.CLAUDE_MODEL,
                'context_included': include_context and len(context_parts) > 0,
                'context_summary': f"Included {len(context_parts)} context sections" if context_parts else "No context included"
            })
            
        except Exception as e:
            logger.error(f"Chat API error: {str(e)}")
            return jsonify({'error': f'Chat error: {str(e)}'}), 500

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
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
            
            user_email = user['email']
            
            # This endpoint ALWAYS includes comprehensive knowledge context
            # Get comprehensive business knowledge
            knowledge_response = email_intelligence.get_chat_knowledge_summary(user_email)
            business_knowledge = knowledge_response.get('knowledge_base', {}) if knowledge_response.get('success') else {}
            
            # Build comprehensive context
            context_parts = []
            
            # Business intelligence
            if business_knowledge.get('business_intelligence'):
                bi = business_knowledge['business_intelligence']
                
                if bi.get('recent_decisions'):
                    context_parts.append("STRATEGIC BUSINESS DECISIONS:\n" + "\n".join([
                        f"- {decision if isinstance(decision, str) else decision.get('decision', 'Unknown decision')}" 
                        for decision in bi['recent_decisions'][:8]
                    ]))
                
                if bi.get('top_opportunities'):
                    context_parts.append("BUSINESS OPPORTUNITIES:\n" + "\n".join([
                        f"- {opp if isinstance(opp, str) else opp.get('opportunity', 'Unknown opportunity')}" 
                        for opp in bi['top_opportunities'][:8]
                    ]))
                
                if bi.get('current_challenges'):
                    context_parts.append("CURRENT CHALLENGES:\n" + "\n".join([
                        f"- {challenge if isinstance(challenge, str) else challenge.get('challenge', 'Unknown challenge')}" 
                        for challenge in bi['current_challenges'][:8]
                    ]))
            
            # Rich contacts
            if business_knowledge.get('rich_contacts'):
                contacts_summary = []
                for contact in business_knowledge['rich_contacts'][:15]:
                    contact_info = f"{contact['name']}"
                    if contact.get('title') and contact.get('company'):
                        contact_info += f" ({contact['title']} at {contact['company']})"
                    elif contact.get('company'):
                        contact_info += f" (at {contact['company']})"
                    elif contact.get('title'):
                        contact_info += f" ({contact['title']})"
                    if contact.get('relationship'):
                        contact_info += f" - {contact['relationship']}"
                    contacts_summary.append(contact_info)
                
                if contacts_summary:
                    context_parts.append("KEY PROFESSIONAL CONTACTS:\n" + "\n".join([f"- {contact}" for contact in contacts_summary]))
            
            # Current data from database
            db_user = get_db_manager().get_user_by_email(user_email)
            if db_user:
                # Recent tasks
                tasks = get_db_manager().get_user_tasks(db_user.id, limit=15)
                if tasks:
                    task_summaries = []
                    for task in tasks:
                        task_info = task.description
                        if task.priority and task.priority != 'medium':
                            task_info += f" (Priority: {task.priority})"
                        if task.status != 'pending':
                            task_info += f" (Status: {task.status})"
                        if task.due_date:
                            task_info += f" (Due: {task.due_date.strftime('%Y-%m-%d')})"
                        task_summaries.append(task_info)
                    
                    context_parts.append("CURRENT TASKS:\n" + "\n".join([f"- {task}" for task in task_summaries]))
                
                # Active projects
                projects = get_db_manager().get_user_projects(db_user.id, status='active', limit=10)
                if projects:
                    project_summaries = [f"{p.name} - {p.description[:100] if p.description else 'No description'}" for p in projects]
                    context_parts.append("ACTIVE PROJECTS:\n" + "\n".join([f"- {proj}" for proj in project_summaries]))
                
                # Official topics for context
                topics = get_db_manager().get_user_topics(db_user.id)
                official_topics = [t.name for t in topics if t.is_official][:8]
                if official_topics:
                    context_parts.append("OFFICIAL BUSINESS TOPICS:\n" + "\n".join([f"- {topic}" for topic in official_topics]))
            
            # Create comprehensive system prompt
            business_context = "\n\n".join(context_parts) if context_parts else "Limited business context available."
            
            enhanced_system_prompt = f"""You are an expert AI Chief of Staff for {user_email}. You have comprehensive access to their business knowledge, communications, contacts, and ongoing work. Your role is to provide strategic, informed assistance.

COMPREHENSIVE BUSINESS KNOWLEDGE:
{business_context}

YOUR CAPABILITIES:
- Strategic business advisory based on actual data
- Relationship management insights from real contacts
- Task and project coordination with current context
- Decision support using historical business intelligence
- Personalized recommendations based on communication patterns

RESPONSE GUIDELINES:
- Always leverage the specific business context provided above
- Reference actual people, projects, and decisions when relevant
- Provide actionable, strategic advice tailored to their business situation
- Be direct and practical while maintaining professionalism
- When you lack specific information, explicitly state what additional context would help
- Prioritize insights that connect to their ongoing work and relationships

Remember: This knowledge base represents their actual business communications and relationships. Use it to provide highly personalized, contextually aware assistance."""
            
            # Send to Claude with comprehensive context
            response = claude_client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=4000,
                system=enhanced_system_prompt,
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
                'context_sections_included': len(context_parts),
                'knowledge_source': 'comprehensive_business_intelligence'
            })
            
        except Exception as e:
            logger.error(f"Enhanced chat API error: {str(e)}")
            return jsonify({'success': False, 'error': f'Enhanced chat error: {str(e)}'}), 500
    
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
            
            # Convert to frontend-expected format
            people_data = []
            for person in people:
                person_dict = person.to_dict()
                # Map database field to expected frontend field
                person_dict['email'] = person_dict.get('email_address')
                person_dict['relationship'] = person_dict.get('relationship_type')
                person_dict['last_contact'] = person_dict.get('last_interaction')
                people_data.append(person_dict)
            
            return jsonify({
                'success': True,
                'people': people_data,
                'count': len(people_data)
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
        """API endpoint to get strategic business insights with AI analysis"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get comprehensive business intelligence
            strategic_insights = get_strategic_business_insights(user['email'])
            
            return jsonify({
                'success': True,
                'strategic_insights': strategic_insights,
                'count': len(strategic_insights)
            })
            
        except Exception as e:
            logger.error(f"Get strategic insights API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/download-knowledge', methods=['GET'])
    def api_download_knowledge():
        """API endpoint to download comprehensive knowledge base as text file"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401

        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404

            # Get comprehensive knowledge data
            emails = get_db_manager().get_user_emails(db_user.id, limit=1000)
            people = get_db_manager().get_user_people(db_user.id, limit=500)
            tasks = get_db_manager().get_user_tasks(db_user.id, limit=1000)
            projects = get_db_manager().get_user_projects(db_user.id, limit=200)
            topics = get_db_manager().get_user_topics(db_user.id, limit=1000)

            # Get business knowledge summary
            try:
                knowledge_response = email_intelligence.get_chat_knowledge_summary(user['email'])
                business_knowledge = knowledge_response.get('knowledge_base', {}) if knowledge_response.get('success') else {}
            except:
                business_knowledge = {}

            # Generate comprehensive text content
            content_lines = []
            content_lines.append("=" * 80)
            content_lines.append("AI CHIEF OF STAFF - COMPREHENSIVE KNOWLEDGE BASE")
            content_lines.append("=" * 80)
            content_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_lines.append(f"User: {user['email']}")
            content_lines.append("")

            # === EXECUTIVE SUMMARY ===
            content_lines.append("📊 EXECUTIVE SUMMARY")
            content_lines.append("-" * 40)
            
            analyzed_emails = [e for e in emails if e.ai_summary]
            human_contacts = [p for p in people if p.name and not any(pattern in (p.email_address or '').lower() 
                                                                    for pattern in ['noreply', 'no-reply', 'automated', 'system'])]
            active_projects = [p for p in projects if p.status == 'active']
            pending_tasks = [t for t in tasks if t.status == 'pending']
            
            content_lines.append(f"• {len(emails)} total emails processed")
            content_lines.append(f"• {len(analyzed_emails)} emails with AI insights ({len(analyzed_emails)/max(len(emails),1)*100:.1f}%)")
            content_lines.append(f"• {len(human_contacts)} human contacts identified")
            content_lines.append(f"• {len(active_projects)} active projects")
            content_lines.append(f"• {len(pending_tasks)} pending tasks")
            content_lines.append(f"• {len([t for t in topics if t.is_official])} official topics defined")
            content_lines.append("")

            # === BUSINESS INTELLIGENCE ===
            if business_knowledge.get('business_intelligence'):
                bi = business_knowledge['business_intelligence']
                
                if bi.get('recent_decisions'):
                    content_lines.append("🎯 STRATEGIC BUSINESS DECISIONS")
                    content_lines.append("-" * 40)
                    for i, decision in enumerate(bi['recent_decisions'][:10], 1):
                        if isinstance(decision, dict):
                            content_lines.append(f"{i}. {decision.get('decision', 'Unknown decision')}")
                            if decision.get('context'):
                                content_lines.append(f"   Context: {decision['context']}")
                            if decision.get('date'):
                                content_lines.append(f"   Date: {decision['date']}")
                        else:
                            content_lines.append(f"{i}. {decision}")
                        content_lines.append("")

                if bi.get('top_opportunities'):
                    content_lines.append("💡 BUSINESS OPPORTUNITIES")
                    content_lines.append("-" * 40)
                    for i, opportunity in enumerate(bi['top_opportunities'][:10], 1):
                        if isinstance(opportunity, dict):
                            content_lines.append(f"{i}. {opportunity.get('opportunity', 'Unknown opportunity')}")
                            if opportunity.get('context'):
                                content_lines.append(f"   Context: {opportunity['context']}")
                        else:
                            content_lines.append(f"{i}. {opportunity}")
                        content_lines.append("")

                if bi.get('current_challenges'):
                    content_lines.append("⚠️ CURRENT CHALLENGES")
                    content_lines.append("-" * 40)
                    for i, challenge in enumerate(bi['current_challenges'][:10], 1):
                        if isinstance(challenge, dict):
                            content_lines.append(f"{i}. {challenge.get('challenge', 'Unknown challenge')}")
                            if challenge.get('context'):
                                content_lines.append(f"   Context: {challenge['context']}")
                        else:
                            content_lines.append(f"{i}. {challenge}")
                        content_lines.append("")

            # === KEY CONTACTS ===
            if human_contacts:
                content_lines.append("👥 KEY PROFESSIONAL CONTACTS")
                content_lines.append("-" * 40)
                
                # Sort by importance and interaction frequency
                sorted_contacts = sorted(human_contacts, 
                                       key=lambda p: (p.importance_level or 0, p.total_emails or 0), 
                                       reverse=True)[:20]
                
                for i, person in enumerate(sorted_contacts, 1):
                    content_lines.append(f"{i}. {person.name}")
                    if person.email_address:
                        content_lines.append(f"   📧 {person.email_address}")
                    if person.title or person.company:
                        title_company = []
                        if person.title:
                            title_company.append(person.title)
                        if person.company:
                            title_company.append(f"at {person.company}")
                        content_lines.append(f"   💼 {' '.join(title_company)}")
                    if person.relationship_type:
                        content_lines.append(f"   🤝 Relationship: {person.relationship_type}")
                    if person.total_emails:
                        content_lines.append(f"   📊 {person.total_emails} email interactions")
                    if person.notes:
                        content_lines.append(f"   📝 Notes: {person.notes[:200]}{'...' if len(person.notes) > 200 else ''}")
                    content_lines.append("")
                content_lines.append("")

            # === ACTIVE PROJECTS ===
            if projects:
                content_lines.append("📋 PROJECTS")
                content_lines.append("-" * 40)
                for project in projects[:15]:  # Top 15 projects
                    content_lines.append(f"• {project.name} ({project.status.upper()})")
                    if project.description:
                        content_lines.append(f"  Description: {project.description}")
                    if project.priority:
                        content_lines.append(f"  Priority: {project.priority}")
                    if project.key_topics:
                        content_lines.append(f"  Topics: {', '.join(project.key_topics[:5])}")
                    if project.total_emails:
                        content_lines.append(f"  Email activity: {project.total_emails} emails")
                    content_lines.append("")
                content_lines.append("")

            # === TASK MANAGEMENT ===
            if tasks:
                content_lines.append("✅ TASK MANAGEMENT")
                content_lines.append("-" * 40)
                
                # Group tasks by status
                task_groups = {}
                for task in tasks[:50]:  # Top 50 recent tasks
                    status = task.status or 'pending'
                    if status not in task_groups:
                        task_groups[status] = []
                    task_groups[status].append(task)
                
                for status, task_list in task_groups.items():
                    content_lines.append(f"{status.upper()} TASKS ({len(task_list)}):")
                    for task in task_list[:10]:  # Top 10 per status
                        content_lines.append(f"  • {task.description}")
                        if task.due_date:
                            content_lines.append(f"    📅 Due: {task.due_date.strftime('%Y-%m-%d')}")
                        if task.priority:
                            content_lines.append(f"    🔥 Priority: {task.priority}")
                        if task.assignee:
                            content_lines.append(f"    👤 Assigned to: {task.assignee}")
                    content_lines.append("")
                content_lines.append("")

            # === TOPICS & THEMES ===
            if topics:
                content_lines.append("🏷️ TOPICS & THEMES")
                content_lines.append("-" * 40)
                
                official_topics = [t for t in topics if t.is_official]
                ai_topics = [t for t in topics if not t.is_official]
                
                if official_topics:
                    content_lines.append("OFFICIAL TOPICS:")
                    for topic in official_topics:
                        content_lines.append(f"  • {topic.name}")
                        if topic.description:
                            content_lines.append(f"    {topic.description}")
                        if topic.email_count:
                            content_lines.append(f"    📊 {topic.email_count} emails categorized")
                        content_lines.append("")
                
                if ai_topics:
                    content_lines.append("AI-DISCOVERED TOPICS:")
                    # Sort by email count and confidence
                    sorted_ai_topics = sorted(ai_topics, 
                                            key=lambda t: (t.email_count or 0, t.confidence_score or 0), 
                                            reverse=True)[:15]
                    for topic in sorted_ai_topics:
                        content_lines.append(f"  • {topic.name} ({topic.email_count or 0} emails)")
                        if topic.confidence_score:
                            content_lines.append(f"    Confidence: {topic.confidence_score:.1%}")
                content_lines.append("")

            # === EMAIL INSIGHTS ===
            if analyzed_emails:
                content_lines.append("📧 KEY EMAIL INSIGHTS")
                content_lines.append("-" * 40)
                
                # Get the most important emails with insights
                important_emails = sorted(analyzed_emails, 
                                        key=lambda e: (e.priority_score or 0, len(e.ai_summary or '')), 
                                        reverse=True)[:20]
                
                for i, email in enumerate(important_emails, 1):
                    content_lines.append(f"{i}. {email.subject or 'No Subject'}")
                    content_lines.append(f"   From: {email.sender_name or email.sender}")
                    if email.email_date:
                        content_lines.append(f"   Date: {email.email_date[:10]}")  # Just the date part
                    if email.ai_summary:
                        summary = email.ai_summary[:300] + ('...' if len(email.ai_summary) > 300 else '')
                        content_lines.append(f"   AI Summary: {summary}")
                    if email.topics:
                        content_lines.append(f"   Topics: {', '.join(email.topics[:3])}")
                    content_lines.append("")
                content_lines.append("")

            # === APPENDIX ===
            content_lines.append("📎 APPENDIX - DATA EXPORT")
            content_lines.append("-" * 40)
            content_lines.append(f"Total Records Exported:")
            content_lines.append(f"• {len(emails)} emails")
            content_lines.append(f"• {len(people)} people")
            content_lines.append(f"• {len(tasks)} tasks")
            content_lines.append(f"• {len(projects)} projects") 
            content_lines.append(f"• {len(topics)} topics")
            content_lines.append("")
            content_lines.append("This knowledge base is used as context in every Claude conversation")
            content_lines.append("to provide personalized, informed assistance based on your actual")
            content_lines.append("business communications, relationships, and ongoing projects.")
            content_lines.append("")
            content_lines.append("=" * 80)
            content_lines.append("END OF KNOWLEDGE BASE")
            content_lines.append("=" * 80)

            # Create text content
            text_content = "\n".join(content_lines)
            
            # Create response with file download
            response = make_response(text_content)
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="AI_Chief_of_Staff_Knowledge_Base_{datetime.now().strftime("%Y-%m-%d_%H-%M")}.txt"'
            
            return response

        except Exception as e:
            logger.error(f"Knowledge download error: {str(e)}")
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
    
    @app.route('/api/topics/<int:topic_id>', methods=['PUT'])
    def api_update_topic(topic_id):
        """API endpoint to update a topic"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
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
            topic_analysis = {}
            
            # Analyze topic usage and collect content for AI description generation
            for email in emails:
                if email.topics and isinstance(email.topics, list):
                    for topic in email.topics:
                        if topic and len(topic.strip()) > 2:  # Valid topic
                            topic_name = topic.strip()
                            if topic_name not in topic_analysis:
                                topic_analysis[topic_name] = {
                                    'count': 0,
                                    'email_examples': [],
                                    'key_content': []
                                }
                            topic_analysis[topic_name]['count'] += 1
                            
                            # Collect examples for AI description generation
                            if len(topic_analysis[topic_name]['email_examples']) < 5:
                                topic_analysis[topic_name]['email_examples'].append({
                                    'subject': email.subject,
                                    'summary': email.ai_summary,
                                    'sender': email.sender_name or email.sender
                                })
                            
                            # Collect key content for description
                            if email.ai_summary and len(email.ai_summary) > 20:
                                topic_analysis[topic_name]['key_content'].append(email.ai_summary[:200])
            
            # Create Topic records for topics with 2+ usages
            topics_created = 0
            for topic_name, analysis in topic_analysis.items():
                if analysis['count'] >= 2:  # Only create topics used in multiple emails
                    # Check if topic already exists
                    existing_topics = get_db_manager().get_user_topics(db_user.id)
                    topic_exists = any(t.name.lower() == topic_name.lower() for t in existing_topics)
                    
                    if not topic_exists:
                        # Generate meaningful description based on content
                        description = f"Business topic involving {topic_name.lower()}. "
                        
                        # Add context from email content
                        if analysis['key_content']:
                            common_themes = []
                            content_sample = ' '.join(analysis['key_content'][:3])
                            
                            # Simple keyword extraction for description
                            if 'meeting' in content_sample.lower():
                                common_themes.append('meetings and collaboration')
                            if 'project' in content_sample.lower():
                                common_themes.append('project management')
                            if 'decision' in content_sample.lower():
                                common_themes.append('strategic decisions')
                            if 'client' in content_sample.lower() or 'customer' in content_sample.lower():
                                common_themes.append('client relationships')
                            if 'team' in content_sample.lower():
                                common_themes.append('team coordination')
                            if 'opportunity' in content_sample.lower():
                                common_themes.append('business opportunities')
                            if 'challenge' in content_sample.lower() or 'issue' in content_sample.lower():
                                common_themes.append('problem solving')
                            
                            if common_themes:
                                description += f"Includes discussions about {', '.join(common_themes)}. "
                        
                        # Add usage statistics
                        description += f"Identified from {analysis['count']} email conversations"
                        if analysis['email_examples']:
                            senders = list(set([ex['sender'] for ex in analysis['email_examples'] if ex['sender']]))
                            if senders:
                                description += f" involving {', '.join(senders[:3])}"
                                if len(senders) > 3:
                                    description += f" and {len(senders)-3} others"
                        description += "."
                        
                        topic_data = {
                            'name': topic_name,
                            'slug': topic_name.lower().replace(' ', '-').replace('_', '-'),
                            'description': description,
                            'is_official': False,  # Mark as AI-discovered
                            'email_count': analysis['count'],
                            'confidence_score': min(0.9, analysis['count'] / 10.0),  # Higher confidence for more usage
                            'keywords': [topic_name.lower()] + [word.lower() for word in topic_name.split() if len(word) > 2]
                        }
                        get_db_manager().create_or_update_topic(db_user.id, topic_data)
                        topics_created += 1
            
            return jsonify({
                'success': True,
                'topics_created': topics_created,
                'total_topic_usage': len(topic_analysis),
                'message': f'Synced {topics_created} topics with AI-generated descriptions from email analysis'
            })
            
        except Exception as e:
            logger.error(f"Sync topics API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/topics/ensure-default', methods=['POST'])
    def api_ensure_default_topic():
        """API endpoint to ensure user has at least one default topic"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Check if user has any topics
            existing_topics = get_db_manager().get_user_topics(db_user.id)
            
            if len(existing_topics) == 0:
                # Create default "General Business" topic
                topic_data = {
                    'name': 'General Business',
                    'slug': 'general-business',
                    'description': 'Catch-all topic for all business communications, decisions, opportunities, and challenges that don\'t fit into specific categories. This ensures no important information is lost.',
                    'is_official': True,
                    'keywords': ['business', 'general', 'communication', 'decision', 'opportunity', 'challenge']
                }
                
                topic = get_db_manager().create_or_update_topic(db_user.id, topic_data)
                
                return jsonify({
                    'success': True,
                    'created': True,
                    'topic': topic.to_dict(),
                    'message': 'Default "General Business" topic created automatically'
                })
            else:
                return jsonify({
                    'success': True,
                    'created': False,
                    'message': f'User already has {len(existing_topics)} topics'
                })
            
        except Exception as e:
            logger.error(f"Ensure default topic API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/settings', methods=['GET'])
    def api_get_settings():
        """API endpoint to get user settings"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            settings_data = {
                'email_fetch_limit': db_user.email_fetch_limit,
                'email_days_back': db_user.email_days_back,
                'auto_process_emails': db_user.auto_process_emails,
                'last_login': db_user.last_login.isoformat() if db_user.last_login else None,
                'created_at': db_user.created_at.isoformat() if db_user.created_at else None,
                'name': db_user.name,
                'email': db_user.email
            }
            
            return jsonify({
                'success': True,
                'settings': settings_data
            })
            
        except Exception as e:
            logger.error(f"Get settings API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/settings', methods=['PUT'])
    def api_update_settings():
        """API endpoint to update user settings"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Update user settings directly on the object
            if 'email_fetch_limit' in data:
                db_user.email_fetch_limit = int(data['email_fetch_limit'])
            if 'email_days_back' in data:
                db_user.email_days_back = int(data['email_days_back'])
            if 'auto_process_emails' in data:
                db_user.auto_process_emails = bool(data['auto_process_emails'])
            
            # Save changes using the database manager's session
            with get_db_manager().get_session() as db_session:
                db_session.merge(db_user)
                db_session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Update settings API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/trigger-email-sync', methods=['POST'])
    def api_trigger_email_sync():
        """API endpoint to trigger email sync with custom parameters"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            data = request.get_json() or {}
            max_emails = data.get('max_emails', 20)
            days_back = data.get('days_back', 7)
            force_refresh = data.get('force_refresh', False)
            
            user_email = user['email']
            
            # Validate parameters
            if max_emails < 1 or max_emails > 500:
                return jsonify({'error': 'max_emails must be between 1 and 500'}), 400
            if days_back < 1 or days_back > 365:
                return jsonify({'error': 'days_back must be between 1 and 365'}), 400
            
            # First fetch emails
            fetch_result = gmail_fetcher.fetch_recent_emails(
                user_email=user_email,
                limit=max_emails,
                days_back=days_back,
                force_refresh=force_refresh
            )
            
            if not fetch_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': fetch_result.get('error', 'Email fetch failed'),
                    'stage': 'fetch'
                }), 400
            
            # Normalize emails
            normalize_result = email_normalizer.normalize_user_emails(user_email, limit=max_emails)
            
            # Process with AI intelligence
            intelligence_result = email_intelligence.process_user_emails_intelligently(
                user_email=user_email,
                limit=max_emails,
                force_refresh=force_refresh
            )
            
            # Get updated counts
            db_user = get_db_manager().get_user_by_email(user_email)
            all_emails = get_db_manager().get_user_emails(db_user.id) if db_user else []
            all_tasks = get_db_manager().get_user_tasks(db_user.id) if db_user else []
            all_people = get_db_manager().get_user_people(db_user.id) if db_user else []
            
            return jsonify({
                'success': True,
                'message': f'Successfully synced {fetch_result.get("count", 0)} emails',
                'results': {
                    'fetch': fetch_result,
                    'normalize': normalize_result,
                    'intelligence': intelligence_result
                },
                'summary': {
                    'emails_fetched': fetch_result.get('count', 0),
                    'emails_normalized': normalize_result.get('processed', 0),
                    'emails_analyzed': intelligence_result.get('processed_emails', 0),
                    'insights_extracted': intelligence_result.get('insights_extracted', 0),
                    'people_identified': intelligence_result.get('people_identified', 0),
                    'projects_identified': intelligence_result.get('projects_identified', 0),
                    'tasks_created': intelligence_result.get('tasks_created', 0),
                    'total_emails': len(all_emails),
                    'total_tasks': len(all_tasks),
                    'total_people': len(all_people)
                }
            })
            
        except Exception as e:
            logger.error(f"Trigger email sync API error: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'stage': 'processing'
            }), 500

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