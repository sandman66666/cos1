"""
Intelligence Routes Blueprint
============================

AI insights, proactive analysis, and chat routes.
Extracted from main.py for better organization.
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from ..middleware.auth_middleware import get_current_user, require_auth

logger = logging.getLogger(__name__)

# Create blueprint
intelligence_bp = Blueprint('intelligence', __name__, url_prefix='/api')


@intelligence_bp.route('/chat', methods=['POST'])
@require_auth
def api_chat():
    """Enhanced Claude chat with REQUIRED business knowledge context"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Import here to avoid circular imports
        import anthropic
        from config.settings import settings
        from processors.email_intelligence import email_intelligence
        from models.database import get_db_manager
        from api.routes.email_routes import get_master_knowledge_tree
        # Import the new prompt loader
        from prompts.prompt_loader import load_prompt, PromptCategories
        
        # Initialize Claude client
        claude_client = None
        if settings.ANTHROPIC_API_KEY:
            claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        if not claude_client:
            return jsonify({'error': 'Claude integration not configured'}), 500
    
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # ENFORCE KNOWLEDGE TREE REQUIREMENT
        master_tree = get_master_knowledge_tree(db_user.id)
        if not master_tree:
            return jsonify({
                'error': 'Knowledge tree required for chat functionality',
                'message': 'Please complete Step 2: Build Knowledge Tree before using the AI chat.',
                'action_required': 'build_knowledge_tree',
                'redirect_to': '/settings'
            }), 400
        
        # Get comprehensive business knowledge
        knowledge_response = email_intelligence.get_chat_knowledge_summary(user_email)
        business_knowledge = knowledge_response.get('knowledge_base', {}) if knowledge_response.get('success') else {}
        
        # Build comprehensive context
        context_parts = []
        
        # Add knowledge tree context FIRST
        context_parts.append("MASTER KNOWLEDGE TREE CONTEXT:")
        context_parts.append(f"Topics: {', '.join([t['name'] for t in master_tree.get('topics', [])])}")
        context_parts.append(f"Key People: {', '.join([p['name'] for p in master_tree.get('people', [])])}")
        context_parts.append(f"Active Projects: {', '.join([p['name'] for p in master_tree.get('projects', [])])}")
        
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
        
        # Create comprehensive business context string
        business_context = "\n\n".join(context_parts) if context_parts else "Knowledge tree available but limited business context."
        
        # ALWAYS use enhanced chat system prompt (no fallback)
        enhanced_system_prompt = load_prompt(
            PromptCategories.INTELLIGENCE_CHAT,
            PromptCategories.ENHANCED_CHAT_SYSTEM,
            user_email=user_email,
            business_context=business_context
        )
        
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
            'knowledge_source': 'knowledge_tree_required',
            'tree_topics_count': len(master_tree.get('topics', [])),
            'tree_people_count': len(master_tree.get('people', [])),
            'tree_projects_count': len(master_tree.get('projects', []))
        })
        
    except Exception as e:
        logger.error(f"Enhanced chat API error: {str(e)}")
        return jsonify({'success': False, 'error': f'Chat error: {str(e)}'}), 500


@intelligence_bp.route('/intelligence-metrics', methods=['GET'])
@require_auth
def api_intelligence_metrics():
    """API endpoint for real-time intelligence metrics - WITH EMAIL QUALITY FILTERING"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter, ContactTier
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # APPLY EMAIL QUALITY FILTERING for intelligent metrics
        logger.info(f"🔍 Applying email quality filtering to intelligence metrics for user {user_email}")
        
        # Get contact tier summary (this triggers analysis if needed)
        tier_summary = email_quality_filter.get_contact_tier_summary(db_user.id)
        
        # Get counts
        all_emails = get_db_manager().get_user_emails(db_user.id, limit=1000)
        all_people = get_db_manager().get_user_people(db_user.id, limit=1000)
        tasks = get_db_manager().get_user_tasks(db_user.id, limit=1000)
        projects = get_db_manager().get_user_projects(db_user.id, limit=1000)
        topics = get_db_manager().get_user_topics(db_user.id, limit=1000)
        
        # Filter emails and people by quality tiers
        quality_filtered_emails = []
        quality_filtered_people = []
        tier_stats = {'tier_1': 0, 'tier_2': 0, 'tier_last_filtered': 0, 'unclassified': 0}
        
        # Filter people by contact tiers
        for person in all_people:
            if person.name and person.email_address:
                contact_stats = email_quality_filter._get_contact_stats(person.email_address.lower(), db_user.id)
                
                if contact_stats.tier == ContactTier.TIER_LAST:
                    tier_stats['tier_last_filtered'] += 1
                    continue  # Skip Tier LAST contacts
                elif contact_stats.tier == ContactTier.TIER_1:
                    tier_stats['tier_1'] += 1
                elif contact_stats.tier == ContactTier.TIER_2:
                    tier_stats['tier_2'] += 1
                else:
                    tier_stats['unclassified'] += 1
                
                quality_filtered_people.append(person)
        
        # Filter emails from quality contacts only
        quality_contact_emails = set()
        for person in quality_filtered_people:
            if person.email_address:
                quality_contact_emails.add(person.email_address.lower())
        
        for email in all_emails:
            if email.sender:
                sender_email = email.sender.lower()
                # Include emails from quality contacts or if no sender specified
                if sender_email in quality_contact_emails or not sender_email:
                    quality_filtered_emails.append(email)
        
        logger.info(f"📊 Quality filtering: {len(quality_filtered_emails)}/{len(all_emails)} emails, {len(quality_filtered_people)}/{len(all_people)} people kept")
        
        # Quality metrics based on filtered data
        processed_emails = [e for e in quality_filtered_emails if e.ai_summary]
        high_quality_people = [p for p in quality_filtered_people if p.name and p.email_address and '@' in p.email_address]
        actionable_tasks = [t for t in tasks if t.status == 'pending' and t.description]
        active_projects = [p for p in projects if p.status == 'active']
        
        # Intelligence quality score (enhanced with tier filtering)
        total_entities = len(quality_filtered_emails) + len(quality_filtered_people) + len(tasks) + len(projects)
        processed_entities = len(processed_emails) + len(high_quality_people) + len(actionable_tasks) + len(active_projects)
        intelligence_quality = (processed_entities / max(total_entities, 1)) * 100
        
        # Enhanced metrics with tier information
        important_contacts = len([p for p in high_quality_people if p.total_emails >= 3])
        tier_1_contacts = tier_stats['tier_1']
        high_priority_tasks = len([t for t in tasks if t.priority == 'high'])
        
        metrics = {
            'total_entities': total_entities,
            'processed_entities': processed_entities,
            'intelligence_quality': round(intelligence_quality, 1),
            'quality_filtering_applied': True,
            'tier_filtering_stats': {
                'tier_1_contacts': tier_stats['tier_1'],
                'tier_2_contacts': tier_stats['tier_2'],
                'tier_last_filtered_out': tier_stats['tier_last_filtered'],
                'unclassified': tier_stats['unclassified'],
                'quality_emails_kept': len(quality_filtered_emails),
                'total_emails': len(all_emails)
            },
            'data_breakdown': {
                'emails': {'total': len(all_emails), 'quality_filtered': len(quality_filtered_emails), 'processed': len(processed_emails)},
                'people': {'total': len(all_people), 'quality_filtered': len(quality_filtered_people), 'tier_1': tier_stats['tier_1']},
                'tasks': {'total': len(tasks), 'actionable': len(actionable_tasks), 'high_priority': high_priority_tasks},
                'projects': {'total': len(projects), 'active': len(active_projects)},
                'topics': {'total': len(topics), 'official': len([t for t in topics if t.is_official])}
            },
            'insights': {
                'important_contacts': important_contacts,
                'tier_1_contacts': tier_1_contacts,
                'pending_decisions': high_priority_tasks,
                'active_work_streams': len(active_projects),
                'data_quality_score': round(intelligence_quality, 1)
            }
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Intelligence metrics error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/intelligence-insights', methods=['GET'])  
@require_auth
def get_intelligence_insights():
    """Strategic business insights for dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Import the business insights function from main
        from __main__ import get_strategic_business_insights
        
        user_email = user['email']
        insights = get_strategic_business_insights(user_email)
        
        return jsonify({
            'success': True,
            'insights': insights,
            'count': len(insights)
        })
        
    except Exception as e:
        logger.error(f"Intelligence insights error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/generate-insights', methods=['POST'])
@require_auth
def api_generate_insights():
    """Generate fresh insights on demand"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # This could trigger a fresh analysis
        from __main__ import get_strategic_business_insights
        
        user_email = user['email']
        insights = get_strategic_business_insights(user_email)
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(insights)} strategic insights',
            'insights': insights
        })
        
    except Exception as e:
        logger.error(f"Generate insights error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/insights/<int:insight_id>/feedback', methods=['POST'])
@require_auth
def api_insight_feedback(insight_id):
    """Record feedback on insights"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        feedback = data.get('feedback')  # 'helpful' or 'not_helpful'
        
        # For now, just log the feedback
        logger.info(f"Insight feedback from {user['email']}: insight_id={insight_id}, feedback={feedback}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback recorded'
        })
        
    except Exception as e:
        logger.error(f"Insight feedback error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/proactive-insights/generate', methods=['POST'])
@require_auth
def generate_proactive_insights():
    """Generate proactive business insights"""
    user = get_current_user() 
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Import here to avoid circular imports
        from processors.intelligence_engine import intelligence_engine
        
        user_email = user['email']
        
        # Generate proactive insights using the intelligence engine
        result = intelligence_engine.generate_proactive_insights(user_email)
        
        return jsonify({
            'success': True,
            'insights': result.get('insights', []),
            'summary': result.get('summary', {}),
            'generated_at': result.get('timestamp')
        })
        
    except Exception as e:
        logger.error(f"Proactive insights generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/business-knowledge', methods=['GET'])
@require_auth
def api_get_business_knowledge():
    """Get comprehensive business knowledge base"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from processors.email_intelligence import email_intelligence
        
        user_email = user['email']
        result = email_intelligence.get_chat_knowledge_summary(user_email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Business knowledge API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/chat-knowledge', methods=['GET'])
@require_auth
def api_get_chat_knowledge():
    """Get knowledge base for chat context"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from processors.email_intelligence import email_intelligence
        
        user_email = user['email']
        result = email_intelligence.get_chat_knowledge_summary(user_email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Chat knowledge API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/download-knowledge-base', methods=['GET'])
@require_auth
def api_download_knowledge_base():
    """Download comprehensive knowledge base as JSON"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from flask import make_response
        from models.database import get_db_manager
        import json
        from datetime import datetime
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get all user data
        emails = get_db_manager().get_user_emails(db_user.id)
        people = get_db_manager().get_user_people(db_user.id)
        tasks = get_db_manager().get_user_tasks(db_user.id)
        projects = get_db_manager().get_user_projects(db_user.id)
        topics = get_db_manager().get_user_topics(db_user.id)
        
        # Build comprehensive knowledge base
        knowledge_base = {
            'user_email': user_email,
            'exported_at': datetime.now().isoformat(),
            'summary': {
                'total_emails': len(emails),
                'total_people': len(people),
                'total_tasks': len(tasks),
                'total_projects': len(projects),
                'total_topics': len(topics)
            },
            'emails': [email.to_dict() for email in emails],
            'people': [person.to_dict() for person in people],
            'tasks': [task.to_dict() for task in tasks],
            'projects': [project.to_dict() for project in projects],
            'topics': [topic.to_dict() for topic in topics]
        }
        
        # Create JSON response
        response_data = json.dumps(knowledge_base, indent=2, default=str)
        response = make_response(response_data)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename="{user_email}_knowledge_base_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
        
    except Exception as e:
        logger.error(f"Download knowledge base error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/entity/<entity_type>/<int:entity_id>/context', methods=['GET'])
@require_auth
def api_get_entity_context(entity_type, entity_id):
    """Get detailed context and raw source content for any entity"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get the entity details
        entity = None
        source_emails = []
        related_entities = {}
        
        if entity_type == 'task':
            entity = get_db_manager().get_task(entity_id)
            if entity and entity.user_id == db_user.id:
                # Find source emails for this task
                if hasattr(entity, 'source_email_id') and entity.source_email_id:
                    source_email = get_db_manager().get_email(entity.source_email_id)
                    if source_email:
                        source_emails.append(source_email)
                
                # Find related people mentioned in task
                if entity.description:
                    people = get_db_manager().get_user_people(db_user.id)
                    related_entities['mentioned_people'] = [
                        p for p in people if p.name.lower() in entity.description.lower()
                    ]
        
        elif entity_type == 'person':
            entity = get_db_manager().get_person(entity_id)
            if entity and entity.user_id == db_user.id:
                # Get all emails from/to this person
                source_emails = [
                    email for email in get_db_manager().get_user_emails(db_user.id)
                    if entity.email_address and (
                        (email.sender and entity.email_address.lower() in email.sender.lower()) or
                        (email.recipients and entity.email_address.lower() in email.recipients.lower())
                    )
                ][:10]  # Limit to 10 most recent
                
                # Get tasks related to this person
                tasks = get_db_manager().get_user_tasks(db_user.id)
                related_entities['related_tasks'] = [
                    t for t in tasks if entity.name.lower() in t.description.lower()
                ][:5]
        
        elif entity_type == 'topic':
            entity = get_db_manager().get_topic(entity_id)
            if entity and entity.user_id == db_user.id:
                # Find emails that contributed to this topic
                all_emails = get_db_manager().get_user_emails(db_user.id)
                source_emails = []
                
                # Search for topic keywords in email content
                topic_keywords = entity.name.lower().split()
                for email in all_emails:
                    if email.ai_summary or email.body:
                        content = (email.ai_summary or email.body or '').lower()
                        if any(keyword in content for keyword in topic_keywords):
                            source_emails.append(email)
                            if len(source_emails) >= 5:  # Limit to 5 examples
                                break
                
                # Get related tasks and people
                tasks = get_db_manager().get_user_tasks(db_user.id)
                people = get_db_manager().get_user_people(db_user.id)
                
                related_entities['related_tasks'] = [
                    t for t in tasks if any(keyword in t.description.lower() for keyword in topic_keywords)
                ][:3]
                
                related_entities['related_people'] = [
                    p for p in people if any(keyword in (p.name or '').lower() for keyword in topic_keywords)
                ][:3]
        
        elif entity_type == 'email':
            entity = get_db_manager().get_email(entity_id)
            if entity and entity.user_id == db_user.id:
                source_emails = [entity]  # The email itself is the source
                
                # Find tasks generated from this email
                tasks = get_db_manager().get_user_tasks(db_user.id)
                related_entities['generated_tasks'] = [
                    t for t in tasks if hasattr(t, 'source_email_id') and t.source_email_id == entity_id
                ]
        
        if not entity:
            return jsonify({'error': 'Entity not found or access denied'}), 404
        
        # Build response
        context_data = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_details': entity.to_dict() if hasattr(entity, 'to_dict') else str(entity),
            'source_emails': [
                {
                    'id': email.id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'recipients': email.recipients,
                    'date_sent': email.date_sent.isoformat() if email.date_sent else None,
                    'body': email.body,
                    'ai_summary': email.ai_summary,
                    'ai_tasks': email.ai_tasks,
                    'ai_insights': email.ai_insights
                } for email in source_emails
            ],
            'related_entities': {
                key: [item.to_dict() if hasattr(item, 'to_dict') else str(item) for item in items]
                for key, items in related_entities.items()
            },
            'traceability': {
                'source_count': len(source_emails),
                'confidence': getattr(entity, 'confidence_score', None) or getattr(entity, 'confidence', None),
                'created_at': getattr(entity, 'created_at', None),
                'last_updated': getattr(entity, 'updated_at', None)
            }
        }
        
        return jsonify({
            'success': True,
            'context': context_data
        })
        
    except Exception as e:
        logger.error(f"Get entity context error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/entity/<entity_type>/<int:entity_id>/raw-sources', methods=['GET'])
@require_auth  
def api_get_entity_raw_sources(entity_type, entity_id):
    """Get raw source content that contributed to an entity's creation/analysis"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        raw_sources = []
        
        if entity_type == 'task':
            # Get the task and find its source email(s)
            task = get_db_manager().get_task(entity_id)
            if task and task.user_id == db_user.id:
                if hasattr(task, 'source_email_id') and task.source_email_id:
                    source_email = get_db_manager().get_email(task.source_email_id)
                    if source_email:
                        raw_sources.append({
                            'type': 'email',
                            'id': source_email.id,
                            'title': f"Email: {source_email.subject}",
                            'content': source_email.body,
                            'metadata': {
                                'sender': source_email.sender,
                                'date': source_email.date_sent.isoformat() if source_email.date_sent else None,
                                'ai_analysis': source_email.ai_summary
                            }
                        })
        
        elif entity_type == 'topic':
            # Find the emails that contributed to this topic
            topic = get_db_manager().get_topic(entity_id)
            if topic and topic.user_id == db_user.id:
                # Search through emails for content that matches this topic
                all_emails = get_db_manager().get_user_emails(db_user.id)
                topic_keywords = topic.name.lower().split()
                
                for email in all_emails[:20]:  # Check recent emails
                    if email.ai_summary or email.body:
                        content = (email.ai_summary or email.body or '').lower()
                        keyword_matches = [kw for kw in topic_keywords if kw in content]
                        
                        if keyword_matches:
                            raw_sources.append({
                                'type': 'email',
                                'id': email.id,
                                'title': f"Email: {email.subject}",
                                'content': email.body,
                                'relevance_score': len(keyword_matches) / len(topic_keywords),
                                'matched_keywords': keyword_matches,
                                'metadata': {
                                    'sender': email.sender,
                                    'date': email.date_sent.isoformat() if email.date_sent else None,
                                    'ai_analysis': email.ai_summary
                                }
                            })
                
                # Sort by relevance
                raw_sources.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
                raw_sources = raw_sources[:5]  # Top 5 most relevant
        
        elif entity_type == 'person':
            # Get emails from/to this person
            person = get_db_manager().get_person(entity_id)
            if person and person.user_id == db_user.id and person.email_address:
                all_emails = get_db_manager().get_user_emails(db_user.id)
                
                for email in all_emails:
                    email_involves_person = False
                    if email.sender and person.email_address.lower() in email.sender.lower():
                        email_involves_person = True
                    elif email.recipients and person.email_address.lower() in email.recipients.lower():
                        email_involves_person = True
                    
                    if email_involves_person:
                        raw_sources.append({
                            'type': 'email',
                            'id': email.id,
                            'title': f"Email: {email.subject}",
                            'content': email.body,
                            'metadata': {
                                'sender': email.sender,
                                'recipients': email.recipients,
                                'date': email.date_sent.isoformat() if email.date_sent else None,
                                'ai_analysis': email.ai_summary,
                                'direction': 'from' if person.email_address.lower() in (email.sender or '').lower() else 'to'
                            }
                        })
                
                # Sort by date, most recent first
                raw_sources.sort(key=lambda x: x['metadata'].get('date', ''), reverse=True)
                raw_sources = raw_sources[:10]  # Most recent 10
        
        return jsonify({
            'success': True,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'raw_sources': raw_sources,
            'sources_count': len(raw_sources)
        })
        
    except Exception as e:
        logger.error(f"Get entity raw sources error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/knowledge/topics/hierarchy', methods=['GET'])
@require_auth
def api_get_topics_hierarchy():
    """Get topic hierarchy for knowledge tree visualization"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get all topics for the user
        topics = get_db_manager().get_user_topics(db_user.id)
        
        # Build hierarchy structure
        topic_dict = {}
        root_topics = []
        
        # Convert topics to dict format and organize by parent
        for topic in topics:
            topic_data = {
                'id': topic.id,
                'name': topic.name,
                'description': topic.description,
                'topic_type': 'business',  # Default since field doesn't exist
                'hierarchy_path': topic.name,  # Use name as path since hierarchy_path doesn't exist
                'depth_level': 0,  # Default since field doesn't exist
                'parent_topic_id': topic.parent_topic_id,
                'confidence_score': topic.confidence_score or 0.0,
                'mention_count': topic.total_mentions or 0,  # Use actual field name
                'auto_generated': not topic.is_official,  # Infer from is_official
                'user_created': topic.is_official,  # Use is_official
                'status': 'active',  # Default since field doesn't exist
                'priority': 'medium',  # Default since field doesn't exist
                'last_mentioned': topic.last_mentioned.isoformat() if topic.last_mentioned else None,
                'children': []
            }
            topic_dict[topic.id] = topic_data
            
            if topic.parent_topic_id is None:
                root_topics.append(topic_data)
        
        # Build parent-child relationships
        for topic in topics:
            if topic.parent_topic_id and topic.parent_topic_id in topic_dict:
                parent = topic_dict[topic.parent_topic_id]
                child = topic_dict[topic.id]
                parent['children'].append(child)
        
        # Calculate statistics
        stats = {
            'total_topics': len(topics),
            'max_depth': 0,  # Default since depth_level doesn't exist
            'auto_generated': len([t for t in topics if not t.is_official]),  # Infer from is_official
            'user_created': len([t for t in topics if t.is_official]),  # Use is_official
            'by_type': {'business': len(topics)},  # Default type since topic_type doesn't exist
            'recent_activity': len([t for t in topics if t.last_mentioned and 
                                  (t.last_mentioned.date() >= (datetime.now().date() - timedelta(days=7)))])
        }
        
        return jsonify({
            'success': True,
            'hierarchy': root_topics,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Get topics hierarchy error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/knowledge/foundation/build-from-bulk-emails', methods=['POST'])
@require_auth
def api_build_knowledge_foundation():
    """Build knowledge foundation and topic hierarchy from bulk email analysis"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        import json
        
        data = request.get_json() or {}
        months_back = data.get('months_back', 6)
        use_tier_filtered_emails = data.get('use_tier_filtered_emails', True)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get emails for analysis (use tier filtering if requested)
        emails = get_db_manager().get_user_emails(
            db_user.id, 
            limit=500,  # Process more emails for better knowledge base
            days_back=months_back * 30
        )
        
        if not emails:
            return jsonify({'error': 'No emails found for knowledge base building'}), 400
        
        # Filter by quality if requested
        quality_emails = []
        if use_tier_filtered_emails:
            # Only use emails from people we have positive engagement with
            for email in emails:
                if email.sender and '@' in email.sender:
                    # Simple heuristic: if we have content and it's not purely informational
                    if (email.body_clean or email.snippet) and email.message_type != 'spam':
                        quality_emails.append(email)
        else:
            quality_emails = [e for e in emails if e.body_clean or e.snippet]
        
        # Build knowledge foundation from email content
        topics_created = 0
        business_areas = set()
        projects = set()
        
        # Extract key business themes from emails
        business_themes = {}
        for email in quality_emails[:100]:  # Process first 100 quality emails
            # Simple keyword-based topic extraction
            content = (email.body_clean or email.snippet or '').lower()
            subject = (email.subject or '').lower()
            
            # Look for business indicators
            if any(word in content + ' ' + subject for word in ['project', 'meeting', 'deadline', 'deliverable']):
                projects.add(email.subject[:50] if email.subject else 'Unnamed Project')
            
            if any(word in content + ' ' + subject for word in ['client', 'customer', 'sales', 'revenue']):
                business_areas.add('Sales & Customer Relations')
            
            if any(word in content + ' ' + subject for word in ['development', 'technical', 'code', 'system']):
                business_areas.add('Technical Development')
            
            if any(word in content + ' ' + subject for word in ['team', 'management', 'leadership', 'strategy']):
                business_areas.add('Team Management')
        
        # Create topics in database
        for area in list(business_areas)[:10]:  # Limit to 10 business areas
            topic_data = {
                'name': area,
                'description': f"Auto-generated business area from email analysis",
                'is_official': False,
                'confidence_score': 0.7
            }
            topic = get_db_manager().create_or_update_topic(db_user.id, topic_data)
            if topic:
                topics_created += 1
        
        # Create project topics
        for project in list(projects)[:5]:  # Limit to 5 projects
            topic_data = {
                'name': f"Project: {project}",
                'description': f"Auto-generated project from email analysis",
                'is_official': False,
                'confidence_score': 0.6
            }
            topic = get_db_manager().create_or_update_topic(db_user.id, topic_data)
            if topic:
                topics_created += 1
        
        foundation_stats = {
            'emails_analyzed': len(quality_emails),
            'topics_created': topics_created,
            'business_areas': len(business_areas),
            'projects': len(projects),
            'quality_filtering_used': use_tier_filtered_emails
        }
        
        return jsonify({
            'success': True,
            'foundation_stats': foundation_stats,
            'message': f'Knowledge foundation built from {len(quality_emails)} emails'
        })
        
    except Exception as e:
        print(f"Build knowledge foundation error: {e}")
        return jsonify({'error': str(e)}), 500


@intelligence_bp.route('/knowledge/reorganize-content', methods=['POST'])
@require_auth
def api_reorganize_content():
    """Reorganize existing content into topic hierarchy"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        data = request.get_json() or {}
        reprocess_emails = data.get('reprocess_emails', True)
        reprocess_tasks = data.get('reprocess_tasks', True)
        update_relationships = data.get('update_relationships', True)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get existing topics
        topics = get_db_manager().get_user_topics(db_user.id)
        if not topics:
            return jsonify({'error': 'No topics found. Please build knowledge foundation first.'}), 400
        
        stats = {
            'emails_categorized': 0,
            'tasks_categorized': 0,
            'relationships_updated': 0,
            'topics_populated': 0
        }
        
        # Reorganize emails by topics
        if reprocess_emails:
            emails = get_db_manager().get_user_emails(db_user.id, limit=200)
            for email in emails:
                if email.body_clean or email.subject:
                    # Simple topic matching based on content
                    content = (email.body_clean or '') + ' ' + (email.subject or '')
                    content_lower = content.lower()
                    
                    for topic in topics:
                        topic_keywords = topic.name.lower().split()
                        if any(keyword in content_lower for keyword in topic_keywords):
                            # Update email with primary topic (simplified approach)
                            try:
                                # Update via session instead of non-existent method
                                with get_db_manager().get_session() as session:
                                    email_obj = session.merge(email)
                                    email_obj.primary_topic_id = topic.id
                                    session.commit()
                                    stats['emails_categorized'] += 1
                                    break
                            except:
                                pass  # Skip if update fails
        
        # Reorganize tasks by topics
        if reprocess_tasks:
            tasks = get_db_manager().get_user_tasks(db_user.id, limit=100)
            for task in tasks:
                if task.description:
                    desc_lower = task.description.lower()
                    
                    for topic in topics:
                        topic_keywords = topic.name.lower().split()
                        if any(keyword in desc_lower for keyword in topic_keywords):
                            # Update task topics (simplified approach)
                            try:
                                # Update via session instead of non-existent method
                                with get_db_manager().get_session() as session:
                                    task_obj = session.merge(task)
                                    if hasattr(task_obj, 'topics'):
                                        import json
                                        current_topics = json.loads(task_obj.topics) if task_obj.topics else []
                                        if topic.name not in current_topics:
                                            current_topics.append(topic.name)
                                            task_obj.topics = json.dumps(current_topics)
                                            session.commit()
                                            stats['tasks_categorized'] += 1
                                            break
                            except:
                                pass  # Skip if update fails
        
        # Update relationships between people and topics
        if update_relationships:
            people = get_db_manager().get_user_people(db_user.id, limit=50)
            for person in people:
                if person.email_address:
                    # Find emails from this person
                    person_emails = [e for e in get_db_manager().get_user_emails(db_user.id, limit=100) 
                                   if e.sender == person.email_address]
                    
                    if person_emails:
                        # Extract topics from their emails
                        person_topics = set()
                        for email in person_emails[:10]:  # Check first 10 emails
                            if hasattr(email, 'primary_topic_id') and email.primary_topic_id:
                                person_topics.add(email.primary_topic_id)
                        
                        if person_topics:
                            stats['relationships_updated'] += 1
        
        stats['topics_populated'] = len([t for t in topics if stats['emails_categorized'] > 0])
        
        return jsonify({
            'success': True,
            'stats': stats,
            'message': f'Reorganized content across {len(topics)} topics'
        })
        
    except Exception as e:
        print(f"Reorganize content error: {e}")
        return jsonify({'error': str(e)}), 500 