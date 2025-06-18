"""
People Routes Blueprint
======================

People management and relationship intelligence routes.
Extracted from main.py for better organization.
"""

import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from ..middleware.auth_middleware import get_current_user, require_auth
from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter, ContactTier

logger = logging.getLogger(__name__)

people_bp = Blueprint('people', __name__, url_prefix='/api')


@people_bp.route('/people', methods=['GET'])
@require_auth
def api_get_people():
    """Get people with relationship intelligence and business context - FILTERED BY CONTACT TIERS"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        
        # Get real user and their people
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get all people first
        all_people = get_db_manager().get_user_people(db_user.id)
        filtered_people = []
        tier_stats = {'tier_1': 0, 'tier_2': 0, 'tier_last_filtered': 0, 'unclassified': 0}
        
        # Get contact tiers
        if not email_quality_filter._contact_tiers:
            email_quality_filter._analyze_all_contacts(db_user.id)
        
        # Filter and enhance people with tier information
        for person in all_people:
            if person.name and person.email_address:
                # Get tier for this contact
                try:
                    contact_stats = email_quality_filter._get_contact_stats(person.email_address.lower(), db_user.id)
                    
                    # ONLY SHOW TIER 1 CONTACTS (people user has sent emails to)
                    if contact_stats.tier != ContactTier.TIER_1:
                        continue  # Skip this contact - not someone we actively correspond with
                    
                    # Handle different types of contact_stats objects
                    contact_tier = None
                    tier_reason = "Unknown"
                    response_rate = 0.0
                    
                    if hasattr(contact_stats, 'tier'):
                        contact_tier = contact_stats.tier
                        tier_reason = getattr(contact_stats, 'tier_reason', 'Unknown')
                        response_rate = getattr(contact_stats, 'response_rate', 0.0)
                    elif hasattr(contact_stats, 'value'):
                        # Handle ContactTier enum directly
                        contact_tier = contact_stats
                        tier_reason = "Direct tier assignment"
                        response_rate = 0.0
                    else:
                        logger.error(f"Unexpected contact_stats type: {type(contact_stats)} for {person.email_address}")
                        continue  # Skip this person
                    
                    # Apply tier filter - only include appropriate tiers
                    tier_filter = request.args.get('tier_filter', 'tier_1_only')  # Default to only Tier 1
                    
                    if tier_filter == 'tier_1_only' and contact_tier != ContactTier.TIER_1:
                        continue
                    elif tier_filter == 'exclude_tier_last' and contact_tier == ContactTier.TIER_LAST:
                        continue
                    
                    # Apply filtering logic
                    if contact_tier == ContactTier.TIER_LAST:
                        # FILTER OUT Tier LAST contacts
                        tier_stats['tier_last_filtered'] += 1
                        logger.debug(f"🗑️  Filtered out Tier LAST contact: {person.email_address}")
                        continue
                    elif contact_tier == ContactTier.TIER_1:
                        tier_stats['tier_1'] += 1
                    elif contact_tier == ContactTier.TIER_2:
                        tier_stats['tier_2'] += 1
                    else:
                        tier_stats['unclassified'] += 1
                    
                    # Add tier information to person
                    person_dict = person.to_dict()
                    person_dict['contact_tier'] = contact_tier.value if hasattr(contact_tier, 'value') else str(contact_tier)
                    person_dict['tier_reason'] = tier_reason
                    person_dict['response_rate'] = response_rate
                    filtered_people.append(person_dict)
                    
                except Exception as e:
                    logger.error(f"Error processing contact stats for {person.email_address}: {str(e)}")
                    # Add person without tier info as fallback
                    person_dict = person.to_dict()
                    person_dict['contact_tier'] = 'unclassified'
                    person_dict['tier_reason'] = f'Error: {str(e)}'
                    person_dict['response_rate'] = 0.0
                    filtered_people.append(person_dict)
                    tier_stats['unclassified'] += 1
        
        logger.info(f"📊 Contact filtering results: Tier 1: {tier_stats['tier_1']}, Tier 2: {tier_stats['tier_2']}, Filtered out: {tier_stats['tier_last_filtered']}")
        
        # Get related data for context
        emails = get_db_manager().get_user_emails(db_user.id, limit=1000)
        
        # Create relationship intelligence maps
        person_email_map = {}
        for email in emails:
            if email.sender:
                sender_email = email.sender.lower()
                # Find matching person in filtered list
                for person in filtered_people:
                    if person['email_address'].lower() == sender_email:
                        if person['id'] not in person_email_map:
                            person_email_map[person['id']] = []
                        person_email_map[person['id']].append(email.to_dict())
        
        # Add email context to people
        for person in filtered_people:
            person['recent_emails'] = person_email_map.get(person['id'], [])[:5]  # Last 5 emails
            person['total_emails'] = len(person_email_map.get(person['id'], []))
        
        return jsonify({
            'success': True,
            'people': filtered_people,
            'tier_stats': tier_stats,
            'total_people': len(filtered_people),
            'filtered_out': tier_stats['tier_last_filtered']
        })
        
    except Exception as e:
        logger.error(f"Get people error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@people_bp.route('/projects', methods=['GET'])
@require_auth
def api_get_projects():
    """Get projects for the authenticated user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        projects = get_db_manager().get_user_projects(db_user.id, status, limit)
        
        return jsonify({
            'success': True,
            'projects': [project.to_dict() for project in projects],
            'count': len(projects),
            'status_filter': status
        })
        
    except Exception as e:
        logger.error(f"Get projects API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@people_bp.route('/augment-with-knowledge', methods=['POST'])
@require_auth
def augment_people_with_knowledge():
    """Augment people profiles with knowledge tree context and email intelligence"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager, Person, Email
        from api.routes.email_routes import get_master_knowledge_tree
        import anthropic
        from config.settings import settings
        from prompts.prompt_loader import load_prompt, PromptCategories
        import json
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get knowledge tree
        master_tree = get_master_knowledge_tree(db_user.id)
        
        with get_db_manager().get_session() as session:
            # Get all Tier 1 contacts (people we've sent emails to)
            people_to_augment = session.query(Person).filter(
                Person.user_id == db_user.id,
                Person.email_address.is_not(None)
            ).all()
            
            if not people_to_augment:
                return jsonify({
                    'success': True,
                    'people_enhanced': 0,
                    'message': 'No people found to augment'
                })
            
            # Filter to only Tier 1 contacts
            tier1_people = []
            for person in people_to_augment:
                try:
                    contact_stats = email_quality_filter._get_contact_stats(person.email_address.lower(), db_user.id)
                    if contact_stats.tier == ContactTier.TIER_1:
                        tier1_people.append(person)
                except Exception as e:
                    logger.error(f"Error checking tier for {person.email_address}: {str(e)}")
                    continue
            
            people_enhanced = 0
            sample_people = []
            claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            
            logger.info(f"Augmenting {len(tier1_people)} Tier 1 contacts with AI intelligence")
            
            for person in tier1_people:
                try:
                    enhanced = False
                    
                    # Get emails from/to this person
                    emails_with_person = session.query(Email).filter(
                        Email.user_id == db_user.id,
                        (Email.sender.ilike(f'%{person.email_address}%') | 
                         Email.recipient_emails.ilike(f'%{person.email_address}%'))
                    ).order_by(Email.email_date.desc()).limit(10).all()
                    
                    if not emails_with_person:
                        continue
                    
                    # Prepare email content for analysis
                    email_context = []
                    for email in emails_with_person:
                        email_content = {
                            'subject': email.subject or 'No subject',
                            'date': email.email_date.strftime('%Y-%m-%d') if email.email_date else 'Unknown',
                            'snippet': email.snippet or email.body_preview or 'No content',
                            'sender': email.sender
                        }
                        email_context.append(email_content)
                    
                    # Find person in knowledge tree
                    tree_person = None
                    if master_tree:
                        for p in master_tree.get('people', []):
                            if p['email'].lower() == person.email_address.lower():
                                tree_person = p
                                break
                    
                    # Build intelligence prompt
                    intelligence_prompt = f"""Analyze this professional contact and extract meaningful insights:

**Contact:** {person.name} ({person.email_address})
**Company:** {person.company or 'Unknown'}
**Current Title:** {person.title or 'Unknown'}

**Recent Email Context:**
{json.dumps(email_context, indent=2)}

**Knowledge Tree Context:**
{json.dumps(tree_person, indent=2) if tree_person else 'No knowledge tree data available'}

Please provide a comprehensive analysis in this JSON format:

{{
  "professional_story": "A 2-3 sentence compelling narrative about this person's professional relationship and significance",
  "communication_style": "Analysis of their communication patterns, tone, and preferred interaction style",
  "key_topics": ["topic1", "topic2", "topic3"],
  "skills": ["skill1", "skill2", "skill3"],
  "interests": ["interest1", "interest2"],
  "personality_traits": ["trait1", "trait2", "trait3"],
  "preferences": {{
    "communication_frequency": "high/medium/low",
    "preferred_contact_method": "email/phone/meeting",
    "response_time": "immediate/same-day/few-days"
  }},
  "notes": "Key insights about working relationship, important context to remember, strategic value",
  "bio": "Professional bio focusing on their role and expertise",
  "strategic_importance": 0.8,
  "relationship_insights": "What makes this relationship valuable and how to nurture it"
}}

Focus on actionable insights that would help in future interactions. Be specific and professional."""
                    
                    try:
                        # Call Claude for intelligence analysis
                        response = claude_client.messages.create(
                            model=settings.CLAUDE_MODEL,
                            max_tokens=3000,
                            messages=[{"role": "user", "content": intelligence_prompt}]
                        )
                        
                        # Parse Claude's response
                        try:
                            intelligence_data = json.loads(response.content[0].text)
                        except json.JSONDecodeError:
                            # Fallback if JSON parsing fails
                            intelligence_data = {
                                'professional_story': f"Active professional contact at {person.company or 'their organization'}",
                                'communication_style': 'Professional email communication',
                                'key_topics': ['business', 'professional'],
                                'notes': f"Regular email correspondent. Total emails: {len(emails_with_person)}"
                            }
                        
                        # Update person with intelligence
                        if intelligence_data.get('professional_story'):
                            person.professional_story = intelligence_data['professional_story']
                            enhanced = True
                        
                        if intelligence_data.get('communication_style'):
                            person.communication_style = intelligence_data['communication_style']
                            enhanced = True
                        
                        if intelligence_data.get('key_topics'):
                            person.key_topics = intelligence_data['key_topics']
                            enhanced = True
                        
                        if intelligence_data.get('skills'):
                            person.skills = intelligence_data['skills']
                            enhanced = True
                        
                        if intelligence_data.get('interests'):
                            person.interests = intelligence_data['interests']
                            enhanced = True
                        
                        if intelligence_data.get('personality_traits'):
                            person.personality_traits = intelligence_data['personality_traits']
                            enhanced = True
                        
                        if intelligence_data.get('preferences'):
                            person.preferences = intelligence_data['preferences']
                            enhanced = True
                        
                        if intelligence_data.get('notes'):
                            person.notes = intelligence_data['notes']
                            enhanced = True
                        
                        if intelligence_data.get('bio'):
                            person.bio = intelligence_data['bio']
                            enhanced = True
                        
                        # Update strategic importance
                        if intelligence_data.get('strategic_importance'):
                            person.importance_level = float(intelligence_data['strategic_importance'])
                            enhanced = True
                        
                        # Update from knowledge tree if available
                        if tree_person:
                            if not person.company and tree_person.get('company'):
                                person.company = tree_person['company']
                                enhanced = True
                            
                            if not person.title and tree_person.get('role'):
                                person.title = tree_person['role']
                                enhanced = True
                        
                        if enhanced:
                            person.last_updated_by_ai = datetime.utcnow()
                            person.ai_version = 'knowledge_augmented_v1'
                            person.knowledge_confidence = 0.8
                            people_enhanced += 1
                            
                            # Add to sample for inspection
                            if len(sample_people) < 5:
                                sample_people.append({
                                    'name': person.name,
                                    'email': person.email_address,
                                    'company': person.company,
                                    'title': person.title,
                                    'professional_story': person.professional_story,
                                    'key_topics': person.key_topics,
                                    'strategic_importance': person.importance_level,
                                    'communication_style': person.communication_style[:100] + '...' if person.communication_style and len(person.communication_style) > 100 else person.communication_style
                                })
                    
                    except Exception as claude_error:
                        logger.error(f"Claude analysis failed for {person.email_address}: {str(claude_error)}")
                        # Fallback enhancement without Claude
                        if not person.professional_story:
                            person.professional_story = f"Professional contact at {person.company or 'their organization'} with {len(emails_with_person)} email interactions"
                            enhanced = True
                        
                        if not person.notes:
                            person.notes = f"Regular email correspondent. Last contact: {emails_with_person[0].email_date.strftime('%Y-%m-%d') if emails_with_person else 'Unknown'}"
                            enhanced = True
                        
                        if enhanced:
                            people_enhanced += 1
                
                except Exception as e:
                    logger.error(f"Error augmenting person {person.id}: {str(e)}")
                    continue
            
            session.commit()
            
            return jsonify({
                'success': True,
                'people_enhanced': people_enhanced,
                'total_people_processed': len(tier1_people),
                'sample_people': sample_people,
                'message': f'Enhanced {people_enhanced} Tier 1 contacts with AI intelligence'
            })
            
    except Exception as e:
        logger.error(f"Augment people with knowledge error: {str(e)}")
        return jsonify({'error': str(e)}), 500 