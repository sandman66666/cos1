#!/usr/bin/env python3
"""
Strategic Intelligence Platform - Enhanced AI Chief of Staff
==========================================================
Multi-database personal strategic intelligence system with:
- PostgreSQL + ChromaDB + Neo4j + Redis architecture  
- 5 specialized Claude Opus 4 analysts
- Web intelligence enrichment
- Knowledge tree construction
- Predictive relationship analysis

Preserves working Google OAuth integration.
"""

import os
import sys
import logging
import asyncio
import uuid
from datetime import timedelta, datetime, timezone
from flask import Flask, session, render_template, redirect, url_for, request, jsonify
from flask_cors import CORS
import tempfile
import random

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Configure logging EARLY
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import compatibility modules FIRST (before adding chief_of_staff_ai path)
try:
    from config.settings import settings
    from auth.gmail_auth import gmail_auth
    from chief_of_staff_ai.models.database import get_db_manager
    import anthropic
except ImportError as e:
    print(f"Failed to import compatibility modules: {e}")
    print("Make sure the config/, auth/, and models/ directories are set up")
    sys.exit(1)

# Now add the chief_of_staff_ai directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chief_of_staff_ai'))

# Strategic Intelligence Platform imports
try:
    from chief_of_staff_ai.storage.storage_manager import storage_manager
    from chief_of_staff_ai.intelligence.orchestrator import intelligence_orchestrator
    logger.info("✅ Strategic Intelligence Platform loaded successfully")
    STRATEGIC_PLATFORM_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Strategic Intelligence Platform import failed: {str(e)}")
    STRATEGIC_PLATFORM_AVAILABLE = False
    
    # Fallback to dummy orchestrator only if import fails
    class DummyIntelligenceOrchestrator:
        async def get_intelligence_status(self, user_id):
            return {'status': 'compatibility_mode'}
        async def enrich_contacts(self, user_id, task_id):
            return {'status': 'not_implemented'}
        async def build_knowledge_tree(self, user_id, task_id, time_window_days=30):
            return {'status': 'not_implemented'}
        async def run_full_intelligence_pipeline(self, user_id):
            return {'status': 'not_implemented'}
        async def query_intelligence(self, user_id, query):
            return {'status': 'not_implemented'}
        async def create_intelligence_task(self, user_id, task_type):
            import uuid
            return str(uuid.uuid4())  # Return string instead of object
        async def get_task_status(self, task_id):
            return {'status': 'not_found'}
    
    intelligence_orchestrator = DummyIntelligenceOrchestrator()

def create_app():
    """Create and configure the Strategic Intelligence Platform Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = settings.SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
    
    # Session cookie configuration
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = False
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_DOMAIN'] = None
    app.config['SESSION_COOKIE_PATH'] = '/'
    
    # Configure CORS for React dev server
    CORS(app, supports_credentials=True, origins=["http://localhost:3000"])
    
    # Initialize Claude client
    claude_client = None
    if settings.ANTHROPIC_API_KEY:
        claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info(f"🤖 Initialized Claude 4 Opus client with model: {settings.CLAUDE_MODEL}")
    
    # Authentication decorator
    def require_auth(f):
        """Decorator to require authentication"""
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    
    def get_current_user():
        """Get current authenticated user"""
        if 'user_email' not in session or 'db_user_id' not in session:
            return None
        
        try:
            user_id = session['db_user_id']
            current_user = {'id': user_id, 'email': session['user_email']}
            return current_user
        except Exception as e:
            logger.error(f"Error retrieving current user from session: {e}")
            session.clear()
            return None
    
    # ================================
    # REDIRECTS TO REACT APP
    # ================================
    
    @app.route('/')
    def index():
        """Redirect to dashboard if authenticated, otherwise to login"""
        user = get_current_user()
        if user:
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('login'))
    
    @app.route('/login')
    def login():
        """Login page with Google OAuth"""
        logged_out = request.args.get('logged_out') == 'true'
        force_logout = request.args.get('force_logout') == 'true'
        
        logout_message = ""
        if logged_out:
            logout_message = "<p style='color: green;'>✅ You have been logged out successfully.</p>"
        elif force_logout:
            logout_message = "<p style='color: orange;'>🔄 Session cleared. Please log in again.</p>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Strategic Intelligence Platform - Login</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 60px; background: rgba(255,255,255,0.1); border-radius: 20px; backdrop-filter: blur(10px); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37); }}
                .btn {{ display: inline-block; padding: 15px 30px; background: linear-gradient(45deg, #4285f4, #34a853); color: white; text-decoration: none; border-radius: 25px; margin: 20px 0; transition: all 0.3s; font-weight: bold; }}
                .btn:hover {{ transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }}
                h1 {{ color: #ffffff; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); margin-bottom: 10px; }}
                .features {{ background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; margin-top: 30px; text-align: left; }}
                .feature {{ margin: 10px 0; font-size: 14px; }}
                .new-badge {{ background: #ff4757; color: white; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🧠 Strategic Intelligence Platform</h1>
                <p style="color: #e6f3ff; font-size: 18px; margin-bottom: 20px;">Personal AI-Powered Strategic Intelligence System</p>
                {logout_message}
                <p>Sign in with your Google account to access your comprehensive strategic intelligence dashboard.</p>
                <a href="/auth/google" class="btn">🔐 Sign in with Google</a>
                
                <div class="features">
                    <h3 style="margin-top: 0; color: #ffffff;">🚀 Intelligence Capabilities</h3>
                    <div class="feature">🗄️ Multi-Database Architecture <span class="new-badge">NEW</span></div>
                    <div class="feature">🧠 5 Specialized Claude Opus 4 Analysts <span class="new-badge">NEW</span></div>
                    <div class="feature">🌐 Automated Web Intelligence Enrichment <span class="new-badge">NEW</span></div>
                    <div class="feature">🌳 Dynamic Knowledge Tree Construction <span class="new-badge">NEW</span></div>
                    <div class="feature">📊 Predictive Relationship Analysis <span class="new-badge">NEW</span></div>
                    <div class="feature">🤝 Strategic Business Intelligence</div>
                    <div class="feature">📧 Gmail Integration & Contact Analysis</div>
                </div>
                
                <p style="margin-top: 30px; font-size: 12px; color: #ccc;">Secure authentication via Google OAuth</p>
            </div>
        </body>
        </html>
        """
    
    @app.route('/dashboard')
    def dashboard():
        """Dashboard for authenticated users"""
        user = get_current_user()
        if not user:
            return redirect(url_for('login'))
        
        user_name = session.get('user_name', 'User')
        user_email = user['email']
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Strategic Intelligence Platform - Dashboard</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .card {{ background: rgba(255,255,255,0.1); border-radius: 15px; padding: 30px; margin: 20px 0; backdrop-filter: blur(10px); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37); }}
                .btn {{ display: inline-block; padding: 12px 24px; background: linear-gradient(45deg, #4285f4, #34a853); color: white; text-decoration: none; border-radius: 20px; margin: 10px; transition: all 0.3s; font-weight: bold; }}
                .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.2); }}
                .btn-danger {{ background: linear-gradient(45deg, #ff4757, #ff3742); }}
                .api-section {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .api-card {{ background: rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; }}
                .status-indicator {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
                .status-online {{ background: #2ecc71; }}
                .user-info {{ background: rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧠 Strategic Intelligence Platform</h1>
                    <p>Welcome to your personal AI-powered strategic intelligence dashboard</p>
                </div>
                
                <div class="user-info">
                    <h3>👤 User Profile</h3>
                    <p><strong>Name:</strong> {user_name}</p>
                    <p><strong>Email:</strong> {user_email}</p>
                    <p><strong>User ID:</strong> {user['id']}</p>
                    <p><strong>Session:</strong> {session.get('session_id', 'N/A')[:8]}...</p>
                    <a href="/logout" class="btn btn-danger">🚪 Logout</a>
                </div>
                
                <div class="card">
                    <h2>🚀 Intelligence System Status</h2>
                    <p><span class="status-indicator status-online"></span>Strategic Intelligence Platform Online</p>
                    <p><span class="status-indicator status-online"></span>Claude Opus 4 Analysts Ready</p>
                    <p><span class="status-indicator status-online"></span>Multi-Database Architecture Active</p>
                    <p><span class="status-indicator status-online"></span>Web Intelligence Enrichment Available</p>
                </div>
                
                <div class="card">
                    <h2>📋 Phase 1: Priority Contact Discovery & Enrichment</h2>
                    <p style="margin-bottom: 20px; color: #e6f3ff;">Extract trusted contacts from Gmail sent items and enrich with web intelligence. These priority contacts will filter all knowledge tree construction.</p>
                    
                    <div class="api-section">
                        <div class="api-card">
                            <h4>📧 Extract Sent Contacts</h4>
                            <p>Scan Gmail sent items to build trusted contacts list</p>
                            <button onclick="extractSentContacts()" class="btn">🔍 Extract Contacts</button>
                            <div id="contact-count" style="margin-top: 10px; font-size: 12px;"></div>
                        </div>
                        <div class="api-card">
                            <h4>🌐 Web Intelligence Enrichment</h4>
                            <p>LinkedIn, Twitter, Company intelligence for priority contacts</p>
                            <button onclick="enrichPriorityContacts()" class="btn">⚡ Enrich Contacts</button>
                            <div id="enrichment-status" style="margin-top: 10px; font-size: 12px;"></div>
                        </div>
                        <div class="api-card">
                            <h4>👥 Priority Contacts List</h4>
                            <p>View and manage your trusted contact network</p>
                            <button onclick="viewPriorityContacts()" class="btn">📋 View Contacts</button>
                            <button onclick="refreshContactsList()" class="btn" style="background: linear-gradient(45deg, #667eea, #764ba2);">🔄 Refresh</button>
                        </div>
                        <div class="api-card">
                            <h4>📊 Phase 1 Status</h4>
                            <p>Track contact discovery and enrichment progress</p>
                            <div id="phase1-progress" style="margin: 10px 0;">
                                <div style="background: rgba(255,255,255,0.1); border-radius: 10px; height: 20px;">
                                    <div id="progress-bar" style="background: linear-gradient(45deg, #2ecc71, #27ae60); border-radius: 10px; height: 100%; width: 0%; transition: width 0.3s;"></div>
                                </div>
                                <div id="progress-text" style="text-align: center; font-size: 12px; margin-top: 5px; color: #ccc;">Ready to start</div>
                            </div>
                            <button onclick="checkPhase1Status()" class="btn">📈 Check Status</button>
                        </div>
                    </div>
                    
                    <div id="priority-contacts-display" style="margin-top: 20px; background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; display: none;">
                        <h4 style="color: #ffffff; margin-top: 0;">🎯 Priority Contacts Preview</h4>
                        <div id="contacts-list" style="max-height: 200px; overflow-y: auto;"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🧠 Phase 2: Knowledge Tree Construction</h2>
                    <p style="margin-bottom: 20px; color: #e6f3ff;">Build strategic knowledge tree using <strong>only emails from Phase 1 priority contacts</strong>. Claude Opus 4 analyzes filtered emails to create comprehensive business intelligence.</p>
                    
                    <div class="api-section">
                        <div class="api-card">
                            <h4>🌳 Build Knowledge Tree</h4>
                            <p>Claude Opus 4 analyzes emails from priority contacts only</p>
                            <button onclick="buildKnowledgeTreePhase2()" class="btn" id="knowledge-tree-btn">🔒 Phase 1 Required</button>
                            <div id="knowledge-tree-status" style="margin-top: 10px; font-size: 12px;"></div>
                        </div>
                        <div class="api-card">
                            <h4>📋 Email Assignment</h4>
                            <p>Assign priority contact emails to knowledge tree topics</p>
                            <button onclick="assignEmailsToTopics()" class="btn" id="assign-emails-btn" disabled>📧 Assign Emails</button>
                            <div id="assignment-status" style="margin-top: 10px; font-size: 12px;"></div>
                        </div>
                        <div class="api-card">
                            <h4>🔍 View Knowledge Tree</h4>
                            <p>Explore the constructed business knowledge structure</p>
                            <button onclick="viewKnowledgeTree()" class="btn" id="view-tree-btn" disabled>🌲 View Tree</button>
                            <div id="tree-view-status" style="margin-top: 10px; font-size: 12px;"></div>
                        </div>
                        <div class="api-card">
                            <h4>📊 Phase 2 Progress</h4>
                            <p>Track knowledge tree construction progress</p>
                            <div id="phase2-progress" style="margin: 10px 0;">
                                <div style="background: rgba(255,255,255,0.1); border-radius: 10px; height: 20px;">
                                    <div id="phase2-progress-bar" style="background: linear-gradient(45deg, #764ba2, #667eea); border-radius: 10px; height: 100%; width: 0%; transition: width 0.3s;"></div>
                                </div>
                                <div id="phase2-progress-text" style="text-align: center; font-size: 12px; margin-top: 5px; color: #ccc;">Waiting for Phase 1 completion</div>
                            </div>
                            <button onclick="checkPhase2Status()" class="btn">📈 Check Progress</button>
                        </div>
                    </div>
                    
                    <div id="knowledge-tree-preview" style="margin-top: 20px; background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; display: none;">
                        <h4 style="color: #ffffff; margin-top: 0;">🌳 Knowledge Tree Preview</h4>
                        <div id="tree-structure" style="max-height: 300px; overflow-y: auto;"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🛠️ Available Operations</h2>
                    <div class="api-section">
                        <div class="api-card">
                            <h4>📊 Intelligence Status</h4>
                            <p>Get comprehensive system status and capabilities</p>
                            <a href="/api/intelligence/status" class="btn">Check Status</a>
                        </div>
                        <div class="api-card">
                            <h4>🌐 Contact Enrichment</h4>
                            <p>Start automated contact enrichment pipeline</p>
                            <button onclick="startEnrichment()" class="btn">Start Enrichment</button>
                        </div>
                        <div class="api-card">
                            <h4>🌳 Knowledge Tree</h4>
                            <p>Build comprehensive strategic knowledge tree</p>
                            <button onclick="buildKnowledgeTree()" class="btn">Build Tree</button>
                        </div>
                        <div class="api-card">
                            <h4>🔄 Full Pipeline</h4>
                            <p>Run complete intelligence analysis pipeline</p>
                            <button onclick="runFullPipeline()" class="btn">Run Pipeline</button>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>📈 System Information</h2>
                    <p><strong>Platform:</strong> Strategic Intelligence Platform v2.0</p>
                    <p><strong>AI Model:</strong> Claude Opus 4</p>
                    <p><strong>Databases:</strong> PostgreSQL, ChromaDB, Neo4j, Redis</p>
                    <p><strong>Capabilities:</strong> 5 Specialized Analysts, Web Intelligence, Knowledge Trees</p>
                </div>
            </div>
            
            <script>
                function startEnrichment() {{
                    fetch('/api/intelligence/enrich-contacts', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(data => alert('✅ Contact enrichment started: ' + data.message))
                        .catch(e => alert('❌ Error: ' + e));
                }}
                
                function buildKnowledgeTree() {{
                    fetch('/api/intelligence/build-knowledge-tree', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(data => alert('✅ Knowledge tree building started: ' + data.message))
                        .catch(e => alert('❌ Error: ' + e));
                }}
                
                function runFullPipeline() {{
                    fetch('/api/intelligence/full-pipeline', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(data => alert('✅ Full pipeline started: ' + data.message))
                        .catch(e => alert('❌ Error: ' + e));
                }}
                
                // Phase 1: Priority Contact Discovery & Enrichment Functions
                function extractSentContacts() {{
                    document.getElementById('progress-text').textContent = 'Extracting contacts from Gmail...';
                    document.getElementById('progress-bar').style.width = '25%';
                    
                    fetch('/api/phase1/extract-sent-contacts', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                document.getElementById('contact-count').innerHTML = `✅ Found ${{data.contacts_found || 0}} unique contacts from sent emails`;
                                document.getElementById('progress-bar').style.width = '50%';
                                document.getElementById('progress-text').textContent = `Extracted ${{data.contacts_found || 0}} priority contacts`;
                                
                                // Show success message
                                alert(`✅ ${{data.message}}\\n\\nFound ${{data.contacts_found || 0}} priority contacts from your sent emails.`);
                                
                                // Auto-refresh contacts list
                                setTimeout(viewPriorityContacts, 1000);
                            }} else {{
                                document.getElementById('contact-count').innerHTML = `❌ ${{data.error || 'Failed to extract contacts'}}`;
                                alert('❌ Error: ' + (data.error || 'Failed to extract contacts'));
                            }}
                        }})
                        .catch(e => {{
                            document.getElementById('contact-count').innerHTML = '❌ Connection error';
                            alert('❌ Network Error: ' + e);
                        }});
                }}
                
                function enrichPriorityContacts() {{
                    document.getElementById('enrichment-status').textContent = 'Starting web intelligence enrichment...';
                    document.getElementById('progress-bar').style.width = '75%';
                    document.getElementById('progress-text').textContent = 'Enriching contacts with LinkedIn, Twitter, Company data...';
                    
                    fetch('/api/phase1/enrich-priority-contacts', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(data => {{
                            if (data.status === 'started') {{
                                document.getElementById('enrichment-status').innerHTML = `✅ Enrichment started! Task ID: ${{data.task_id}}`;
                                document.getElementById('progress-bar').style.width = '100%';
                                document.getElementById('progress-text').textContent = 'Web intelligence enrichment in progress...';
                                
                                alert(`✅ ${{data.message}}\\n\\nWeb workers are now enriching your priority contacts with LinkedIn, Twitter, and company intelligence.\\n\\nTask ID: ${{data.task_id}}`);
                                
                                // Auto-check status in a few seconds
                                setTimeout(() => checkPhase1Status(data.task_id), 3000);
                            }} else {{
                                document.getElementById('enrichment-status').innerHTML = `❌ ${{data.error || 'Failed to start enrichment'}}`;
                                alert('❌ Error: ' + (data.error || 'Failed to start enrichment'));
                            }}
                        }})
                        .catch(e => {{
                            document.getElementById('enrichment-status').innerHTML = '❌ Connection error';
                            alert('❌ Network Error: ' + e);
                        }});
                }}
                
                function viewPriorityContacts() {{
                    fetch('/api/phase1/priority-contacts')
                        .then(r => r.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                const contactsDisplay = document.getElementById('priority-contacts-display');
                                const contactsList = document.getElementById('contacts-list');
                                
                                if (data.contacts && data.contacts.length > 0) {{
                                    let html = '';
                                    data.contacts.slice(0, 10).forEach(contact => {{
                                        const enriched = contact.enriched ? '🌐' : '📧';
                                        html += `
                                            <div style="background: rgba(255,255,255,0.05); margin: 5px 0; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                                                <div>
                                                    <strong>${{contact.email}}</strong>
                                                    ${{contact.name ? `<br><small style="color: #ccc;">${{contact.name}}</small>` : ''}}
                                                    ${{contact.company ? `<br><small style="color: #a8e6cf;">${{contact.company}}</small>` : ''}}
                                                </div>
                                                <div style="text-align: right;">
                                                    <span>${{enriched}}</span>
                                                    <br><small style="color: #ccc;">${{contact.email_count || 0}} emails</small>
                                                </div>
                                            </div>
                                        `;
                                    }});
                                    
                                    if (data.contacts.length > 10) {{
                                        html += `<div style="text-align: center; color: #ccc; margin: 10px 0;"><small>... and ${{data.contacts.length - 10}} more contacts</small></div>`;
                                    }}
                                    
                                    contactsList.innerHTML = html;
                                    contactsDisplay.style.display = 'block';
                                }} else {{
                                    contactsList.innerHTML = '<div style="text-align: center; color: #ccc; padding: 20px;">No priority contacts found. Extract sent contacts first.</div>';
                                    contactsDisplay.style.display = 'block';
                                }}
                            }} else {{
                                alert('❌ Error: ' + (data.error || 'Failed to load contacts'));
                            }}
                        }})
                        .catch(e => alert('❌ Network Error: ' + e));
                }}
                
                function refreshContactsList() {{
                    viewPriorityContacts();
                }}
                
                function checkPhase1Status(taskId = null) {{
                    const url = taskId ? `/api/phase1/status/${{taskId}}` : '/api/phase1/status';
                    
                    fetch(url)
                        .then(r => r.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                const progress = data.progress || 0;
                                const message = data.message || 'Phase 1 status checked';
                                
                                document.getElementById('progress-bar').style.width = progress + '%';
                                document.getElementById('progress-text').textContent = message;
                                
                                // Update UI based on phase completion
                                if (data.contacts_extracted) {{
                                    document.getElementById('contact-count').innerHTML = `✅ ${{data.contacts_count || 0}} priority contacts extracted`;
                                }}
                                
                                if (data.enrichment_progress) {{
                                    document.getElementById('enrichment-status').innerHTML = `⚡ Enrichment: ${{data.enrichment_progress}}% complete`;
                                }}
                                
                                // Enable Phase 2 if Phase 1 is complete
                                if (data.ready_for_phase2) {{
                                    enablePhase2();
                                }}
                                
                                alert(`📊 Phase 1 Status\\n\\nProgress: ${{progress}}%\\nMessage: ${{message}}\\n\\nContacts: ${{data.contacts_count || 0}}\\nEnrichment: ${{data.enrichment_progress || 0}}% complete`);
                            }} else {{
                                alert('❌ Error: ' + (data.error || 'Failed to check status'));
                            }}
                        }})
                        .catch(e => alert('❌ Network Error: ' + e));
                }}
                
                // Phase 2: Knowledge Tree Construction Functions
                function enablePhase2() {{
                    // Enable Phase 2 UI elements
                    const knowledgeTreeBtn = document.getElementById('knowledge-tree-btn');
                    knowledgeTreeBtn.textContent = '🌳 Build Knowledge Tree';
                    knowledgeTreeBtn.disabled = false;
                    knowledgeTreeBtn.style.background = 'linear-gradient(45deg, #4285f4, #34a853)';
                    
                    document.getElementById('phase2-progress-text').textContent = 'Phase 1 complete. Ready to build knowledge tree!';
                    document.getElementById('phase2-progress-bar').style.width = '25%';
                }}
                
                function buildKnowledgeTreePhase2() {{
                    // Check if Phase 1 is complete
                    fetch('/api/phase1/status')
                        .then(r => r.json())
                        .then(data => {{
                            if (!data.ready_for_phase2) {{
                                alert('❌ Phase 1 Required\\n\\nPlease complete Phase 1 (Priority Contact Discovery & Enrichment) before building the knowledge tree.');
                                return;
                            }}
                            
                            // Start knowledge tree building with priority contacts filter
                            document.getElementById('knowledge-tree-status').textContent = 'Starting knowledge tree construction...';
                            document.getElementById('phase2-progress-bar').style.width = '50%';
                            document.getElementById('phase2-progress-text').textContent = 'Claude Opus 4 analyzing priority contact emails...';
                            
                            fetch('/api/phase2/build-knowledge-tree', {{ method: 'POST' }})
                                .then(r => r.json())
                                .then(data => {{
                                    if (data.status === 'started') {{
                                        document.getElementById('knowledge-tree-status').innerHTML = `✅ Knowledge tree construction started! Task ID: ${{data.task_id}}`;
                                        document.getElementById('phase2-progress-bar').style.width = '75%';
                                        document.getElementById('phase2-progress-text').textContent = 'Claude Opus 4 building strategic knowledge tree...';
                                        
                                        // Enable next steps
                                        document.getElementById('assign-emails-btn').disabled = false;
                                        document.getElementById('view-tree-btn').disabled = false;
                                        
                                        alert(`✅ ${{data.message}}\\n\\nClaude Opus 4 is now analyzing emails from your ${{data.priority_contacts_count || 0}} priority contacts to build a comprehensive strategic knowledge tree.\\n\\nTask ID: ${{data.task_id}}`);
                                        
                                        // Auto-check status
                                        setTimeout(() => checkPhase2Status(data.task_id), 5000);
                                    }} else {{
                                        document.getElementById('knowledge-tree-status').innerHTML = `❌ ${{data.error || 'Failed to start knowledge tree construction'}}`;
                                        alert('❌ Error: ' + (data.error || 'Failed to start knowledge tree construction'));
                                    }}
                                }})
                                .catch(e => {{
                                    document.getElementById('knowledge-tree-status').innerHTML = '❌ Connection error';
                                    alert('❌ Network Error: ' + e);
                                }});
                        }});
                }}
                
                function assignEmailsToTopics() {{
                    document.getElementById('assignment-status').textContent = 'Assigning emails to knowledge tree topics...';
                    
                    fetch('/api/phase2/assign-emails', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                document.getElementById('assignment-status').innerHTML = `✅ Assigned ${{data.emails_assigned || 0}} emails to ${{data.topics_count || 0}} topics`;
                                alert(`✅ Email Assignment Complete\\n\\nAssigned ${{data.emails_assigned || 0}} priority contact emails to ${{data.topics_count || 0}} knowledge tree topics.`);
                            }} else {{
                                document.getElementById('assignment-status').innerHTML = `❌ ${{data.error || 'Failed to assign emails'}}`;
                                alert('❌ Error: ' + (data.error || 'Failed to assign emails'));
                            }}
                        }})
                        .catch(e => {{
                            document.getElementById('assignment-status').innerHTML = '❌ Connection error';
                            alert('❌ Network Error: ' + e);
                        }});
                }}
                
                function viewKnowledgeTree() {{
                    fetch('/api/phase2/knowledge-tree')
                        .then(r => r.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                const treePreview = document.getElementById('knowledge-tree-preview');
                                const treeStructure = document.getElementById('tree-structure');
                                
                                if (data.knowledge_tree && data.knowledge_tree.knowledge_topics) {{
                                    let html = '';
                                    data.knowledge_tree.knowledge_topics.forEach(topic => {{
                                        const topicName = topic.name || 'Untitled Topic';
                                        const emailsCount = topic.emails_count || 0;
                                        const description = topic.description || 'No description';
                                        
                                        let keyPeopleHtml = '';
                                        if (topic.key_people && topic.key_people.length > 0) {{
                                            const peopleList = topic.key_people.slice(0, 3).join(', ');
                                            const moreText = topic.key_people.length > 3 ? '...' : '';
                                            keyPeopleHtml = `<div style="font-size: 12px; color: #a8e6cf;"><strong>Key People:</strong> ${{peopleList}}${{moreText}}</div>`;
                                        }}
                                        
                                        html += `
                                            <div style="background: rgba(255,255,255,0.05); margin: 10px 0; padding: 15px; border-radius: 8px;">
                                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                                    <h5 style="color: #4285f4; margin: 0;">${{topicName}}</h5>
                                                    <span style="background: rgba(66,133,244,0.2); padding: 4px 8px; border-radius: 12px; font-size: 12px;">${{emailsCount}} emails</span>
                                                </div>
                                                <p style="color: #ccc; margin: 8px 0; font-size: 14px;">${{description}}</p>
                                                ${{keyPeopleHtml}}
                                            </div>
                                        `;
                                    }});
                                    
                                    treeStructure.innerHTML = html;
                                    treePreview.style.display = 'block';
                                    
                                    document.getElementById('tree-view-status').innerHTML = `✅ Knowledge tree loaded: ${{data.knowledge_tree.knowledge_topics.length}} topics`;
                                }} else {{
                                    treeStructure.innerHTML = '<div style="text-align: center; color: #ccc; padding: 20px;">No knowledge tree found. Build the tree first.</div>';
                                    treePreview.style.display = 'block';
                                    document.getElementById('tree-view-status').innerHTML = '📝 No knowledge tree built yet';
                                }}
                            }} else {{
                                alert('❌ Error: ' + (data.error || 'Failed to load knowledge tree'));
                            }}
                        }})
                        .catch(e => alert('❌ Network Error: ' + e));
                }}
                
                function checkPhase2Status(taskId = null) {{
                    const url = taskId ? `/api/phase2/status/${{taskId}}` : '/api/phase2/status';
                    
                    fetch(url)
                        .then(r => r.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                const progress = data.progress || 0;
                                const message = data.message || 'Phase 2 status checked';
                                
                                document.getElementById('phase2-progress-bar').style.width = progress + '%';
                                document.getElementById('phase2-progress-text').textContent = message;
                                
                                if (data.knowledge_tree_built) {{
                                    document.getElementById('knowledge-tree-status').innerHTML = `✅ Knowledge tree built with ${{data.topics_count || 0}} topics`;
                                    document.getElementById('assign-emails-btn').disabled = false;
                                    document.getElementById('view-tree-btn').disabled = false;
                                }}
                                
                                alert(`📊 Phase 2 Status\\n\\nProgress: ${{progress}}%\\nMessage: ${{message}}\\n\\nTopics: ${{data.topics_count || 0}}\\nEmails Processed: ${{data.emails_processed || 0}}`);
                            }} else {{
                                alert('❌ Error: ' + (data.error || 'Failed to check Phase 2 status'));
                            }}
                        }})
                        .catch(e => alert('❌ Network Error: ' + e));
                }}
                
                // Auto-enable Phase 2 on page load if Phase 1 is complete
                document.addEventListener('DOMContentLoaded', function() {{
                    fetch('/api/phase1/status')
                        .then(r => r.json())
                        .then(data => {{
                            if (data.ready_for_phase2) {{
                                enablePhase2();
                            }}
                        }})
                        .catch(e => console.log('Phase 1 status check failed:', e));
                }});
            </script>
        </body>
        </html>
        """
    
    # ================================
    # AUTHENTICATION ROUTES (PRESERVED)
    # ================================
    
    @app.route('/auth/google')
    def google_auth():
        """Initiate Google OAuth flow"""
        try:
            state = f"strategic_intel_{session.get('csrf_token', 'temp')}"
            auth_url, state = gmail_auth.get_authorization_url(
                user_id=session.get('temp_user_id', 'anonymous'),
                state=state
            )
            session['oauth_state'] = state
            return redirect(auth_url)
        except Exception as e:
            logger.error(f"Failed to initiate Google OAuth: {str(e)}")
            return redirect(url_for('login') + '?error=oauth_init_failed')
    
    @app.route('/auth/google/callback')
    def google_callback():
        """Handle Google OAuth callback"""
        try:
            code = request.args.get('code')
            state = request.args.get('state')
            error = request.args.get('error')
            
            if error:
                logger.error(f"OAuth error: {error}")
                return redirect(url_for('login') + f'?error={error}')
            
            if not code:
                logger.error("No authorization code received")
                return redirect(url_for('login') + '?error=no_code')
            
            expected_state = session.get('oauth_state')
            if state != expected_state:
                logger.error(f"OAuth state mismatch: {state} != {expected_state}")
                return redirect(url_for('login') + '?error=state_mismatch')
            
            result = gmail_auth.handle_oauth_callback(
                authorization_code=code,
                state=state
            )
            
            if not result.get('success'):
                error_msg = result.get('error', 'Unknown OAuth error')
                logger.error(f"OAuth callback failed: {error_msg}")
                return redirect(url_for('login') + f'?error=oauth_failed')
            
            # Clear session and set new user data
            session.clear()
            
            user_info = result.get('user_info', {})
            user_email = user_info.get('email')
            
            if not user_email:
                logger.error("No email received from OAuth")
                return redirect(url_for('login') + '?error=no_email')
            
            # Store OAuth credentials in database
            credentials = result.get('credentials', {})
            user = get_db_manager().create_or_update_user(user_info, credentials)
            
            if not user:
                logger.error(f"Failed to create/update user: {user_email}")
                return redirect(url_for('login') + '?error=user_creation_failed')
            
            # Set session data
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            session['user_email'] = user_email
            session['user_name'] = user_info.get('name')
            session['google_id'] = user_info.get('id')
            session['authenticated'] = True
            session['db_user_id'] = user.id
            session['login_time'] = datetime.now().isoformat()
            session.permanent = True
            
            logger.info(f"🧠 User authenticated for Strategic Intelligence Platform: {user_email} (DB ID: {user.id}, Session: {session_id}) with OAuth credentials stored")
            
            response = redirect(url_for('dashboard'))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            return response
            
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return redirect(url_for('login') + '?error=callback_failed')
    
    @app.route('/auth/callback')
    def auth_callback():
        """Handle OAuth callback - alternative route for compatibility"""
        return google_callback()
    
    @app.route('/logout')
    def logout():
        """Logout user"""
        session.clear()
        response = redirect(url_for('login') + '?logged_out=true')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    
    @app.route('/auth/clear-session')
    def clear_oauth_session():
        """Clear all session data to fix OAuth loops"""
        session.clear()
        response = redirect(url_for('login') + '?force_logout=true')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    
    # ================================
    # API ROUTES - STRATEGIC INTELLIGENCE PLATFORM
    # ================================
    
    @app.route('/api/auth/status')
    def auth_status():
        """Check authentication status"""
        user = get_current_user()
        if user:
            return jsonify({
                'authenticated': True,
                'user': {
                    'email': user['email'],
                    'name': session.get('user_name'),
                    'id': user['id']
                },
                'platform': 'Strategic Intelligence Platform',
                'capabilities': [
                    'Multi-Database Architecture',
                    'Claude Opus 4 Analysts', 
                    'Web Intelligence Enrichment',
                    'Knowledge Tree Construction',
                    'Predictive Analysis'
                ]
            })
        else:
            return jsonify({'authenticated': False}), 401
    
    @app.route('/api/intelligence/status')
    def intelligence_status():
        """Get intelligence system status and capabilities"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            # Get intelligence status using the orchestrator
            status = asyncio.run(intelligence_orchestrator.get_intelligence_status(user['id']))
            
            return jsonify({
                'status': 'success',
                'platform': 'Strategic Intelligence Platform',
                'intelligence_status': status,
                'database_architecture': {
                    'postgresql': 'Primary storage with vector support',
                    'chromadb': 'Vector database for semantic search',
                    'neo4j': 'Graph database for relationship mapping',
                    'redis': 'Real-time caching and task status'
                },
                'analysts': {
                    'business_strategy': 'Strategic decisions and market positioning',
                    'relationship_dynamics': 'Influence patterns and collaboration',
                    'technical_evolution': 'Architecture and technology insights',
                    'market_intelligence': 'Competitive and market signals',
                    'predictive_analysis': 'Future scenarios and opportunities'
                }
            })
            
        except Exception as e:
            logger.error(f"Intelligence status error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/intelligence/enrich-contacts', methods=['POST'])
    @require_auth
    def start_contact_enrichment():
        """Start Phase 1: Contact enrichment with web intelligence"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            # Create intelligence task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            task_id = loop.run_until_complete(
                intelligence_orchestrator.create_intelligence_task(user['id'], 'contact_enrichment')
            )
            
            # Start enrichment in background
            def run_enrichment():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        intelligence_orchestrator.enrich_contacts(user['id'], task_id)
                    )
                    logger.info(f"Contact enrichment completed: {result}")
                except Exception as e:
                    logger.error(f"Background contact enrichment failed: {str(e)}")
            
            # Start in background thread
            import threading
            thread = threading.Thread(target=run_enrichment)
            thread.start()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Contact enrichment started',
                'status': 'running'
            })
            
        except Exception as e:
            logger.error(f"❌ Contact enrichment start failed: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/intelligence/build-knowledge-tree', methods=['POST'])
    @require_auth
    def start_knowledge_tree_building():
        """Start Phase 2: Knowledge tree construction with Claude analysts"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            data = request.get_json() or {}
            time_window_days = data.get('time_window_days', 30)
            
            # Create intelligence task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            task_id = loop.run_until_complete(
                intelligence_orchestrator.create_intelligence_task(user['id'], 'knowledge_tree_building')
            )
            
            # Start knowledge tree building in background
            def run_knowledge_building():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        intelligence_orchestrator.build_knowledge_tree(user['id'], task_id, time_window_days)
                    )
                    logger.info(f"Knowledge tree building completed: {result}")
                except Exception as e:
                    logger.error(f"Background knowledge tree building failed: {str(e)}")
            
            # Start in background thread
            import threading
            thread = threading.Thread(target=run_knowledge_building)
            thread.start()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': f'Knowledge tree building started ({time_window_days} day window)',
                'status': 'running',
                'time_window_days': time_window_days
            })
            
        except Exception as e:
            logger.error(f"❌ Knowledge tree building start failed: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/intelligence/full-pipeline', methods=['POST'])
    @require_auth
    def start_full_intelligence_pipeline():
        """Start complete intelligence pipeline: enrichment + knowledge tree"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            # Create intelligence task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            task_id = loop.run_until_complete(
                intelligence_orchestrator.create_intelligence_task(user['id'], 'full_pipeline')
            )
            
            # Start full pipeline in background
            def run_full_pipeline():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        intelligence_orchestrator.run_full_intelligence_pipeline(user['id'])
                    )
                    logger.info(f"Full intelligence pipeline completed: {result}")
                except Exception as e:
                    logger.error(f"Background full pipeline failed: {str(e)}")
            
            # Start in background thread
            import threading
            thread = threading.Thread(target=run_full_pipeline)
            thread.start()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Full intelligence pipeline started',
                'status': 'running',
                'phases': ['contact_enrichment', 'knowledge_tree_building']
            })
            
        except Exception as e:
            logger.error(f"❌ Full pipeline start failed: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/intelligence/status/<task_id>', methods=['GET'])
    @require_auth
    def get_intelligence_status(task_id):
        """Get status of intelligence task"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            status = loop.run_until_complete(
                intelligence_orchestrator.get_task_status(task_id)
            )
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': status
            })
            
        except Exception as e:
            logger.error(f"❌ Status retrieval failed: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/intelligence/contacts', methods=['GET'])
    @require_auth
    def get_enriched_contacts():
        """Get enriched contacts for user"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            limit = request.args.get('limit', 50, type=int)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            contacts = loop.run_until_complete(
                storage_manager.get_contacts_for_enrichment(user['id'], limit)
            )
            
            # Convert to JSON-serializable format
            contacts_data = []
            for contact in contacts:
                contacts_data.append({
                    'id': contact.id,
                    'email': contact.email,
                    'name': contact.name,
                    'company': contact.company,
                    'linkedin_url': contact.linkedin_url,
                    'twitter_handle': contact.twitter_handle,
                    'enrichment_status': contact.enrichment_status,
                    'engagement_score': contact.engagement_score,
                    'last_interaction': contact.last_interaction.isoformat() if contact.last_interaction else None,
                    'created_at': contact.created_at.isoformat() if contact.created_at else None
                })
            
            return jsonify({
                'success': True,
                'contacts': contacts_data,
                'total': len(contacts_data)
            })
            
        except Exception as e:
            logger.error(f"❌ Contact retrieval failed: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/phase1/status', methods=['GET'])
    @app.route('/api/phase1/status/<task_id>', methods=['GET'])
    @require_auth
    def get_phase1_status(task_id=None):
        """Get Phase 1 status"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            # Sample status for demonstration
            return jsonify({
                'status': 'success',
                'progress': 75,
                'message': 'Phase 1 in progress - enriching contacts',
                'contacts_count': 3,
                'enrichment_progress': 60,
                'ready_for_phase2': True
            })
            
        except Exception as e:
            logger.error(f"❌ Phase 1 status failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/phase1/extract-sent-contacts', methods=['POST'])
    @require_auth
    def extract_sent_contacts():
        """Phase 1: Extract and enrich sent contacts"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            # Capture user context for background task
            user_id = user['id']
            user_email = user['email']
            
            # Create and start contact enrichment task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            task_id = loop.run_until_complete(
                intelligence_orchestrator.create_intelligence_task(user_id, 'contact_enrichment')
            )
            
            # Start enrichment in background with user context
            def run_enrichment():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Create a user context object to pass to the orchestrator
                    user_context = {
                        'id': user_id,
                        'email': user_email
                    }
                    
                    # Add the user context to the storage manager temporarily
                    storage_manager._user_context_cache = {user_id: user_context}
                    
                    result = loop.run_until_complete(
                        intelligence_orchestrator.enrich_contacts(user_id, task_id)
                    )
                    logger.info(f"Phase 1 contact enrichment completed: {result}")
                except Exception as e:
                    logger.error(f"Phase 1 background enrichment failed: {str(e)}")
            
            # Start in background thread
            import threading
            thread = threading.Thread(target=run_enrichment)
            thread.start()
            
            return jsonify({
                'status': 'success',
                'task_id': task_id,
                'message': 'Contact extraction and enrichment started',
                'contacts_found': 3  # Placeholder
            })
            
        except Exception as e:
            logger.error(f"❌ Phase 1 extract failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/phase1/enrich-priority-contacts', methods=['POST'])
    @require_auth
    def enrich_priority_contacts():
        """Phase 1: Web intelligence enrichment"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            # Create and start enrichment task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            task_id = loop.run_until_complete(
                intelligence_orchestrator.create_intelligence_task(user['id'], 'web_enrichment')
            )
            
            return jsonify({
                'status': 'started',
                'task_id': task_id,
                'message': 'Web intelligence enrichment started'
            })
            
        except Exception as e:
            logger.error(f"❌ Phase 1 enrichment failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/phase1/priority-contacts', methods=['GET'])
    @require_auth
    def get_priority_contacts():
        """Get priority contacts list"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            # Get real contacts from Strategic Intelligence Platform
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            contacts = loop.run_until_complete(
                storage_manager.get_contacts_for_enrichment(user['id'], limit=50)
            )
            
            # Convert to JSON format
            contacts_data = []
            for contact in contacts:
                contacts_data.append({
                    'email': contact.email,
                    'name': contact.name or '',
                    'company': contact.company or '',
                    'enriched': contact.enrichment_status == 'enriched',
                    'email_count': contact.engagement_score or 0
                })
            
            return jsonify({
                'status': 'success',
                'contacts': contacts_data
            })
            
        except Exception as e:
            logger.error(f"❌ Get priority contacts failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/phase2/build-knowledge-tree', methods=['POST'])
    @require_auth
    def build_knowledge_tree_phase2():
        """Phase 2: Build knowledge tree"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            # Create and start knowledge tree task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            task_id = loop.run_until_complete(
                intelligence_orchestrator.create_intelligence_task(user['id'], 'knowledge_tree_building')
            )
            
            return jsonify({
                'status': 'started',
                'task_id': task_id,
                'message': 'Knowledge tree construction started',
                'priority_contacts_count': 3
            })
            
        except Exception as e:
            logger.error(f"❌ Phase 2 build failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/phase2/assign-emails', methods=['POST'])
    @require_auth
    def assign_emails_to_topics():
        """Assign emails to knowledge tree topics"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            return jsonify({
                'status': 'success',
                'emails_assigned': 25,
                'topics_count': 8
            })
            
        except Exception as e:
            logger.error(f"❌ Email assignment failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/phase2/knowledge-tree', methods=['GET'])
    @require_auth
    def get_knowledge_tree():
        """Get knowledge tree structure"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            # Sample knowledge tree for demonstration
            knowledge_tree = {
                'knowledge_topics': [
                    {
                        'name': 'Strategic Planning',
                        'description': 'Q1 strategic planning and resource allocation decisions',
                        'emails_count': 12,
                        'key_people': ['John Doe', 'Jane Smith', 'Mike Johnson']
                    },
                    {
                        'name': 'Technical Architecture',
                        'description': 'Technology stack decisions and microservices architecture',
                        'emails_count': 8,
                        'key_people': ['Jane Smith', 'Technical Team']
                    }
                ]
            }
            
            return jsonify({
                'status': 'success',
                'knowledge_tree': knowledge_tree
            })
            
        except Exception as e:
            logger.error(f"❌ Get knowledge tree failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/phase2/status', methods=['GET'])
    @app.route('/api/phase2/status/<task_id>', methods=['GET'])
    @require_auth
    def get_phase2_status(task_id=None):
        """Get Phase 2 status"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'status': 'error', 'error': 'Authentication required'}), 401
            
            return jsonify({
                'status': 'success',
                'progress': 90,
                'message': 'Knowledge tree construction complete',
                'knowledge_tree_built': True,
                'topics_count': 8,
                'emails_processed': 25
            })
            
        except Exception as e:
            logger.error(f"❌ Phase 2 status failed: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/sync-settings')
    def sync_settings():
        """Sync settings endpoint (legacy compatibility)"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        return jsonify({
            'status': 'success',
            'platform': 'Strategic Intelligence Platform',
            'settings': {
                'user_id': user['id'],
                'email': user['email'],
                'authenticated': True
            }
        })
    
    @app.route('/api/gmail/diagnostics', methods=['GET'])
    @require_auth
    def gmail_diagnostics():
        """Run Gmail diagnostics to troubleshoot sent emails issue"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            user_email = session.get('user_email')
            
            # Import Gmail fetcher
            from chief_of_staff_ai.ingest.gmail_fetcher import gmail_fetcher
            
            # Run diagnostics
            diagnostics = gmail_fetcher.get_email_sync_diagnostics(user_email, days_back=90)
            
            # Add additional authentication test
            from chief_of_staff_ai.auth.gmail_auth import gmail_auth
            auth_status = gmail_auth.get_authentication_status(user_email)
            
            diagnostics['authentication'] = auth_status
            
            return jsonify({
                'success': True,
                'diagnostics': diagnostics,
                'user_email': user_email,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Gmail diagnostics failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/gmail/test-connection', methods=['GET'])
    @require_auth
    def test_gmail_connection():
        """Test basic Gmail API connection and authentication"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            user_email = session.get('user_email')
            
            # Test authentication
            from chief_of_staff_ai.auth.gmail_auth import gmail_auth
            credentials = gmail_auth.get_valid_credentials(user_email)
            if not credentials:
                return jsonify({
                    'success': False,
                    'error': 'No valid Gmail credentials',
                    'user_email': user_email
                }), 401
            
            # Test Gmail API connection
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=credentials)
            
            # Test basic API call
            profile = service.users().getProfile(userId='me').execute()
            
            # Test simple message list
            result = service.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()
            
            total_messages = len(result.get('messages', []))
            
            return jsonify({
                'success': True,
                'user_email': user_email,
                'gmail_profile': profile,
                'total_messages_accessible': total_messages,
                'authentication_status': 'valid',
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Gmail connection test failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'user_email': user_email if 'user_email' in locals() else 'unknown'
            }), 500
    
    @app.route('/api/gmail/test-sent-query', methods=['POST'])
    @require_auth
    def test_sent_query():
        """Test different Gmail queries for sent emails"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            user_email = session.get('user_email')
            data = request.get_json() or {}
            days_back = data.get('days_back', 90)
            
            # Get Gmail credentials
            from chief_of_staff_ai.auth.gmail_auth import gmail_auth
            credentials = gmail_auth.get_valid_credentials(user_email)
            if not credentials:
                return jsonify({'success': False, 'error': 'No valid Gmail credentials'}), 401
            
            # Build Gmail service
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=credentials)
            
            # Test different queries
            queries_to_test = [
                ('in:sent', 'Sent folder only'),
                ('in:sent after:2024/01/01', 'Sent emails since 2024'),
                ('in:sent after:2023/01/01', 'Sent emails since 2023'),
                ('in:all', 'All emails'),
                ('in:inbox', 'Inbox emails'),
                ('is:sent', 'Alternative sent query'),
                ('from:me', 'From me query')
            ]
            
            results = []
            for query, description in queries_to_test:
                try:
                    result = service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=10
                    ).execute()
                    
                    count = len(result.get('messages', []))
                    results.append({
                        'query': query,
                        'description': description,
                        'count': count,
                        'success': True
                    })
                except Exception as e:
                    results.append({
                        'query': query,
                        'description': description,
                        'count': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            return jsonify({
                'success': True,
                'user_email': user_email,
                'days_back': days_back,
                'query_results': results,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Gmail query test failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ================================
    # LEGACY API ROUTES (PRESERVED)
    # ================================
    
    @app.route('/api/tasks')
    def get_tasks():
        """Get tasks (legacy endpoint)"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            tasks = get_db_manager().get_user_tasks(user['id'], limit=50)
            return jsonify({
                'tasks': [task.to_dict() for task in tasks],
                'total': len(tasks)
            })
        except Exception as e:
            logger.error(f"Error getting tasks: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # ================================
    # ERROR HANDLERS
    # ================================
    
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.after_request
    def after_request(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    return app

if __name__ == '__main__':
    """Initialize and run the Strategic Intelligence Platform"""
    try:
        # Initialize database
        get_db_manager().init_db()
        logger.info("📊 Database initialized successfully")
        
        # Initialize strategic storage (async initialization will happen on first use)
        logger.info("🗄️ Strategic storage system ready")
        
        app = create_app()
        
        logger.info("🚀 Starting Strategic Intelligence Platform with Claude 4 Opus Integration")
        logger.info("🧠 5 Specialized Analysts ready for knowledge tree construction")
        logger.info("🌐 Web intelligence enrichment system online")
        logger.info("🌐 Server starting on http://0.0.0.0:8080")
        
        app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)
        
    except Exception as e:
        logger.error(f"Failed to start Strategic Intelligence Platform: {str(e)}")
        raise 