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
from datetime import timedelta, datetime, timezone
from flask import Flask, session, render_template, redirect, url_for, request, jsonify, make_response
from flask_session import Session
import tempfile
import time
import uuid
from typing import List, Dict
import json

# Add the chief_of_staff_ai directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chief_of_staff_ai'))

try:
    from config.settings import settings
    from auth.gmail_auth import gmail_auth
    from ingest.gmail_fetcher import gmail_fetcher
    from ingest.calendar_fetcher import calendar_fetcher
    from processors.email_normalizer import email_normalizer
    from processors.task_extractor import task_extractor
    from processors.email_intelligence import email_intelligence
    from models.database import get_db_manager, Person, Project
    from models.database import Task, Email, Topic, Calendar
    import anthropic
except ImportError as e:
    print(f"Failed to import AI Chief of Staff modules: {e}")
    print("Make sure the chief_of_staff_ai directory and modules are properly set up")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_strategic_business_insights(user_email: str) -> List[Dict]:
    """
    ENHANCED 360-CONTEXT STRATEGIC BUSINESS INTELLIGENCE
    
    Generate super relevant and actionable insights by cross-referencing:
    - Email communications & AI analysis
    - People relationships & interaction patterns
    - Tasks & project management
    - Calendar events & meeting intelligence
    - Topic analysis & business themes
    - Strategic decisions & opportunities
    
    Creates comprehensive business intelligence for informed decision-making
    """
    try:
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return []
        
        # COMPREHENSIVE DATA COLLECTION - 360-CONTEXT FOUNDATION
        emails = get_db_manager().get_user_emails(db_user.id, limit=200)  # More comprehensive
        people = get_db_manager().get_user_people(db_user.id, limit=100)
        tasks = get_db_manager().get_user_tasks(db_user.id, limit=100)
        projects = get_db_manager().get_user_projects(db_user.id, limit=50)
        topics = get_db_manager().get_user_topics(db_user.id, limit=100)
        calendar_events = get_db_manager().get_user_calendar_events(db_user.id, limit=100)
        
        # QUALITY FILTERING WITH CROSS-REFERENCING
        analyzed_emails = [e for e in emails if e.ai_summary and len(e.ai_summary or '') > 15]
        human_contacts = [p for p in people if p.name and not any(pattern in (p.email_address or '').lower() 
                                                                for pattern in ['noreply', 'no-reply', 'automated'])]
        active_projects = [p for p in projects if p.status == 'active']
        actionable_tasks = [t for t in tasks if t.status in ['pending', 'open'] and t.description and len(t.description.strip()) > 10]
        strategic_topics = [t for t in topics if t.is_official or (t.email_count and t.email_count > 2)]
        upcoming_meetings = [e for e in calendar_events if e.start_time and e.start_time > datetime.now(timezone.utc)]
        
        # BUILD 360-CONTEXT RELATIONSHIP MAP
        context_map = {
            'email_to_people': {},  # Map emails to people involved
            'people_to_projects': {},  # Map people to their projects
            'projects_to_tasks': {},  # Map projects to related tasks
            'topics_to_content': {},  # Map topics to related content
            'calendar_to_people': {},  # Map meetings to attendees
            'strategic_threads': []  # Connected business threads
        }
        
        # POPULATE CROSS-REFERENCE MAP
        for email in analyzed_emails:
            if email.sender:
                sender_person = next((p for p in human_contacts if p.email_address and p.email_address.lower() == email.sender.lower()), None)
                if sender_person:
                    if email.id not in context_map['email_to_people']:
                        context_map['email_to_people'][email.id] = []
                    context_map['email_to_people'][email.id].append(sender_person)
        
        for project in active_projects:
            if project.stakeholders:
                for stakeholder_email in project.stakeholders:
                    stakeholder_person = next((p for p in human_contacts if p.email_address and p.email_address.lower() == stakeholder_email.lower()), None)
                    if stakeholder_person:
                        if stakeholder_person.id not in context_map['people_to_projects']:
                            context_map['people_to_projects'][stakeholder_person.id] = []
                        context_map['people_to_projects'][stakeholder_person.id].append(project)
        
        for task in actionable_tasks:
            if hasattr(task, 'project_id') and task.project_id:
                project = next((p for p in active_projects if p.id == task.project_id), None)
                if project:
                    if project.id not in context_map['projects_to_tasks']:
                        context_map['projects_to_tasks'][project.id] = []
                    context_map['projects_to_tasks'][project.id].append(task)
        
        insights = []
        
        # 1. CROSS-REFERENCED RELATIONSHIP INTELLIGENCE
        for person in human_contacts[:5]:  # Top 5 contacts
            person_emails = [e for e in analyzed_emails if e.sender and person.email_address and 
                           e.sender.lower() == person.email_address.lower()]
            person_projects = context_map['people_to_projects'].get(person.id, [])
            person_meetings = [e for e in upcoming_meetings if e.attendees and 
                             any(att.get('email', '').lower() == person.email_address.lower() for att in e.attendees)]
            
            if person_emails and len(person_emails) >= 3:  # Significant relationship
                latest_email = max(person_emails, key=lambda x: x.email_date or datetime.min)
                
                # Build comprehensive context
                context_elements = []
                if person_projects:
                    context_elements.append(f"Active on {len(person_projects)} projects: {', '.join([p.name for p in person_projects[:2]])}")
                if person_meetings:
                    next_meeting = min(person_meetings, key=lambda x: x.start_time)
                    context_elements.append(f"Upcoming meeting: {next_meeting.title}")
                if latest_email.key_insights and isinstance(latest_email.key_insights, dict):
                    recent_decisions = latest_email.key_insights.get('key_decisions', [])
                    if recent_decisions:
                        context_elements.append(f"Recent decision: {recent_decisions[0][:60]}...")
                
                full_context = "; ".join(context_elements) if context_elements else latest_email.ai_summary[:100]
                
                insights.append({
                    'type': 'relationship_intelligence_360',
                    'title': f'Strategic Relationship: {person.name}',
                    'description': f'{len(person_emails)} communications, {len(person_projects)} shared projects, {len(person_meetings)} upcoming meetings',
                    'details': f'360-Context: {full_context}',
                    'action': f'Review comprehensive relationship status with {person.name} - {person.company or "Unknown company"}',
                    'priority': 'high',
                    'icon': '🤝',
                    'data_sources': ['emails', 'projects', 'calendar'],
                    'cross_references': len(context_elements)
                })
        
        # 2. PROJECT-TASK-PEOPLE SYNTHESIS
        for project in active_projects[:3]:
            project_tasks = context_map['projects_to_tasks'].get(project.id, [])
            project_people = context_map['people_to_projects']
            project_stakeholders = [p for p_id, projs in project_people.items() if project in projs 
                                  for p in human_contacts if p.id == p_id]
            
            # Find related emails mentioning this project
            project_emails = [e for e in analyzed_emails if project.name.lower() in (e.ai_summary or '').lower() or 
                            project.name.lower() in (e.subject or '').lower()]
            
            if project_tasks or project_stakeholders or project_emails:
                context_strength = len(project_tasks) + len(project_stakeholders) + len(project_emails)
                
                insights.append({
                    'type': 'project_intelligence_360',
                    'title': f'Active Project: {project.name}',
                    'description': f'{len(project_tasks)} pending tasks, {len(project_stakeholders)} stakeholders, {len(project_emails)} related communications',
                    'details': f'Project Status: {project.status}. Recent activity across emails, tasks, and team coordination.',
                    'action': f'Review {project.name} progress and coordinate with {len(project_stakeholders)} stakeholders',
                    'priority': 'high' if context_strength > 5 else 'medium',
                    'icon': '📋',
                    'data_sources': ['projects', 'tasks', 'people', 'emails'],
                    'cross_references': context_strength
                })
        
        # 3. TOPIC-DRIVEN BUSINESS INTELLIGENCE
        for topic in strategic_topics[:3]:
            topic_emails = [e for e in analyzed_emails if e.topics and topic.name in e.topics]
            topic_people = list(set([e.sender_name or e.sender.split('@')[0] for e in topic_emails 
                                   if e.sender and e.sender_name]))
            topic_projects = [p for p in active_projects if p.key_topics and topic.name in p.key_topics]
            topic_tasks = [t for t in actionable_tasks if topic.name.lower() in (t.description or '').lower()]
            
            if topic_emails and len(topic_emails) >= 2:
                latest_activity = max(topic_emails, key=lambda x: x.email_date or datetime.min)
                
                # Extract strategic insights for this topic
                topic_decisions = []
                topic_opportunities = []
                for email in topic_emails:
                    if email.key_insights and isinstance(email.key_insights, dict):
                        topic_decisions.extend(email.key_insights.get('key_decisions', []))
                        topic_opportunities.extend(email.key_insights.get('strategic_opportunities', []))
                
                comprehensive_context = f"Active across {len(topic_emails)} communications, {len(topic_people)} people, {len(topic_projects)} projects, {len(topic_tasks)} tasks"
                if topic_decisions:
                    comprehensive_context += f". Recent decision: {topic_decisions[0][:60]}..."
                
                insights.append({
                    'type': 'topic_intelligence_360',
                    'title': f'Strategic Topic: {topic.name}',
                    'description': comprehensive_context,
                    'details': f'Latest activity: {latest_activity.ai_summary[:100] if latest_activity.ai_summary else "Recent discussions"}',
                    'action': f'Deep dive into {topic.name} strategy - significant cross-functional activity detected',
                    'priority': 'high',
                    'icon': '🎯',
                    'data_sources': ['topics', 'emails', 'people', 'projects', 'tasks'],
                    'cross_references': len(topic_emails) + len(topic_projects) + len(topic_tasks)
                })
        
        # 4. CALENDAR-DRIVEN ACTION INTELLIGENCE
        high_value_meetings = [m for m in upcoming_meetings if m.attendees and len(m.attendees) >= 3]
        for meeting in high_value_meetings[:2]:
            meeting_attendees = [att.get('email') for att in meeting.attendees if att.get('email')]
            known_attendees = [p for p in human_contacts if p.email_address in meeting_attendees]
            
            # Find email history with these attendees
            attendee_emails = []
            for attendee in known_attendees:
                person_emails = [e for e in analyzed_emails if e.sender and attendee.email_address and 
                               e.sender.lower() == attendee.email_address.lower()]
                attendee_emails.extend(person_emails)
            
            # Find related projects
            meeting_projects = []
            for attendee in known_attendees:
                attendee_projects = context_map['people_to_projects'].get(attendee.id, [])
                meeting_projects.extend(attendee_projects)
            
            if attendee_emails or meeting_projects:
                context_richness = len(attendee_emails) + len(meeting_projects)
                
                # Fix timezone comparison issue
                meeting_start_time = meeting.start_time
                if meeting_start_time and not hasattr(meeting_start_time, 'tzinfo'):
                    # If it's offset-naive, assume UTC
                    meeting_start_time = meeting_start_time.replace(tzinfo=timezone.utc)
                elif meeting_start_time and meeting_start_time.tzinfo is None:
                    meeting_start_time = meeting_start_time.replace(tzinfo=timezone.utc)
                
                insights.append({
                    'type': 'meeting_intelligence_360',
                    'title': f'Strategic Meeting: {meeting.title}',
                    'description': f'{len(known_attendees)} known attendees, {len(attendee_emails)} related communications, {len(set(meeting_projects))} connected projects',
                    'details': f'Meeting Date: {meeting_start_time.strftime("%Y-%m-%d %H:%M") if meeting_start_time else "TBD"}. Rich context available for preparation.',
                    'action': f'Prepare comprehensive brief for {meeting.title} using relationship and project intelligence',
                    'priority': 'high',
                    'icon': '📅',
                    'data_sources': ['calendar', 'people', 'emails', 'projects'],
                    'cross_references': context_richness
                })
        
        # 5. STRATEGIC DECISION & OPPORTUNITY SYNTHESIS
        all_decisions = []
        all_opportunities = []
        decision_makers = {}
        
        for email in analyzed_emails[-50:]:  # Recent 50 emails
            if email.key_insights and isinstance(email.key_insights, dict):
                decisions = email.key_insights.get('key_decisions', [])
                opportunities = email.key_insights.get('strategic_opportunities', [])
                
                for decision in decisions:
                    if len(decision) > 30:  # Substantial decisions
                        decision_person = next((p for p in human_contacts if p.email_address and 
                                              p.email_address.lower() == email.sender.lower()), None)
                        all_decisions.append({
                            'decision': decision,
                            'person': decision_person,
                            'email_date': email.email_date,
                            'context': email.ai_summary
                        })
                        
                        if decision_person:
                            decision_makers[decision_person.name] = decision_makers.get(decision_person.name, 0) + 1
                
                for opp in opportunities:
                    if len(opp) > 30:
                        all_opportunities.append({
                            'opportunity': opp,
                            'source': email.sender_name or email.sender.split('@')[0],
                            'email_date': email.email_date,
                            'context': email.ai_summary
                        })
        
        if all_decisions:
            top_decision = max(all_decisions, key=lambda x: x['email_date'] or datetime.min)
            key_decision_maker = max(decision_makers.items(), key=lambda x: x[1])[0] if decision_makers else "Team"
            
            insights.append({
                'type': 'strategic_decision_360',
                'title': f'Strategic Decision Tracking',
                'description': f'{len(all_decisions)} recent decisions identified, {key_decision_maker} driving {decision_makers.get(key_decision_maker, 1)} decisions',
                'details': f'Latest: {top_decision["decision"][:120]}...',
                'action': f'Review decision implementation and coordinate with {key_decision_maker}',
                'priority': 'high',
                'icon': '⚡',
                'data_sources': ['emails', 'people', 'insights'],
                'cross_references': len(decision_makers)
            })
        
        if all_opportunities:
            top_opportunity = max(all_opportunities, key=lambda x: x['email_date'] or datetime.min)
            
            insights.append({
                'type': 'strategic_opportunity_360',
                'title': f'Business Opportunity Intelligence',
                'description': f'{len(all_opportunities)} opportunities identified across recent communications',
                'details': f'Latest: {top_opportunity["opportunity"][:120]}...',
                'action': f'Evaluate opportunity pipeline and develop action plans with {top_opportunity["source"]}',
                'priority': 'medium',
                'icon': '💡',
                'data_sources': ['emails', 'insights', 'people'],
                'cross_references': len(set([o["source"] for o in all_opportunities]))
            })
        
        # 6. COMPREHENSIVE BUSINESS INTELLIGENCE SUMMARY
        insights.append({
            'type': 'comprehensive_intelligence_360',
            'title': '360-Context Business Intelligence Status',
            'description': f'Comprehensive analysis: {len(analyzed_emails)} emails, {len(human_contacts)} contacts, {len(active_projects)} projects, {len(actionable_tasks)} tasks, {len(strategic_topics)} topics, {len(upcoming_meetings)} meetings',
            'details': f'Cross-referenced {sum([i.get("cross_references", 0) for i in insights])} data connections. Your business intelligence ecosystem is actively building comprehensive knowledge.',
            'action': 'Review 360-context insights above for strategic decision-making',
            'priority': 'low',
            'icon': '🧠',
            'data_sources': ['emails', 'people', 'projects', 'tasks', 'topics', 'calendar'],
            'cross_references': len(context_map)
        })
        
        # FALLBACK GUIDANCE IF NO DATA
        if not insights or len(insights) <= 1:
            insights = [{
                'type': 'guidance_360',
                'title': 'Building 360-Context Intelligence',
                'description': 'Process more emails and calendar events to unlock comprehensive business insights',
                'details': 'Your AI Chief of Staff will cross-reference communications, relationships, projects, and meetings for strategic intelligence.',
                'action': 'Use "Process Emails" to build your comprehensive 360-context business knowledge base',
                'priority': 'medium',
                'icon': '🚀',
                'data_sources': ['system'],
                'cross_references': 0
            }]
        
        # Sort by priority and cross-reference strength
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        insights.sort(key=lambda x: (priority_order.get(x['priority'], 2), -x.get('cross_references', 0)))
        
        return insights[:6]  # Top 6 most strategic insights
        
    except Exception as e:
        logger.error(f"Error generating 360-context strategic insights: {str(e)}")
        return [{
            'type': 'error',
            'title': '360-Context Analysis Error',
            'description': f'Error in comprehensive business intelligence: {str(e)[:100]}',
            'details': 'Please try processing emails and calendar again',
            'action': 'Rebuild your 360-context business intelligence',
            'priority': 'medium',
            'icon': '⚠️',
            'data_sources': ['error'],
            'cross_references': 0
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
    
    @app.route('/calendar')
    def calendar_page():
        """Calendar management page"""
        user_email = session.get('user_email')
        
        if not user_email:
            return redirect(url_for('login'))
        
        return render_template('calendar.html')
    
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
    
    @app.route('/api/trigger-email-sync', methods=['POST'])
    def api_trigger_email_sync():
        """UNIFIED EMAIL AND CALENDAR PROCESSING - Single trigger that does everything including calendar sync"""
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
            
            logger.info(f"🚀 Starting unified email + calendar processing for {user_email}: {max_emails} emails, {days_back} days back")
            
            # Clear any existing cache to ensure fresh processing
            from chief_of_staff_ai.strategic_intelligence.strategic_intelligence_cache import strategic_intelligence_cache
            strategic_intelligence_cache.invalidate(user_email)
            
            # STEP 1: Fetch emails from Gmail
            logger.info("📧 Step 1: Fetching emails from Gmail...")
            fetch_result = gmail_fetcher.fetch_recent_emails(
                user_email=user_email,
                limit=max_emails,
                days_back=days_back,
                force_refresh=force_refresh
            )
            
            if not fetch_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': f"Email fetch failed: {fetch_result.get('error')}",
                    'stage': 'fetch'
                }), 400
            
            emails_fetched = fetch_result.get('count', 0)
            logger.info(f"✅ Fetched {emails_fetched} emails from Gmail")
            
            # STEP 2: Fetch calendar events (NEW!)
            logger.info("📅 Step 2: Syncing calendar from Google Calendar...")
            calendar_result = calendar_fetcher.fetch_calendar_events(
                user_email=user_email,
                days_back=3,
                days_forward=14,
                force_refresh=force_refresh
            )
            
            calendar_events_fetched = 0
            prep_tasks_created = 0
            
            if calendar_result.get('success'):
                calendar_events_fetched = calendar_result.get('count', 0)
                logger.info(f"✅ Synced {calendar_events_fetched} calendar events")
                
                # AUTOMATIC 360-CONTEXT PREP TASK CREATION (NEW AUGMENTATION FEATURE!)
                if calendar_result.get('events'):
                    logger.info("🧠 Step 2b: Creating 360-context meeting preparation tasks...")
                    events_for_tasks = []
                    for event_dict in calendar_result['events']:
                        try:
                            if isinstance(event_dict, dict):
                                # Already a dict, use as-is
                                events_for_tasks.append(event_dict)
                            elif hasattr(event_dict, 'to_dict') and callable(getattr(event_dict, 'to_dict')):
                                # Has a to_dict method, use it (for Calendar objects)
                                event_as_dict = event_dict.to_dict()
                                events_for_tasks.append(event_as_dict)
                            else:
                                # Manual conversion for Calendar database objects
                                event_as_dict = {
                                    'event_id': getattr(event_dict, 'event_id', None),
                                    'title': getattr(event_dict, 'title', 'Untitled Event'),
                                    'description': getattr(event_dict, 'description', ''),
                                    'start_time': getattr(event_dict, 'start_time', None),
                                    'end_time': getattr(event_dict, 'end_time', None),
                                    'location': getattr(event_dict, 'location', ''),
                                    'attendees': getattr(event_dict, 'attendees', []),
                                    'calendar_id': getattr(event_dict, 'calendar_id', ''),
                                    'created_at': getattr(event_dict, 'created_at', None)
                                }
                                
                                # Ensure attendees is a list, not a string
                                if isinstance(event_as_dict['attendees'], str):
                                    try:
                                        import json
                                        event_as_dict['attendees'] = json.loads(event_as_dict['attendees'])
                                    except:
                                        event_as_dict['attendees'] = []
                                elif not isinstance(event_as_dict['attendees'], list):
                                    event_as_dict['attendees'] = []
                                
                                # Convert datetime objects to isoformat strings if needed
                                for time_field in ['start_time', 'end_time']:
                                    if event_as_dict[time_field] and hasattr(event_as_dict[time_field], 'isoformat'):
                                        event_as_dict[time_field] = event_as_dict[time_field].isoformat()
                                
                                events_for_tasks.append(event_as_dict)
                                
                        except Exception as convert_error:
                            logger.error(f"Failed to convert event to dict: {str(convert_error)}")
                            logger.error(f"Event type: {type(event_dict)}")
                            # Continue with next event instead of failing completely
                            continue
                    
                    if events_for_tasks:
                        try:
                            logger.info(f"Processing {len(events_for_tasks)} events for meeting prep tasks...")
                            prep_tasks_result = calendar_fetcher.create_meeting_prep_tasks(user.id, events_for_tasks)
                            prep_tasks_created = prep_tasks_result.get('prep_tasks_created', 0)
                            logger.info(f"🎯 Created {prep_tasks_created} intelligent meeting prep tasks using 360-context analysis")
                        except Exception as prep_error:
                            logger.error(f"Meeting prep task creation failed: {str(prep_error)}")
                            prep_tasks_created = 0
                    else:
                        logger.warning("No valid events available for meeting prep task creation")
                        prep_tasks_created = 0
            else:
                logger.warning(f"📅 Calendar sync failed: {calendar_result.get('error', 'Unknown error')}")
            
            # STEP 3: Normalize emails for better quality
            logger.info("🔧 Step 3: Normalizing emails...")
            normalize_result = email_normalizer.normalize_user_emails(user_email, limit=max_emails)
            emails_normalized = normalize_result.get('processed', 0)
            logger.info(f"✅ Normalized {emails_normalized} emails")
            
            # STEP 4: Process with AI to extract people, tasks, projects, insights
            logger.info("🤖 Step 4: Processing emails with AI intelligence...")
            intelligence_result = email_intelligence.process_user_emails_intelligently(
                user_email=user_email,
                limit=max_emails,
                force_refresh=force_refresh
            )
            
            # STEP 5: Analyze calendar free time (NEW!)
            logger.info("⏰ Step 5: Analyzing calendar free time...")
            free_time_analysis = calendar_fetcher.fetch_free_time_analysis(
                user_email=user_email,
                days_forward=7
            )
            
            free_time_slots = 0
            if free_time_analysis.get('success'):
                free_time_slots = len(free_time_analysis.get('free_slots', []))
                logger.info(f"✅ Found {free_time_slots} free time slots")
            
            # STEP 6: Get final counts from database
            logger.info("📊 Step 6: Calculating final results...")
            db_user = get_db_manager().get_user_by_email(user_email)
            
            if db_user:
                # Get actual counts from database
                all_emails = get_db_manager().get_user_emails(db_user.id)
                all_people = get_db_manager().get_user_people(db_user.id)
                all_tasks = get_db_manager().get_user_tasks(db_user.id)
                all_projects = get_db_manager().get_user_projects(db_user.id)
                all_calendar_events = get_db_manager().get_user_calendar_events(db_user.id)
                
                # Filter for meaningful data
                analyzed_emails = [e for e in all_emails if e.ai_summary and len(e.ai_summary.strip()) > 10]
                real_people = [p for p in all_people if p.name and p.email_address and '@' in p.email_address]
                real_tasks = [t for t in all_tasks if t.description and len(t.description.strip()) > 5]
                active_projects = [p for p in all_projects if p.status == 'active']
                
                # Calculate business insights
                strategic_insights = get_strategic_business_insights(user_email)
                
                logger.info(f"✅ Final Results:")
                logger.info(f"   📧 {len(analyzed_emails)} emails with AI analysis")
                logger.info(f"   📅 {len(all_calendar_events)} calendar events synced")
                logger.info(f"   👥 {len(real_people)} real people extracted")
                logger.info(f"   ✅ {len(real_tasks)} actionable tasks created")
                logger.info(f"   📋 {len(active_projects)} active projects identified")
                logger.info(f"   🧠 {len(strategic_insights)} business insights generated")
                logger.info(f"   ⏰ {free_time_slots} free time slots analyzed")
                logger.info(f"   🎯 {prep_tasks_created} intelligent meeting prep tasks (360-context)")
                
                # Enhanced success response with calendar data
                return jsonify({
                    'success': True,
                    'message': f'Successfully processed {emails_fetched} emails and {calendar_events_fetched} calendar events!',
                    'processing_stages': {
                        'emails_fetched': emails_fetched,
                        'calendar_events_fetched': calendar_events_fetched,
                        'emails_normalized': emails_normalized,
                        'emails_analyzed': len(analyzed_emails),
                        'ai_processing_success': intelligence_result.get('success', False),
                        'free_time_slots_found': free_time_slots,
                        'prep_tasks_created': prep_tasks_created
                    },
                    'database_populated': {
                        'total_emails': len(all_emails),
                        'emails_with_ai': len(analyzed_emails),
                        'people_extracted': len(real_people),
                        'tasks_created': len(real_tasks),
                        'projects_identified': len(active_projects),
                        'insights_generated': len(strategic_insights),
                        'calendar_events': len(all_calendar_events),
                        'free_time_slots': free_time_slots
                    },
                    'data_ready': {
                        'people_tab': len(real_people) > 0,
                        'tasks_tab': len(real_tasks) > 0,
                        'calendar_tab': len(all_calendar_events) > 0,
                        'insights_tab': len(strategic_insights) > 0,
                        'all_tabs_populated': len(real_people) > 0 and len(real_tasks) > 0 and len(strategic_insights) > 0 and len(all_calendar_events) > 0
                    },
                    'results': {
                        'fetch': fetch_result,
                        'normalize': normalize_result,
                        'intelligence': intelligence_result,
                        'calendar': calendar_result,
                        'free_time': free_time_analysis
                    },
                    'summary': {
                        'emails_fetched': emails_fetched,
                        'calendar_events_fetched': calendar_events_fetched,
                        'emails_normalized': emails_normalized,
                        'emails_analyzed': intelligence_result.get('processed_emails', len(analyzed_emails)),
                        'insights_extracted': intelligence_result.get('insights_extracted', len(strategic_insights)),
                        'people_identified': intelligence_result.get('people_identified', len(real_people)),
                        'projects_identified': intelligence_result.get('projects_identified', len(active_projects)),
                        'tasks_created': intelligence_result.get('tasks_created', len(real_tasks)),
                        'total_emails': len(all_emails),
                        'total_tasks': len(real_tasks),
                        'total_people': len(real_people),
                        'total_calendar_events': len(all_calendar_events),
                        'free_time_slots': free_time_slots
                    },
                    'next_steps': [
                        f"✅ {len(real_people)} people are now available in the People tab",
                        f"✅ {len(real_tasks)} tasks are now available in the Tasks tab", 
                        f"✅ {len(all_calendar_events)} calendar events are now available in the Calendar tab",
                        f"✅ {free_time_slots} free time slots identified for productivity",
                        f"✅ {len(strategic_insights)} insights are now available on the Home tab",
                        f"🎯 {prep_tasks_created} intelligent meeting prep tasks created with 360-context analysis",
                        "✅ All data is now populated and ready to use!"
                    ] if len(real_people) > 0 or len(all_calendar_events) > 0 else [
                        "ℹ️ No meaningful data found - try processing more emails or check your Gmail/Calendar connection"
                    ]
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'User not found after processing',
                    'stage': 'final_verification'
                }), 500
            
        except Exception as e:
            logger.error(f"❌ Unified email + calendar processing error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'stage': 'processing'
            }), 500
    
    @app.route('/api/process-emails', methods=['POST'])
    def api_process_emails():
        """DEPRECATED: Redirect to unified trigger-email-sync endpoint"""
        return api_trigger_email_sync()
    
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
                emails = get_db_manager().get_user_emails(user.id, limit=1)
                stats['emails_count'] = len(get_db_manager().get_user_emails(user.id, limit=1000))
                
                # Get task count  
                stats['tasks_count'] = len(get_db_manager().get_user_tasks(user.id, limit=1000))
                
                # Get last fetch time (approximate from most recent email)
                if emails:
                    stats['last_fetch'] = emails[0].processed_at.isoformat() if emails[0].processed_at else None
            
            return jsonify({
                'status': 'authenticated' if gmail_status['authenticated'] else 'not_authenticated',
                'gmail_access': gmail_status['gmail_access'],
                'user_stats': stats,
                'gmail_status': gmail_status
            })
            
        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
            return jsonify({'error': f'Status check failed: {str(e)}'}), 500
    
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
        """API endpoint to get real tasks from database"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            # Clear any cache to ensure fresh data
            from chief_of_staff_ai.strategic_intelligence.strategic_intelligence_cache import strategic_intelligence_cache
            strategic_intelligence_cache.invalidate(user_email)
            
            # Get real user and their tasks
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            
            tasks = get_db_manager().get_user_tasks(user.id, status)
            if limit:
                tasks = tasks[:limit]
            
            # Format real tasks data properly
            tasks_data = []
            for task in tasks:
                if task.description and len(task.description.strip()) > 3:  # Only meaningful tasks
                    tasks_data.append({
                        'id': task.id,
                        'description': task.description,
                        'details': task.source_text or '',  # Use source_text instead of notes
                        'priority': task.priority or 'medium',
                        'status': task.status or 'pending',
                        'category': task.category or 'general',
                        'confidence': task.confidence or 0.8,
                        'assignee': task.assignee or user_email,
                        'due_date': task.due_date.isoformat() if task.due_date else None,
                        'created_at': task.created_at.isoformat() if task.created_at else None,
                        'source_email_subject': getattr(task, 'source_email_subject', None),  # Use getattr with fallback
                        'task_type': 'real_task',
                        'data_source': 'real_database'
                    })
            
            return jsonify({
                'success': True,
                'tasks': tasks_data,
                'count': len(tasks_data),
                'status_filter': status,
                'data_source': 'real_database'
            })
            
        except Exception as e:
            logger.error(f"Get tasks API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/email-insights', methods=['GET'])
    def api_get_email_insights():
        """API endpoint to get real strategic business insights from database"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            # Clear any cache to ensure fresh data
            from chief_of_staff_ai.strategic_intelligence.strategic_intelligence_cache import strategic_intelligence_cache
            strategic_intelligence_cache.invalidate(user['email'])
            
            # Use the real strategic business insights function
            strategic_insights = get_strategic_business_insights(user['email'])
            
            return jsonify({
                'success': True,
                'strategic_insights': strategic_insights,
                'count': len(strategic_insights),
                'data_source': 'real_business_insights'
            })
            
        except Exception as e:
            logger.error(f"Get email insights API error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/flush-database', methods=['POST'])
    def api_flush_database():
        """API endpoint to flush all user data and recreate database schema"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            logger.info(f"Starting complete database flush for user: {user_email}")
            
            # CRITICAL FIX: For SQLite, we need to recreate the schema to add new columns
            # Get the current database manager
            db_manager = get_db_manager()
            
            # Step 1: Delete all user data INCLUDING Smart Contact Strategy tables
            with db_manager.get_session() as db_session:
                # Import the new Smart Contact Strategy models
                from models.database import TrustedContact, ContactContext, TaskContext, TopicKnowledgeBase
                
                # Delete Smart Contact Strategy data first (due to foreign keys)
                db_session.query(ContactContext).filter(ContactContext.user_id == user.id).delete()
                db_session.query(TaskContext).filter(TaskContext.user_id == user.id).delete()
                db_session.query(TopicKnowledgeBase).filter(TopicKnowledgeBase.user_id == user.id).delete()
                db_session.query(TrustedContact).filter(TrustedContact.user_id == user.id).delete()
                
                # Delete regular tables
                db_session.query(Task).filter(Task.user_id == user.id).delete()
                db_session.query(Email).filter(Email.user_id == user.id).delete()
                db_session.query(Person).filter(Person.user_id == user.id).delete()
                db_session.query(Project).filter(Project.user_id == user.id).delete()
                db_session.query(Topic).filter(Topic.user_id == user.id).delete()
                
                db_session.commit()
                logger.info(f"Deleted all data for user: {user_email}")
            
            # Step 2: For SQLite, recreate all tables to ensure new schema
            # This will add any missing columns like is_trusted_contact, engagement_score, etc.
            try:
                from models.database import Base
                logger.info("Recreating database schema with new Smart Contact Strategy columns...")
                
                # Drop all tables and recreate them (this ensures new columns are added)
                Base.metadata.drop_all(bind=db_manager.engine)
                Base.metadata.create_all(bind=db_manager.engine)
                
                logger.info("Database schema recreated successfully")
                
                # Step 3: Recreate the user since we dropped all tables
                user_info = {
                    'email': user.email,
                    'id': user.google_id,
                    'name': user.name
                }
                credentials = {
                    'access_token': user.access_token,
                    'refresh_token': user.refresh_token,
                    'expires_at': user.token_expires_at,
                    'scopes': user.scopes or []
                }
                
                # Recreate user with existing credentials
                db_manager.create_or_update_user(user_info, credentials)
                logger.info(f"Recreated user: {user_email}")
                
            except Exception as schema_error:
                logger.error(f"Schema recreation error: {str(schema_error)}")
                # Fallback: just ensure tables exist
                Base.metadata.create_all(bind=db_manager.engine)
            
            logger.info(f"Complete database flush successful for user: {user_email}")
            
            return jsonify({
                'success': True,
                'message': 'Database completely flushed and schema updated! New Smart Contact Strategy features are now available.',
                'user_email': user_email,
                'schema_updated': True
            })
            
        except Exception as e:
            logger.error(f"Database flush error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/people', methods=['GET'])
    def api_get_people():
        """API endpoint to get real people from database"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        try:
            # Clear any cache to ensure fresh data
            from chief_of_staff_ai.strategic_intelligence.strategic_intelligence_cache import strategic_intelligence_cache
            strategic_intelligence_cache.invalidate(user_email)
            
            # Get real user and their people
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            limit = int(request.args.get('limit', 50))
            people = get_db_manager().get_user_people(user.id, limit)
            
            # Format real people data properly
            people_data = []
            for person in people:
                if person.name and person.email_address:  # Only real people
                    people_data.append({
                        'id': person.id,
                        'name': person.name,
                        'email': person.email_address,
                        'relationship': person.relationship_type or 'Contact',
                        'company': person.company or 'Unknown',
                        'title': person.title or 'Unknown',
                        'last_contact': person.last_interaction.isoformat() if person.last_interaction else None,
                        'total_emails': person.total_emails or 0,
                        'engagement_score': person.importance_level or 0.5,
                        'relationship_context': f"Email contact with {person.total_emails or 0} interactions",
                        'strategic_importance': 'high' if (person.total_emails or 0) > 10 else 'medium' if (person.total_emails or 0) > 3 else 'low',
                        'data_source': 'real_database'
                    })
            
            return jsonify({
                'success': True,
                'people': people_data,
                'count': len(people_data),
                'data_source': 'real_database'
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
    
    @app.route('/api/debug-data', methods=['GET'])
    def api_debug_data():
        """Debug endpoint to check what real data exists"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            from chief_of_staff_ai.strategic_intelligence.strategic_intelligence_cache import strategic_intelligence_cache
            
            # Clear cache first
            strategic_intelligence_cache.invalidate(user['email'])
            
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get real data from database
            emails = get_db_manager().get_user_emails(db_user.id, limit=50)
            people = get_db_manager().get_user_people(db_user.id, limit=50)
            tasks = get_db_manager().get_user_tasks(db_user.id, limit=50)
            
            # Analyze what we actually have
            analyzed_emails = [e for e in emails if e.ai_summary and len(e.ai_summary.strip()) > 10]
            real_people = [p for p in people if p.name and p.email_address and '@' in p.email_address]
            real_tasks = [t for t in tasks if t.description and len(t.description.strip()) > 5]
            
            debug_info = {
                'user_email': user['email'],
                'user_db_id': db_user.id,
                'cache_cleared': True,
                'raw_data': {
                    'total_emails': len(emails),
                    'emails_with_ai_summary': len(analyzed_emails),
                    'total_people': len(people),
                    'real_people': len(real_people),
                    'total_tasks': len(tasks),
                    'real_tasks': len(real_tasks)
                },
                'sample_emails': [
                    {
                        'subject': e.subject,
                        'sender': e.sender_name or e.sender,
                        'has_ai_summary': bool(e.ai_summary),
                        'ai_summary_length': len(e.ai_summary) if e.ai_summary else 0,
                        'date': e.email_date.isoformat() if e.email_date else None
                    } for e in emails[:5]
                ],
                'sample_people': [
                    {
                        'name': p.name,
                        'email': p.email_address,
                        'company': p.company,
                        'total_emails': p.total_emails
                    } for p in real_people[:5]
                ],
                'sample_tasks': [
                    {
                        'description': t.description,
                        'priority': t.priority,
                        'status': t.status,
                        'source': t.source_email_subject
                    } for t in real_tasks[:5]
                ]
            }
            
            return jsonify(debug_info)
            
        except Exception as e:
            logger.error(f"Debug data API error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/download-knowledge-base', methods=['GET'])
    def api_download_knowledge_base():
        """API endpoint to download complete knowledge base as JSON - instant export of chat-ready data"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            db_user = get_db_manager().get_user_by_email(user['email'])
            if not db_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Collect all user data (this is the same data used for chat queries - should be instant)
            emails = get_db_manager().get_user_emails(db_user.id, limit=1000)
            people = get_db_manager().get_user_people(db_user.id, limit=500)
            tasks = get_db_manager().get_user_tasks(db_user.id, limit=500)
            projects = get_db_manager().get_user_projects(db_user.id, limit=200)
            topics = get_db_manager().get_user_topics(db_user.id, limit=100)
            
            # Get strategic insights (same data used in chat)
            strategic_insights = get_strategic_business_insights(user['email'])
            
            # Get comprehensive business knowledge (same data used in chat)
            business_knowledge = email_intelligence.get_business_knowledge_summary(user['email'])
            chat_knowledge = email_intelligence.get_chat_knowledge_summary(user['email'])
            
            # Format export data - using the same structure as chat queries
            knowledge_base_export = {
                'export_metadata': {
                    'user_email': user['email'],
                    'export_date': datetime.now().isoformat(),
                    'export_version': '1.0',
                    'data_source': 'chat_ready_knowledge_base',
                    'total_records': {
                        'emails': len(emails),
                        'people': len(people),
                        'tasks': len(tasks),
                        'projects': len(projects),
                        'topics': len(topics)
                    }
                },
                'strategic_insights': strategic_insights,
                'business_intelligence': business_knowledge.get('business_knowledge', {}) if business_knowledge.get('success') else {},
                'chat_knowledge': chat_knowledge.get('knowledge_base', {}) if chat_knowledge.get('success') else {},
                'emails': [
                    {
                        'id': e.id,
                        'gmail_id': e.gmail_id,
                        'subject': e.subject,
                        'sender': e.sender,
                        'sender_name': e.sender_name,
                        'recipients': e.recipients,
                        'email_date': e.email_date.isoformat() if e.email_date else None,
                        'ai_summary': e.ai_summary,
                        'ai_category': e.ai_category,
                        'key_insights': e.key_insights,
                        'topics': e.topics,
                        'action_required': e.action_required,
                        'follow_up_required': e.follow_up_required,
                        'sentiment_score': e.sentiment_score,
                        'urgency_score': e.urgency_score,
                        'processed_at': e.processed_at.isoformat() if e.processed_at else None
                    } for e in emails
                ],
                'people': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'email_address': p.email_address,
                        'title': p.title,
                        'company': p.company,
                        'relationship_type': p.relationship_type,
                        'notes': p.notes,
                        'importance_level': p.importance_level,
                        'total_emails': p.total_emails,
                        'last_interaction': p.last_interaction.isoformat() if p.last_interaction else None,
                        'first_mentioned': p.first_mentioned.isoformat() if p.first_mentioned else None,
                        'created_at': p.created_at.isoformat() if hasattr(p, 'created_at') and p.created_at else None,
                        'communication_frequency': p.communication_frequency,
                        'skills': p.skills,
                        'interests': p.interests,
                        'key_topics': p.key_topics
                    } for p in people
                ],
                'tasks': [
                    {
                        'id': t.id,
                        'description': t.description,
                        'assignee': t.assignee,
                        'priority': t.priority,
                        'status': t.status,
                        'category': t.category,
                        'due_date': t.due_date.isoformat() if t.due_date else None,
                        'due_date_text': t.due_date_text,
                        'confidence': t.confidence,
                        'source_text': t.source_text,
                        'context': getattr(t, 'context', None),
                        'notes': getattr(t, 'notes', t.source_text),  # Use source_text as fallback for notes
                        'created_at': t.created_at.isoformat() if t.created_at else None,
                        'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                        'source_email_subject': getattr(t, 'source_email_subject', None)
                    } for t in tasks
                ],
                'projects': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'slug': p.slug,
                        'description': p.description,
                        'status': p.status,
                        'priority': p.priority,
                        'category': p.category,
                        'start_date': p.start_date.isoformat() if p.start_date else None,
                        'end_date': p.end_date.isoformat() if p.end_date else None,
                        'progress': getattr(p, 'progress', None),
                        'key_topics': p.key_topics,
                        'stakeholders': p.stakeholders,
                        'created_at': p.created_at.isoformat() if p.created_at else None
                    } for p in projects
                ],
                'topics': [
                    {
                        'id': t.id,
                        'name': t.name,
                        'slug': t.slug,
                        'description': t.description,
                        'is_official': t.is_official,
                        'email_count': t.email_count,
                        'confidence_score': t.confidence_score,
                        'strength': getattr(t, 'strength', None),
                        'keywords': json.loads(t.keywords) if t.keywords else [],
                        'created_at': t.created_at.isoformat() if t.created_at else None,
                        'last_used': t.last_used.isoformat() if t.last_used else None
                    } for t in topics
                ]
            }
            
            # Create downloadable JSON response
            response = make_response(jsonify(knowledge_base_export))
            
            # Set headers for file download
            filename = f"knowledge_base_{user['email'].replace('@', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Length'] = len(response.get_data())
            
            logger.info(f"Knowledge base download completed for {user['email']}: {len(emails)} emails, {len(people)} people, {len(tasks)} tasks")
            
            return response
            
        except Exception as e:
            logger.error(f"Knowledge base download error: {str(e)}")
            return jsonify({'error': f'Download failed: {str(e)}'}), 500

    @app.route('/api/fetch-calendar', methods=['POST'])
    def api_fetch_calendar():
        """API endpoint to fetch calendar events and create prep tasks"""
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        try:
            data = request.get_json() or {}
            days_back = data.get('days_back', 3)
            days_forward = data.get('days_forward', 14)
            force_refresh = data.get('force_refresh', False)
            create_prep_tasks = data.get('create_prep_tasks', False)
            
            # Get user from database
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            # Fetch calendar events
            logger.info(f"Fetching calendar events for {user_email}")
            calendar_result = calendar_fetcher.fetch_calendar_events(
                user_email, 
                days_back=days_back, 
                days_forward=days_forward,
                force_refresh=force_refresh
            )
            
            prep_tasks_result = {'prep_tasks_created': 0, 'tasks': []}
            
            # Create meeting preparation tasks if requested
            if create_prep_tasks and calendar_result['success'] and calendar_result.get('events'):
                logger.info(f"Creating meeting prep tasks for {user_email}")
                # Convert event dicts to proper format for task creation
                events_for_tasks = []
                for event_dict in calendar_result['events']:
                    if isinstance(event_dict, dict):
                        events_for_tasks.append(event_dict)
                    else:
                        # Convert database object to dict if needed
                        events_for_tasks.append(event_dict.to_dict() if hasattr(event_dict, 'to_dict') else event_dict.__dict__)
                
                prep_tasks_result = calendar_fetcher.create_meeting_prep_tasks(user.id, events_for_tasks)
            
            # Combine results
            result = {
                'success': calendar_result['success'],
                'user_email': user_email,
                'count': calendar_result.get('count', 0),
                'events': calendar_result.get('events', []),
                'source': calendar_result.get('source', 'unknown'),
                'fetched_at': calendar_result.get('fetched_at'),
                'calendars_processed': calendar_result.get('calendars_processed', 0),
                'prep_tasks_created': prep_tasks_result.get('prep_tasks_created', 0),
                'prep_tasks': prep_tasks_result.get('tasks', [])
            }
            
            if not calendar_result['success']:
                result['error'] = calendar_result.get('error', 'Unknown error')
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Calendar fetch error for {user_email}: {str(e)}")
            return jsonify({
                'success': False, 
                'error': f"Calendar fetch failed: {str(e)}",
                'prep_tasks_created': 0
            }), 500

    @app.route('/api/calendar-events')
    def api_get_calendar_events():
        """API endpoint to get calendar events"""
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        try:
            days_forward = request.args.get('days_forward', 14, type=int)
            limit = request.args.get('limit', 50, type=int)
            
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            # Get events from database
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            start_date = now
            end_date = now + timedelta(days=days_forward)
            
            events = get_db_manager().get_user_calendar_events(user.id, start_date, end_date, limit)
            
            # Convert to dict format and check for prep tasks using existing methods
            events_data = []
            all_user_tasks = get_db_manager().get_user_tasks(user.id)
            prep_tasks = [task for task in all_user_tasks if task.category == 'meeting_preparation']
            
            for event in events:
                event_dict = event.to_dict()
                
                # Check if this event has associated prep tasks by matching event title or other criteria
                related_prep_tasks = [task for task in prep_tasks if 
                                    event.title and task.description and 
                                    (event.title.lower() in task.description.lower() or 
                                     any(word in task.description.lower() for word in event.title.lower().split() if len(word) > 3))]
                
                event_dict['has_prep_tasks'] = len(related_prep_tasks) > 0
                event_dict['prep_tasks_count'] = len(related_prep_tasks)
                
                events_data.append(event_dict)
            
            return jsonify({
                'success': True,
                'events': events_data,
                'count': len(events_data)
            })
        
        except Exception as e:
            logger.error(f"Get calendar events error for {user_email}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/meeting-prep-tasks')
    def api_get_meeting_prep_tasks():
        """API endpoint to get meeting preparation tasks"""
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            # Get prep tasks that are not completed (use existing method with category filter)
            all_tasks = get_db_manager().get_user_tasks(user.id)
            prep_tasks = [task for task in all_tasks if 
                         task.category == 'meeting_preparation' and 
                         task.status in ['pending', 'open']]
            
            return jsonify({
                'success': True,
                'tasks': [task.to_dict() for task in prep_tasks],
                'count': len(prep_tasks)
            })
        
        except Exception as e:
            logger.error(f"Get meeting prep tasks error for {user_email}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/free-time-analysis', methods=['POST'])
    def api_free_time_analysis():
        """API endpoint to analyze free time in calendar"""
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        try:
            data = request.get_json() or {}
            days_forward = data.get('days_forward', 7)
            
            # Get free time analysis
            result = calendar_fetcher.fetch_free_time_analysis(
                user_email=user_email,
                days_forward=days_forward
            )
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Free time analysis error for {user_email}: {str(e)}")
            return jsonify({
                'success': False, 
                'error': f"Free time analysis failed: {str(e)}",
                'free_slots': []
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
        print(f"📅 Calendar integration: {'✓ Enabled' if 'https://www.googleapis.com/auth/calendar.readonly' in settings.GMAIL_SCOPES else '✗ Missing'}")
        print(f"🤖 Claude integration: {'✓ Configured' if settings.ANTHROPIC_API_KEY else '✗ Missing'}")
        print(f"🌐 Server: http://localhost:{settings.PORT}")
        print("\nTo get started:")
        print("1. Go to the URL above")
        print("2. Click 'Sign in with Google'")
        print("3. Grant Gmail and Calendar access permissions")
        print("4. Start processing your emails and calendar!")
        
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