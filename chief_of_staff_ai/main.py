# Main Flask application for AI Chief of Staff - Enhanced V2.0
# Updated to use the new entity-centric API architecture

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import anthropic

# Configuration and Auth
from config.settings import settings
from auth.gmail_auth import gmail_auth

# Enhanced API System
from api import enhanced_api_bp

# Enhanced Processors
from ingest.gmail_fetcher import gmail_fetcher
from processors.unified_entity_engine import entity_engine, EntityContext
from processors.enhanced_ai_pipeline import enhanced_ai_processor
from processors.realtime_processing import realtime_processor, EventType
from processors import processor_manager
from models.enhanced_models import Topic, Person, Task, IntelligenceInsight, EntityRelationship, Email

# Database
from models.database import get_db_manager

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

# Version constant
CURRENT_VERSION = 'v2.0-enhanced'

# Start enhanced processor system when app starts
if not realtime_processor.is_running:
    processor_manager.start_all_processors()

# =====================================================================
# API BLUEPRINT REGISTRATION
# =====================================================================

# Register enhanced API blueprint
app.register_blueprint(enhanced_api_bp)

logger.info("Registered enhanced API blueprints:")
logger.info("  - Enhanced API: /api/enhanced/*")

# =====================================================================
# FRONTEND ROUTES (Updated to use enhanced backend)
# =====================================================================

@app.route('/')
def index():
    """Main dashboard route - enhanced with new entity data"""
    user_email = session.get('user_email')
    
    if not user_email:
        return render_template('login.html')
    
    try:
        # Get user information
        user_info = gmail_auth.get_user_by_email(user_email)
        if not user_info:
            session.clear()
            return render_template('login.html')
        
        # Get enhanced user statistics using new models
        user = get_db_manager().get_user_by_email(user_email)
        user_stats = {
            'total_emails': 0,
            'total_tasks': 0,
            'pending_tasks': 0,
            'completed_tasks': 0,
            'total_people': 0,
            'total_topics': 0,
            'recent_insights': 0
        }
        
        if user:
            with get_db_manager().get_session() as db_session:
                # Email statistics
                user_stats['total_emails'] = db_session.query(Email).filter(
                    Email.user_id == user.id
                ).count()
                
                # Task statistics  
                user_stats['total_tasks'] = db_session.query(Task).filter(
                    Task.user_id == user.id
                ).count()
                
                user_stats['pending_tasks'] = db_session.query(Task).filter(
                    Task.user_id == user.id,
                    Task.status.in_(['pending', 'open'])
                ).count()
                
                user_stats['completed_tasks'] = db_session.query(Task).filter(
                    Task.user_id == user.id,
                    Task.status == 'completed'
                ).count()
                
                # Entity statistics (new)
                user_stats['total_people'] = db_session.query(Person).filter(
                    Person.user_id == user.id
                ).count()
                
                user_stats['total_topics'] = db_session.query(Topic).filter(
                    Topic.user_id == user.id
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
            session['db_user_id'] = result.get('db_user_id')  # For enhanced API compatibility
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

# =====================================================================
# ENHANCED ENTITY PAGES
# =====================================================================

@app.route('/people')
def people_page():
    """People management page"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('people.html', user_email=user_email)

@app.route('/topics')
def topics_page():
    """Topics management page"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('topics.html', user_email=user_email)

@app.route('/analytics')
def analytics_page():
    """Analytics dashboard page"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('analytics.html', 
                         user_email=user_email)

@app.route('/real-time')
def realtime_page():
    """Real-time processing dashboard"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('realtime.html', 
                         user_email=user_email)

@app.route('/api-testing')
def api_testing_page():
    """API testing and documentation interface"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('api_testing.html', 
                         user_email=user_email)

@app.route('/batch-processing')
def batch_processing_page():
    """Batch processing management page"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('batch_processing.html', 
                         user_email=user_email)

@app.route('/tasks')
def tasks_page():
    """Enhanced task management page"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('tasks.html', user_email=user_email)

@app.route('/profile')
def profile_page():
    """User profile and settings page"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('profile.html', 
                         user_email=user_email)

@app.route('/search')
def search_page():
    """Universal search and discovery page"""
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('login'))
    
    return render_template('search.html', user_email=user_email)

# =====================================================================
# LEGACY API ENDPOINTS (Maintained for backward compatibility)
# =====================================================================

@app.route('/api/process-emails', methods=['POST'])
def api_process_emails():
    """Legacy API endpoint - now uses enhanced processing"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() or {}
        days_back = data.get('days_back', 7)
        limit = data.get('limit', 50)
        force_refresh = data.get('force_refresh', False)
        
        logger.info(f"Legacy email processing for {user_email} (using enhanced backend)")
        
        # Get user database ID for enhanced processing
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Fetch and process emails using enhanced Gmail fetcher
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
        
        # Return enhanced processing result
        response = {
            'success': True,
            'fetch_result': fetch_result,
            'enhanced_processing': True,
            'processed_at': datetime.utcnow().isoformat()
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Legacy email processing error for {user_email}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f"Processing failed: {str(e)}"
        }), 500

@app.route('/api/emails')
def api_get_emails():
    """Legacy API endpoint for getting emails"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        limit = request.args.get('limit', 50, type=int)
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        emails = get_db_manager().get_user_emails(user.id, limit)
        
        response = {
            'success': True,
            'emails': [email.to_dict() for email in emails],
            'count': len(emails)
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Get emails error for {user_email}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks')
def api_get_tasks():
    """Legacy API endpoint for getting tasks"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get tasks directly from database
        tasks = get_db_manager().get_user_tasks(user.id, status=status, limit=limit)
        
        response = {
            'success': True,
            'tasks': [task.to_dict() for task in tasks],
            'count': len(tasks)
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Get tasks error for {user_email}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
def api_update_task_status(task_id):
    """Legacy API endpoint for updating task status"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'open', 'in_progress', 'completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Update task status directly
        task = get_db_manager().update_task_status(task_id, new_status, user.id)
        
        if task:
            response = {
                'success': True,
                'task': task.to_dict()
            }
        else:
            response = {
                'success': False,
                'error': 'Task not found or access denied'
            }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Update task status error for {user_email}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Enhanced API endpoint for Claude chat with entity context"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # Get enhanced user context
        user = get_db_manager().get_user_by_email(user_email)
        context_info = ""
        
        if user:
            # Generate comprehensive insights for context
            insights_result = processor_manager.generate_user_insights(user.id, 'comprehensive')
            
            if insights_result['success']:
                insights = insights_result['result']
                
                # Build rich context from insights
                context_parts = []
                
                if insights.get('proactive_insights'):
                    recent_insights = insights['proactive_insights'][:3]
                    insights_list = "\n".join([f"- {insight['title']}" for insight in recent_insights])
                    context_parts.append(f"Recent insights:\n{insights_list}")
                
                # Add predictive analytics context if available
                if insights.get('predictive_analytics'):
                    pred_analytics = insights['predictive_analytics']
                    if pred_analytics.get('upcoming_needs'):
                        needs_list = "\n".join([f"- {need['title']}" for need in pred_analytics['upcoming_needs'][:3]])
                        context_parts.append(f"Upcoming needs:\n{needs_list}")
                
                if context_parts:
                    context_info = f"\n\nCurrent context:\n" + "\n\n".join(context_parts)
        
        # Build enhanced system prompt
        system_prompt = f"""You are an AI Chief of Staff assistant helping {user_email}. 
You have access to their comprehensive work data including tasks, contacts, and business topics.

Be helpful, professional, and concise. Focus on actionable advice related to their work, relationships, and strategic priorities. Use the context provided to give personalized recommendations.{context_info}"""
        
        # Call Claude with enhanced context
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
            'enhanced_context': bool(context_info),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Enhanced chat error for {user_email}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': 'Failed to process chat message'
        }), 500

@app.route('/api/status')
def api_status():
    """Enhanced API endpoint to get system status"""
    user_email = session.get('user_email')
    
    status = {
        'authenticated': bool(user_email),
        'user_email': user_email,
        'timestamp': datetime.utcnow().isoformat(),
        'api_version': CURRENT_VERSION,
        'enhanced_features': True,
        'database_connected': True,
        'gmail_auth_available': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        'claude_available': bool(settings.ANTHROPIC_API_KEY),
        'processor_manager': True,
        'real_time_processing': True
    }
    
    # Test database connection
    try:
        get_db_manager().get_session().close()
    except Exception as e:
        status['database_connected'] = False
        status['database_error'] = str(e)
    
    # Test processor manager
    try:
        stats_result = processor_manager.get_processing_statistics()
        status['processor_manager_stats'] = stats_result['result'] if stats_result['success'] else None
    except Exception as e:
        status['processor_manager'] = False
        status['processor_manager_error'] = str(e)
    
    # Test Gmail auth if user is authenticated
    if user_email:
        try:
            auth_status = gmail_auth.get_authentication_status(user_email)
            status['gmail_auth_status'] = auth_status
        except Exception as e:
            status['gmail_auth_error'] = str(e)
    
    resp = jsonify(status)
    return add_version_headers(resp, CURRENT_VERSION), 200

# =====================================================================
# BUSINESS INTELLIGENCE ENDPOINT (NEW)
# =====================================================================

def get_strategic_business_insights(user_email: str) -> List[Dict]:
    """Generate strategic business insights for a user"""
    try:
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return []
        
        # Use processor manager to generate comprehensive insights
        insights_result = processor_manager.generate_user_insights(user.id, 'strategic')
        
        if insights_result['success']:
            return insights_result['result'].get('insights', [])
        else:
            logger.error(f"Failed to generate insights: {insights_result['error']}")
            return []
    
    except Exception as e:
        logger.error(f"Error generating strategic insights: {str(e)}")
        return []

# =====================================================================
# ENHANCED UNIFIED PROCESSING ENDPOINT
# =====================================================================

@app.route('/api/enhanced-unified-sync', methods=['POST'])
def enhanced_unified_intelligence_sync():
    """
    Enhanced unified processing using entity-centric architecture.
    Demonstrates the full power of the integrated intelligence platform.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        data = request.get_json() or {}
        max_emails = data.get('max_emails', 10)
        days_back = data.get('days_back', 3)
        enable_real_time = data.get('enable_real_time', True)
        
        processing_summary = {
            'success': True,
            'enhanced_architecture': True,
            'entity_intelligence': {},
            'processing_stages': {},
            'proactive_insights': [],
            'real_time_processing': enable_real_time,
            'entity_relationships': {},
            'intelligence_quality': {}
        }
        
        # Stage 1: Enhanced Email Processing with Entity Intelligence
        logger.info(f"Starting enhanced unified sync for {user_email}")
        
        email_result = gmail_fetcher.fetch_recent_emails(
            user_email, max_emails=max_emails, days_back=days_back
        )
        
        processing_summary['processing_stages']['emails_fetched'] = email_result.get('emails_fetched', 0)
        
        if email_result.get('success') and email_result.get('emails'):
            if enable_real_time:
                # Send to real-time processor
                for email_data in email_result['emails']:
                    realtime_processor.process_new_email(email_data, user.id, priority=2)
            else:
                # Process directly through enhanced AI pipeline
                for email_data in email_result['emails']:
                    result = enhanced_ai_processor.process_email_with_context(email_data, user.id)
                    if result.success:
                        processing_summary['processing_stages']['emails_processed'] = processing_summary['processing_stages'].get('emails_processed', 0) + 1
        
        # Stage 2: Generate Entity Intelligence Summary
        entity_intelligence = generate_entity_intelligence_summary(user.id)
        processing_summary['entity_intelligence'] = entity_intelligence
        
        # Stage 3: Generate Proactive Insights
        proactive_insights = entity_engine.generate_proactive_insights(user.id)
        processing_summary['proactive_insights'] = [
            {
                'id': insight.id,
                'type': insight.insight_type,
                'title': insight.title,
                'description': insight.description,
                'priority': insight.priority,
                'confidence': insight.confidence,
                'created_at': insight.created_at.isoformat()
            }
            for insight in proactive_insights
        ]
        
        # Stage 4: Entity Relationship Analysis
        relationship_analysis = analyze_entity_relationships(user.id)
        processing_summary['entity_relationships'] = relationship_analysis
        
        # Stage 5: Intelligence Quality Metrics
        quality_metrics = calculate_intelligence_quality_metrics(user.id)
        processing_summary['intelligence_quality'] = quality_metrics
        
        # Stage 6: Real-time Processing Statistics
        if enable_real_time:
            rt_stats = realtime_processor.get_stats()
            processing_summary['real_time_stats'] = {
                'queue_size': rt_stats['queue_size'],
                'events_processed': rt_stats['events_processed'],
                'avg_processing_time': rt_stats['avg_processing_time'],
                'workers_active': rt_stats['workers_active']
            }
        
        logger.info(f"Enhanced unified sync complete: {len(proactive_insights)} insights generated")
        
        return jsonify(processing_summary)
        
    except Exception as e:
        logger.error(f"Enhanced unified sync failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'enhanced_architecture': True,
            'real_time_processing': False
        }), 500

# =====================================================================
# ENTITY-CENTRIC API ENDPOINTS
# =====================================================================

@app.route('/api/entities/topics', methods=['GET'])
def get_topics_with_intelligence():
    """Get topics with accumulated intelligence and relationship data"""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            topics = session.query(Topic).filter(Topic.user_id == user.id).all()
            
            topics_data = []
            for topic in topics:
                topic_data = {
                    'id': topic.id,
                    'name': topic.name,
                    'description': topic.description,
                    'keywords': topic.keywords.split(',') if topic.keywords else [],
                    'is_official': topic.is_official,
                    'confidence_score': topic.confidence_score,
                    'total_mentions': topic.total_mentions,
                    'last_mentioned': topic.last_mentioned.isoformat() if topic.last_mentioned else None,
                    'intelligence_summary': topic.intelligence_summary,
                    'strategic_importance': topic.strategic_importance,
                    'created_at': topic.created_at.isoformat(),
                    'updated_at': topic.updated_at.isoformat(),
                    'version': topic.version,
                    
                    # Relationship data
                    'connected_people': len(topic.people),
                    'related_tasks': len(topic.tasks),
                    'connected_events': len(topic.events),
                    'total_connections': len(topic.people) + len(topic.tasks) + len(topic.events)
                }
                topics_data.append(topic_data)
            
            # Sort by strategic importance and recent activity
            topics_data.sort(key=lambda x: (x['strategic_importance'], x['total_mentions']), reverse=True)
            
            return jsonify({
                'success': True,
                'topics': topics_data,
                'summary': {
                    'total_topics': len(topics_data),
                    'official_topics': len([t for t in topics_data if t['is_official']]),
                    'high_importance': len([t for t in topics_data if t['strategic_importance'] > 0.7]),
                    'recently_active': len([t for t in topics_data if t['last_mentioned'] and 
                                          datetime.fromisoformat(t['last_mentioned']) > datetime.utcnow() - timedelta(days=7)]),
                    'highly_connected': len([t for t in topics_data if t['total_connections'] > 3])
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get topics with intelligence: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/entities/people', methods=['GET'])
def get_people_with_relationship_intelligence():
    """Get people with comprehensive relationship intelligence"""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            people = session.query(Person).filter(Person.user_id == user.id).all()
            
            people_data = []
            for person in people:
                person_data = {
                    'id': person.id,
                    'name': person.name,
                    'email_address': person.email_address,
                    'phone': person.phone,
                    'company': person.company,
                    'title': person.title,
                    'relationship_type': person.relationship_type,
                    'importance_level': person.importance_level,
                    'communication_frequency': person.communication_frequency,
                    'last_contact': person.last_contact.isoformat() if person.last_contact else None,
                    'total_interactions': person.total_interactions,
                    'linkedin_url': person.linkedin_url,
                    'professional_story': person.professional_story,
                    'created_at': person.created_at.isoformat(),
                    'updated_at': person.updated_at.isoformat(),
                    
                    # Relationship intelligence
                    'connected_topics': [{'name': topic.name, 'strategic_importance': topic.strategic_importance} for topic in person.topics],
                    'assigned_tasks': len(person.tasks_assigned),
                    'mentioned_in_tasks': len(person.tasks_mentioned),
                    'topic_connections': len(person.topics),
                    'engagement_score': calculate_person_engagement_score(person)
                }
                people_data.append(person_data)
            
            # Sort by importance and recent activity
            people_data.sort(key=lambda x: (x['importance_level'] or 0, x['total_interactions']), reverse=True)
            
            return jsonify({
                'success': True,
                'people': people_data,
                'summary': {
                    'total_people': len(people_data),
                    'high_importance': len([p for p in people_data if (p['importance_level'] or 0) > 0.7]),
                    'recent_contacts': len([p for p in people_data if p['last_contact'] and 
                                          datetime.fromisoformat(p['last_contact']) > datetime.utcnow() - timedelta(days=30)]),
                    'highly_connected': len([p for p in people_data if p['topic_connections'] > 2]),
                    'with_professional_story': len([p for p in people_data if p['professional_story']])
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get people with relationship intelligence: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intelligence/insights', methods=['GET'])
def get_proactive_intelligence_insights():
    """Get proactive intelligence insights with filtering"""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get query parameters
        status_filter = request.args.get('status', 'new')
        insight_type = request.args.get('type', None)
        limit = int(request.args.get('limit', 20))
        
        with get_db_manager().get_session() as session:
            query = session.query(IntelligenceInsight).filter(
                IntelligenceInsight.user_id == user.id
            )
            
            if status_filter:
                query = query.filter(IntelligenceInsight.status == status_filter)
            
            if insight_type:
                query = query.filter(IntelligenceInsight.insight_type == insight_type)
            
            # Filter out expired insights
            query = query.filter(
                (IntelligenceInsight.expires_at.is_(None)) | 
                (IntelligenceInsight.expires_at > datetime.utcnow())
            )
            
            insights = query.order_by(
                IntelligenceInsight.priority.desc(),
                IntelligenceInsight.created_at.desc()
            ).limit(limit).all()
            
            insights_data = []
            for insight in insights:
                insight_data = {
                    'id': insight.id,
                    'insight_type': insight.insight_type,
                    'title': insight.title,
                    'description': insight.description,
                    'priority': insight.priority,
                    'confidence': insight.confidence,
                    'status': insight.status,
                    'user_feedback': insight.user_feedback,
                    'created_at': insight.created_at.isoformat(),
                    'expires_at': insight.expires_at.isoformat() if insight.expires_at else None,
                    'related_entity': {
                        'type': insight.related_entity_type,
                        'id': insight.related_entity_id
                    } if insight.related_entity_type else None
                }
                insights_data.append(insight_data)
            
            return jsonify({
                'success': True,
                'insights': insights_data,
                'summary': {
                    'total_insights': len(insights_data),
                    'by_type': count_insights_by_type(insights_data),
                    'by_priority': count_insights_by_priority(insights_data),
                    'actionable': len([i for i in insights_data if i['status'] == 'new']),
                    'high_confidence': len([i for i in insights_data if i['confidence'] > 0.8])
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get intelligence insights: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intelligence/generate-insights', methods=['POST'])
def generate_proactive_insights():
    """Generate proactive insights manually (for testing)"""
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    user = get_db_manager().get_user_by_email(user_email)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    try:
        # Generate insights using entity engine
        insights = entity_engine.generate_proactive_insights(user.id)
        
        return jsonify({
            'success': True,
            'insights_generated': len(insights),
            'insights': [
                {
                    'type': insight.insight_type,
                    'title': insight.title,
                    'description': insight.description,
                    'priority': insight.priority,
                    'confidence': insight.confidence,
                    'created_at': insight.created_at.isoformat()
                }
                for insight in insights
            ]
        })
        
    except Exception as e:
        logger.error(f"Failed to generate proactive insights: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/real-time/status', methods=['GET'])
def get_realtime_processing_status():
    """Get real-time processing status and statistics"""
    try:
        stats = realtime_processor.get_stats()
        queue_status = realtime_processor.get_queue_status()
        
        return jsonify({
            'success': True,
            'real_time_processing': {
                'is_running': stats['is_running'],
                'queue_size': stats['queue_size'],
                'workers_active': stats['workers_active'],
                'events_processed': stats['events_processed'],
                'events_failed': stats['events_failed'],
                'avg_processing_time': stats['avg_processing_time'],
                'last_processed': stats['last_processed'].isoformat() if stats['last_processed'] else None
            },
            'performance_metrics': {
                'processing_rate': stats['events_processed'] / max(1, (datetime.utcnow() - realtime_processor.stats.get('start_time', datetime.utcnow())).total_seconds() / 60),  # events per minute
                'error_rate': stats['events_failed'] / max(1, stats['events_processed'] + stats['events_failed']),
                'queue_utilization': stats['queue_size'] / 1000  # Assume max queue size of 1000
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get real-time status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================================
# ENHANCED METRICS AND FEEDBACK ENDPOINTS (MISSING FROM DASHBOARD)
# =====================================================================

@app.route('/api/entities/metrics', methods=['GET'])
def get_entity_metrics():
    """Get comprehensive entity metrics for dashboard"""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            # Entity counts
            topics_count = session.query(Topic).filter(Topic.user_id == user.id).count()
            people_count = session.query(Person).filter(Person.user_id == user.id).count()
            tasks_count = session.query(Task).filter(Task.user_id == user.id).count()
            insights_count = session.query(IntelligenceInsight).filter(
                IntelligenceInsight.user_id == user.id,
                IntelligenceInsight.status == 'new'
            ).count()
            
            # Active relationships
            relationships_count = session.query(EntityRelationship).filter(
                EntityRelationship.user_id == user.id
            ).count()
            
            # Calculate intelligence quality score
            high_conf_topics = session.query(Topic).filter(
                Topic.user_id == user.id,
                Topic.confidence_score > 0.8
            ).count()
            
            topics_with_summary = session.query(Topic).filter(
                Topic.user_id == user.id,
                Topic.intelligence_summary.isnot(None)
            ).count()
            
            intelligence_quality = 0.0
            if topics_count > 0:
                intelligence_quality = (high_conf_topics + topics_with_summary) / (topics_count * 2)
            
            # Topic momentum (topics active in last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            active_topics = session.query(Topic).filter(
                Topic.user_id == user.id,
                Topic.last_mentioned > week_ago
            ).count()
            
            topic_momentum = 0.0
            if topics_count > 0:
                topic_momentum = active_topics / topics_count
            
            # Relationship density
            relationship_density = 0.0
            total_entities = topics_count + people_count
            if total_entities > 0:
                relationship_density = relationships_count / total_entities
            
            metrics = {
                'total_entities': topics_count + people_count + tasks_count,
                'topics': topics_count,
                'people': people_count,
                'tasks': tasks_count,
                'active_insights': insights_count,
                'entity_relationships': relationships_count,
                'intelligence_quality': intelligence_quality,
                'topic_momentum': topic_momentum,
                'relationship_density': relationship_density
            }
            
            return jsonify({'success': True, 'metrics': metrics})
            
    except Exception as e:
        logger.error(f"Failed to get entity metrics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intelligence/feedback', methods=['POST'])
def record_insight_feedback():
    """Record user feedback on intelligence insights"""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        data = request.get_json()
        insight_id = data.get('insight_id')
        feedback = data.get('feedback')
        
        if not insight_id or not feedback:
            return jsonify({'success': False, 'error': 'Missing insight_id or feedback'}), 400
        
        with get_db_manager().get_session() as session:
            insight = session.query(IntelligenceInsight).filter(
                IntelligenceInsight.id == insight_id,
                IntelligenceInsight.user_id == user.id
            ).first()
            
            if not insight:
                return jsonify({'success': False, 'error': 'Insight not found'}), 404
            
            insight.user_feedback = feedback
            insight.updated_at = datetime.utcnow()
            
            # Mark as reviewed if feedback provided
            if insight.status == 'new':
                insight.status = 'reviewed'
            
            session.commit()
            
            return jsonify({'success': True, 'message': 'Feedback recorded'})
            
    except Exception as e:
        logger.error(f"Failed to record insight feedback: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_enhanced_tasks():
    """Enhanced task endpoint with context information"""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        limit = request.args.get('limit', 20, type=int)
        with_context = request.args.get('with_context', 'false').lower() == 'true'
        status = request.args.get('status')
        
        with get_db_manager().get_session() as session:
            query = session.query(Task).filter(Task.user_id == user.id)
            
            if with_context:
                query = query.filter(Task.context_story.isnot(None))
            
            if status:
                query = query.filter(Task.status == status)
            
            tasks = query.order_by(Task.created_at.desc()).limit(limit).all()
            
            tasks_data = []
            for task in tasks:
                task_data = {
                    'id': task.id,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'confidence': task.confidence,
                    'context_story': task.context_story,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'created_at': task.created_at.isoformat(),
                    'assignee': {
                        'name': task.assignee.name if task.assignee else None,
                        'email': task.assignee.email_address if task.assignee else None
                    } if task.assignee else None
                }
                tasks_data.append(task_data)
            
            return jsonify({'success': True, 'tasks': tasks_data})
            
    except Exception as e:
        logger.error(f"Failed to get enhanced tasks: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================================
# UNIFIED INTELLIGENCE SYNC ENDPOINT (MISSING FROM REFACTOR)
# =====================================================================

@app.route('/api/unified-intelligence-sync', methods=['POST'])
def unified_intelligence_sync():
    """
    Enhanced unified processing that integrates email, calendar, and generates
    real-time intelligence with entity-centric architecture.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user = get_db_manager().get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get processing parameters
        data = request.get_json() or {}
        max_emails = data.get('max_emails', 20)
        days_back = data.get('days_back', 7)
        days_forward = data.get('days_forward', 14)
        force_refresh = data.get('force_refresh', False)
        
        processing_summary = {
            'success': True,
            'processing_stages': {},
            'entity_intelligence': {},
            'insights_generated': [],
            'real_time_processing': True,
            'next_steps': []
        }
        
        # Stage 1: Fetch and process emails in real-time
        logger.info(f"Starting unified intelligence sync for {user_email}")
        
        # Fetch emails
        email_result = gmail_fetcher.fetch_recent_emails(
            user_email, max_emails=max_emails, days_back=days_back, force_refresh=force_refresh
        )
        
        processing_summary['processing_stages']['emails_fetched'] = email_result.get('emails_fetched', 0)
        
        if email_result.get('success') and email_result.get('emails'):
            # Process each email through real-time pipeline
            for email_data in email_result['emails']:
                realtime_processor.process_new_email(email_data, user.id, priority=3)
        
        # Stage 2: Fetch and enhance calendar events (if calendar fetcher available)
        try:
            from ingest.calendar_fetcher import calendar_fetcher
            calendar_result = calendar_fetcher.fetch_calendar_events(
                user_email, days_back=3, days_forward=days_forward, create_prep_tasks=True
            )
            
            processing_summary['processing_stages']['calendar_events_fetched'] = calendar_result.get('events_fetched', 0)
            
            if calendar_result.get('success') and calendar_result.get('events'):
                # Process each calendar event through real-time pipeline
                for event_data in calendar_result['events']:
                    realtime_processor.process_new_calendar_event(event_data, user.id, priority=4)
        except ImportError:
            logger.info("Calendar fetcher not available, skipping calendar processing")
            processing_summary['processing_stages']['calendar_events_fetched'] = 0
        
        # Stage 3: Generate comprehensive business intelligence
        intelligence_summary = generate_360_business_intelligence(user.id)
        processing_summary['entity_intelligence'] = intelligence_summary
        
        # Stage 4: Generate proactive insights
        proactive_insights = entity_engine.generate_proactive_insights(user.id)
        processing_summary['insights_generated'] = [
            {
                'type': insight.insight_type if hasattr(insight, 'insight_type') else 'general',
                'title': insight.title if hasattr(insight, 'title') else 'Insight',
                'description': insight.description if hasattr(insight, 'description') else 'No description',
                'priority': insight.priority if hasattr(insight, 'priority') else 'medium',
                'confidence': insight.confidence if hasattr(insight, 'confidence') else 0.5
            }
            for insight in proactive_insights
        ]
        
        # Generate next steps based on intelligence
        processing_summary['next_steps'] = generate_intelligent_next_steps(intelligence_summary, proactive_insights)
        
        logger.info(f"Completed unified intelligence sync for {user_email}: "
                   f"{processing_summary['processing_stages']['emails_fetched']} emails, "
                   f"{processing_summary['processing_stages']['calendar_events_fetched']} events, "
                   f"{len(proactive_insights)} insights")
        
        return jsonify(processing_summary)
        
    except Exception as e:
        logger.error(f"Failed unified intelligence sync: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'processing_stages': {},
            'real_time_processing': False
        }), 500

# =====================================================================
# BUSINESS INTELLIGENCE GENERATION (MISSING FROM REFACTOR)
# =====================================================================

def generate_360_business_intelligence(user_id: int) -> Dict:
    """Generate comprehensive 360-degree business intelligence"""
    try:
        intelligence = {
            'entity_summary': {},
            'relationship_intelligence': {},
            'strategic_insights': {},
            'activity_patterns': {},
            'intelligence_quality': {}
        }
        
        with get_db_manager().get_session() as session:
            # Entity summary
            topics_count = session.query(Topic).filter(Topic.user_id == user_id).count()
            people_count = session.query(Person).filter(Person.user_id == user_id).count()
            tasks_count = session.query(Task).filter(Task.user_id == user_id).count()
            
            from models.enhanced_models import CalendarEvent
            events_count = session.query(CalendarEvent).filter(CalendarEvent.user_id == user_id).count()
            
            intelligence['entity_summary'] = {
                'topics': topics_count,
                'people': people_count,
                'tasks': tasks_count,
                'calendar_events': events_count,
                'total_entities': topics_count + people_count + tasks_count + events_count
            }
            
            # Relationship intelligence
            from models.enhanced_models import EntityRelationship
            relationships_count = session.query(EntityRelationship).filter(
                EntityRelationship.user_id == user_id
            ).count()
            
            # Active topics (mentioned in last 30 days)
            active_topics = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.last_mentioned > datetime.utcnow() - timedelta(days=30)
            ).count()
            
            # Recent contacts
            recent_contacts = session.query(Person).filter(
                Person.user_id == user_id,
                Person.last_contact > datetime.utcnow() - timedelta(days=30)
            ).count()
            
            intelligence['relationship_intelligence'] = {
                'total_relationships': relationships_count,
                'active_topics': active_topics,
                'recent_contacts': recent_contacts,
                'relationship_density': relationships_count / max(1, people_count + topics_count)
            }
            
            # Activity patterns
            recent_tasks = session.query(Task).filter(
                Task.user_id == user_id,
                Task.created_at > datetime.utcnow() - timedelta(days=7)
            ).count()
            
            intelligence['activity_patterns'] = {
                'tasks_this_week': recent_tasks,
                'average_daily_tasks': recent_tasks / 7,
                'topic_momentum': active_topics / max(1, topics_count)
            }
            
            # Intelligence quality metrics
            high_confidence_tasks = session.query(Task).filter(
                Task.user_id == user_id,
                Task.confidence > 0.8
            ).count()
            
            tasks_with_context = session.query(Task).filter(
                Task.user_id == user_id,
                Task.context_story.isnot(None)
            ).count()
            
            intelligence['intelligence_quality'] = {
                'high_confidence_extractions': high_confidence_tasks / max(1, tasks_count),
                'contextualized_tasks': tasks_with_context / max(1, tasks_count),
                'entity_interconnection': relationships_count / max(1, intelligence['entity_summary']['total_entities'])
            }
        
        return intelligence
        
    except Exception as e:
        logger.error(f"Failed to generate 360 business intelligence: {str(e)}")
        return {}

def generate_intelligent_next_steps(intelligence_summary: Dict, insights: List) -> List[str]:
    """Generate intelligent next steps based on business intelligence"""
    next_steps = []
    
    try:
        entity_summary = intelligence_summary.get('entity_summary', {})
        relationship_intel = intelligence_summary.get('relationship_intelligence', {})
        activity_patterns = intelligence_summary.get('activity_patterns', {})
        
        # Suggest next steps based on data
        if entity_summary.get('total_entities', 0) < 10:
            next_steps.append("Process more email data to build comprehensive business intelligence")
        
        if relationship_intel.get('relationship_density', 0) < 0.3:
            next_steps.append("Focus on building relationship connections between contacts and topics")
        
        if activity_patterns.get('tasks_this_week', 0) > 10:
            next_steps.append("Consider prioritizing and organizing your task backlog")
        
        if len(insights) > 5:
            next_steps.append("Review and act on high-priority insights")
        elif len(insights) < 2:
            next_steps.append("Continue processing communications to generate more insights")
        
        # Always suggest at least one action
        if not next_steps:
            next_steps.append("Continue using the system to build your business intelligence")
        
    except Exception as e:
        logger.error(f"Failed to generate intelligent next steps: {str(e)}")
        next_steps = ["Continue building your business intelligence"]
    
    return next_steps

def calculate_relationship_strength(person: Person) -> float:
    """Calculate relationship strength for a person"""
    score = 0.0
    
    # Interaction frequency
    if person.total_interactions > 10:
        score += 0.3
    elif person.total_interactions > 5:
        score += 0.2
    elif person.total_interactions > 0:
        score += 0.1
    
    # Recent contact
    if person.last_contact and person.last_contact > datetime.utcnow() - timedelta(days=7):
        score += 0.3
    elif person.last_contact and person.last_contact > datetime.utcnow() - timedelta(days=30):
        score += 0.2
    
    # Importance level
    if person.importance_level:
        score += person.importance_level * 0.4
    
    return min(1.0, score)

def calculate_communication_frequency(person: Person) -> str:
    """Calculate communication frequency description"""
    if not person.last_contact:
        return "No recent contact"
    
    days_since = (datetime.utcnow() - person.last_contact).days
    
    if days_since <= 7:
        return "Weekly"
    elif days_since <= 30:
        return "Monthly"
    elif days_since <= 90:
        return "Quarterly"
    else:
        return "Infrequent"

def calculate_engagement_score(person: Person) -> float:
    """Calculate engagement score for a person"""
    score = 0.0
    
    # Interaction frequency
    if person.total_interactions > 10:
        score += 0.3
    elif person.total_interactions > 5:
        score += 0.2
    elif person.total_interactions > 0:
        score += 0.1
    
    # Recent contact
    if person.last_contact and person.last_contact > datetime.utcnow() - timedelta(days=7):
        score += 0.3
    elif person.last_contact and person.last_contact > datetime.utcnow() - timedelta(days=30):
        score += 0.2
    
    # Professional context
    if person.professional_story:
        score += 0.2
    
    # Topic connections
    topic_count = len(person.topics) if person.topics else 0
    if topic_count > 3:
        score += 0.2
    elif topic_count > 0:
        score += 0.1
    
    return min(1.0, score)

def get_person_topic_affinity(person_id: int, topic_id: int) -> float:
    """Get affinity score between person and topic"""
    try:
        from models.database import get_db_manager
        from models.enhanced_models import person_topic_association
        
        with get_db_manager().get_session() as session:
            # Query the association table for affinity score
            result = session.execute(
                person_topic_association.select().where(
                    (person_topic_association.c.person_id == person_id) &
                    (person_topic_association.c.topic_id == topic_id)
                )
            ).first()
            
            return result.affinity_score if result else 0.5
            
    except Exception as e:
        logger.error(f"Failed to get person-topic affinity: {str(e)}")
        return 0.5

def calculate_task_strategic_importance(task: Task) -> float:
    """Calculate strategic importance of a task"""
    importance = 0.0
    
    # High priority tasks are more strategic
    if task.priority == 'high':
        importance += 0.4
    elif task.priority == 'medium':
        importance += 0.2
    
    # Tasks with context are more strategic
    if task.context_story:
        importance += 0.3
    
    # Tasks with high confidence are more strategic
    if task.confidence > 0.8:
        importance += 0.2
    
    # Tasks connected to multiple topics are more strategic
    topic_count = len(task.topics) if task.topics else 0
    if topic_count > 2:
        importance += 0.1
    
    return min(1.0, importance)

def count_by_field(data_list: List[Dict], field: str) -> Dict:
    """Count items by a specific field"""
    counts = {}
    for item in data_list:
        value = item.get(field, 'unknown')
        counts[value] = counts.get(value, 0) + 1
    return counts

# =====================================================================
# HELPER FUNCTIONS FOR ENHANCED PROCESSING
# =====================================================================

def add_version_headers(response, version: str):
    """Add version headers to API responses"""
    response.headers['X-API-Version'] = version
    response.headers['X-Enhanced-Features'] = 'true'
    return response

def generate_entity_intelligence_summary(user_id: int) -> Dict:
    """Generate comprehensive entity intelligence summary"""
    try:
        with get_db_manager().get_session() as session:
            # Count entities
            topics_count = session.query(Topic).filter(Topic.user_id == user_id).count()
            people_count = session.query(Person).filter(Person.user_id == user_id).count()
            tasks_count = session.query(Task).filter(Task.user_id == user_id).count()
            insights_count = session.query(IntelligenceInsight).filter(IntelligenceInsight.user_id == user_id).count()
            
            # Active entities (recently updated)
            week_ago = datetime.utcnow() - timedelta(days=7)
            active_topics = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.last_mentioned > week_ago
            ).count()
            
            recent_contacts = session.query(Person).filter(
                Person.user_id == user_id,
                Person.last_contact > week_ago
            ).count()
            
            return {
                'entity_counts': {
                    'topics': topics_count,
                    'people': people_count,
                    'tasks': tasks_count,
                    'insights': insights_count,
                    'total_entities': topics_count + people_count + tasks_count
                },
                'activity_metrics': {
                    'active_topics': active_topics,
                    'recent_contacts': recent_contacts,
                    'activity_rate': (active_topics + recent_contacts) / max(1, topics_count + people_count)
                },
                'intelligence_density': {
                    'topics_per_person': topics_count / max(1, people_count),
                    'tasks_per_topic': tasks_count / max(1, topics_count),
                    'insights_per_entity': insights_count / max(1, topics_count + people_count)
                }
            }
            
    except Exception as e:
        logger.error(f"Failed to generate entity intelligence summary: {str(e)}")
        return {}

def analyze_entity_relationships(user_id: int) -> Dict:
    """Analyze entity relationships and connection patterns"""
    try:
        with get_db_manager().get_session() as session:
            relationships = session.query(EntityRelationship).filter(
                EntityRelationship.user_id == user_id
            ).all()
            
            relationship_types = {}
            strong_relationships = 0
            
            for rel in relationships:
                rel_type = rel.relationship_type
                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
                
                if rel.strength > 0.7:
                    strong_relationships += 1
            
            return {
                'total_relationships': len(relationships),
                'relationship_types': relationship_types,
                'strong_relationships': strong_relationships,
                'relationship_density': len(relationships) / max(1, session.query(Topic).filter(Topic.user_id == user_id).count() + session.query(Person).filter(Person.user_id == user_id).count()),
                'avg_relationship_strength': sum(rel.strength for rel in relationships) / max(1, len(relationships))
            }
            
    except Exception as e:
        logger.error(f"Failed to analyze entity relationships: {str(e)}")
        return {}

def calculate_intelligence_quality_metrics(user_id: int) -> Dict:
    """Calculate intelligence quality metrics"""
    try:
        with get_db_manager().get_session() as session:
            # High confidence entities
            high_conf_topics = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.confidence_score > 0.8
            ).count()
            
            high_conf_tasks = session.query(Task).filter(
                Task.user_id == user_id,
                Task.confidence > 0.8
            ).count()
            
            # Entities with context
            topics_with_summary = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.intelligence_summary.isnot(None)
            ).count()
            
            tasks_with_context = session.query(Task).filter(
                Task.user_id == user_id,
                Task.context_story.isnot(None)
            ).count()
            
            total_topics = session.query(Topic).filter(Topic.user_id == user_id).count()
            total_tasks = session.query(Task).filter(Task.user_id == user_id).count()
            
            return {
                'confidence_metrics': {
                    'high_confidence_topics': high_conf_topics / max(1, total_topics),
                    'high_confidence_tasks': high_conf_tasks / max(1, total_tasks)
                },
                'context_richness': {
                    'topics_with_intelligence': topics_with_summary / max(1, total_topics),
                    'tasks_with_context': tasks_with_context / max(1, total_tasks)
                },
                'overall_quality_score': (
                    (high_conf_topics / max(1, total_topics)) +
                    (high_conf_tasks / max(1, total_tasks)) +
                    (topics_with_summary / max(1, total_topics)) +
                    (tasks_with_context / max(1, total_tasks))
                ) / 4
            }
            
    except Exception as e:
        logger.error(f"Failed to calculate intelligence quality metrics: {str(e)}")
        return {}

def calculate_person_engagement_score(person: Person) -> float:
    """Calculate engagement score for a person"""
    score = 0.0
    
    # Interaction frequency
    if person.total_interactions > 10:
        score += 0.3
    elif person.total_interactions > 5:
        score += 0.2
    elif person.total_interactions > 0:
        score += 0.1
    
    # Recent contact
    if person.last_contact and person.last_contact > datetime.utcnow() - timedelta(days=7):
        score += 0.3
    elif person.last_contact and person.last_contact > datetime.utcnow() - timedelta(days=30):
        score += 0.2
    
    # Professional context
    if person.professional_story:
        score += 0.2
    
    # Topic connections
    topic_count = len(person.topics) if person.topics else 0
    if topic_count > 3:
        score += 0.2
    elif topic_count > 0:
        score += 0.1
    
    return min(1.0, score)

def count_insights_by_type(insights_data: List[Dict]) -> Dict:
    """Count insights by type"""
    counts = {}
    for insight in insights_data:
        insight_type = insight['insight_type']
        counts[insight_type] = counts.get(insight_type, 0) + 1
    return counts

def count_insights_by_priority(insights_data: List[Dict]) -> Dict:
    """Count insights by priority"""
    counts = {}
    for insight in insights_data:
        priority = insight['priority']
        counts[priority] = counts.get(priority, 0) + 1
    return counts

# =====================================================================
# ERROR HANDLERS
# =====================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', api_version=CURRENT_VERSION), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html', api_version=CURRENT_VERSION), 500

# =====================================================================
# APPLICATION STARTUP
# =====================================================================

if __name__ == '__main__':
    # Validate configuration
    config_errors = settings.validate_config()
    if config_errors:
        logger.error("Configuration errors:")
        for error in config_errors:
            logger.error(f"  - {error}")
        exit(1)
    
    logger.info("Starting AI Chief of Staff Enhanced Application v2.0...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    logger.info(f"Environment: {'Production' if settings.is_production() else 'Development'}")
    logger.info(f"API Version: {CURRENT_VERSION}")
    
    # Initialize database with enhanced models
    try:
        get_db_manager().initialize_database()
        logger.info("Enhanced database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        exit(1)
    
    # Initialize processor manager
    try:
        # Test processor manager connection
        stats_result = processor_manager.get_processing_statistics()
        if stats_result['success']:
            logger.info("Processor manager initialized successfully")
        else:
            logger.warning(f"Processor manager warning: {stats_result['error']}")
    except Exception as e:
        logger.error(f"Processor manager initialization failed: {str(e)}")
        # Don't exit - application can still run with reduced functionality
    
    # Start real-time processing engine
    try:
        from processors.realtime_processing import realtime_processor
        realtime_processor.start(num_workers=3)
        logger.info("Real-time processing engine started successfully")
    except Exception as e:
        logger.error(f"Real-time processor startup failed: {str(e)}")
        # Don't exit - application can still run with batch processing
    
    logger.info("Enhanced API endpoints registered:")
    logger.info("  - Legacy compatibility maintained")
    logger.info("  - New v2 APIs available")
    logger.info("  - Real-time processing enabled")
    logger.info("  - Entity management active")
    logger.info("  - Analytics engine ready")
    
    # Start the application
    app.run(
        host='0.0.0.0',
        port=settings.PORT,
        debug=settings.DEBUG
    ) 