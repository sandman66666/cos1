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
        from models.database import get_db_manager
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
        from models.database import get_db_manager
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
        from models.database import get_db_manager, Email
        
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
        from models.database import get_db_manager, Email
        
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
        from models.database import get_db_manager
        
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
        from models.database import get_db_manager, Person, Topic
        
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
            model="claude-3-5-sonnet-20241022",
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
            model="claude-3-5-sonnet-20241022",
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
        from models.database import get_db_manager
        
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
            model="claude-3-5-sonnet-20241022",
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