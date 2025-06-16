#!/usr/bin/env python3
"""
AI Chief of Staff - Flask Web Application (Refactored & Clean)

This is the cleaned-up main application that provides:
1. Google OAuth authentication with Gmail access
2. Web interface for managing emails and tasks
3. Core Flask setup with modular API blueprints
4. Integration with Claude 4 Sonnet for intelligent assistance

Note: ALL API routes are now handled by modular blueprints in api/routes/
"""

import os
import sys
import logging
from datetime import timedelta, datetime, timezone
from flask import Flask, session, render_template, redirect, url_for, request, jsonify
from flask_session import Session
import tempfile
import time
import uuid
from typing import List, Dict

# Add CORS support for React dev server
from flask_cors import CORS

# Add the chief_of_staff_ai directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chief_of_staff_ai'))

try:
    from config.settings import settings
    from auth.gmail_auth import gmail_auth
    from models.database import get_db_manager
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
    FOCUSED STRATEGIC BUSINESS INTELLIGENCE WITH EMAIL QUALITY FILTERING
    
    Generate specific, actionable insights that help with:
    - Critical business decisions pending
    - Key relationships needing attention
    - Important projects with deadlines
    - Revenue/business opportunities
    - Risk factors requiring action
    
    Only high-value, actionable intelligence from QUALITY contacts.
    """
    try:
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter, ContactTier
        
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return []
        
        logger.info(f"🧠 Generating strategic insights with email quality filtering for {user_email}")
        
        # APPLY EMAIL QUALITY FILTERING - This is the key enhancement!
        tier_summary = email_quality_filter.get_contact_tier_summary(db_user.id)
        
        # Get ALL data first
        all_emails = get_db_manager().get_user_emails(db_user.id, limit=100)
        all_people = get_db_manager().get_user_people(db_user.id, limit=50)
        tasks = get_db_manager().get_user_tasks(db_user.id, limit=50)
        projects = get_db_manager().get_user_projects(db_user.id, limit=20)
        
        # Filter people by contact tiers (QUALITY FILTERING)
        quality_people = []
        tier_stats = {'tier_1': 0, 'tier_2': 0, 'tier_last_filtered': 0}
        
        for person in all_people:
            if person.name and person.email_address and '@' in person.email_address:
                contact_stats = email_quality_filter._get_contact_stats(person.email_address.lower(), db_user.id)
                
                if contact_stats.tier == ContactTier.TIER_LAST:
                    tier_stats['tier_last_filtered'] += 1
                    continue  # FILTER OUT low-quality contacts
                elif contact_stats.tier == ContactTier.TIER_1:
                    tier_stats['tier_1'] += 1
                    person.priority_weight = 2.0  # Give Tier 1 contacts higher weight
                elif contact_stats.tier == ContactTier.TIER_2:
                    tier_stats['tier_2'] += 1
                    person.priority_weight = 1.0
                else:
                    person.priority_weight = 0.5
                
                person.contact_tier = contact_stats.tier.value
                person.response_rate = contact_stats.response_rate
                quality_people.append(person)
        
        # Filter emails from quality contacts only
        quality_contact_emails = set()
        for person in quality_people:
            if person.email_address:
                quality_contact_emails.add(person.email_address.lower())
        
        quality_emails = []
        for email in all_emails:
            if email.sender and email.ai_summary:
                sender_email = email.sender.lower()
                if sender_email in quality_contact_emails or not sender_email:
                    quality_emails.append(email)
        
        logger.info(f"📊 Strategic insights filtering: {len(quality_emails)}/{len(all_emails)} emails, {len(quality_people)}/{len(all_people)} people (filtered out {tier_stats['tier_last_filtered']} Tier LAST)")
        
        # Use FILTERED data for insights
        analyzed_emails = [e for e in quality_emails if e.ai_summary and len(e.ai_summary.strip()) > 30]
        real_people = quality_people  # Already filtered for quality
        actionable_tasks = [t for t in tasks if t.description and len(t.description.strip()) > 15 and t.status == 'pending']
        active_projects = [p for p in projects if p.status == 'active']
        
        insights = []
        
        # 1. URGENT BUSINESS DECISIONS NEEDED (same logic, but with quality data)
        high_priority_tasks = [t for t in actionable_tasks if t.priority == 'high']
        if len(high_priority_tasks) >= 3:
            critical_tasks = [t.description[:80] + "..." for t in high_priority_tasks[:3]]
            insights.append({
                'type': 'critical_decisions',
                'title': f'{len(high_priority_tasks)} Critical Business Decisions Pending',
                'description': f'You have {len(high_priority_tasks)} high-priority tasks requiring immediate attention. Top priorities: {", ".join(critical_tasks[:2])}.',
                'details': f'Critical actions needed: {"; ".join([t.description for t in high_priority_tasks[:3]])}',
                'action': f'Review and prioritize these {len(high_priority_tasks)} critical decisions to prevent business impact',
                'priority': 'high',
                'icon': '🚨',
                'data_sources': ['tasks'],
                'cross_references': len(high_priority_tasks),
                'quality_filtered': True
            })
        
        # 2. KEY RELATIONSHIPS REQUIRING ATTENTION (enhanced with tier data)
        if real_people:
            # Prioritize Tier 1 contacts that haven't been contacted recently
            now = datetime.now(timezone.utc)
            stale_relationships = []
            
            for person in real_people:
                if person.last_interaction:
                    days_since_contact = (now - person.last_interaction).days
                    # Different thresholds based on tier
                    tier_threshold = 15 if getattr(person, 'contact_tier', '') == 'tier_1' else 30
                    
                    if (days_since_contact > tier_threshold and 
                        person.total_emails >= 5):
                        priority_weight = getattr(person, 'priority_weight', 1.0)
                        stale_relationships.append((person, days_since_contact, priority_weight))
            
            if stale_relationships:
                # Sort by tier priority and days since contact
                top_stale = sorted(stale_relationships, key=lambda x: (x[2], x[1]), reverse=True)[:2]
                person_summaries = [f"{p.name} ({p.company or 'Unknown'}) - {days} days [Tier {getattr(p, 'contact_tier', 'unknown').replace('tier_', '')}]" for p, days, weight in top_stale]
                
                insights.append({
                    'type': 'relationship_risk',
                    'title': f'{len(stale_relationships)} Important Relationships Need Attention',
                    'description': f'Key business contacts haven\'t been contacted recently: {", ".join(person_summaries)}',
                    'details': f'These relationships have {sum(p.total_emails for p, _, _ in top_stale)} total communications but have gone silent. Tier 1 contacts require more frequent engagement.',
                    'action': f'Reach out to {", ".join([p.name for p, _, _ in top_stale[:2]])} to maintain these valuable business relationships',
                    'priority': 'medium',
                    'icon': '🤝',
                    'data_sources': ['people', 'emails'],
                    'cross_references': len(stale_relationships),
                    'quality_filtered': True,
                    'tier_breakdown': {
                        'tier_1_count': tier_stats['tier_1'],
                        'tier_2_count': tier_stats['tier_2'],
                        'filtered_out': tier_stats['tier_last_filtered']
                    }
                })
        
        # 3. TIER 1 RELATIONSHIP INSIGHTS (new insight type)
        tier_1_people = [p for p in real_people if getattr(p, 'contact_tier', '') == 'tier_1']
        if tier_1_people and len(tier_1_people) >= 3:
            recent_tier_1_activity = [p for p in tier_1_people if p.last_interaction and (now - p.last_interaction).days <= 7]
            
            insights.append({
                'type': 'tier_1_focus',
                'title': f'{len(tier_1_people)} Tier 1 High-Value Relationships',
                'description': f'You have {len(tier_1_people)} high-engagement contacts with {len(recent_tier_1_activity)} recent interactions. These are your most valuable business relationships.',
                'details': f'Tier 1 contacts: {", ".join([p.name for p in tier_1_people[:5]])}. These contacts consistently engage with you and should be prioritized for strategic opportunities.',
                'action': f'Leverage these {len(tier_1_people)} high-value relationships for strategic initiatives and business development',
                'priority': 'medium',
                'icon': '👑',
                'data_sources': ['people', 'email_quality_filter'],
                'cross_references': len(tier_1_people),
                'quality_filtered': True,
                'tier_focus': 'tier_1'
            })
        
        # Filter out empty insights and sort by priority
        meaningful_insights = [i for i in insights if i.get('cross_references', 0) > 0]
        
        if not meaningful_insights:
            quality_summary = f"{len(quality_emails)} quality emails from {len(quality_people)} verified contacts"
            filtered_summary = f"(filtered out {tier_stats['tier_last_filtered']} low-quality contacts)"
            
            return [{
                'type': 'data_building',
                'title': 'Building Your Business Intelligence Foundation',
                'description': f'Processing {quality_summary} to identify strategic insights, critical decisions, and business opportunities.',
                'details': f'Current quality data: {quality_summary} {filtered_summary}. Continue processing emails to unlock comprehensive business intelligence.',
                'action': 'Use "Sync" to process more emails and build strategic business insights',
                'priority': 'medium',
                'icon': '🚀',
                'data_sources': ['system'],
                'cross_references': 0,
                'quality_filtered': True
            }]
        
        # Sort by business impact (priority + cross_references + quality filtering)
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        meaningful_insights.sort(key=lambda x: (priority_order.get(x['priority'], 1), x.get('cross_references', 0)), reverse=True)
        
        return meaningful_insights[:5]  # Top 5 most strategic insights
        
    except Exception as e:
        logger.error(f"Error generating strategic business insights: {str(e)}")
        return [{
            'type': 'error',
            'title': 'Business Intelligence Analysis Error',
            'description': f'Error analyzing business data: {str(e)[:80]}',
            'details': 'Please try syncing emails again to rebuild business intelligence',
            'action': 'Rebuild your business intelligence by syncing emails',
            'priority': 'medium',
            'icon': '⚠️',
            'data_sources': ['error'],
            'cross_references': 0,
            'quality_filtered': False
        }]

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = settings.SECRET_KEY
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'cos_flask_session')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
    
    # Configure CORS for React dev server
    CORS(app, supports_credentials=True, origins=["http://localhost:3000"])
    
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
            
            # For this request context, we can trust the session's user_id
            current_user = {'id': user_id, 'email': session['user_email']}
            return current_user
            
        except Exception as e:
            logger.error(f"Error retrieving current user from session: {e}")
            session.clear()
            return None
    
    # ================================
    # PAGE ROUTES (Redirect to React)
    # ================================
    
    @app.route('/')
    def index():
        """Always redirect to React app for UI"""
        return redirect('http://localhost:3000')
    
    @app.route('/home')
    def home():
        """Redirect to React app"""
        return redirect('http://localhost:3000')
    
    @app.route('/tasks')
    def tasks():
        """Redirect to React app"""
        return redirect('http://localhost:3000')
    
    @app.route('/people')
    def people_page():
        """Redirect to React app"""
        return redirect('http://localhost:3000')
    
    @app.route('/knowledge')
    def knowledge_page():
        """Redirect to React app"""
        return redirect('http://localhost:3000')
    
    @app.route('/calendar')
    def calendar_page():
        """Redirect to React app"""
        return redirect('http://localhost:3000')
    
    @app.route('/settings')
    def settings_page():
        """Redirect to React app"""
        return redirect('http://localhost:3000')
    
    @app.route('/dashboard')
    def dashboard():
        """Redirect to React app"""
        return redirect('http://localhost:3000')
    
    @app.route('/login')
    def login():
        """Login page with Google OAuth - simple HTML instead of missing template"""
        logged_out = request.args.get('logged_out') == 'true'
        force_logout = request.args.get('force_logout') == 'true'
        
        logout_message = ""
        if logged_out:
            logout_message = "<p style='color: green;'>✅ You have been logged out successfully.</p>"
        elif force_logout:
            logout_message = "<p style='color: orange;'>🔄 Session cleared. Please log in again.</p>"
        
        # Return simple HTML instead of missing template
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Chief of Staff - Login</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }}
                .container {{ max-width: 400px; margin: 0 auto; padding: 40px; background: #2a2a2a; border-radius: 10px; }}
                .btn {{ display: inline-block; padding: 15px 30px; background: #4285f4; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .btn:hover {{ background: #357ae8; }}
                h1 {{ color: #4285f4; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 AI Chief of Staff</h1>
                {logout_message}
                <p>Sign in with your Google account to access your AI Chief of Staff dashboard.</p>
                <a href="/auth/google" class="btn">🔐 Sign in with Google</a>
                <p><small>Secure authentication via Google OAuth</small></p>
            </div>
        </body>
        </html>
        """
    
    # ================================
    # AUTHENTICATION ROUTES
    # ================================
    
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
            response = redirect('http://localhost:3000?login_success=true&t=' + str(int(datetime.now().timestamp())))
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
    
    @app.route('/debug/session')
    def debug_session():
        """Debug session information"""
        return jsonify({
            'session_data': dict(session),
            'user_email': session.get('user_email'),
            'authenticated': session.get('authenticated'),
            'session_keys': list(session.keys())
        })
    
    # ================================
    # ERROR HANDLERS
    # ================================
    
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found'}), 404
        # Return simple text response instead of missing template
        return f"<h1>404 - Page Not Found</h1><p>The requested page could not be found.</p><a href='/'>Go Home</a>", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        # Return simple text response instead of missing template
        return f"<h1>500 - Internal Server Error</h1><p>Something went wrong. Please try again.</p><a href='/'>Go Home</a>", 500
    
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
    
    # Register API blueprints directly
    try:
        print("🔧 Attempting to import API blueprints...")
        print(f"📁 Current working directory: {os.getcwd()}")
        print(f"📁 Main file location: {os.path.dirname(os.path.abspath(__file__))}")
        
        # Ensure we're in the correct directory
        main_dir = os.path.dirname(os.path.abspath(__file__))
        if os.getcwd() != main_dir:
            os.chdir(main_dir)
            print(f"📁 Changed to main directory: {main_dir}")
        
        # CRITICAL: Ensure the current directory is FIRST in Python path
        # This prevents the chief_of_staff_ai/api directory from being imported instead
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        elif sys.path.index(current_dir) != 0:
            sys.path.remove(current_dir)
            sys.path.insert(0, current_dir)
        
        print(f"📁 Python path priority: {sys.path[:3]}")
        
        # Now import from the ROOT api directory (not chief_of_staff_ai/api)
        from api.routes.auth_routes import auth_bp
        print("✓ Imported auth_routes")
        
        from api.routes.email_routes import email_bp
        print("✓ Imported email_routes")
        
        from api.routes.settings_routes import settings_bp
        print("✓ Imported settings_routes")
        
        from api.routes.intelligence_routes import intelligence_bp
        print("✓ Imported intelligence_routes")
        
        from api.routes.task_routes import task_bp
        print("✓ Imported task_routes")
        
        from api.routes.people_routes import people_bp
        print("✓ Imported people_routes")
        
        from api.routes.topic_routes import topic_bp
        print("✓ Imported topic_routes")
        
        from api.routes.calendar_routes import calendar_bp
        print("✓ Imported calendar_routes")
        
        # Register all blueprints
        app.register_blueprint(auth_bp)
        app.register_blueprint(email_bp)
        app.register_blueprint(settings_bp)
        app.register_blueprint(intelligence_bp)
        app.register_blueprint(task_bp)
        app.register_blueprint(people_bp)
        app.register_blueprint(topic_bp)
        app.register_blueprint(calendar_bp)
        
        print("✅ Successfully registered 8 API blueprints")
        
    except ImportError as e:
        print(f"⚠️ Warning: Could not import API blueprints: {e}")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"📁 Directory contents: {os.listdir('.')[:10]}")
        print("✓ Running with page routes only (API endpoints disabled)")
    except Exception as e:
        print(f"⚠️ Warning: Error registering blueprints: {e}")
        print("✓ Running with page routes only (API endpoints disabled)")
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    try:
        # Validate settings
        config_errors = settings.validate_config()
        if config_errors:
            raise ValueError(f"Configuration errors: {', '.join(config_errors)}")
        
        print("🚀 Starting AI Chief of Staff Web Application (Refactored)")
        print(f"📧 Gmail integration: {'✓ Configured' if settings.GOOGLE_CLIENT_ID else '✗ Missing'}")
        print(f"📅 Calendar integration: {'✓ Enabled' if 'https://www.googleapis.com/auth/calendar.readonly' in settings.GMAIL_SCOPES else '✗ Missing'}")
        print(f"🤖 Claude integration: {'✓ Configured' if settings.ANTHROPIC_API_KEY else '✗ Missing'}")
        print(f"🧠 Enhanced Intelligence: ✓ Active")
        print(f"🔧 Modular Architecture: ✓ Active")
        print(f"🌐 Server: http://localhost:8080")
        
        app.run(host='localhost', port=8080, debug=False)
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1) 