"""
Task Routes Blueprint
====================

Task management routes with knowledge tree integration.
"""

import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from ..middleware.auth_middleware import get_current_user, require_auth

logger = logging.getLogger(__name__)

# Create blueprint
task_bp = Blueprint('task', __name__, url_prefix='/api/tasks')


@task_bp.route('/create-tactical', methods=['POST'])
@require_auth
def create_tactical_tasks():
    """Create tactical tasks with knowledge tree context and high confidence threshold"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager, Email
        from prompts.prompt_loader import load_prompt, PromptCategories
        import anthropic
        from config.settings import settings
        
        data = request.get_json() or {}
        use_knowledge_tree = data.get('use_knowledge_tree', True)
        tactical_only = data.get('tactical_only', True)
        confidence_threshold = data.get('confidence_threshold', 0.7)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get knowledge tree for context
        if use_knowledge_tree:
            from api.routes.email_routes import get_master_knowledge_tree
            master_tree = get_master_knowledge_tree(db_user.id)
            if not master_tree:
                return jsonify({
                    'success': False,
                    'error': 'No knowledge tree found. Please build the knowledge tree first.'
                }), 400
        
        # Get emails that have been assigned to knowledge tree but don't have tasks yet
        with get_db_manager().get_session() as session:
            emails_for_tasks = session.query(Email).filter(
                Email.user_id == db_user.id,
                Email.ai_summary.is_not(None),  # Has been processed
                Email.business_category.is_not(None),  # Has been assigned to tree
                Email.strategic_importance >= 0.5  # Only strategically important emails
            ).limit(50).all()
            
            if not emails_for_tasks:
                return jsonify({
                    'success': True,
                    'tasks_created': 0,
                    'message': 'No emails ready for tactical task extraction'
                })
            
            # Initialize Claude
            claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            tasks_created = 0
            high_priority_tasks = 0
            sample_tasks = []
            
            logger.info(f"Creating tactical tasks from {len(emails_for_tasks)} knowledge-categorized emails")
            
            for email in emails_for_tasks:
                try:
                    # Prepare enhanced email context with knowledge tree
                    email_data = {
                        'subject': email.subject or '',
                        'sender': email.sender or '',
                        'content': email.body_clean or email.snippet or '',
                        'ai_summary': email.ai_summary or '',
                        'primary_topic': email.business_category or '',
                        'importance_score': email.strategic_importance or 0.0,
                        'date': email.email_date.isoformat() if email.email_date else ''
                    }
                    
                    # Load tactical task extraction prompt
                    prompt = load_prompt(
                        PromptCategories.TASK_EXTRACTION,
                        PromptCategories.TASK_EXTRACTION_360,
                        enhanced_email_context=_format_email_for_tactical_tasks(email_data, master_tree if use_knowledge_tree else None),
                        context_strength=0.8,  # High context strength since we have knowledge tree
                        connection_count=3  # Assume good connections since email is categorized
                    )
                    
                    # Add tactical-only instruction
                    tactical_instruction = f"""
TACTICAL TASK EXTRACTION (Confidence Threshold: {confidence_threshold}):
- ONLY extract OBVIOUS, CLEAR, ACTIONABLE tasks
- IGNORE vague or ambiguous requests
- FOCUS on specific deliverables with clear deadlines
- SKIP general "follow up" tasks unless very specific
- REQUIRE confidence >= {confidence_threshold} for all tasks
- TACTICAL tasks are concrete, specific, and measurable

{prompt}"""
                    
                    response = claude_client.messages.create(
                        model=settings.CLAUDE_MODEL,
                        max_tokens=2000,
                        messages=[{"role": "user", "content": tactical_instruction}]
                    )
                    
                    # Parse tasks
                    response_text = response.content[0].text.strip()
                    tasks = _parse_tactical_tasks(response_text, confidence_threshold)
                    
                    # Save high-confidence tasks only
                    for task_data in tasks:
                        if task_data.get('confidence', 0) >= confidence_threshold:
                            task = _save_tactical_task(task_data, email, db_user.id, master_tree)
                            if task:
                                tasks_created += 1
                                if task_data.get('priority') == 'high':
                                    high_priority_tasks += 1
                                
                                if len(sample_tasks) < 5:
                                    sample_tasks.append({
                                        'description': task_data['description'],
                                        'priority': task_data.get('priority', 'medium'),
                                        'confidence': task_data.get('confidence', 0),
                                        'source_email': email.subject
                                    })
                    
                except Exception as e:
                    logger.error(f"Error processing email {email.id} for tactical tasks: {str(e)}")
                    continue
            
            session.commit()
            
            return jsonify({
                'success': True,
                'tasks_created': tasks_created,
                'high_priority_tasks': high_priority_tasks,
                'knowledge_context_applied': use_knowledge_tree,
                'confidence_threshold': confidence_threshold,
                'emails_processed': len(emails_for_tasks),
                'sample_tasks': sample_tasks,
                'message': f'Created {tasks_created} tactical tasks with {confidence_threshold} confidence threshold'
            })
            
    except Exception as e:
        logger.error(f"Create tactical tasks error: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _format_email_for_tactical_tasks(email_data, master_tree=None):
    """Format email with knowledge tree context for tactical task extraction"""
    context = f"""
EMAIL DETAILS:
Subject: {email_data['subject']}
From: {email_data['sender']}
Date: {email_data['date']}
AI Summary: {email_data['ai_summary']}

EMAIL CONTENT:
{email_data['content']}

KNOWLEDGE TREE CONTEXT:
Primary Topic: {email_data['primary_topic']}
Strategic Importance: {email_data['importance_score']:.2f}
"""
    
    if master_tree:
        # Add relevant context from knowledge tree
        related_topics = []
        related_people = []
        related_projects = []
        
        # Find related items in knowledge tree
        for topic in master_tree.get('topics', []):
            if topic['name'].lower() in email_data['ai_summary'].lower():
                related_topics.append(topic['name'])
        
        for person in master_tree.get('people', []):
            if person['email'].lower() == email_data['sender'].lower():
                related_people.append(f"{person['name']} ({person.get('role', 'Unknown role')})")
        
        for project in master_tree.get('projects', []):
            if project['name'].lower() in email_data['ai_summary'].lower():
                related_projects.append(f"{project['name']} (Status: {project.get('status', 'Unknown')})")
        
        if related_topics:
            context += f"\nRelated Topics: {', '.join(related_topics)}"
        if related_people:
            context += f"\nRelated People: {', '.join(related_people)}"
        if related_projects:
            context += f"\nRelated Projects: {', '.join(related_projects)}"
    
    return context


def _parse_tactical_tasks(response_text, confidence_threshold):
    """Parse Claude response for tactical tasks with confidence filtering"""
    import json
    import re
    
    try:
        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not json_match:
            return []
        
        tasks_data = json.loads(json_match.group())
        if not isinstance(tasks_data, list):
            return []
        
        # Filter by confidence threshold
        tactical_tasks = []
        for task in tasks_data:
            if isinstance(task, dict) and task.get('confidence', 0) >= confidence_threshold:
                tactical_tasks.append(task)
        
        logger.info(f"Filtered {len(tactical_tasks)} tactical tasks from {len(tasks_data)} candidates")
        return tactical_tasks
        
    except Exception as e:
        logger.error(f"Error parsing tactical tasks: {str(e)}")
        return []


def _save_tactical_task(task_data, source_email, user_id, master_tree=None):
    """Save a tactical task to the database with knowledge tree context"""
    try:
        from chief_of_staff_ai.models.database import get_db_manager, Task
        from datetime import datetime
        
        # Enhanced task description with knowledge context
        description = task_data['description']
        if master_tree and source_email.business_category:
            description = f"[{source_email.business_category}] {description}"
        
        task = Task(
            user_id=user_id,
            email_id=source_email.id,
            description=description,
            category=task_data.get('category', 'tactical'),
            priority=task_data.get('priority', 'medium'),
            status='pending',
            confidence=task_data.get('confidence', 0.7),
            due_date=_parse_due_date(task_data.get('due_date_text')),
            created_at=datetime.utcnow(),
            source_context=f"Tactical extraction from: {source_email.subject}",
            # Enhanced with knowledge tree context
            business_intelligence={
                'knowledge_tree_topic': source_email.business_category,
                'strategic_importance': source_email.strategic_importance,
                'tactical_task': True,
                'confidence_threshold': 0.7,
                'extraction_method': 'knowledge_tree_tactical'
            }
        )
        
        with get_db_manager().get_session() as session:
            session.add(task)
            session.commit()
            return task
        
    except Exception as e:
        logger.error(f"Error saving tactical task: {str(e)}")
        return None


def _parse_due_date(date_text):
    """Parse due date from text"""
    if not date_text:
        return None
    
    try:
        from dateutil import parser
        return parser.parse(date_text, fuzzy=True)
    except:
        return None


@task_bp.route('/tasks', methods=['GET'])
@require_auth
def api_get_tasks():
    """Get tasks with comprehensive context and business intelligence"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        
        user_email = user['email']
        
        # Clear any cache to ensure fresh data
        try:
            from chief_of_staff_ai.strategic_intelligence.strategic_intelligence_cache import strategic_intelligence_cache
            strategic_intelligence_cache.invalidate(user_email)
        except ImportError:
            pass  # Cache module might not exist
        
        # Get real user and their tasks
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        tasks = get_db_manager().get_user_tasks(db_user.id, status)
        if limit:
            tasks = tasks[:limit]
        
        # Build task data with context
        tasks_data = []
        for task in tasks:
            if task.description and len(task.description.strip()) > 3:
                task_data = {
                    'id': task.id,
                    'description': task.description,
                    'details': task.source_text or '',
                    'priority': task.priority or 'medium',
                    'status': task.status or 'pending',
                    'category': task.category or 'general',
                    'confidence': task.confidence or 0.8,
                    'assignee': task.assignee or user_email,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'source_email_subject': getattr(task, 'source_email_subject', None),
                }
                tasks_data.append(task_data)
        
        return jsonify({
            'success': True,
            'tasks': tasks_data,
            'count': len(tasks_data),
            'status_filter': status
        })
        
    except Exception as e:
        logger.error(f"Get tasks API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@task_bp.route('/email-insights', methods=['GET'])
@require_auth  
def api_get_email_insights():
    """Get strategic business insights from emails"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Placeholder for business insights
        return jsonify({
            'success': True,
            'strategic_insights': [],
            'count': 0,
            'data_source': 'real_business_insights'
        })
        
    except Exception as e:
        logger.error(f"Get email insights API error: {str(e)}")
        return jsonify({'error': str(e)}), 500 