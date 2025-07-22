"""
Email Routes Blueprint
====================

Email synchronization, processing, and quality filtering routes.
Extracted from main.py for better organization.
"""

import logging
from flask import Blueprint, request, jsonify
from ..middleware.auth_middleware import get_current_user, require_auth
from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

# Create blueprint
email_bp = Blueprint('email', __name__, url_prefix='/api')


@email_bp.route('/fetch-emails', methods=['POST'])
def api_fetch_emails():
    """API endpoint to fetch emails"""
    from ..middleware.auth_middleware import get_current_user
    from chief_of_staff_ai.ingest.gmail_fetcher import gmail_fetcher
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() or {}
        max_emails = data.get('max_emails', 10)
        days_back = data.get('days_back', 7)
        
        result = gmail_fetcher.fetch_recent_emails(
            user_email=user['email'],
            limit=max_emails,
            days_back=days_back
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Email fetch API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/trigger-email-sync', methods=['POST'])
def api_trigger_email_sync():
    """Unified email and calendar processing endpoint"""
    from ..middleware.auth_middleware import get_current_user
    from chief_of_staff_ai.ingest.gmail_fetcher import gmail_fetcher
    from chief_of_staff_ai.ingest.calendar_fetcher import calendar_fetcher
    from chief_of_staff_ai.processors.email_normalizer import email_normalizer
    from chief_of_staff_ai.processors.email_intelligence import email_intelligence
    from chief_of_staff_ai.models.database import get_db_manager
    
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
        
        logger.info(f"🚀 Starting email sync for {user_email}")
        
        # Fetch emails
        fetch_result = gmail_fetcher.fetch_recent_emails(
            user_email=user_email,
            limit=max_emails,
            days_back=days_back,
            force_refresh=force_refresh
        )
        
        if not fetch_result.get('success'):
            return jsonify({
                'success': False,
                'error': f"Email fetch failed: {fetch_result.get('error')}"
            }), 400
        
        emails_fetched = fetch_result.get('count', 0)
        
        # Normalize emails
        normalize_result = email_normalizer.normalize_user_emails(user_email, limit=max_emails)
        emails_normalized = normalize_result.get('processed', 0)
        
        # Process with AI
        intelligence_result = email_intelligence.process_user_emails_intelligently(
            user_email=user_email,
            limit=max_emails,
            force_refresh=force_refresh
        )
        
        # Get final results
        db_user = get_db_manager().get_user_by_email(user_email)
        if db_user:
            all_emails = get_db_manager().get_user_emails(db_user.id)
            all_people = get_db_manager().get_user_people(db_user.id)
            all_tasks = get_db_manager().get_user_tasks(db_user.id)
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {emails_fetched} emails!',
                'summary': {
                    'emails_fetched': emails_fetched,
                    'emails_normalized': emails_normalized,
                    'total_emails': len(all_emails),
                    'total_people': len(all_people), 
                    'total_tasks': len(all_tasks)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'User not found after processing'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Email sync error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Processing failed: {str(e)}'
        }), 500


@email_bp.route('/emails', methods=['GET'])
def api_get_emails():
    """Get existing emails"""
    from ..middleware.auth_middleware import get_current_user
    from chief_of_staff_ai.models.database import get_db_manager
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        emails = get_db_manager().get_user_emails(db_user.id, limit=50)
        
        return jsonify({
            'success': True,
            'emails': [email.to_dict() for email in emails],
            'count': len(emails)
        })
        
    except Exception as e:
        logger.error(f"Get emails API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/extract-sent-contacts', methods=['POST'])
def api_extract_sent_contacts():
    """Extract contacts from sent emails for building engagement tier rules"""
    from ..middleware.auth_middleware import get_current_user
    from chief_of_staff_ai.engagement_analysis.smart_contact_strategy import smart_contact_strategy
    from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() or {}
        days_back = data.get('days_back', 180)  # Default 6 months
        metadata_only = data.get('metadata_only', True)
        sent_only = data.get('sent_only', True)
        
        user_email = user['email']
        
        logger.info(f"🔍 Extracting sent contacts for {user_email} (last {days_back} days)")
        
        # Use the existing smart contact strategy to build trusted contact database
        result = smart_contact_strategy.build_trusted_contact_database(
            user_email=user_email,
            days_back=days_back
        )
        
        if result.get('success'):
            # Mark all contacts from sent emails as Tier 1
            contacts_analyzed = result.get('contacts_analyzed', 0)
            
            # Format response for frontend
            contact_patterns = {
                'analyzed_period_days': days_back,
                'total_contacts': contacts_analyzed,
                'tier_1_contacts': contacts_analyzed,  # All contacts are Tier 1
                'trusted_contacts_created': result.get('trusted_contacts_created', 0)
            }
            
            # Force all contacts to Tier 1 in the quality filter
            email_quality_filter.set_all_contacts_tier_1(user_email)
            
            return jsonify({
                'success': True,
                'message': f'Analyzed {result.get("sent_emails_analyzed", 0)} sent emails - all contacts marked as Tier 1',
                'emails_analyzed': result.get('sent_emails_analyzed', 0),
                'unique_contacts': contacts_analyzed,
                'contact_patterns': contact_patterns,
                'processing_metadata': {
                    'days_back': days_back,
                    'metadata_only': metadata_only,
                    'sent_only': sent_only,
                    'processed_at': f"{result.get('sent_emails_analyzed', 0)} sent emails analyzed"
                }
            })
        else:
            error_msg = result.get('error', 'Unknown error during sent email analysis')
            logger.error(f"❌ Sent contact extraction failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Extract sent contacts error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to extract sent contacts: {str(e)}'
        }), 500


@email_bp.route('/emails/fetch-sent', methods=['POST'])
@require_auth
def fetch_sent_emails():
    """Fetch sent emails for contact building"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.ingest.gmail_fetcher import gmail_fetcher
        
        data = request.get_json() or {}
        months_back = data.get('months_back', 6)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Fetch sent emails
        result = gmail_fetcher.fetch_sent_emails(
            user_email=user_email,
            days_back=months_back * 30,
            max_emails=1000
        )
        
        if result.get('success'):
            # Save each email to the database
            saved_count = 0
            for email in result.get('emails', []):
                try:
                    get_db_manager().save_email(db_user.id, email)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save email: {str(e)}")
                    continue
            
            return jsonify({
                'success': True,
                'emails_fetched': saved_count,
                'message': f"Fetched and saved {saved_count} sent emails"
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error fetching sent emails')
            }), 400
            
    except Exception as e:
        logger.error(f"Fetch sent emails error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/emails/fetch-all', methods=['POST'])
@require_auth
def fetch_all_emails():
    """Fetch all emails in batches"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.ingest.gmail_fetcher import gmail_fetcher
        
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 50)
        days_back = data.get('days_back', 30)  # Add days_back parameter
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Fetch emails using the correct method
        result = gmail_fetcher.fetch_recent_emails(
            user_email=user_email,
            limit=batch_size,
            days_back=days_back,
            force_refresh=True
        )
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'emails_fetched': result.get('emails_fetched', 0),
                'remaining_count': 0,  # This method doesn't track remaining
                'message': f"Fetched {result.get('emails_fetched', 0)} emails"
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error fetching emails')
            }), 400
            
    except Exception as e:
        logger.error(f"Fetch all emails error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/emails/build-knowledge-tree', methods=['POST'])
@require_auth
def build_knowledge_tree():
    """Build or refine the master knowledge tree from unprocessed emails"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager, Email
        
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 50)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        with get_db_manager().get_session() as session:
            # Get unprocessed emails for tree building
            unprocessed_emails = session.query(Email).filter(
                Email.user_id == db_user.id,
                Email.ai_summary.is_(None)
            ).limit(batch_size).all()
            
            if not unprocessed_emails:
                return jsonify({
                    'success': True,
                    'message': 'No emails to analyze for tree building',
                    'tree': None
                })
            
            # Prepare email data for tree building
            emails_for_tree = []
            for email in unprocessed_emails:
                email_data = {
                    'id': email.gmail_id,
                    'subject': email.subject or '',
                    'sender': email.sender or '',
                    'sender_name': email.sender_name or '',
                    'date': email.email_date.isoformat() if email.email_date else '',
                    'content': (email.body_clean or email.snippet or '')[:1000],  # Limit content length
                    'recipients': email.recipient_emails or []
                }
                emails_for_tree.append(email_data)
            
            # Check if we have an existing master tree
            existing_tree = get_master_knowledge_tree(db_user.id)
            
            # Build or refine the knowledge tree
            if existing_tree:
                logger.info(f"Refining existing knowledge tree with {len(unprocessed_emails)} new emails")
                tree_result = refine_knowledge_tree(emails_for_tree, existing_tree, user_email)
            else:
                logger.info(f"Building initial knowledge tree from {len(unprocessed_emails)} emails")
                tree_result = build_initial_knowledge_tree(emails_for_tree, user_email)
            
            if not tree_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': f"Failed to build knowledge tree: {tree_result.get('error')}"
                }), 500
            
            # Save the master tree
            save_master_knowledge_tree(db_user.id, tree_result['tree'])
            
            tree_structure = tree_result['tree']
            
            return jsonify({
                'success': True,
                'tree': tree_structure,
                'tree_stats': {
                    'topics_count': len(tree_structure.get('topics', [])),
                    'people_count': len(tree_structure.get('people', [])),
                    'projects_count': len(tree_structure.get('projects', [])),
                    'relationships_count': len(tree_structure.get('relationships', [])),
                    'emails_analyzed': len(emails_for_tree),
                    'is_refinement': existing_tree is not None
                },
                'message': f"{'Refined' if existing_tree else 'Built'} knowledge tree from {len(emails_for_tree)} emails"
            })
            
    except Exception as e:
        logger.error(f"Build knowledge tree error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/emails/assign-to-tree', methods=['POST'])
@require_auth
def assign_emails_to_tree():
    """Assign emails to the existing knowledge tree"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager, Email
        
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 50)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get the master knowledge tree
        master_tree = get_master_knowledge_tree(db_user.id)
        if not master_tree:
            return jsonify({
                'success': False,
                'error': 'No knowledge tree found. Please build the tree first.'
            }), 400
        
        with get_db_manager().get_session() as session:
            # Get unprocessed emails
            unprocessed_emails = session.query(Email).filter(
                Email.user_id == db_user.id,
                Email.ai_summary.is_(None)
            ).limit(batch_size).all()
            
            if not unprocessed_emails:
                return jsonify({
                    'success': True,
                    'processed_count': 0,
                    'remaining_count': 0,
                    'message': 'No emails to assign'
                })
            
            logger.info(f"Assigning {len(unprocessed_emails)} emails to knowledge tree")
            
            processed_count = 0
            assignment_results = []
            
            for email in unprocessed_emails:
                try:
                    # Assign email to tree and extract insights
                    assignment_result = assign_email_to_knowledge_tree(
                        email, master_tree, user_email
                    )
                    
                    if assignment_result.get('success'):
                        # Update email with tree-based insights
                        email.ai_summary = assignment_result['summary']
                        email.business_category = assignment_result['primary_topic']
                        email.strategic_importance = assignment_result['importance_score']
                        email.sentiment = assignment_result['sentiment_score']
                        email.processed_at = datetime.utcnow()
                        email.processing_version = "knowledge_tree_v1.0"
                        
                        processed_count += 1
                        assignment_results.append({
                            'email_id': email.gmail_id,
                            'subject': email.subject,
                            'assigned_topic': assignment_result['primary_topic'],
                            'importance': assignment_result['importance_score']
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing email {email.id}: {str(e)}")
                    continue
            
            session.commit()
            
            # Get remaining count
            remaining_count = session.query(Email).filter(
                Email.user_id == db_user.id,
                Email.ai_summary.is_(None)
            ).count()
            
            return jsonify({
                'success': True,
                'processed_count': processed_count,
                'remaining_count': remaining_count,
                'assignments': assignment_results[:10],  # Show first 10 assignments
                'message': f"Assigned {processed_count} emails to knowledge tree"
            })
            
    except Exception as e:
        logger.error(f"Assign emails to tree error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/emails/knowledge-tree', methods=['GET'])
@require_auth
def get_knowledge_tree():
    """Get the current master knowledge tree"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        master_tree = get_master_knowledge_tree(db_user.id)
        
        if not master_tree:
            return jsonify({
                'success': True,
                'tree': None,
                'message': 'No knowledge tree built yet'
            })
        
        return jsonify({
            'success': True,
            'tree': master_tree,
            'tree_stats': {
                'topics_count': len(master_tree.get('topics', [])),
                'people_count': len(master_tree.get('people', [])),
                'projects_count': len(master_tree.get('projects', [])),
                'relationships_count': len(master_tree.get('relationships', []))
            }
        })
        
    except Exception as e:
        logger.error(f"Get knowledge tree error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/emails/process-batch', methods=['POST'])
@require_auth
def process_email_batch():
    """Legacy endpoint - now just assigns emails to existing tree"""
    return assign_emails_to_tree()


@email_bp.route('/emails/sync-tree-to-database', methods=['POST'])
@require_auth  
def sync_knowledge_tree_to_database():
    """Sync knowledge tree JSON data to database tables for UI display"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager, Person, Topic
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get the master knowledge tree
        master_tree = get_master_knowledge_tree(db_user.id)
        if not master_tree:
            return jsonify({
                'success': False,
                'error': 'No knowledge tree found. Please build the tree first.'
            }), 400
        
        with get_db_manager().get_session() as session:
            sync_stats = {
                'people_created': 0,
                'people_updated': 0,
                'topics_created': 0,
                'topics_updated': 0
            }
            
            # Sync PEOPLE from knowledge tree to database
            for person_data in master_tree.get('people', []):
                existing_person = session.query(Person).filter(
                    Person.user_id == db_user.id,
                    Person.email_address == person_data['email']
                ).first()
                
                if existing_person:
                    # Update existing person with knowledge tree data
                    existing_person.name = person_data.get('name', existing_person.name)
                    existing_person.company = person_data.get('company', existing_person.company)
                    existing_person.title = person_data.get('role', existing_person.title)
                    existing_person.engagement_score = person_data.get('relationship_strength', 0.5) * 100
                    existing_person.business_context = {
                        'primary_topics': person_data.get('primary_topics', []),
                        'role': person_data.get('role'),
                        'relationship_strength': person_data.get('relationship_strength')
                    }
                    sync_stats['people_updated'] += 1
                else:
                    # Create new person from knowledge tree
                    new_person = Person(
                        user_id=db_user.id,
                        name=person_data.get('name', 'Unknown'),
                        email_address=person_data['email'],
                        company=person_data.get('company'),
                        title=person_data.get('role'),
                        engagement_score=person_data.get('relationship_strength', 0.5) * 100,
                        total_emails=0,  # Will be updated when processing emails
                        business_context={
                            'primary_topics': person_data.get('primary_topics', []),
                            'role': person_data.get('role'),
                            'relationship_strength': person_data.get('relationship_strength')
                        }
                    )
                    session.add(new_person)
                    sync_stats['people_created'] += 1
            
            # Sync TOPICS from knowledge tree to database
            for topic_data in master_tree.get('topics', []):
                existing_topic = session.query(Topic).filter(
                    Topic.user_id == db_user.id,
                    Topic.name == topic_data['name']
                ).first()
                
                if existing_topic:
                    # Update existing topic
                    existing_topic.description = topic_data.get('description', existing_topic.description)
                    existing_topic.confidence_score = topic_data.get('importance', 0.5)
                    existing_topic.keywords = topic_data.get('subtopics', [])
                    sync_stats['topics_updated'] += 1
                else:
                    # Create new topic from knowledge tree
                    new_topic = Topic(
                        user_id=db_user.id,
                        name=topic_data['name'],
                        description=topic_data.get('description', ''),
                        confidence_score=topic_data.get('importance', 0.5),
                        keywords=topic_data.get('subtopics', []),
                        is_official=True,  # Knowledge tree topics are considered official
                        mention_count=topic_data.get('frequency', 0)
                    )
                    session.add(new_topic)
                    sync_stats['topics_created'] += 1
            
            session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Knowledge tree synced to database successfully',
                'stats': sync_stats,
                'tree_stats': {
                    'total_people_in_tree': len(master_tree.get('people', [])),
                    'total_topics_in_tree': len(master_tree.get('topics', [])),
                    'total_projects_in_tree': len(master_tree.get('projects', []))
                }
            })
            
    except Exception as e:
        logger.error(f"Sync knowledge tree to database error: {str(e)}")
        return jsonify({'error': str(e)}), 500


def build_initial_knowledge_tree(emails_data, user_email):
    """Build the initial master knowledge tree from emails"""
    try:
        import anthropic
        from config.settings import settings
        # Import the new prompt loader
        from prompts.prompt_loader import load_prompt, PromptCategories
        
        # Initialize Claude client using the existing pattern
        claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Load prompt from external file instead of embedding it
        prompt = load_prompt(
            PromptCategories.KNOWLEDGE_TREE,
            PromptCategories.BUILD_INITIAL_TREE,
            user_email=user_email,
            emails_data=json.dumps(emails_data, indent=2)
        )

        response = claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tree_content = response.content[0].text
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', tree_content, re.DOTALL)
        if json_match:
            tree_structure = json.loads(json_match.group())
            return {
                'success': True,
                'tree': tree_structure,
                'raw_response': tree_content
            }
        else:
            return {
                'success': False,
                'error': 'Could not parse knowledge tree from Claude response'
            }
            
    except Exception as e:
        logger.error(f"Error building initial knowledge tree: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def refine_knowledge_tree(new_emails_data, existing_tree, user_email):
    """Refine existing knowledge tree with new emails"""
    try:
        import anthropic
        from config.settings import settings
        # Import the new prompt loader
        from prompts.prompt_loader import load_prompt, PromptCategories
        
        # Initialize Claude client using the existing pattern
        claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Load prompt from external file instead of embedding it
        prompt = load_prompt(
            PromptCategories.KNOWLEDGE_TREE,
            PromptCategories.REFINE_EXISTING_TREE,
            user_email=user_email,
            existing_tree=json.dumps(existing_tree, indent=2),
            new_emails_data=json.dumps(new_emails_data, indent=2)
        )

        response = claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tree_content = response.content[0].text
        
        import re
        json_match = re.search(r'\{.*\}', tree_content, re.DOTALL)
        if json_match:
            refined_tree = json.loads(json_match.group())
            return {
                'success': True,
                'tree': refined_tree,
                'raw_response': tree_content
            }
        else:
            return {
                'success': False,
                'error': 'Could not parse refined knowledge tree from Claude response'
            }
            
    except Exception as e:
        logger.error(f"Error refining knowledge tree: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_master_knowledge_tree(user_id):
    """Get the stored master knowledge tree for a user"""
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        
        with get_db_manager().get_session() as session:
            # This would typically be stored in a dedicated table
            # For now, we'll use a simple file-based approach
            import os
            tree_file = f"knowledge_trees/user_{user_id}_master_tree.json"
            
            if os.path.exists(tree_file):
                with open(tree_file, 'r') as f:
                    return json.load(f)
            return None
            
    except Exception as e:
        logger.error(f"Error getting master knowledge tree: {str(e)}")
        return None


def save_master_knowledge_tree(user_id, tree_structure):
    """Save the master knowledge tree for a user"""
    try:
        import os
        
        # Create directory if it doesn't exist
        os.makedirs("knowledge_trees", exist_ok=True)
        
        tree_file = f"knowledge_trees/user_{user_id}_master_tree.json"
        with open(tree_file, 'w') as f:
            json.dump(tree_structure, f, indent=2)
            
        logger.info(f"Saved master knowledge tree for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error saving master knowledge tree: {str(e)}")


def assign_email_to_knowledge_tree(email, tree_structure, user_email):
    """Assign individual email to the pre-built knowledge tree"""
    try:
        import anthropic
        from config.settings import settings
        # Import the new prompt loader
        from prompts.prompt_loader import load_prompt, PromptCategories
        
        # Initialize Claude client using the existing pattern
        claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        email_data = {
            'subject': email.subject or '',
            'sender': email.sender or '',
            'content': email.body_clean or email.snippet or '',
            'date': email.email_date.isoformat() if email.email_date else ''
        }
        
        # Load prompt from external file instead of embedding it
        prompt = load_prompt(
            PromptCategories.KNOWLEDGE_TREE,
            PromptCategories.ASSIGN_EMAIL_TO_TREE,
            tree_structure=json.dumps(tree_structure, indent=2),
            email_data=json.dumps(email_data, indent=2)
        )

        response = claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse response
        assignment_content = response.content[0].text
        
        import re
        json_match = re.search(r'\{.*\}', assignment_content, re.DOTALL)
        if json_match:
            assignment_data = json.loads(json_match.group())
            assignment_data['success'] = True
            return assignment_data
        else:
            return {
                'success': False,
                'error': 'Could not parse email assignment from Claude response'
            }
            
    except Exception as e:
        logger.error(f"Error assigning email to knowledge tree: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@email_bp.route('/normalize-emails', methods=['POST'])
@require_auth
def api_normalize_emails():
    """Normalize emails to prepare them for intelligence processing"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.processors.email_normalizer import email_normalizer
        
        data = request.get_json() or {}
        limit = data.get('limit', 200)
        
        user_email = user['email']
        
        # Normalize emails for this user
        result = email_normalizer.normalize_user_emails(user_email, limit)
        
        if result['success']:
            return jsonify({
                'success': True,
                'processed': result['processed'],
                'errors': result.get('errors', 0),
                'normalizer_version': result.get('normalizer_version'),
                'user_email': result['user_email'],
                'message': f"Normalized {result['processed']} emails successfully"
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        logger.error(f"Email normalization API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/knowledge-driven-pipeline', methods=['POST'])
@require_auth
def knowledge_driven_email_pipeline():
    """
    UNIFIED KNOWLEDGE-DRIVEN EMAIL PROCESSING PIPELINE
    
    Phase 1: Smart Contact Filtering (quality gate)
    Phase 2: Bulk Knowledge Tree Creation (Claude 4 Opus on ALL emails)
    Phase 3: Email Assignment to Topics
    Phase 4: Cross-Topic Intelligence Generation
    Phase 5: Agent Augmentation of Knowledge Topics
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.engagement_analysis.smart_contact_strategy import smart_contact_strategy
        from chief_of_staff_ai.agents.intelligence_agent import IntelligenceAgent
        from chief_of_staff_ai.agents.mcp_agent import MCPConnectorAgent
        import anthropic
        from config.settings import settings
        
        data = request.get_json() or {}
        force_rebuild = data.get('force_rebuild', False)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"🚀 Starting Knowledge-Driven Pipeline for {user_email}")
        
        # =================================================================
        # PHASE 1: SMART CONTACT FILTERING (Quality Gate)
        # =================================================================
        logger.info("📧 Phase 1: Smart Contact Filtering")
        
        # Build trusted contact database if not exists
        trusted_result = smart_contact_strategy.build_trusted_contact_database(
            user_email=user_email,
            days_back=365
        )
        
        if not trusted_result.get('success'):
            return jsonify({
                'success': False, 
                'error': f"Failed to build trusted contacts: {trusted_result.get('error')}"
            }), 500
        
        # Get ALL emails
        all_emails = get_db_manager().get_user_emails(db_user.id, limit=1000)
        
        # Filter emails using Smart Contact Strategy
        quality_filtered_emails = []
        for email in all_emails:
            if email.sender and email.subject:
                email_data = {
                    'sender': email.sender,
                    'sender_name': email.sender_name,
                    'subject': email.subject,
                    'body_preview': email.body_preview or email.snippet,
                    'date': email.email_date.isoformat() if email.email_date else None
                }
                
                classification = smart_contact_strategy.classify_incoming_email(
                    user_email=user_email,
                    email_data=email_data
                )
                
                # Only include high-quality emails for knowledge building
                if classification.action in ['ANALYZE_WITH_AI', 'PROCESS_WITH_AI']:
                    quality_filtered_emails.append(email)
        
        logger.info(f"📊 Filtered {len(quality_filtered_emails)} quality emails from {len(all_emails)} total")
        
        # =================================================================
        # PHASE 2: BULK KNOWLEDGE TREE CREATION (Claude 4 Opus)
        # =================================================================
        logger.info("🧠 Phase 2: Bulk Knowledge Tree Creation with Claude 4 Opus")
        
        # Check if we should rebuild
        existing_tree = get_master_knowledge_tree(db_user.id)
        if existing_tree and not force_rebuild:
            logger.info("📚 Using existing knowledge tree")
            master_tree = existing_tree
        else:
            # Prepare ALL filtered emails for bulk analysis
            emails_for_knowledge = []
            for email in quality_filtered_emails:
                emails_for_knowledge.append({
                    'id': email.gmail_id,
                    'subject': email.subject or '',
                    'sender': email.sender or '',
                    'sender_name': email.sender_name or '',
                    'date': email.email_date.isoformat() if email.email_date else '',
                    'content': (email.body_clean or email.snippet or '')[:2000],  # Longer content for knowledge building
                    'recipients': email.recipient_emails or []
                })
            
            logger.info(f"🎯 Building knowledge tree from {len(emails_for_knowledge)} quality emails")
            
            # Enhanced Claude 4 Opus prompt for knowledge-driven architecture
            knowledge_prompt = f"""You are Claude 4 Opus analyzing ALL business communications for {user_email} to build a comprehensive KNOWLEDGE-DRIVEN architecture.

MISSION: Create a master knowledge tree that represents this person's complete business world.

FILTERED QUALITY EMAILS ({len(emails_for_knowledge)} emails from trusted network):
{json.dumps(emails_for_knowledge, indent=2)}

BUILD COMPREHENSIVE KNOWLEDGE ARCHITECTURE:

1. **CORE BUSINESS TOPICS** (8-15 major knowledge areas):
   - Strategic business themes that span multiple communications
   - Project areas and business initiatives  
   - Operational domains and business functions
   - Industry/market areas of focus
   - Partnership and relationship categories

2. **TOPIC DESCRIPTIONS** (Rich context for each topic):
   - Clear description of what this knowledge area covers
   - How it relates to the user's business/role
   - Key people typically involved
   - Strategic importance and current status

3. **KNOWLEDGE RELATIONSHIPS**:
   - How topics connect and influence each other
   - Cross-topic dependencies and overlaps
   - Strategic hierarchies and priorities

4. **PEOPLE WITHIN KNOWLEDGE CONTEXT**:
   - Key people organized by their primary knowledge areas
   - Their expertise and role in different topics
   - Relationship strength and communication patterns

RETURN COMPREHENSIVE JSON:
{{
    "knowledge_topics": [
        {{
            "name": "Strategic Topic Name",
            "description": "Comprehensive description of this knowledge area and how it relates to the user's business world",
            "strategic_importance": 0.9,
            "current_status": "active/developing/monitoring",
            "key_themes": ["theme1", "theme2", "theme3"],
            "typical_activities": ["activity1", "activity2"],
            "decision_patterns": ["type of decisions made in this area"],
            "success_metrics": ["how success is measured in this area"],
            "external_dependencies": ["what external factors affect this"],
            "knowledge_depth": "deep/moderate/surface",
            "update_frequency": "daily/weekly/monthly"
        }}
    ],
    "topic_relationships": [
        {{
            "topic_a": "Topic Name 1",
            "topic_b": "Topic Name 2", 
            "relationship_type": "depends_on/influences/collaborates_with/competes_with",
            "strength": 0.8,
            "description": "How these knowledge areas interact"
        }}
    ],
    "knowledge_people": [
        {{
            "email": "person@company.com",
            "name": "Person Name",
            "primary_knowledge_areas": ["Topic 1", "Topic 2"],
            "expertise_level": {{"Topic 1": 0.9, "Topic 2": 0.7}},
            "communication_role": "decision_maker/expert/collaborator/stakeholder",
            "strategic_value": 0.8,
            "knowledge_contribution": "What unique knowledge/perspective they bring"
        }}
    ],
    "business_intelligence": {{
        "industry_context": "Primary industry/market context",
        "business_stage": "startup/growth/enterprise/transition",
        "strategic_priorities": ["priority1", "priority2", "priority3"],
        "knowledge_gaps": ["areas where more intelligence is needed"],
        "opportunity_areas": ["where knowledge suggests opportunities"],
        "risk_areas": ["where knowledge suggests risks/challenges"]
    }}
}}

FOCUS: This is the foundation for ALL future intelligence. Make it comprehensive, strategic, and knowledge-centric."""

            # Call Claude 4 Opus for comprehensive knowledge analysis
            claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = claude_client.messages.create(
                model=settings.CLAUDE_MODEL,  # Claude 4 Opus
                max_tokens=6000,  # Increased for comprehensive analysis
                messages=[{"role": "user", "content": knowledge_prompt}]
            )
            
            # Parse and save knowledge tree
            tree_content = response.content[0].text
            import re
            json_start = tree_content.find('{')
            json_end = tree_content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                master_tree = json.loads(tree_content[json_start:json_end])
                save_master_knowledge_tree(db_user.id, master_tree)
                logger.info(f"✅ Built knowledge tree with {len(master_tree.get('knowledge_topics', []))} topics")
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to parse knowledge tree from Claude 4 Opus'
                }), 500
        
        # =================================================================
        # PHASE 3: EMAIL ASSIGNMENT TO KNOWLEDGE TOPICS
        # =================================================================
        logger.info("📋 Phase 3: Assigning emails to knowledge topics")
        
        email_assignments = []
        topics_enhanced = 0
        
        for email in quality_filtered_emails[:100]:  # Process top 100 quality emails
            try:
                assignment_result = assign_email_to_knowledge_tree(email, master_tree, user_email)
                
                if assignment_result.get('success'):
                    # Update email with knowledge assignment
                    email.ai_summary = assignment_result.get('summary')
                    email.business_category = assignment_result.get('primary_topic')
                    email.strategic_importance = assignment_result.get('importance_score', 0.5)
                    email.sentiment = assignment_result.get('sentiment_score', 0.0)
                    email.processed_at = datetime.utcnow()
                    email.processing_version = "knowledge_driven_v1.0"
                    
                    email_assignments.append({
                        'email_id': email.gmail_id,
                        'subject': email.subject,
                        'assigned_topic': assignment_result.get('primary_topic'),
                        'importance': assignment_result.get('importance_score')
                    })
                    topics_enhanced += 1
                    
            except Exception as e:
                logger.error(f"Error assigning email {email.id}: {str(e)}")
                continue
        
        # Commit email updates
        with get_db_manager().get_session() as session:
            session.commit()
        
        logger.info(f"📊 Assigned {topics_enhanced} emails to knowledge topics")
        
        # =================================================================
        # PHASE 4: CROSS-TOPIC INTELLIGENCE GENERATION
        # =================================================================
        logger.info("💡 Phase 4: Cross-Topic Intelligence Generation")
        
        # Generate cross-topic insights and tasks
        intelligence_prompt = f"""Based on the complete knowledge tree and email assignments, generate strategic intelligence:

KNOWLEDGE TOPICS: {json.dumps(master_tree.get('knowledge_topics', []), indent=2)}

EMAIL ASSIGNMENTS: {json.dumps(email_assignments[:20], indent=2)}

GENERATE CROSS-TOPIC INTELLIGENCE:

1. **STRATEGIC TASKS** (Real actions needed across topics):
   - Look for patterns across multiple emails in each topic
   - Identify genuine deadlines and commitments
   - Find cross-topic dependencies requiring action
   - Extract strategic decisions that need follow-up

2. **KNOWLEDGE INSIGHTS**:
   - Patterns that emerge across different knowledge areas
   - Opportunities for connecting different topics
   - Strategic timing based on multiple topic developments
   - Risk areas requiring attention

3. **TOPIC STATUS UPDATES**:
   - Current state of each knowledge area based on recent emails
   - Momentum and energy levels in different topics
   - Emerging themes and new developments

RETURN JSON:
{{
    "strategic_tasks": [
        {{
            "description": "Clear, actionable task based on cross-topic analysis",
            "knowledge_topics": ["Topic 1", "Topic 2"],
            "rationale": "Why this task is needed based on topic knowledge",
            "priority": "high/medium/low",
            "due_date_hint": "Timeline based on topic context",
            "stakeholders": ["person@email.com"],
            "success_criteria": "What completion looks like",
            "cross_topic_impact": "How this affects multiple knowledge areas"
        }}
    ],
    "knowledge_insights": [
        {{
            "title": "Strategic insight title",
            "description": "Detailed insight based on cross-topic analysis",
            "affected_topics": ["Topic 1", "Topic 2"],
            "insight_type": "opportunity/risk/trend/connection",
            "confidence": 0.8,
            "recommended_action": "What should be done about this insight"
        }}
    ],
    "topic_status_updates": [
        {{
            "topic_name": "Topic Name",
            "current_momentum": "high/medium/low",
            "recent_developments": "What's happening in this area",
            "key_decisions_needed": ["Decision 1", "Decision 2"],
            "next_milestones": ["Milestone 1", "Milestone 2"],
            "attention_required": "What needs focus in this area"
        }}
    ]
}}"""

        intelligence_response = claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": intelligence_prompt}]
        )
        
        # Parse intelligence results
        intelligence_content = intelligence_response.content[0].text
        json_start = intelligence_content.find('{')
        json_end = intelligence_content.rfind('}') + 1
        
        cross_topic_intelligence = {}
        if json_start != -1 and json_end > json_start:
            cross_topic_intelligence = json.loads(intelligence_content[json_start:json_end])
        
        # =================================================================
        # PHASE 5: AGENT AUGMENTATION OF KNOWLEDGE TOPICS  
        # =================================================================
        logger.info("🤖 Phase 5: Agent Augmentation")
        
        # Initialize agents for knowledge enhancement
        # Note: Simplified for now - full async agent integration would require async route
        augmented_topics = []
        
        try:
            # For now, we'll prepare the structure for agent enhancement
            # The agents can be called separately or in background tasks
            for topic in master_tree.get('knowledge_topics', [])[:3]:  # Top 3 topics
                augmented_topics.append({
                    'topic': topic['name'],
                    'enhancement_status': 'ready_for_agent_processing',
                    'enhancement_type': 'external_research_pending'
                })
                
            logger.info(f"🤖 Prepared {len(augmented_topics)} topics for agent augmentation")
            
        except Exception as e:
            logger.error(f"Agent preparation failed: {str(e)}")
            # Continue without agent augmentation
        
        # =================================================================
        # FINAL RESULTS
        # =================================================================
        
        pipeline_results = {
            'success': True,
            'pipeline_version': 'knowledge_driven_v1.0',
            'phases_completed': 5,
            'processing_summary': {
                'total_emails_available': len(all_emails),
                'quality_filtered_emails': len(quality_filtered_emails),
                'emails_assigned_to_topics': topics_enhanced,
                'knowledge_topics_created': len(master_tree.get('knowledge_topics', [])),
                'strategic_tasks_identified': len(cross_topic_intelligence.get('strategic_tasks', [])),
                'knowledge_insights_generated': len(cross_topic_intelligence.get('knowledge_insights', [])),
                'topics_augmented_by_agents': len(augmented_topics)
            },
            'knowledge_tree': master_tree,
            'email_assignments': email_assignments[:10],  # Sample assignments
            'cross_topic_intelligence': cross_topic_intelligence,
            'agent_augmentations': augmented_topics,
            'pipeline_efficiency': {
                'quality_filter_ratio': len(quality_filtered_emails) / max(len(all_emails), 1),
                'knowledge_coverage': topics_enhanced / max(len(quality_filtered_emails), 1),
                'intelligence_density': len(cross_topic_intelligence.get('strategic_tasks', [])) / max(len(master_tree.get('knowledge_topics', [])), 1)
            }
        }
        
        logger.info(f"🎉 Knowledge-Driven Pipeline Complete: {pipeline_results['processing_summary']}")
        
        return jsonify(pipeline_results)
        
    except Exception as e:
        logger.error(f"Knowledge-driven pipeline error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Individual Phase Testing Endpoints

@email_bp.route('/knowledge-pipeline/phase1-contacts', methods=['POST'])
@require_auth
def phase1_smart_contact_filtering():
    """
    PHASE 1: Smart Contact Filtering & Contact Building
    Builds trusted contact database from sent emails and shows results in People tab
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.engagement_analysis.smart_contact_strategy import smart_contact_strategy
        
        data = request.get_json() or {}
        days_back = data.get('days_back', 365)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"🚀 Phase 1: Smart Contact Filtering for {user_email}")
        
        # Build trusted contact database from sent emails
        trusted_result = smart_contact_strategy.build_trusted_contact_database(
            user_email=user_email,
            days_back=days_back
        )
        
        if not trusted_result.get('success'):
            return jsonify({
                'success': False, 
                'error': f"Failed to build trusted contacts: {trusted_result.get('error')}"
            }), 500
        
        # Get all contacts created/updated
        all_people = get_db_manager().get_user_people(db_user.id)
        
        # Prepare detailed contact list for frontend
        contacts_created = []
        for person in all_people:
            contacts_created.append({
                'id': person.id,
                'name': person.name,
                'email': person.email_address,
                'company': person.company,
                'title': person.title,
                'engagement_score': person.engagement_score,
                'total_emails': person.total_emails,
                'created_from': 'sent_emails_analysis'
            })
        
        return jsonify({
            'success': True,
            'phase': 1,
            'phase_name': 'Smart Contact Filtering',
            'results': {
                'sent_emails_analyzed': trusted_result.get('sent_emails_analyzed', 0),
                'contacts_identified': trusted_result.get('contacts_analyzed', 0),
                'trusted_contacts_created': trusted_result.get('trusted_contacts_created', 0),
                'total_people_in_database': len(all_people)
            },
            'contacts_created': contacts_created,
            'next_step': 'Phase 2: Create initial knowledge tree from these contacts',
            'message': f"✅ Created {len(contacts_created)} trusted contacts from sent email analysis"
        })
        
    except Exception as e:
        logger.error(f"Phase 1 error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/knowledge-pipeline/phase2-knowledge-tree', methods=['POST'])
@require_auth
def phase2_initial_knowledge_tree():
    """
    PHASE 2: Initial Knowledge Tree Creation
    Creates knowledge tree from filtered emails and displays structure
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.engagement_analysis.smart_contact_strategy import smart_contact_strategy
        import anthropic
        from config.settings import settings
        
        data = request.get_json() or {}
        max_emails = data.get('max_emails', 50)
        force_rebuild = data.get('force_rebuild', False)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"🧠 Phase 2: Knowledge Tree Creation for {user_email}")
        
        # Check if knowledge tree already exists
        existing_tree = get_master_knowledge_tree(db_user.id)
        if existing_tree and not force_rebuild:
            return jsonify({
                'success': True,
                'phase': 2,
                'phase_name': 'Knowledge Tree Creation',
                'results': {
                    'tree_exists': True,
                    'knowledge_topics': len(existing_tree.get('knowledge_topics', [])),
                    'knowledge_people': len(existing_tree.get('knowledge_people', [])),
                    'topic_relationships': len(existing_tree.get('topic_relationships', []))
                },
                'knowledge_tree': existing_tree,
                'message': f"✅ Knowledge tree already exists with {len(existing_tree.get('knowledge_topics', []))} topics",
                'next_step': 'Phase 3: Sync calendar to augment contacts'
            })
        
        # Get filtered emails for knowledge creation
        all_emails = get_db_manager().get_user_emails(db_user.id, limit=max_emails)
        
        if not all_emails:
            return jsonify({
                'success': False,
                'error': 'No emails found. Please fetch emails first.'
            }), 400
        
        # Filter emails using smart contact strategy
        quality_filtered_emails = []
        for email in all_emails:
            if email.sender and email.subject:
                email_data = {
                    'sender': email.sender,
                    'sender_name': email.sender_name,
                    'subject': email.subject,
                    'body_preview': email.body_preview or email.snippet,
                    'date': email.email_date.isoformat() if email.email_date else None
                }
                
                classification = smart_contact_strategy.classify_incoming_email(
                    user_email=user_email,
                    email_data=email_data
                )
                
                if classification.action in ['ANALYZE_WITH_AI', 'PROCESS_WITH_AI']:
                    quality_filtered_emails.append(email)
        
        # Prepare emails for knowledge tree creation
        emails_for_knowledge = []
        for email in quality_filtered_emails:
            emails_for_knowledge.append({
                'id': email.gmail_id,
                'subject': email.subject or '',
                'sender': email.sender or '',
                'sender_name': email.sender_name or '',
                'date': email.email_date.isoformat() if email.email_date else '',
                'content': (email.body_clean or email.snippet or '')[:1500],
                'recipients': email.recipient_emails or []
            })
        
        logger.info(f"🎯 Creating knowledge tree from {len(emails_for_knowledge)} quality emails")
        
        # Create knowledge tree using Claude 4 Opus
        knowledge_prompt = f"""You are Claude 4 Opus creating a comprehensive knowledge tree from business communications for {user_email}.

QUALITY EMAILS ({len(emails_for_knowledge)} filtered emails):
{json.dumps(emails_for_knowledge, indent=2)}

CREATE INITIAL KNOWLEDGE ARCHITECTURE:

1. **BUSINESS TOPICS** (5-12 major areas):
   - Core business themes from communications
   - Project areas and initiatives
   - Operational domains
   - Partnership/relationship categories

2. **PEOPLE & RELATIONSHIPS**:
   - Key contacts with their expertise areas
   - Relationship strength and communication patterns
   - Role in different business topics

3. **BUSINESS CONTEXT**:
   - Industry and market context
   - Business stage and priorities
   - Strategic focus areas

RETURN JSON:
{{
    "knowledge_topics": [
        {{
            "name": "Topic Name",
            "description": "What this topic covers",
            "strategic_importance": 0.8,
            "current_status": "active/developing/monitoring",
            "key_themes": ["theme1", "theme2"],
            "email_count": 5,
            "key_people": ["person1@email.com", "person2@email.com"]
        }}
    ],
    "knowledge_people": [
        {{
            "email": "person@company.com",
            "name": "Person Name",
            "primary_knowledge_areas": ["Topic 1", "Topic 2"],
            "relationship_strength": 0.8,
            "communication_role": "decision_maker/expert/collaborator",
            "company": "Company Name",
            "expertise_summary": "What they bring to conversations"
        }}
    ],
    "business_intelligence": {{
        "industry_context": "Industry/market",
        "business_stage": "startup/growth/enterprise",
        "strategic_priorities": ["priority1", "priority2"],
        "communication_patterns": ["pattern1", "pattern2"]
    }},
    "tree_metadata": {{
        "created_from_emails": {len(emails_for_knowledge)},
        "quality_filtered_ratio": "{len(quality_filtered_emails)}/{len(all_emails)}",
        "creation_date": "{datetime.now().isoformat()}"
    }}
}}"""

        claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=5000,
            messages=[{"role": "user", "content": knowledge_prompt}]
        )
        
        # Parse knowledge tree
        tree_content = response.content[0].text
        json_start = tree_content.find('{')
        json_end = tree_content.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            knowledge_tree = json.loads(tree_content[json_start:json_end])
            save_master_knowledge_tree(db_user.id, knowledge_tree)
            
            return jsonify({
                'success': True,
                'phase': 2,
                'phase_name': 'Knowledge Tree Creation',
                'results': {
                    'tree_created': True,
                    'emails_analyzed': len(emails_for_knowledge),
                    'quality_filter_ratio': f"{len(quality_filtered_emails)}/{len(all_emails)}",
                    'knowledge_topics': len(knowledge_tree.get('knowledge_topics', [])),
                    'knowledge_people': len(knowledge_tree.get('knowledge_people', [])),
                    'business_intelligence_extracted': True
                },
                'knowledge_tree': knowledge_tree,
                'message': f"✅ Created knowledge tree with {len(knowledge_tree.get('knowledge_topics', []))} topics from {len(emails_for_knowledge)} emails",
                'next_step': 'Phase 3: Sync calendar to augment contact data'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to parse knowledge tree from Claude 4 Opus'
            }), 500
        
    except Exception as e:
        logger.error(f"Phase 2 error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/knowledge-pipeline/phase3-calendar-sync', methods=['POST'])
@require_auth
def phase3_calendar_augmentation():
    """
    PHASE 3: Calendar Sync & Contact Augmentation
    Syncs calendar data and augments contacts with meeting information
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.ingest.calendar_fetcher import calendar_fetcher
        
        data = request.get_json() or {}
        days_back = data.get('days_back', 30)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"📅 Phase 3: Calendar Sync & Contact Augmentation for {user_email}")
        
        # Fetch calendar events
        calendar_result = calendar_fetcher.fetch_recent_events(
            user_email=user_email,
            days_back=days_back
        )
        
        if not calendar_result.get('success'):
            return jsonify({
                'success': False,
                'error': f"Calendar sync failed: {calendar_result.get('error')}"
            }), 500
        
        events_fetched = calendar_result.get('events_fetched', 0)
        
        # Extract contacts from calendar events
        calendar_contacts = []
        meeting_insights = []
        
        if events_fetched > 0:
            # Get calendar events from database
            calendar_events = get_db_manager().get_user_calendar_events(db_user.id, limit=50)
            
            for event in calendar_events:
                # Extract attendees as potential contacts
                if hasattr(event, 'attendees') and event.attendees:
                    for attendee_email in event.attendees:
                        if attendee_email != user_email and '@' in attendee_email:
                            calendar_contacts.append({
                                'email': attendee_email,
                                'source': 'calendar',
                                'meeting_count': 1,
                                'last_meeting': event.start_time.isoformat() if event.start_time else None,
                                'meeting_title': event.title
                            })
                
                # Create meeting insights
                meeting_insights.append({
                    'title': event.title,
                    'date': event.start_time.isoformat() if event.start_time else None,
                    'attendee_count': len(event.attendees) if event.attendees else 0,
                    'duration_hours': event.duration_hours if hasattr(event, 'duration_hours') else None
                })
        
        # Update existing contacts with calendar data
        contacts_augmented = 0
        existing_people = get_db_manager().get_user_people(db_user.id)
        
        for person in existing_people:
            # Check if this person appears in calendar
            calendar_data = next((c for c in calendar_contacts if c['email'] == person.email_address), None)
            if calendar_data:
                # Augment person record with calendar information
                if not person.business_context:
                    person.business_context = {}
                
                person.business_context['calendar_meetings'] = calendar_data['meeting_count']
                person.business_context['last_meeting'] = calendar_data['last_meeting']
                person.business_context['meeting_frequency'] = 'regular' if calendar_data['meeting_count'] > 2 else 'occasional'
                contacts_augmented += 1
        
        # Save updates
        with get_db_manager().get_session() as session:
            session.commit()
        
        return jsonify({
            'success': True,
            'phase': 3,
            'phase_name': 'Calendar Sync & Contact Augmentation',
            'results': {
                'calendar_events_fetched': events_fetched,
                'calendar_contacts_found': len(calendar_contacts),
                'existing_contacts_augmented': contacts_augmented,
                'meeting_insights_generated': len(meeting_insights)
            },
            'calendar_contacts': calendar_contacts[:10],  # Show first 10
            'meeting_insights': meeting_insights[:5],     # Show first 5
            'message': f"✅ Synced {events_fetched} calendar events and augmented {contacts_augmented} contacts",
            'next_step': 'Phase 4: Fetch more emails and enhance knowledge tree'
        })
        
    except Exception as e:
        logger.error(f"Phase 3 error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/knowledge-pipeline/phase4-email-enhancement', methods=['POST'])
@require_auth
def phase4_email_knowledge_enhancement():
    """
    PHASE 4: Fetch More Emails & Enhance Knowledge Tree
    Fetches additional emails and enhances the knowledge tree with more context
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.ingest.gmail_fetcher import gmail_fetcher
        import anthropic
        from config.settings import settings
        
        data = request.get_json() or {}
        additional_emails = data.get('additional_emails', 50)
        days_back = data.get('days_back', 60)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"📧 Phase 4: Email Enhancement for {user_email}")
        
        # Check if knowledge tree exists
        existing_tree = get_master_knowledge_tree(db_user.id)
        if not existing_tree:
            return jsonify({
                'success': False,
                'error': 'No knowledge tree found. Please run Phase 2 first.'
            }), 400
        
        # Fetch additional emails
        fetch_result = gmail_fetcher.fetch_recent_emails(
            user_email=user_email,
            limit=additional_emails,
            days_back=days_back,
            force_refresh=True
        )
        
        new_emails_count = fetch_result.get('emails_fetched', 0)
        
        # Get recent emails for enhancement
        all_emails = get_db_manager().get_user_emails(db_user.id, limit=additional_emails * 2)
        
        # Find emails not yet assigned to knowledge topics
        unprocessed_emails = [
            email for email in all_emails 
            if not email.business_category or email.processing_version != "knowledge_driven_v1.0"
        ]
        
        # Assign new emails to knowledge tree
        emails_assigned = 0
        topic_enhancements = {}
        
        for email in unprocessed_emails[:additional_emails]:
            try:
                assignment_result = assign_email_to_knowledge_tree(email, existing_tree, user_email)
                
                if assignment_result.get('success'):
                    # Update email with knowledge assignment
                    email.ai_summary = assignment_result.get('summary')
                    email.business_category = assignment_result.get('primary_topic')
                    email.strategic_importance = assignment_result.get('importance_score', 0.5)
                    email.processing_version = "knowledge_driven_v1.0"
                    
                    # Track topic enhancements
                    topic = assignment_result.get('primary_topic')
                    if topic:
                        if topic not in topic_enhancements:
                            topic_enhancements[topic] = []
                        topic_enhancements[topic].append({
                            'subject': email.subject,
                            'sender': email.sender,
                            'importance': assignment_result.get('importance_score', 0.5)
                        })
                    
                    emails_assigned += 1
                    
            except Exception as e:
                logger.error(f"Error assigning email {email.id}: {str(e)}")
                continue
        
        # Commit email updates
        with get_db_manager().get_session() as session:
            session.commit()
        
        # Generate enhancement summary
        enhancement_summary = {
            'topics_enhanced': len(topic_enhancements),
            'emails_per_topic': {topic: len(emails) for topic, emails in topic_enhancements.items()},
            'avg_importance': sum(
                email['importance'] for emails in topic_enhancements.values() for email in emails
            ) / max(emails_assigned, 1)
        }
        
        return jsonify({
            'success': True,
            'phase': 4,
            'phase_name': 'Email Knowledge Enhancement',
            'results': {
                'new_emails_fetched': new_emails_count,
                'emails_assigned_to_topics': emails_assigned,
                'topics_enhanced': len(topic_enhancements),
                'unprocessed_emails_remaining': len(unprocessed_emails) - emails_assigned,
                'knowledge_tree_version': 'enhanced_v1.1'
            },
            'topic_enhancements': dict(list(topic_enhancements.items())[:5]),  # Show first 5 topics
            'enhancement_summary': enhancement_summary,
            'message': f"✅ Enhanced knowledge tree with {emails_assigned} new emails across {len(topic_enhancements)} topics",
            'next_step': 'Phase 5: Generate cross-topic intelligence and strategic tasks'
        })
        
    except Exception as e:
        logger.error(f"Phase 4 error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/knowledge-pipeline/phase5-intelligence', methods=['POST'])
@require_auth
def phase5_cross_topic_intelligence():
    """
    PHASE 5: Generate Cross-Topic Intelligence & Strategic Tasks
    Analyzes knowledge tree to generate strategic insights and actionable tasks
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        import anthropic
        from config.settings import settings
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"💡 Phase 5: Cross-Topic Intelligence Generation for {user_email}")
        
        # Get current knowledge tree
        knowledge_tree = get_master_knowledge_tree(db_user.id)
        if not knowledge_tree:
            return jsonify({
                'success': False,
                'error': 'No knowledge tree found. Please run previous phases first.'
            }), 400
        
        # Get emails assigned to topics for context
        processed_emails = get_db_manager().get_user_emails(db_user.id, limit=200)
        email_assignments = []
        
        for email in processed_emails:
            if email.business_category and email.processing_version == "knowledge_driven_v1.0":
                email_assignments.append({
                    'subject': email.subject,
                    'topic': email.business_category,
                    'importance': email.strategic_importance or 0.5,
                    'sender': email.sender,
                    'date': email.email_date.isoformat() if email.email_date else None
                })
        
        # Generate cross-topic intelligence
        intelligence_prompt = f"""Analyze this comprehensive knowledge tree and email assignments to generate strategic intelligence:

KNOWLEDGE TREE:
{json.dumps(knowledge_tree, indent=2)}

EMAIL ASSIGNMENTS SAMPLE ({len(email_assignments[:30])} recent assignments):
{json.dumps(email_assignments[:30], indent=2)}

GENERATE STRATEGIC INTELLIGENCE:

1. **STRATEGIC TASKS** - Real, actionable items that span multiple topics
2. **KNOWLEDGE INSIGHTS** - Patterns and opportunities across topics  
3. **TOPIC STATUS** - Current momentum and next steps for each topic

RETURN JSON:
{{
    "strategic_tasks": [
        {{
            "description": "Specific actionable task",
            "knowledge_topics": ["Topic1", "Topic2"],
            "priority": "high/medium/low",
            "rationale": "Why this task is important",
            "estimated_effort": "time estimate",
            "stakeholders": ["person@email.com"],
            "success_criteria": "How to measure completion"
        }}
    ],
    "knowledge_insights": [
        {{
            "title": "Insight title",
            "description": "Detailed insight description",
            "affected_topics": ["Topic1", "Topic2"],
            "insight_type": "opportunity/risk/trend/connection",
            "confidence": 0.8,
            "recommended_action": "What to do about this"
        }}
    ],
    "topic_status_updates": [
        {{
            "topic_name": "Topic Name",
            "current_momentum": "high/medium/low",
            "recent_activity": "What's been happening",
            "next_milestones": ["milestone1", "milestone2"],
            "attention_needed": "What requires focus"
        }}
    ],
    "intelligence_summary": {{
        "total_strategic_value": 0.8,
        "execution_complexity": "low/medium/high",
        "time_sensitivity": "urgent/moderate/low",
        "resource_requirements": "Resource needs overview"
    }}
}}"""

        claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": intelligence_prompt}]
        )
        
        # Parse intelligence results
        intelligence_content = response.content[0].text
        json_start = intelligence_content.find('{')
        json_end = intelligence_content.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            cross_topic_intelligence = json.loads(intelligence_content[json_start:json_end])
            
            return jsonify({
                'success': True,
                'phase': 5,
                'phase_name': 'Cross-Topic Intelligence Generation',
                'results': {
                    'strategic_tasks_generated': len(cross_topic_intelligence.get('strategic_tasks', [])),
                    'knowledge_insights_generated': len(cross_topic_intelligence.get('knowledge_insights', [])),
                    'topics_analyzed': len(cross_topic_intelligence.get('topic_status_updates', [])),
                    'intelligence_quality': cross_topic_intelligence.get('intelligence_summary', {}).get('total_strategic_value', 0.0)
                },
                'cross_topic_intelligence': cross_topic_intelligence,
                'knowledge_tree_stats': {
                    'total_topics': len(knowledge_tree.get('knowledge_topics', [])),
                    'total_people': len(knowledge_tree.get('knowledge_people', [])),
                    'emails_analyzed': len(email_assignments)
                },
                'message': f"✅ Generated {len(cross_topic_intelligence.get('strategic_tasks', []))} strategic tasks and {len(cross_topic_intelligence.get('knowledge_insights', []))} insights",
                'next_step': 'All phases complete! Review strategic tasks and insights.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to parse intelligence results from Claude'
            }), 500
        
    except Exception as e:
        logger.error(f"Phase 5 error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/knowledge-tree/current', methods=['GET'])
@require_auth
def get_current_knowledge_tree():
    """
    Get the current knowledge tree for viewing in the Knowledge tab
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get current knowledge tree
        knowledge_tree = get_master_knowledge_tree(db_user.id)
        
        if not knowledge_tree:
            return jsonify({
                'success': True,
                'has_tree': False,
                'message': 'No knowledge tree found. Run Phase 2 to create one.',
                'tree': None
            })
        
        # Get some stats about assigned emails
        processed_emails = get_db_manager().get_user_emails(db_user.id, limit=500)
        assigned_emails = [
            email for email in processed_emails 
            if email.business_category and email.processing_version == "knowledge_driven_v1.0"
        ]
        
        # Create topic statistics
        topic_stats = {}
        for email in assigned_emails:
            topic = email.business_category
            if topic:
                if topic not in topic_stats:
                    topic_stats[topic] = {'email_count': 0, 'importance_sum': 0.0}
                topic_stats[topic]['email_count'] += 1
                topic_stats[topic]['importance_sum'] += (email.strategic_importance or 0.5)
        
        # Calculate average importance per topic
        for topic in topic_stats:
            if topic_stats[topic]['email_count'] > 0:
                topic_stats[topic]['avg_importance'] = topic_stats[topic]['importance_sum'] / topic_stats[topic]['email_count']
            else:
                topic_stats[topic]['avg_importance'] = 0.0
        
        return jsonify({
            'success': True,
            'has_tree': True,
            'tree': knowledge_tree,
            'tree_stats': {
                'knowledge_topics': len(knowledge_tree.get('knowledge_topics', [])),
                'knowledge_people': len(knowledge_tree.get('knowledge_people', [])),
                'topic_relationships': len(knowledge_tree.get('topic_relationships', [])),
                'emails_assigned': len(assigned_emails),
                'total_emails_processed': len(processed_emails)
            },
            'topic_stats': topic_stats,
            'message': f"Knowledge tree with {len(knowledge_tree.get('knowledge_topics', []))} topics and {len(assigned_emails)} assigned emails"
        })
        
    except Exception as e:
        logger.error(f"Get knowledge tree error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500 