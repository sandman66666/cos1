# Enhanced Email Intelligence Processor using Claude 4 Sonnet

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import anthropic
import time

from config.settings import settings
from chief_of_staff_ai.models.database import get_db_manager, Email, Person, Project, Task, User

logger = logging.getLogger(__name__)

class EmailIntelligenceProcessor:
    """Advanced email intelligence using Claude 4 Sonnet for comprehensive understanding"""
    
    def __init__(self):
        self.claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL  # Now uses Claude 4 Opus from settings
        self.version = "2.2"  # Debug version with relaxed filters
        
        # Quality filtering patterns (RELAXED FOR DEBUGGING)
        self.non_human_patterns = [
            'noreply', 'no-reply', 'donotreply', 'automated', 'newsletter',
            'unsubscribe', 'notification', 'system', 'support', 'help',
            'admin', 'contact', 'info', 'sales', 'marketing', 'hello',
            'team', 'notifications', 'alerts', 'updates', 'reports'
        ]
        
        # RELAXED quality thresholds to capture more content
        self.min_insight_length = 10  # Reduced from 15
        self.min_confidence_score = 0.4  # Reduced from 0.6 - be more inclusive
        
    def process_user_emails_intelligently(self, user_email: str, limit: int = None, force_refresh: bool = False) -> Dict:
        """
        Process user emails with Claude 4 Sonnet for high-quality business intelligence
        Enhanced with quality filtering and strategic insights
        """
        try:
            logger.info(f"Starting quality-focused email processing for {user_email}")
            
            # Get user and validate
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
                
            # Get business context for enhanced AI analysis
            user_context = self._get_user_business_context(user.id)
            
            # Get emails needing processing with quality pre-filtering
            emails_to_process = self._get_emails_needing_processing(user.id, limit or 100, force_refresh)
            
            # RELAXED: Filter for quality emails but be more inclusive
            quality_filtered_emails = self._filter_quality_emails_debug(emails_to_process, user_email)
            
            logger.info(f"Found {len(emails_to_process)} emails to process, {len(quality_filtered_emails)} passed quality filters")
            
            if not quality_filtered_emails:
                logger.warning(f"No emails passed quality filters for {user_email}")
                return {
                    'success': True,
                    'user_email': user_email,
                    'processed_emails': 0,
                    'high_quality_insights': 0,
                    'human_contacts_identified': 0,
                    'meaningful_projects': 0,
                    'actionable_tasks': 0,
                    'processor_version': self.version,
                    'debug_info': f"No emails passed filters out of {len(emails_to_process)} total emails"
                }
            
            # Limit to top quality emails for processing
            emails_to_process = quality_filtered_emails[:limit or 50]
            
            processed_count = 0
            insights_extracted = 0
            people_identified = 0
            projects_identified = 0
            tasks_created = 0
            
            for idx, email in enumerate(emails_to_process):
                try:
                    logger.info(f"Processing email {idx + 1}/{len(emails_to_process)} for {user_email}")
                    logger.debug(f"Email from: {email.sender}, subject: {email.subject}")
                    
                    # Skip if email has issues
                    if not email.body_clean and not email.snippet:
                        logger.warning(f"Skipping email {email.gmail_id} - no content")
                        continue
                    
                    # Get comprehensive email analysis from Claude with enhanced prompts
                    analysis = self._get_quality_focused_email_analysis(email, user, user_context)
                    
                    if analysis:
                        logger.debug(f"AI Analysis received for email {email.gmail_id}")
                        logger.debug(f"Strategic value score: {analysis.get('strategic_value_score', 'N/A')}")
                        logger.debug(f"Sender analysis: {analysis.get('sender_analysis', {})}")
                        logger.debug(f"People found: {len(analysis.get('people', []))}")
                        
                        if self._validate_analysis_quality_debug(analysis):
                            # Update email with insights
                            self._update_email_with_insights(email, analysis)
                            
                            # Extract and update people information (with human filtering)
                            if analysis.get('people') or analysis.get('sender_analysis'):
                                people_count = self._process_human_contacts_only_debug(user.id, analysis, email)
                                people_identified += people_count
                                logger.info(f"Extracted {people_count} people from email {email.gmail_id}")
                            
                            # Extract and update project information
                            if analysis.get('project') and self._validate_project_quality(analysis['project']):
                                project = self._process_project_insights(user.id, analysis['project'], email)
                                if project:
                                    projects_identified += 1
                                    email.project_id = project.id
                            
                            # Extract high-confidence tasks only
                            if analysis.get('tasks'):
                                tasks_count = self._process_high_quality_tasks(user.id, email.id, analysis['tasks'])
                                tasks_created += tasks_count
                            
                            insights_extracted += 1
                        else:
                            logger.info(f"Analysis for email {email.gmail_id} didn't meet quality thresholds")
                    else:
                        logger.warning(f"No analysis returned for email {email.gmail_id}")
                    
                    processed_count += 1
                    
                    # Add a small delay to prevent overwhelming the system
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to intelligently process email {email.gmail_id}: {str(e)}")
                    continue
            
            logger.info(f"Quality-focused processing: {processed_count} emails, {people_identified} people identified for {user_email}")
            
            return {
                'success': True,
                'user_email': user_email,
                'processed_emails': processed_count,
                'high_quality_insights': insights_extracted,
                'human_contacts_identified': people_identified,
                'meaningful_projects': projects_identified,
                'actionable_tasks': tasks_created,
                'processor_version': self.version,
                'debug_info': f"Processed {processed_count} emails, passed quality filters: {len(quality_filtered_emails)}"
            }
            
        except Exception as e:
            logger.error(f"Failed intelligent email processing for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_emails_needing_processing(self, user_id: int, limit: int, force_refresh: bool) -> List[Email]:
        """Get emails that need Claude analysis (generic filter)"""
        with get_db_manager().get_session() as session:
            query = session.query(Email).filter(
                Email.user_id == user_id,
                Email.body_clean.isnot(None)
            )
            
            if not force_refresh:
                query = query.filter(Email.ai_summary.is_(None))
            
            # Detach from session before returning to avoid issues
            emails = query.order_by(Email.email_date.desc()).limit(limit).all()
            session.expunge_all()
            return emails

    def _filter_unreplied_emails(self, emails: List[Email], user_email: str) -> List[Email]:
        """Filter a list of emails to find ones that are likely unreplied"""
        unreplied = []
        for email in emails:
            # If email is from the user themselves, skip
            if email.sender and user_email.lower() in email.sender.lower():
                continue

            # If email contains certain patterns suggesting it's automated, skip
            automated_patterns = [
                'noreply', 'no-reply', 'donotreply', 'automated', 'newsletter',
                'unsubscribe', 'notification only', 'system generated'
            ]
            sender_lower = (email.sender or '').lower()
            subject_lower = (email.subject or '').lower()
            if any(pattern in sender_lower or pattern in subject_lower for pattern in automated_patterns):
                continue

            # Default to including emails that seem personal/business oriented
            unreplied.append(email)
        return unreplied
    
    def _is_unreplied_email(self, email: Email, user_email: str) -> bool:
        """Determine if an email is unreplied using heuristics"""
        # If email is from the user themselves, skip
        if email.sender and user_email.lower() in email.sender.lower():
            return False
        
        # If email contains certain patterns suggesting it's automated, skip
        automated_patterns = [
            'noreply', 'no-reply', 'donotreply', 'automated', 'newsletter',
            'unsubscribe', 'notification only', 'system generated'
        ]
        
        sender_lower = (email.sender or '').lower()
        subject_lower = (email.subject or '').lower()
        
        if any(pattern in sender_lower or pattern in subject_lower for pattern in automated_patterns):
            return False
        
        # If email is marked as important or has action-oriented subject, include it
        action_words = ['review', 'approve', 'sign', 'confirm', 'urgent', 'asap', 'deadline', 'meeting']
        if any(word in subject_lower for word in action_words):
            return True
        
        # Default to including emails that seem personal/business oriented
        return True
    
    def _get_quality_focused_email_analysis(self, email: Email, user, user_context: Dict) -> Optional[Dict]:
        """Get quality-focused email analysis from Claude with enhanced business context"""
        try:
            # Safety check to prevent processing very large emails
            email_content = email.body_clean or email.snippet or ""
            if len(email_content) > 10000:  # Limit email content size
                logger.warning(f"Email {email.gmail_id} too large ({len(email_content)} chars), truncating")
                email_content = email_content[:10000] + "... [truncated]"
            
            if len(email_content) < 10:  # Skip very short emails
                logger.warning(f"Email {email.gmail_id} too short, skipping AI analysis")
                return None
            
            email_context = self._prepare_enhanced_email_context(email, user)
            
            # Limit context size to prevent API issues
            if len(email_context) > 15000:
                logger.warning(f"Email context too large for {email.gmail_id}, truncating")
                email_context = email_context[:15000] + "... [truncated]"
            
            # Enhanced system prompt with business context and quality requirements
            business_context_str = self._format_business_context(user_context)
            
            system_prompt = f"""You are an expert AI Chief of Staff that provides comprehensive email analysis for business intelligence and productivity. Be INCLUSIVE and extract valuable insights from business communications.

**YOUR MISSION:**
- Extract ALL valuable business intelligence, contacts, tasks, and insights
- Be inclusive rather than restrictive - capture business value wherever it exists
- Focus on building comprehensive knowledge about professional relationships and work

**BUSINESS CONTEXT FOR {user.email}:**
{business_context_str}

**ANALYSIS REQUIREMENTS:**

1. **EMAIL SUMMARY**: Clear description of the email's business purpose and content
2. **PEOPLE EXTRACTION**: Extract ALL human contacts with professional relevance (be generous!)
   - ALWAYS extract the sender if they're a real person
   - Extract anyone mentioned by name with business context
   - Include names even with limited contact information
3. **TASK IDENTIFICATION**: Find ANY actionable items or commitments mentioned
4. **BUSINESS INSIGHTS**: Extract any strategic value, opportunities, or challenges
5. **PROJECT CONTEXT**: Identify any work initiatives or business activities
6. **TOPIC EXTRACTION**: Identify business topics, project names, company names, technologies

**INCLUSIVE EXTRACTION GUIDELINES:**
- Extract people even if limited info is available (name + context is enough)
- Include tasks with clear actionable language, even if informal
- Capture business insights at any level (strategic, operational, or tactical)
- Process emails from colleagues, clients, partners, vendors - anyone professional
- Include follow-ups, scheduling, decisions, updates, and work discussions
- Extract topics like project names, company names, technologies, business areas
- Be generous with topic extraction - include any business-relevant subjects

Return a JSON object with this structure:
{{
    "summary": "Clear description of the email's business purpose and key content",
    "strategic_value_score": 0.7,  // Be generous - most business emails have value
    "sender_analysis": {{
        "name": "Sender's actual name (extract from signature or display name)",
        "role": "Their role/title if mentioned",
        "company": "Their company if identifiable",
        "relationship": "Professional relationship context",
        "is_human_contact": true,  // Default to true for most senders
        "business_relevance": "Why this person is professionally relevant"
    }},
    "people": [
        {{
            "name": "Full name of any person mentioned",
            "email": "their_email@example.com",
            "role": "Their role if mentioned",
            "company": "Company if mentioned", 
            "relationship": "Professional context",
            "business_relevance": "Why they're mentioned/relevant",
            "mentioned_context": "How they were mentioned in the email"
        }}
    ],
    "project": {{
        "name": "Project or initiative name",
        "description": "Description of the work or project",
        "category": "business/client_work/internal/operational",
        "priority": "high/medium/low",
        "status": "active/planning/discussed",
        "business_impact": "Potential impact or value",
        "key_stakeholders": ["person1", "person2"]
    }},
    "business_insights": {{
        "key_decisions": ["Any decisions mentioned or needed"],
        "strategic_opportunities": ["Opportunities or potential business value"],
        "business_challenges": ["Challenges or issues discussed"],
        "actionable_metrics": ["Any numbers or metrics mentioned"],
        "competitive_intelligence": ["Market or competitor information"],
        "partnership_opportunities": ["Collaboration potential"]
    }},
    "tasks": [
        {{
            "description": "Clear description of the actionable item",
            "assignee": "{user.email}",
            "due_date": "2025-02-15",
            "due_date_text": "deadline mentioned in email",
            "priority": "high/medium/low",
            "category": "action_item/follow_up/meeting/review",
            "confidence": 0.8,  // Be generous with confidence scores
            "business_context": "Why this task matters",
            "success_criteria": "What completion looks like"
        }}
    ],
    "topics": ["HitCraft", "board meeting", "fundraising", "AI in music", "certification", "business development"],  // Extract: project names, company names, technologies, business areas, meeting types
    "ai_category": "business_communication/client_work/project_coordination/operational"
}}

**IMPORTANT**: Extract value from most business emails. Only skip obvious spam or completely irrelevant content. Be generous with people extraction and task identification.
"""

            user_prompt = f"""Analyze this email comprehensively for business intelligence. Extract ALL valuable people, tasks, and insights:

{email_context}

Focus on building comprehensive business knowledge. Extract people and tasks generously - capture business value wherever it exists."""

            # Add timeout and retry protection
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    logger.info(f"Calling Claude API for comprehensive analysis of email {email.gmail_id}, attempt {attempt + 1}")
                    
                    message = self.claude_client.messages.create(
                        model=self.model,
                        max_tokens=3000,
                        temperature=0.1,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    
                    response_text = message.content[0].text.strip()
                    
                    # Handle null responses (low-quality emails)
                    if response_text.lower().strip() in ['null', 'none', '{}', '']:
                        logger.info(f"Claude rejected email {email.gmail_id} as low-quality")
                        return None
                    
                    # Parse JSON response with better error handling
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        json_text = response_text[json_start:json_end]
                        try:
                            analysis = json.loads(json_text)
                            logger.info(f"Successfully analyzed email {email.gmail_id}")
                            return analysis
                        except json.JSONDecodeError as json_error:
                            logger.error(f"JSON parsing error for email {email.gmail_id}: {str(json_error)}")
                            if attempt < max_retries - 1:
                                time.sleep(1)  # Wait before retry
                                continue
                            return None
                    else:
                        logger.warning(f"No valid JSON found in Claude response for email {email.gmail_id}")
                        if attempt < max_retries - 1:
                            time.sleep(1)  # Wait before retry
                            continue
                        return None
                        
                except Exception as api_error:
                    logger.error(f"Claude API error for email {email.gmail_id}, attempt {attempt + 1}: {str(api_error)}")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait longer before retry
                        continue
                    return None
            
            logger.warning(f"Failed to analyze email {email.gmail_id} after {max_retries} attempts")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get email analysis from Claude for {email.gmail_id}: {str(e)}")
            return None
    
    def _format_business_context(self, user_context: Dict) -> str:
        """Format business context for AI prompt"""
        context_parts = []
        
        if user_context.get('existing_projects'):
            context_parts.append(f"Current Projects: {', '.join(user_context['existing_projects'])}")
        
        if user_context.get('key_contacts'):
            context_parts.append(f"Key Business Contacts: {', '.join(user_context['key_contacts'][:5])}")  # Top 5
        
        if user_context.get('official_topics'):
            context_parts.append(f"Business Focus Areas: {', '.join(user_context['official_topics'])}")
        
        return '\n'.join(context_parts) if context_parts else "No existing business context available"
    
    def _validate_analysis_quality(self, analysis: Dict) -> bool:
        """Validate that the analysis meets quality standards - RELAXED VERSION"""
        try:
            # RELAXED: Check strategic value score - lowered threshold
            strategic_value = analysis.get('strategic_value_score', 0)
            if strategic_value < 0.5:  # Reduced from 0.6 to 0.5
                logger.info(f"Analysis rejected - low strategic value: {strategic_value}")
                return False
            
            # RELAXED: Check summary quality - reduced minimum length
            summary = analysis.get('summary', '')
            if len(summary) < self.min_insight_length:
                logger.info(f"Analysis rejected - summary too short: {len(summary)} chars")
                return False
            
            # RELAXED: More lenient trivial content detection
            trivial_phrases = [
                'thanks', 'thank you', 'got it', 'received', 'noted', 'okay', 'ok',
                'sounds good', 'will do', 'understood', 'acknowledged'
            ]
            
            # Only reject if it's VERY short AND contains only trivial phrases
            if any(phrase in summary.lower() for phrase in trivial_phrases) and len(summary) < 30:  # Reduced from 50
                logger.info(f"Analysis rejected - trivial content detected")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating analysis quality: {str(e)}")
            return False
    
    def _validate_project_quality(self, project_data: Dict) -> bool:
        """Validate that project data meets quality standards"""
        if not project_data or not project_data.get('name'):
            return False
        
        # Check project name is substantial
        if len(project_data['name']) < 5:
            return False
        
        # Check for meaningful description
        description = project_data.get('description', '')
        if len(description) < self.min_insight_length:
            return False
        
        return True
    
    def _process_human_contacts_only_debug(self, user_id: int, analysis: Dict, email: Email) -> int:
        """Process people information with COMPREHENSIVE RELATIONSHIP INTELLIGENCE GENERATION"""
        people_count = 0
        
        # Process sender first (with comprehensive relationship intelligence)
        sender_analysis = analysis.get('sender_analysis')
        if (sender_analysis and email.sender and 
            not self._is_obviously_non_human_contact(email.sender)):
            
            # Get existing person to accumulate knowledge
            existing_person = get_db_manager().find_person_by_email(user_id, email.sender)
            
            # Generate comprehensive relationship story and intelligence
            comprehensive_relationship_story = self._generate_comprehensive_relationship_story(sender_analysis, email, existing_person)
            relationship_insights = self._generate_relationship_insights(sender_analysis, email, existing_person)
            
            # Accumulate notes and context over time
            existing_notes = existing_person.notes if existing_person else ""
            new_relevance = sender_analysis.get('business_relevance', '')
            
            # Combine old and new notes intelligently
            accumulated_notes = existing_notes
            if new_relevance and new_relevance not in accumulated_notes:
                if accumulated_notes:
                    accumulated_notes += f"\n\nRecent Context: {new_relevance}"
                else:
                    accumulated_notes = new_relevance
            
            # Create enhanced person data with comprehensive intelligence
            person_data = {
                'email_address': email.sender,
                'name': sender_analysis.get('name', email.sender_name or email.sender.split('@')[0]),
                'title': sender_analysis.get('role'),
                'company': sender_analysis.get('company'),
                'relationship_type': sender_analysis.get('relationship', 'Contact'),
                'notes': accumulated_notes,  # Accumulated knowledge
                'importance_level': 0.8,  # Default importance
                'ai_version': self.version,
                'total_emails': (existing_person.total_emails if existing_person else 0) + 1,  # Increment email count
                
                # COMPREHENSIVE RELATIONSHIP INTELLIGENCE - These are the rich stories that make people clickable
                'comprehensive_relationship_story': comprehensive_relationship_story,
                'relationship_insights': relationship_insights,
                
                # Enhanced communication timeline
                'communication_timeline': self._generate_communication_timeline_entry(email),
                
                # Business intelligence metadata
                'relationship_intelligence': {
                    'context_story': comprehensive_relationship_story[:200] + '...' if len(comprehensive_relationship_story) > 200 else comprehensive_relationship_story,
                    'business_relevance': self._assess_business_relevance(sender_analysis, email),
                    'strategic_value': self._calculate_strategic_value(sender_analysis, email),
                    'recent_activity': 1,  # This email counts as recent activity
                    'communication_frequency': self._assess_communication_frequency(existing_person),
                    'last_strategic_topic': self._extract_strategic_topic_from_email(email),
                    'collaboration_score': self._calculate_collaboration_score(sender_analysis, email),
                    'expertise_areas': self._extract_expertise_areas(email, sender_analysis),
                    'meeting_participant': self._is_meeting_participant(email),
                    'communication_style': self._assess_communication_style(email),
                    'avg_urgency': self._assess_email_urgency(email)
                },
                
                # Enhanced business context
                'business_context': {
                    'strategic_topics': self._extract_strategic_topics_list(email),
                    'business_insights_count': 1,  # This email contributes insights
                    'communication_patterns': [self._categorize_communication_pattern(email)],
                    'project_involvement': self._extract_project_involvement(email, sender_analysis),
                    'has_strategic_communications': self._is_strategic_communication(email),
                    'last_strategic_communication': self._format_last_strategic_communication(email) if self._is_strategic_communication(email) else None,
                    'key_decisions_involved': self._extract_key_decisions(analysis, email),
                    'opportunities_discussed': self._extract_opportunities(analysis, email),
                    'challenges_mentioned': self._extract_challenges(analysis, email),
                    'collaboration_projects': self._extract_collaboration_projects(email, analysis),
                    'expertise_indicators': self._extract_expertise_indicators(email, sender_analysis),
                    'meeting_frequency': self._calculate_meeting_frequency(email),
                    'response_reliability': self._assess_response_reliability(existing_person)
                },
                
                # Enhanced relationship analytics
                'relationship_analytics': {
                    'total_interactions': (existing_person.total_emails if existing_person else 0) + 1,
                    'recent_interactions': 1,  # This is a recent interaction
                    'strategic_interactions': 1 if self._is_strategic_communication(email) else 0,
                    'avg_email_importance': self._calculate_avg_email_importance(email),
                    'relationship_trend': self._assess_relationship_trend(existing_person),
                    'engagement_level': self._assess_engagement_level(email, sender_analysis),
                    'communication_consistency': self._assess_communication_consistency(existing_person),
                    'business_value_score': self._calculate_business_value_score(sender_analysis, email),
                    'collaboration_strength': self._calculate_collaboration_strength(email, analysis),
                    'decision_influence': self._assess_decision_influence(analysis, email),
                    'topic_expertise_count': len(self._extract_expertise_areas(email, sender_analysis)),
                    'urgency_compatibility': self._assess_urgency_compatibility(email)
                }
            }
            
            get_db_manager().create_or_update_person(user_id, person_data)
            people_count += 1
            logger.info(f"Created/updated person with comprehensive intelligence: {person_data['name']} ({person_data['email_address']})")
        
        # Process mentioned people (also with comprehensive intelligence but lighter weight)
        people_mentioned = analysis.get('people', [])
        for person_info in people_mentioned:
            if (person_info.get('email') and 
                not self._is_obviously_non_human_contact(person_info['email'])):
                
                existing_person = get_db_manager().find_person_by_email(user_id, person_info['email'])
                
                # Generate lighter but still comprehensive relationship intelligence for mentioned people
                comprehensive_relationship_story = self._generate_mentioned_person_relationship_story(person_info, email, existing_person)
                relationship_insights = self._generate_mentioned_person_insights(person_info, email, existing_person)
                
                person_data = {
                    'email_address': person_info['email'],
                    'name': person_info.get('name', person_info['email'].split('@')[0]),
                    'title': person_info.get('role'),
                    'company': person_info.get('company'),
                    'relationship_type': person_info.get('relationship', 'Mentioned Contact'),
                    'notes': person_info.get('business_relevance', '') + f"\n\nMentioned in: {email.subject}",
                    'importance_level': 0.6,  # Lower importance for mentioned people
                    'ai_version': self.version,
                    'total_emails': (existing_person.total_emails if existing_person else 0),  # Don't increment for mentions
                    
                    # Comprehensive intelligence for mentioned people too
                    'comprehensive_relationship_story': comprehensive_relationship_story,
                    'relationship_insights': relationship_insights,
                    
                    # Lighter business intelligence for mentioned people
                    'relationship_intelligence': {
                        'context_story': f"Mentioned in discussion about {email.subject or 'business matters'}",
                        'business_relevance': 'mentioned_contact',
                        'strategic_value': 0.3,  # Lower strategic value for mentions
                        'recent_activity': 0,  # No direct activity
                        'communication_frequency': 'mentioned_only',
                        'last_strategic_topic': self._extract_strategic_topic_from_email(email),
                        'collaboration_score': 0.2,
                        'expertise_areas': [],
                        'meeting_participant': False,
                        'communication_style': 'unknown',
                        'avg_urgency': 0.5
                    }
                }
                
                get_db_manager().create_or_update_person(user_id, person_data)
                people_count += 1
                logger.info(f"Created/updated mentioned person: {person_data['name']} ({person_data['email_address']})")
        
        return people_count
    
    def _generate_comprehensive_relationship_story(self, sender_analysis: Dict, email: Email, existing_person=None) -> str:
        """Generate a comprehensive relationship story explaining the full context of this business relationship"""
        try:
            story_parts = []
            
            # Relationship introduction
            name = sender_analysis.get('name', email.sender_name or email.sender.split('@')[0] if email.sender else 'Contact')
            company = sender_analysis.get('company', 'Unknown Company')
            role = sender_analysis.get('role', 'Professional Contact')
            
            story_parts.append(f"👤 **Professional Contact:** {name}")
            if role and role != 'Professional Contact':
                story_parts.append(f"💼 **Role:** {role}")
            if company and company != 'Unknown Company':
                story_parts.append(f"🏢 **Company:** {company}")
            
            # Relationship context
            relationship = sender_analysis.get('relationship', 'Business Contact')
            business_relevance = sender_analysis.get('business_relevance', '')
            
            story_parts.append(f"🤝 **Relationship:** {relationship}")
            if business_relevance:
                story_parts.append(f"💡 **Business Relevance:** {business_relevance}")
            
            # Current communication context
            if email.subject:
                story_parts.append(f"📧 **Current Discussion:** '{email.subject}'")
            
            if email.ai_summary and len(email.ai_summary) > 20:
                story_parts.append(f"💬 **Latest Communication:** {email.ai_summary}")
            
            # Historical context if available
            if existing_person:
                total_emails = existing_person.total_emails or 0
                if total_emails > 1:
                    story_parts.append(f"📊 **Communication History:** {total_emails} previous email exchanges")
                
                if existing_person.last_interaction:
                    from datetime import datetime, timezone
                    days_since = (datetime.now(timezone.utc) - existing_person.last_interaction).days
                    if days_since < 7:
                        story_parts.append(f"⏰ **Recent Activity:** Last contacted {days_since} days ago")
                    elif days_since < 30:
                        story_parts.append(f"⏰ **Regular Contact:** Last contacted {days_since} days ago")
                    else:
                        story_parts.append(f"⏰ **Reconnection:** Last contacted {days_since} days ago")
            else:
                story_parts.append("🆕 **New Contact:** First recorded interaction")
            
            # Business impact assessment
            if self._is_strategic_communication(email):
                story_parts.append("⭐ **Strategic Importance:** This communication has high strategic value")
            
            return "\n".join(story_parts)
            
        except Exception as e:
            logger.error(f"Error generating comprehensive relationship story: {str(e)}")
            return f"Professional contact: {sender_analysis.get('name', 'Business Contact')}"
    
    def _generate_relationship_insights(self, sender_analysis: Dict, email: Email, existing_person=None) -> str:
        """Generate actionable relationship insights and recommendations"""
        try:
            insights = []
            
            # Relationship strength assessment
            name = sender_analysis.get('name', 'Contact')
            
            if existing_person and existing_person.total_emails and existing_person.total_emails > 5:
                insights.append(f"🔗 **Strong Relationship:** You've exchanged {existing_person.total_emails} emails with {name}, indicating an established professional relationship.")
            elif existing_person and existing_person.total_emails and existing_person.total_emails > 1:
                insights.append(f"🌱 **Developing Relationship:** Building relationship with {name} through ongoing communication.")
            else:
                insights.append(f"🆕 **New Connection:** This is your first recorded interaction with {name}.")
            
            # Business value insights
            business_relevance = sender_analysis.get('business_relevance', '')
            if business_relevance:
                insights.append(f"💼 **Business Value:** {business_relevance}")
            
            # Communication pattern insights
            if self._is_strategic_communication(email):
                insights.append("⭐ **Strategic Relevance:** This person is involved in strategic business discussions.")
            
            # Company/role insights
            company = sender_analysis.get('company')
            role = sender_analysis.get('role')
            if company:
                insights.append(f"🏢 **Company Intelligence:** {name} works at {company}, potentially opening collaboration opportunities.")
            if role:
                insights.append(f"👔 **Role Intelligence:** As {role}, they may have decision-making authority or specialized expertise.")
            
            # Engagement recommendations
            if existing_person and existing_person.last_interaction:
                from datetime import datetime, timezone
                days_since = (datetime.now(timezone.utc) - existing_person.last_interaction).days
                if days_since > 60:
                    insights.append(f"📅 **Engagement Opportunity:** Consider reaching out to {name} to maintain the relationship.")
                elif days_since < 7:
                    insights.append(f"🔥 **Active Relationship:** Regular communication with {name} indicates strong engagement.")
            
            # Topic-based insights
            strategic_topic = self._extract_strategic_topic_from_email(email)
            if strategic_topic:
                insights.append(f"🎯 **Topic Expertise:** {name} is engaged in discussions about {strategic_topic}.")
            
            return "\n".join(insights)
            
        except Exception as e:
            logger.error(f"Error generating relationship insights: {str(e)}")
            return f"Professional relationship with valuable business context."
    
    def _generate_mentioned_person_relationship_story(self, person_info: Dict, email: Email, existing_person=None) -> str:
        """Generate relationship story for people mentioned in emails"""
        try:
            story_parts = []
            
            name = person_info.get('name', person_info.get('email', 'Unknown').split('@')[0])
            story_parts.append(f"👤 **Mentioned Contact:** {name}")
            
            # Context of mention
            mentioned_context = person_info.get('mentioned_context', '')
            if mentioned_context:
                story_parts.append(f"💬 **Mentioned In Context:** {mentioned_context}")
            
            # Business relevance
            business_relevance = person_info.get('business_relevance', '')
            if business_relevance:
                story_parts.append(f"💼 **Business Relevance:** {business_relevance}")
            
            # Email context
            if email.subject:
                story_parts.append(f"📧 **Discussion Context:** Mentioned in '{email.subject}'")
            
            # Historical context if available
            if existing_person and existing_person.total_emails:
                story_parts.append(f"📊 **Previous Contact:** {existing_person.total_emails} direct communications on record")
            else:
                story_parts.append("📝 **Indirect Contact:** Known through mentions in communications")
            
            return "\n".join(story_parts)
            
        except Exception as e:
            logger.error(f"Error generating mentioned person story: {str(e)}")
            return f"Contact mentioned in business communications."
    
    def _generate_mentioned_person_insights(self, person_info: Dict, email: Email, existing_person=None) -> str:
        """Generate insights for people mentioned in emails"""
        try:
            insights = []
            
            name = person_info.get('name', 'Contact')
            
            # Mention analysis
            insights.append(f"💭 **Indirect Intelligence:** {name} was mentioned in business communications, indicating relevance to your work.")
            
            # Business context
            business_relevance = person_info.get('business_relevance', '')
            if business_relevance:
                insights.append(f"🎯 **Strategic Value:** {business_relevance}")
            
            # Potential for direct engagement
            if person_info.get('email'):
                insights.append(f"📧 **Engagement Opportunity:** Consider direct outreach to {name} for collaboration or information.")
            
            # Company intelligence
            company = person_info.get('company')
            if company:
                insights.append(f"🏢 **Company Connection:** {name} at {company} may represent partnership or business opportunities.")
            
            return "\n".join(insights)
            
        except Exception as e:
            logger.error(f"Error generating mentioned person insights: {str(e)}")
            return f"Mentioned in business context with potential strategic value."
    
    def _process_high_quality_tasks(self, user_id: int, email_id: int, tasks_data: List[Dict]) -> int:
        """Process and create high-quality tasks with COMPREHENSIVE CONTEXT STORIES"""
        tasks_created = 0
        
        # Get the source email for rich context generation
        with get_db_manager().get_session() as session:
            source_email = session.query(Email).filter(Email.id == email_id).first()
            if not source_email:
                logger.error(f"Could not find source email with ID {email_id}")
                return 0
        
        for task_data in tasks_data:
            try:
                # Enhanced quality validation
                description = task_data.get('description', '').strip()
                confidence = task_data.get('confidence', 0.0)
                
                if len(description) < 5 or confidence < self.min_confidence_score:
                    logger.debug(f"Task rejected: description='{description}', confidence={confidence}")
                    continue
                
                # GENERATE COMPREHENSIVE CONTEXT STORY
                comprehensive_context_story = self._generate_comprehensive_task_context_story(task_data, source_email)
                
                # GENERATE DETAILED TASK MEANING
                detailed_task_meaning = self._generate_detailed_task_meaning(task_data, source_email)
                
                # GENERATE COMPREHENSIVE IMPORTANCE ANALYSIS  
                comprehensive_importance_analysis = self._generate_comprehensive_importance_analysis(task_data, source_email)
                
                # GENERATE COMPREHENSIVE ORIGIN DETAILS
                comprehensive_origin_details = self._generate_comprehensive_origin_details(task_data, source_email)
                
                # Parse due date with better handling
                due_date = None
                due_date_text = task_data.get('due_date_text', '')
                if task_data.get('due_date'):
                    due_date = self._parse_due_date(task_data['due_date'])
                
                # Create enhanced task with comprehensive context
                enhanced_task_data = {
                    'description': description,
                    'assignee': task_data.get('assignee'),
                    'due_date': due_date,
                    'due_date_text': due_date_text,
                    'priority': task_data.get('priority', 'medium'),
                    'status': 'pending',
                    'category': task_data.get('category', 'action_item'),
                    'confidence': confidence,
                    'source_text': task_data.get('business_context', ''),
                    'context': task_data.get('business_context', ''),
                    'email_id': email_id,
                    'source_email_subject': source_email.subject,
                    'ai_version': self.version,
                    
                    # COMPREHENSIVE CONTEXT FIELDS - This is what makes tasks rich and detailed
                    'comprehensive_context_story': comprehensive_context_story,
                    'detailed_task_meaning': detailed_task_meaning,
                    'comprehensive_importance_analysis': comprehensive_importance_analysis,
                    'comprehensive_origin_details': comprehensive_origin_details,
                    
                    # Enhanced metadata for frontend intelligence
                    'business_intelligence': {
                        'entity_connections': 1 if source_email.sender else 0,
                        'source_quality': 'high' if source_email.ai_summary else 'medium',
                        'ai_confidence': confidence,
                        'cross_referenced': True,
                        'relationship_strength': 1,  # Will be enhanced based on sender frequency
                        'business_impact_score': confidence * 0.8,  # Strategic importance estimate
                        'action_clarity': 'high' if len(description) > 20 else 'medium',
                        'contextual_richness': 'comprehensive'
                    }
                }
                
                task = get_db_manager().create_or_update_task(user_id, enhanced_task_data)
                if task:
                    tasks_created += 1
                    logger.info(f"Created comprehensive task: {description[:50]}...")
                
            except Exception as e:
                logger.error(f"Failed to create enhanced task: {str(e)}")
                continue
        
        return tasks_created
    
    def _generate_comprehensive_task_context_story(self, task_data: Dict, source_email: Email) -> str:
        """Generate a comprehensive context story explaining the full background of this task"""
        try:
            # Build rich narrative about the task context
            story_parts = []
            
            # Email source context
            if source_email:
                sender_name = source_email.sender_name or source_email.sender.split('@')[0] if source_email.sender else "someone"
                
                # Timing context
                if source_email.email_date:
                    from datetime import datetime, timezone
                    days_ago = (datetime.now(timezone.utc) - source_email.email_date).days
                    if days_ago == 0:
                        timing = f"today ({source_email.email_date.strftime('%I:%M %p')})"
                    elif days_ago == 1:
                        timing = f"yesterday ({source_email.email_date.strftime('%I:%M %p')})"
                    elif days_ago < 7:
                        timing = f"{days_ago} days ago ({source_email.email_date.strftime('%A, %I:%M %p')})"
                    else:
                        timing = source_email.email_date.strftime('%B %d at %I:%M %p')
                else:
                    timing = "recently"
                
                story_parts.append(f"📧 **Email from:** {sender_name}")
                story_parts.append(f"📅 **Timing:** Received {timing}")
                
                if source_email.subject:
                    story_parts.append(f"📝 **Subject:** '{source_email.subject}'")
                
                # Email content context
                if source_email.ai_summary and len(source_email.ai_summary) > 20:
                    story_parts.append(f"💬 **Email Summary:** {source_email.ai_summary}")
                
                # Business category if available
                if hasattr(source_email, 'ai_category') and source_email.ai_category:
                    story_parts.append(f"🏢 **Business Category:** {source_email.ai_category}")
            
            # Task-specific context
            business_context = task_data.get('business_context', '')
            if business_context:
                story_parts.append(f"🎯 **Business Impact:** {business_context}")
            
            # Success criteria if available
            success_criteria = task_data.get('success_criteria', '')
            if success_criteria:
                story_parts.append(f"✅ **Success Criteria:** {success_criteria}")
            
            return "\n".join(story_parts)
            
        except Exception as e:
            logger.error(f"Error generating comprehensive task context: {str(e)}")
            return f"Task from email communication requiring attention."
    
    def _generate_detailed_task_meaning(self, task_data: Dict, source_email: Email) -> str:
        """Generate detailed explanation of what this task actually means and how to complete it"""
        try:
            explanation_parts = []
            description = task_data.get('description', '')
            description_lower = description.lower()
            
            # Analyze the type of action required
            if any(word in description_lower for word in ['call', 'phone', 'ring']):
                explanation_parts.append("🔔 **Action Type:** You need to make a phone call")
                explanation_parts.append(f"📞 **Specific Task:** {description}")
                explanation_parts.append("📋 **Steps to Complete:**")
                explanation_parts.append("   1. Find contact information")
                explanation_parts.append("   2. Prepare talking points based on email context")
                explanation_parts.append("   3. Make the call")
                explanation_parts.append("   4. Follow up if needed")
                
            elif any(word in description_lower for word in ['email', 'send', 'reply', 'respond']):
                explanation_parts.append("✉️ **Action Type:** You need to send an email or document")
                explanation_parts.append(f"📧 **Specific Task:** {description}")
                explanation_parts.append("📋 **Steps to Complete:**")
                explanation_parts.append("   1. Review the original email context")
                explanation_parts.append("   2. Draft your response/email")
                explanation_parts.append("   3. Include relevant information or attachments")
                explanation_parts.append("   4. Send and track response")
                
            elif any(word in description_lower for word in ['schedule', 'book', 'meeting', 'appointment']):
                explanation_parts.append("📅 **Action Type:** You need to arrange a meeting or appointment")
                explanation_parts.append(f"🗓️ **Specific Task:** {description}")
                explanation_parts.append("📋 **Steps to Complete:**")
                explanation_parts.append("   1. Check your calendar availability")
                explanation_parts.append("   2. Propose meeting times")
                explanation_parts.append("   3. Send calendar invite")
                explanation_parts.append("   4. Confirm attendance")
                
            elif any(word in description_lower for word in ['review', 'check', 'examine', 'evaluate']):
                explanation_parts.append("🔍 **Action Type:** You need to examine or evaluate something")
                explanation_parts.append(f"📋 **Specific Task:** {description}")
                
            elif any(word in description_lower for word in ['follow up', 'followup', 'follow-up']):
                explanation_parts.append("⏰ **Action Type:** You need to check back on something or continue a conversation")
                explanation_parts.append(f"🔄 **Specific Task:** {description}")
                
            elif any(word in description_lower for word in ['complete', 'finish', 'deliver', 'submit']):
                explanation_parts.append("✅ **Action Type:** You need to complete or deliver something")
                explanation_parts.append(f"🎯 **Specific Task:** {description}")
                
            else:
                explanation_parts.append("⚡ **Action Type:** General business action required")
                explanation_parts.append(f"📝 **Specific Task:** {description}")
            
            # Add email context for better understanding
            if source_email and source_email.ai_summary:
                explanation_parts.append(f"📖 **Background Context:** {source_email.ai_summary}")
            
            return "\n".join(explanation_parts)
            
        except Exception as e:
            logger.error(f"Error generating detailed task meaning: {str(e)}")
            return f"Action required: {task_data.get('description', 'Task completion needed')}"
    
    def _generate_comprehensive_importance_analysis(self, task_data: Dict, source_email: Email) -> str:
        """Generate comprehensive analysis of why this task is important"""
        try:
            importance_factors = []
            
            # Priority analysis
            priority = task_data.get('priority', 'medium')
            if priority == 'high':
                importance_factors.append("🚨 **Priority Level:** This is marked as HIGH PRIORITY - requires immediate attention")
            elif priority == 'medium':
                importance_factors.append("⚠️ **Priority Level:** This is medium priority - should be completed soon")
            else:
                importance_factors.append("📝 **Priority Level:** This is standard priority")
            
            # AI confidence analysis
            confidence = task_data.get('confidence', 0.0)
            if confidence > 0.9:
                importance_factors.append("🤖 **AI Confidence:** VERY HIGH (95%+) - This is definitely a real action item")
            elif confidence > 0.8:
                importance_factors.append("🤖 **AI Confidence:** HIGH (80%+) - This is very likely a real action item")
            elif confidence > 0.6:
                importance_factors.append("🤖 **AI Confidence:** MEDIUM (60%+) - This appears to be an action item")
            
            # Business impact
            business_context = task_data.get('business_context', '')
            if business_context:
                importance_factors.append(f"💼 **Business Impact:** {business_context}")
            
            # Email source importance
            if source_email:
                if hasattr(source_email, 'strategic_importance') and source_email.strategic_importance and source_email.strategic_importance > 0.7:
                    importance_factors.append("⭐ **Strategic Value:** The source email was marked as strategically important")
                
                if hasattr(source_email, 'urgency_score') and source_email.urgency_score and source_email.urgency_score > 0.7:
                    importance_factors.append("💼 **Business Impact:** The original email was marked as urgent")
                
                if hasattr(source_email, 'action_required') and source_email.action_required:
                    importance_factors.append("💼 **Business Impact:** The original email explicitly requested action")
            
            # Due date urgency
            due_date_text = task_data.get('due_date_text', '')
            if due_date_text:
                importance_factors.append(f"⏰ **Timing:** Deadline mentioned: {due_date_text}")
            
            return "\n".join(importance_factors)
            
        except Exception as e:
            logger.error(f"Error generating importance analysis: {str(e)}")
            return "Standard business task requiring attention."
    
    def _generate_comprehensive_origin_details(self, task_data: Dict, source_email: Email) -> str:
        """Generate comprehensive details about where this task originated"""
        try:
            origin_details = []
            
            if source_email:
                # Source identification
                if source_email.sender_name and source_email.sender:
                    origin_details.append(f"📧 **Original Email From:** {source_email.sender_name} ({source_email.sender})")
                elif source_email.sender:
                    origin_details.append(f"📧 **Original Email From:** {source_email.sender}")
                
                # Email details
                if source_email.subject:
                    origin_details.append(f"📄 **Email Subject:** '{source_email.subject}'")
                
                if source_email.email_date:
                    origin_details.append(f"📅 **Received:** {source_email.email_date.strftime('%A, %B %d, %Y at %I:%M %p')}")
                
                # Email content preview
                if hasattr(source_email, 'body_text') and source_email.body_text:
                    preview = source_email.body_text[:300].strip()
                    if len(source_email.body_text) > 300:
                        preview += "..."
                    origin_details.append(f"📝 **Email Content Preview:** {preview}")
                elif source_email.ai_summary:
                    origin_details.append(f"📝 **Email Content Summary:** {source_email.ai_summary}")
                
                # Processing details
                if source_email.processed_at:
                    origin_details.append(f"🤖 **AI Processed:** {source_email.processed_at.strftime('%Y-%m-%d at %I:%M %p')}")
                
                # Email metadata
                metadata = []
                if hasattr(source_email, 'thread_id') and source_email.thread_id:
                    metadata.append("Part of email thread")
                if hasattr(source_email, 'labels') and source_email.labels:
                    metadata.append(f"Gmail labels: {', '.join(source_email.labels[:3])}")
                if metadata:
                    origin_details.append(f"📊 **Email Metadata:** {'; '.join(metadata)}")
            else:
                origin_details.append("📝 **Task Origin:** Created manually or from unknown source")
                origin_details.append("ℹ️ **Note:** This task was not automatically extracted from an email")
            
            return "\n".join(origin_details)
            
        except Exception as e:
            logger.error(f"Error generating origin details: {str(e)}")
            return "Task created from email communication."
    
    def _prepare_enhanced_email_context(self, email: Email, user) -> str:
        """Prepare comprehensive email context for Claude analysis"""
        timestamp = email.email_date.strftime('%Y-%m-%d %H:%M') if email.email_date else 'Unknown'
        
        context = f"""EMAIL ANALYSIS REQUEST

Recipient: {user.email} ({user.name})
From: {email.sender_name or 'Unknown'} <{email.sender}>
Date: {timestamp}
Subject: {email.subject}

Email Content:
{email.body_clean or email.snippet}

Additional Context:
- Recipients: {', '.join(email.recipient_emails) if email.recipient_emails else 'Not specified'}
- Thread ID: {email.thread_id}
- Email Labels: {', '.join(email.labels) if email.labels else 'None'}
- Message Type: {email.message_type or 'Unknown'}
- Priority Score: {email.priority_score or 'Not calculated'}
"""
        return context
    
    def _update_email_with_insights(self, email: Email, analysis: Dict):
        """Update email record with Claude insights"""
        with get_db_manager().get_session() as session:
            email_record = session.query(Email).filter(Email.id == email.id).first()
            if email_record:
                email_record.ai_summary = analysis.get('summary')
                email_record.ai_category = analysis.get('ai_category')
                email_record.sentiment_score = analysis.get('sentiment_score')
                email_record.urgency_score = analysis.get('urgency_score')
                email_record.key_insights = analysis.get('business_insights')
                email_record.topics = analysis.get('topics')
                email_record.action_required = analysis.get('action_required', False)
                email_record.follow_up_required = analysis.get('follow_up_required', False)
                
                session.commit()
    
    def _process_project_insights(self, user_id: int, project_data: Dict, email: Email) -> Optional[Project]:
        """Process and update project information - SAFE VERSION"""
        if not project_data or not project_data.get('name'):
            return None
        
        try:
            project_info = {
                'name': project_data['name'],
                'slug': self._create_slug(project_data['name']),
                'description': project_data.get('description'),
                'category': project_data.get('category'),
                'priority': project_data.get('priority', 'medium'),
                'status': project_data.get('status', 'active'),
                'key_topics': project_data.get('key_topics', []),
                'stakeholders': project_data.get('stakeholders', []),
                'ai_version': self.version
            }
            
            return get_db_manager().create_or_update_project(user_id, project_info)
            
        except Exception as e:
            logger.error(f"Error processing project insights: {str(e)}")
            return None
    
    def _create_slug(self, name: str) -> str:
        """Create URL-friendly slug from name"""
        return re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
    
    def _parse_due_date(self, date_str: str) -> Optional[datetime]:
        """Parse due date string into datetime"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None
    
    def get_business_knowledge_summary(self, user_email: str) -> Dict:
        """Get comprehensive business knowledge summary with quality synthesis"""
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get all processed emails with quality filtering
            emails = get_db_manager().get_user_emails(user.id, limit=1000)
            projects = get_db_manager().get_user_projects(user.id, limit=200)
            people = get_db_manager().get_user_people(user.id, limit=500)
            
            # Filter for high-quality insights only
            quality_emails = [e for e in emails if e.ai_summary and len(e.ai_summary) > self.min_insight_length]
            human_contacts = [p for p in people if not self._is_non_human_contact(p.email_address or '')]
            substantial_projects = [p for p in projects if p.description and len(p.description) > self.min_insight_length]
            
            # Synthesize high-quality business insights
            strategic_decisions = []
            business_opportunities = []
            key_challenges = []
            competitive_insights = []
            
            for email in quality_emails:
                if email.key_insights and isinstance(email.key_insights, dict):
                    insights = email.key_insights
                    
                    # Extract strategic-level insights only
                    decisions = insights.get('key_decisions', [])
                    strategic_decisions.extend([d for d in decisions if len(d) > self.min_insight_length])
                    
                    opportunities = insights.get('strategic_opportunities', insights.get('opportunities', []))
                    business_opportunities.extend([o for o in opportunities if len(o) > self.min_insight_length])
                    
                    challenges = insights.get('business_challenges', insights.get('challenges', []))
                    key_challenges.extend([c for c in challenges if len(c) > self.min_insight_length])
                    
                    competitive = insights.get('competitive_intelligence', [])
                    competitive_insights.extend([ci for ci in competitive if len(ci) > self.min_insight_length])
            
            # Get meaningful topics
            topics = get_db_manager().get_user_topics(user.id, limit=1000)
            business_topics = [topic.name for topic in topics if topic.is_official or 
                              (topic.description and len(topic.description) > 10)]
            
            return {
                'success': True,
                'user_email': user_email,
                'business_knowledge': {
                    'summary_stats': {
                        'quality_emails_analyzed': len(quality_emails),
                        'human_contacts': len(human_contacts),
                        'substantial_projects': len(substantial_projects),
                        'strategic_insights': len(strategic_decisions) + len(business_opportunities) + len(key_challenges)
                    },
                    'strategic_intelligence': {
                        'key_decisions': self._deduplicate_and_rank(strategic_decisions)[:8],  # Top 8 strategic decisions
                        'business_opportunities': self._deduplicate_and_rank(business_opportunities)[:8],
                        'key_challenges': self._deduplicate_and_rank(key_challenges)[:8],
                        'competitive_intelligence': self._deduplicate_and_rank(competitive_insights)[:5]
                    },
                    'business_topics': business_topics[:15],  # Top 15 business topics
                    'network_intelligence': {
                        'total_human_contacts': len(human_contacts),
                        'active_projects': len([p for p in substantial_projects if p.status == 'active']),
                        'project_categories': list(set([p.category for p in substantial_projects if p.category]))
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get business knowledge for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_chat_knowledge_summary(self, user_email: str) -> Dict:
        """Get comprehensive knowledge summary for chat interface with enhanced context"""
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get all processed data with quality filters
            emails = get_db_manager().get_user_emails(user.id, limit=1000)
            projects = get_db_manager().get_user_projects(user.id, limit=200)
            people = get_db_manager().get_user_people(user.id, limit=500)
            topics = get_db_manager().get_user_topics(user.id, limit=1000)
            
            # GET CALENDAR EVENTS FOR KNOWLEDGE BASE
            now = datetime.now(timezone.utc)
            calendar_events = get_db_manager().get_user_calendar_events(
                user.id, 
                start_date=now - timedelta(days=30),  # Past 30 days for context
                end_date=now + timedelta(days=60),    # Next 60 days for planning
                limit=200
            )
            
            # Filter for high-quality content
            quality_emails = [e for e in emails if e.ai_summary and len(e.ai_summary) > self.min_insight_length]
            human_contacts = [p for p in people if not self._is_non_human_contact(p.email_address or '') and p.name]
            
            # Compile rich contacts with enhanced professional context
            rich_contacts = []
            for person in human_contacts[:15]:  # Top 15 human contacts
                # Create rich professional story
                professional_story = self._create_professional_story(person, quality_emails)
                
                contact_info = {
                    'name': person.name,
                    'email': person.email_address,
                    'title': person.title or person.role,
                    'company': person.company,
                    'relationship': person.relationship_type,
                    'story': professional_story,
                    'total_emails': person.total_emails or 0,
                    'last_interaction': person.last_interaction.isoformat() if person.last_interaction else None,
                    'importance_score': person.importance_level or 0.5
                }
                rich_contacts.append(contact_info)
            
            # Enhanced business intelligence compilation
            business_decisions = []
            opportunities = []
            challenges = []
            
            for email in quality_emails:
                if email.key_insights and isinstance(email.key_insights, dict):
                    insights = email.key_insights
                    
                    # Enhanced insight extraction with context
                    decisions = insights.get('key_decisions', [])
                    for decision in decisions:
                        if len(decision) > self.min_insight_length:
                            business_decisions.append({
                                'decision': decision,
                                'context': email.ai_summary,
                                'sender': email.sender_name or email.sender,
                                'date': email.email_date.isoformat() if email.email_date else None
                            })
                    
                    opps = insights.get('strategic_opportunities', insights.get('opportunities', []))
                    for opp in opps:
                        if len(opp) > self.min_insight_length:
                            opportunities.append({
                                'opportunity': opp,
                                'context': email.ai_summary,
                                'source': email.sender_name or email.sender,
                                'date': email.email_date.isoformat() if email.email_date else None
                            })
                    
                    chals = insights.get('business_challenges', insights.get('challenges', []))
                    for chal in chals:
                        if len(chal) > self.min_insight_length:
                            challenges.append({
                                'challenge': chal,
                                'context': email.ai_summary,
                                'source': email.sender_name or email.sender,
                                'date': email.email_date.isoformat() if email.email_date else None
                            })
            
            # Enhanced topic knowledge with rich contexts
            topic_knowledge = {
                'all_topics': [topic.name for topic in topics if topic.is_official or 
                              (topic.description and len(topic.description) > 10)],
                'official_topics': [topic.name for topic in topics if topic.is_official],
                'topic_contexts': {}
            }
            
            for topic in topics:
                if topic.is_official or (topic.description and len(topic.description) > 10):
                    topic_emails = [email for email in quality_emails if email.topics and topic.name in email.topics]
                    contexts = []
                    for email in topic_emails[:3]:  # Top 3 emails per topic
                        if email.ai_summary:
                            contexts.append({
                                'summary': email.ai_summary,
                                'sender': email.sender_name or email.sender,
                                'date': email.email_date.isoformat() if email.email_date else None,
                                'email_subject': email.subject
                            })
                    topic_knowledge['topic_contexts'][topic.name] = contexts
            
            # Enhanced statistics
            summary_stats = {
                'total_emails_analyzed': len(quality_emails),
                'rich_contacts': len(rich_contacts),
                'business_decisions': len(business_decisions),
                'opportunities_identified': len(opportunities),
                'challenges_tracked': len(challenges),
                'active_projects': len([p for p in projects if p.status == 'active']),
                'official_topics': len([t for t in topics if t.is_official]),
                'calendar_events': len(calendar_events),
                'upcoming_meetings': len([e for e in calendar_events if e.start_time and e.start_time > now]),
                'recent_meetings': len([e for e in calendar_events if e.start_time and e.start_time < now])
            }
            
            # Process calendar intelligence for knowledge base
            calendar_intelligence = self._extract_calendar_intelligence(calendar_events, people, now)
            
            return {
                'success': True,
                'user_email': user_email,
                'knowledge_base': {
                    'summary_stats': summary_stats,
                    'rich_contacts': rich_contacts,
                    'business_intelligence': {
                        'recent_decisions': sorted(business_decisions, 
                                                 key=lambda x: x['date'] or '', reverse=True)[:8],
                        'top_opportunities': sorted(opportunities,
                                                  key=lambda x: x['date'] or '', reverse=True)[:8],
                        'current_challenges': sorted(challenges,
                                                   key=lambda x: x['date'] or '', reverse=True)[:8]
                    },
                    'topic_knowledge': topic_knowledge,
                    'projects_summary': [
                        {
                            'name': project.name,
                            'description': project.description,
                            'status': project.status,
                            'priority': project.priority,
                            'stakeholders': project.stakeholders or [],
                            'key_topics': project.key_topics or []
                        }
                        for project in projects if project.description and len(project.description) > self.min_insight_length
                    ][:10],  # Top 10 substantial projects
                    'calendar_events': calendar_events,
                    'calendar_intelligence': calendar_intelligence
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to get chat knowledge for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _create_professional_story(self, person: Person, emails: List[Email]) -> str:
        """Create a rich professional story for a contact based on email interactions"""
        try:
            # Find emails from this person
            person_emails = [e for e in emails if e.sender and person.email_address and 
                           e.sender.lower() == person.email_address.lower()]
            
            if not person_emails:
                return f"Professional contact with {person.relationship_type or 'business'} relationship."
            
            # Analyze communication patterns and content
            total_emails = len(person_emails)
            recent_emails = sorted(person_emails, key=lambda x: x.email_date or datetime.min, reverse=True)[:3]
            
            # Extract key themes from their communication
            themes = []
            for email in recent_emails:
                if email.ai_summary and len(email.ai_summary) > 20:
                    themes.append(email.ai_summary)
            
            # Create professional narrative
            story_parts = []
            
            if person.company and person.title:
                story_parts.append(f"{person.title} at {person.company}")
            elif person.company:
                story_parts.append(f"Works at {person.company}")
            elif person.title:
                story_parts.append(f"{person.title}")
            
            if total_emails > 1:
                story_parts.append(f"Active correspondence with {total_emails} substantive emails")
            
            if themes:
                story_parts.append(f"Recent discussions: {'; '.join(themes[:2])}")
            
            if person.relationship_type:
                story_parts.append(f"Relationship: {person.relationship_type}")
            
            return '. '.join(story_parts) if story_parts else "Professional business contact"
            
        except Exception as e:
            logger.error(f"Error creating professional story: {str(e)}")
            return "Professional business contact"
    
    def _deduplicate_and_rank(self, items: List[str]) -> List[str]:
        """Deduplicate similar items and rank by relevance"""
        if not items:
            return []
        
        # Simple deduplication by similarity (basic approach)
        unique_items = []
        for item in items:
            # Check if this item is too similar to existing ones
            is_duplicate = False
            for existing in unique_items:
                # Simple similarity check - if 70% of words overlap, consider duplicate
                item_words = set(item.lower().split())
                existing_words = set(existing.lower().split())
                
                if len(item_words) > 0 and len(existing_words) > 0:
                    overlap = len(item_words & existing_words)
                    similarity = overlap / min(len(item_words), len(existing_words))
                    if similarity > 0.7:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_items.append(item)
        
        # Rank by length and specificity (longer, more specific items are often better)
        unique_items.sort(key=lambda x: (len(x), len(x.split())), reverse=True)
        
        return unique_items

    def _get_user_business_context(self, user_id: int) -> Dict:
        """Get existing business context to enhance AI analysis"""
        try:
            # Get existing high-quality projects
            projects = get_db_manager().get_user_projects(user_id, limit=50)
            project_context = [p.name for p in projects if p.description and len(p.description) > 20]
            
            # Get existing high-quality people
            people = get_db_manager().get_user_people(user_id, limit=100)
            people_context = [f"{p.name} ({p.role or 'Unknown role'}) at {p.company or 'Unknown company'}" 
                             for p in people if p.name and not self._is_non_human_contact(p.email_address or '')]
            
            # Get existing topics
            topics = get_db_manager().get_user_topics(user_id, limit=100)
            topic_context = [t.name for t in topics if t.is_official]
            
            return {
                'existing_projects': project_context[:10],  # Top 10 projects
                'key_contacts': people_context[:20],  # Top 20 human contacts
                'official_topics': topic_context[:15]  # Top 15 official topics
            }
        except Exception as e:
            logger.error(f"Failed to get user business context: {str(e)}")
            return {'existing_projects': [], 'key_contacts': [], 'official_topics': []}

    def _is_non_human_contact(self, email_address: str) -> bool:
        """Determine if an email address belongs to a non-human sender - BALANCED VERSION"""
        if not email_address:
            return True
            
        email_lower = email_address.lower()
        
        # FOCUSED: Only filter obvious automation, preserve business contacts
        definite_non_human_patterns = [
            'noreply', 'no-reply', 'donotreply', 'do-not-reply', 
            'mailer-daemon', 'postmaster@', 'daemon@', 'bounce@',
            'robot@', 'bot@', 'automated@', 'system@notification',
            'newsletter@', 'digest@', 'updates@notifications'
        ]
        
        # Check against definite non-human patterns only
        for pattern in definite_non_human_patterns:
            if pattern in email_lower:
                return True
        
        # SPECIFIC: Only filter major newsletter/automation services
        automation_domains = [
            'substack.com', 'beehiiv.com', 'mailchimp.com', 'constantcontact.com',
            'campaign-archive.com', 'sendgrid.net', 'mailgun.org', 'mandrill.com'
        ]
        
        for domain in automation_domains:
            if domain in email_lower:
                return True
        
        # PRESERVE: Keep business contacts that might use standard business email patterns
        # Removed: 'admin@', 'info@', 'contact@', 'help@', 'service@', 'team@', 'hello@', 'hi@'
        # Removed: 'linkedin.com', 'facebook.com', etc. - people use these for business
                
        return False

    def _filter_quality_emails_debug(self, emails: List[Email], user_email: str) -> List[Email]:
        """Enhanced filtering for quality-focused email processing - ULTRA PERMISSIVE DEBUG VERSION"""
        quality_emails = []
        
        for email in emails:
            logger.debug(f"Evaluating email from {email.sender} with subject: {email.subject}")
            
            # Skip emails from the user themselves - check both email and name
            if email.sender and user_email.lower() in email.sender.lower():
                logger.debug(f"Skipping email from user themselves: {email.sender}")
                continue
            
            # ULTRA PERMISSIVE: Accept almost all emails for debugging
            # Only skip completely empty emails
            content = email.body_clean or email.snippet or email.subject or ''
            if len(content.strip()) < 3:  # Ultra permissive - just need any content
                logger.debug(f"Skipping email with no content: {len(content)} chars")
                continue
                
            logger.debug(f"Email passed ultra-permissive quality filters: {email.sender}")
            quality_emails.append(email)
        
        logger.info(f"Quality filtering (DEBUG MODE): {len(quality_emails)} emails passed out of {len(emails)} total")
        return quality_emails

    def _is_obviously_non_human_contact(self, email_address: str) -> bool:
        """RELAXED: Only filter obviously non-human contacts - for debugging"""
        if not email_address:
            return True
            
        email_lower = email_address.lower()
        
        # Only the most obvious non-human patterns
        obvious_non_human_patterns = [
            'noreply', 'no-reply', 'donotreply', 'mailer-daemon',
            'postmaster@', 'daemon@', 'bounce@', 'automated@',
            'robot@', 'bot@'
        ]
        
        # Check against obvious non-human patterns only
        for pattern in obvious_non_human_patterns:
            if pattern in email_lower:
                logger.debug(f"Obvious non-human pattern detected: {pattern} in {email_address}")
                return True
                
        return False

    def _is_obvious_newsletter_or_promotional(self, email: Email) -> bool:
        """RELAXED: Only filter obvious newsletters - for debugging"""
        if not email:
            return True
            
        sender = (email.sender or '').lower()
        subject = (email.subject or '').lower()
        content = (email.body_clean or email.snippet or '').lower()
        
        # Only check for very obvious newsletter patterns
        obvious_newsletter_patterns = [
            'substack.com', 'mailchimp.com', 'beehiiv.com',
            'unsubscribe', 'view in browser', 'manage preferences'
        ]
        
        # Check domain patterns
        for pattern in obvious_newsletter_patterns:
            if pattern in sender or pattern in content:
                logger.debug(f"Obvious newsletter pattern detected: {pattern}")
                return True
                
        return False

    def _validate_analysis_quality_debug(self, analysis: Dict) -> bool:
        """Validate that the analysis meets quality standards - DEBUG VERSION (more permissive)"""
        try:
            # Check strategic value score - very relaxed threshold
            strategic_value = analysis.get('strategic_value_score', 0)
            if strategic_value < 0.3:  # Very relaxed - was 0.5
                logger.debug(f"Analysis rejected - low strategic value: {strategic_value}")
                return False
            
            # Check summary quality - very short minimum
            summary = analysis.get('summary', '')
            if len(summary) < 5:  # Very short minimum
                logger.debug(f"Analysis rejected - summary too short: {len(summary)} chars")
                return False
            
            # Very relaxed trivial content detection
            if len(summary) < 15 and summary.lower().strip() in ['ok', 'thanks', 'got it', 'noted']:
                logger.debug(f"Analysis rejected - trivial content detected: {summary}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating analysis quality: {str(e)}")
            return False
    
    # Helper methods for comprehensive relationship intelligence
    def _generate_communication_timeline_entry(self, email: Email) -> Dict:
        """Generate a timeline entry for this communication"""
        return {
            'date': email.email_date.isoformat() if email.email_date else None,
            'subject': email.subject,
            'summary': email.ai_summary[:100] + '...' if email.ai_summary and len(email.ai_summary) > 100 else email.ai_summary,
            'urgency': self._assess_email_urgency(email),
            'action_required': self._has_action_required(email),
            'business_category': self._categorize_communication_pattern(email)
        }
    
    def _assess_business_relevance(self, sender_analysis: Dict, email: Email) -> str:
        """Assess the business relevance of this relationship"""
        business_relevance = sender_analysis.get('business_relevance', '')
        if business_relevance:
            return business_relevance
        
        # Fallback assessment based on email content
        if self._is_strategic_communication(email):
            return 'high'
        elif sender_analysis.get('company'):
            return 'medium'
        else:
            return 'standard'
    
    def _calculate_strategic_value(self, sender_analysis: Dict, email: Email) -> float:
        """Calculate strategic value of this relationship"""
        value = 0.5  # Base value
        
        # Company factor
        if sender_analysis.get('company'):
            value += 0.2
        
        # Role factor
        role = sender_analysis.get('role', '').lower()
        if any(keyword in role for keyword in ['director', 'manager', 'ceo', 'founder', 'vp', 'head', 'lead']):
            value += 0.2
        
        # Strategic communication factor
        if self._is_strategic_communication(email):
            value += 0.3
        
        return min(1.0, value)
    
    def _assess_communication_frequency(self, existing_person) -> str:
        """Assess communication frequency pattern"""
        if not existing_person or not existing_person.total_emails:
            return 'new'
        
        total_emails = existing_person.total_emails
        if total_emails >= 20:
            return 'frequent'
        elif total_emails >= 5:
            return 'regular'
        elif total_emails >= 2:
            return 'occasional'
        else:
            return 'minimal'
    
    def _extract_strategic_topic_from_email(self, email: Email) -> str:
        """Extract the main strategic topic from email"""
        if email.subject:
            # Simple extraction of key terms
            subject_lower = email.subject.lower()
            strategic_keywords = ['project', 'meeting', 'proposal', 'partnership', 'deal', 'contract', 'strategy', 'funding', 'launch']
            for keyword in strategic_keywords:
                if keyword in subject_lower:
                    return keyword.capitalize()
        
        # Fallback to business category
        return self._categorize_communication_pattern(email)
    
    def _calculate_collaboration_score(self, sender_analysis: Dict, email: Email) -> float:
        """Calculate collaboration potential score"""
        score = 0.3  # Base score
        
        # Project involvement
        if any(word in (email.ai_summary or '').lower() for word in ['project', 'collaboration', 'work together', 'partnership']):
            score += 0.4
        
        # Role-based collaboration potential
        role = sender_analysis.get('role', '').lower()
        if any(keyword in role for keyword in ['manager', 'director', 'lead', 'coordinator']):
            score += 0.3
        
        return min(1.0, score)
    
    def _extract_expertise_areas(self, email: Email, sender_analysis: Dict) -> List[str]:
        """Extract areas of expertise from communication"""
        expertise_areas = []
        
        # From role
        role = sender_analysis.get('role', '')
        if role:
            expertise_areas.append(role)
        
        # From email content
        if email.ai_summary:
            technical_terms = ['AI', 'machine learning', 'technology', 'software', 'development', 'marketing', 'sales', 'finance', 'strategy']
            content_lower = email.ai_summary.lower()
            for term in technical_terms:
                if term.lower() in content_lower:
                    expertise_areas.append(term)
        
        return list(set(expertise_areas))[:3]  # Limit to top 3
    
    def _is_meeting_participant(self, email: Email) -> bool:
        """Check if this person is likely a meeting participant"""
        if email.subject:
            meeting_indicators = ['meeting', 'call', 'zoom', 'teams', 'conference', 'discussion']
            return any(indicator in email.subject.lower() for indicator in meeting_indicators)
        return False
    
    def _assess_communication_style(self, email: Email) -> str:
        """Assess communication style"""
        if email.subject:
            subject_lower = email.subject.lower()
            if any(word in subject_lower for word in ['urgent', 'asap', 'immediately']):
                return 'urgent'
            elif any(word in subject_lower for word in ['follow up', 'checking in', 'update']):
                return 'collaborative'
            elif any(word in subject_lower for word in ['meeting', 'call', 'discussion']):
                return 'meeting-focused'
        return 'professional'
    
    def _assess_email_urgency(self, email: Email) -> float:
        """Assess urgency of email communication"""
        if email.subject:
            urgent_keywords = ['urgent', 'asap', 'immediately', 'critical', 'emergency']
            subject_lower = email.subject.lower()
            if any(keyword in subject_lower for keyword in urgent_keywords):
                return 0.9
            elif any(keyword in subject_lower for keyword in ['important', 'priority']):
                return 0.7
        return 0.5  # Default moderate urgency
    
    def _extract_strategic_topics_list(self, email: Email) -> List[str]:
        """Extract list of strategic topics from email"""
        topics = []
        
        # From subject
        if email.subject:
            # Extract project names, company names, etc.
            words = email.subject.split()
            for word in words:
                if len(word) > 3 and word[0].isupper():  # Likely proper noun
                    topics.append(word)
        
        # From business categories
        category = self._categorize_communication_pattern(email)
        if category:
            topics.append(category)
        
        return list(set(topics))[:5]  # Limit to top 5
    
    def _categorize_communication_pattern(self, email: Email) -> str:
        """Categorize the communication pattern"""
        if email.subject:
            subject_lower = email.subject.lower()
            if any(word in subject_lower for word in ['meeting', 'call', 'zoom']):
                return 'meeting_coordination'
            elif any(word in subject_lower for word in ['project', 'task', 'deliverable']):
                return 'project_management'
            elif any(word in subject_lower for word in ['follow up', 'status', 'update']):
                return 'status_update'
            elif any(word in subject_lower for word in ['proposal', 'contract', 'agreement']):
                return 'business_development'
        return 'general_business'
    
    def _extract_project_involvement(self, email: Email, sender_analysis: Dict) -> List[Dict]:
        """Extract project involvement information"""
        projects = []
        
        if email.ai_summary:
            # Simple project detection
            summary_lower = email.ai_summary.lower()
            if 'project' in summary_lower:
                projects.append({
                    'project': 'Ongoing Project',
                    'email_date': email.email_date.isoformat() if email.email_date else None,
                    'role': 'collaborator',
                    'context': email.ai_summary[:100] + '...' if len(email.ai_summary) > 100 else email.ai_summary
                })
        
        return projects
    
    def _is_strategic_communication(self, email: Email) -> bool:
        """Check if this is a strategic communication"""
        if hasattr(email, 'strategic_importance') and email.strategic_importance:
            return email.strategic_importance > 0.7
        
        # Fallback analysis
        if email.subject:
            strategic_keywords = ['strategy', 'strategic', 'important', 'critical', 'partnership', 'deal', 'funding', 'board']
            return any(keyword in email.subject.lower() for keyword in strategic_keywords)
        
        return False
    
    def _format_last_strategic_communication(self, email: Email) -> Dict:
        """Format strategic communication details"""
        return {
            'date': email.email_date.isoformat() if email.email_date else None,
            'subject': email.subject,
            'summary': email.ai_summary,
            'importance': getattr(email, 'strategic_importance', 0.8),
            'category': self._categorize_communication_pattern(email),
            'action_required': self._has_action_required(email),
            'urgency': self._assess_email_urgency(email)
        }
    
    def _extract_key_decisions(self, analysis: Dict, email: Email) -> List[str]:
        """Extract key decisions from analysis"""
        decisions = []
        business_insights = analysis.get('business_insights', {})
        if isinstance(business_insights, dict):
            decisions.extend(business_insights.get('key_decisions', []))
        return decisions[:3]  # Limit to top 3
    
    def _extract_opportunities(self, analysis: Dict, email: Email) -> List[str]:
        """Extract opportunities from analysis"""
        opportunities = []
        business_insights = analysis.get('business_insights', {})
        if isinstance(business_insights, dict):
            opportunities.extend(business_insights.get('strategic_opportunities', []))
        return opportunities[:3]  # Limit to top 3
    
    def _extract_challenges(self, analysis: Dict, email: Email) -> List[str]:
        """Extract challenges from analysis"""
        challenges = []
        business_insights = analysis.get('business_insights', {})
        if isinstance(business_insights, dict):
            challenges.extend(business_insights.get('business_challenges', []))
        return challenges[:2]  # Limit to top 2
    
    def _extract_collaboration_projects(self, email: Email, analysis: Dict) -> List[str]:
        """Extract collaboration projects"""
        projects = []
        
        # From project analysis
        project_data = analysis.get('project', {})
        if project_data and project_data.get('name'):
            projects.append(project_data['name'])
        
        # From email content
        if email.subject and 'project' in email.subject.lower():
            projects.append(email.subject)
        
        return list(set(projects))[:3]
    
    def _extract_expertise_indicators(self, email: Email, sender_analysis: Dict) -> List[str]:
        """Extract expertise indicators"""
        indicators = []
        
        # From role
        role = sender_analysis.get('role', '')
        if role:
            indicators.append(role)
        
        # From company
        company = sender_analysis.get('company', '')
        if company:
            indicators.append(f"{company} expertise")
        
        return indicators[:2]
    
    def _calculate_meeting_frequency(self, email: Email) -> int:
        """Calculate meeting frequency indicator"""
        if self._is_meeting_participant(email):
            return 1
        return 0
    
    def _assess_response_reliability(self, existing_person) -> str:
        """Assess response reliability"""
        if not existing_person:
            return 'unknown'
        
        # Simple assessment based on email frequency
        if existing_person.total_emails and existing_person.total_emails >= 5:
            return 'reliable'
        elif existing_person.total_emails and existing_person.total_emails >= 2:
            return 'moderate'
        else:
            return 'limited'
    
    def _calculate_avg_email_importance(self, email: Email) -> float:
        """Calculate average email importance"""
        if hasattr(email, 'strategic_importance') and email.strategic_importance:
            return email.strategic_importance
        
        # Fallback calculation
        if self._is_strategic_communication(email):
            return 0.8
        else:
            return 0.5
    
    def _assess_relationship_trend(self, existing_person) -> str:
        """Assess relationship trend"""
        if not existing_person:
            return 'new'
        
        # Simple trend assessment
        if existing_person.total_emails and existing_person.total_emails >= 10:
            return 'stable'
        elif existing_person.total_emails and existing_person.total_emails >= 3:
            return 'growing'
        else:
            return 'developing'
    
    def _assess_engagement_level(self, email: Email, sender_analysis: Dict) -> str:
        """Assess engagement level"""
        # High engagement indicators
        if self._is_strategic_communication(email):
            return 'high'
        elif sender_analysis.get('company') and sender_analysis.get('role'):
            return 'medium'
        else:
            return 'standard'
    
    def _assess_communication_consistency(self, existing_person) -> str:
        """Assess communication consistency"""
        if not existing_person:
            return 'new'
        
        if existing_person.total_emails and existing_person.total_emails >= 15:
            return 'consistent'
        elif existing_person.total_emails and existing_person.total_emails >= 5:
            return 'regular'
        else:
            return 'sporadic'
    
    def _calculate_business_value_score(self, sender_analysis: Dict, email: Email) -> float:
        """Calculate business value score"""
        value = 0.3  # Base value
        
        # Strategic communication adds value
        if self._is_strategic_communication(email):
            value += 0.4
        
        # Company affiliation adds value
        if sender_analysis.get('company'):
            value += 0.2
        
        # Role authority adds value
        role = sender_analysis.get('role', '').lower()
        if any(keyword in role for keyword in ['director', 'manager', 'ceo', 'vp']):
            value += 0.3
        
        return min(1.0, value)
    
    def _calculate_collaboration_strength(self, email: Email, analysis: Dict) -> float:
        """Calculate collaboration strength"""
        strength = 0.2  # Base strength
        
        # Project involvement
        if analysis.get('project'):
            strength += 0.5
        
        # Meeting coordination
        if self._is_meeting_participant(email):
            strength += 0.3
        
        return min(1.0, strength)
    
    def _assess_decision_influence(self, analysis: Dict, email: Email) -> float:
        """Assess decision influence"""
        influence = 0.3  # Base influence
        
        # Key decisions mentioned
        business_insights = analysis.get('business_insights', {})
        if isinstance(business_insights, dict) and business_insights.get('key_decisions'):
            influence += 0.4
        
        # Strategic communication
        if self._is_strategic_communication(email):
            influence += 0.3
        
        return min(1.0, influence)
    
    def _assess_urgency_compatibility(self, email: Email) -> str:
        """Assess urgency compatibility"""
        urgency = self._assess_email_urgency(email)
        
        if urgency > 0.7:
            return 'high-urgency'
        elif urgency > 0.4:
            return 'moderate-urgency'
        else:
            return 'low-urgency'
    
    def _has_action_required(self, email: Email) -> bool:
        """Check if email has action required"""
        if hasattr(email, 'action_required') and email.action_required:
            return True
        
        # Fallback analysis
        if email.subject:
            action_keywords = ['please', 'need', 'require', 'action', 'respond', 'reply', 'confirm']
            return any(keyword in email.subject.lower() for keyword in action_keywords)
        
        return False

# Global instance
email_intelligence = EmailIntelligenceProcessor() 