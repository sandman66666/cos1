# Enhanced Email Intelligence Processor using Claude 4 Sonnet

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import anthropic
import time

from config.settings import settings
from models.database import get_db_manager, Email, Person, Project, Task, User

logger = logging.getLogger(__name__)

class EmailIntelligenceProcessor:
    """Advanced email intelligence using Claude 4 Sonnet for comprehensive understanding"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"
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
3. **TASK IDENTIFICATION**: Find ANY actionable items or commitments mentioned
4. **BUSINESS INSIGHTS**: Extract any strategic value, opportunities, or challenges
5. **PROJECT CONTEXT**: Identify any work initiatives or business activities

**INCLUSIVE EXTRACTION GUIDELINES:**
- Extract people even if limited info is available (name + context is enough)
- Include tasks with clear actionable language, even if informal
- Capture business insights at any level (strategic, operational, or tactical)
- Process emails from colleagues, clients, partners, vendors - anyone professional
- Include follow-ups, scheduling, decisions, updates, and work discussions

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
    "topics": ["business topic 1", "work area 2"],
    "ai_category": "business_communication/client_work/project_coordination/operational"
}}

**IMPORTANT**: Extract value from most business emails. Only skip obvious spam or completely irrelevant content. Be generous with people extraction and task identification."""

            user_prompt = f"""Analyze this email comprehensively for business intelligence. Extract ALL valuable people, tasks, and insights:

{email_context}

Focus on building comprehensive business knowledge. Extract people and tasks generously - capture business value wherever it exists."""

            # Add timeout and retry protection
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    logger.info(f"Calling Claude API for comprehensive analysis of email {email.gmail_id}, attempt {attempt + 1}")
                    
                    message = self.client.messages.create(
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
    
    def _process_human_contacts_only(self, user_id: int, analysis: Dict, email: Email) -> int:
        """Process people information with human contact filtering and KNOWLEDGE ACCUMULATION"""
        people_count = 0
        
        # Process sender first (with human validation and knowledge accumulation)
        sender_analysis = analysis.get('sender_analysis')
        if (sender_analysis and email.sender and 
            sender_analysis.get('is_human_contact') and
            not self._is_non_human_contact(email.sender)):
            
            # Get existing person to accumulate knowledge
            existing_person = get_db_manager().find_person_by_email(user_id, email.sender)
            
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
            
            person_data = {
                'email_address': email.sender,
                'name': sender_analysis.get('name', email.sender_name or email.sender),
                'role': sender_analysis.get('role') or (existing_person.role if existing_person else None),
                'company': sender_analysis.get('company') or (existing_person.company if existing_person else None),
                'relationship_type': sender_analysis.get('relationship') or (existing_person.relationship_type if existing_person else None),
                'notes': accumulated_notes,  # Accumulated knowledge
                'importance_level': max(0.8, existing_person.importance_level if existing_person else 0.8),  # Increment importance
                'ai_version': self.version,
                'total_emails': (existing_person.total_emails if existing_person else 0) + 1  # Increment email count
            }
            get_db_manager().create_or_update_person(user_id, person_data)
            people_count += 1
        
        # Process mentioned people (with human validation and accumulation)
        people_data = analysis.get('people', [])
        if isinstance(people_data, list):
            for person_info in people_data:
                if (person_info.get('email') or person_info.get('name')) and person_info.get('business_relevance'):
                    # Additional human validation
                    email_addr = person_info.get('email', '')
                    if email_addr and self._is_non_human_contact(email_addr):
                        continue
                    
                    # Get existing person to accumulate knowledge
                    existing_person = None
                    if email_addr:
                        existing_person = get_db_manager().find_person_by_email(user_id, email_addr)
                    
                    # Accumulate knowledge
                    existing_notes = existing_person.notes if existing_person else ""
                    new_relevance = person_info.get('business_relevance', '')
                    
                    accumulated_notes = existing_notes
                    if new_relevance and new_relevance not in accumulated_notes:
                        if accumulated_notes:
                            accumulated_notes += f"\n\nMentioned Context: {new_relevance}"
                        else:
                            accumulated_notes = new_relevance
                    
                    person_data = {
                        'email_address': person_info.get('email'),
                        'name': person_info['name'],
                        'role': person_info.get('role') or (existing_person.role if existing_person else None),
                        'company': person_info.get('company') or (existing_person.company if existing_person else None),
                        'relationship_type': person_info.get('relationship') or (existing_person.relationship_type if existing_person else None),
                        'notes': accumulated_notes,  # Accumulated knowledge
                        'ai_version': self.version
                    }
                    get_db_manager().create_or_update_person(user_id, person_data)
                    people_count += 1
        
        return people_count
    
    def _process_high_quality_tasks(self, user_id: int, email_id: int, tasks_data: List[Dict]) -> int:
        """Process and save actionable tasks - VERY INCLUSIVE VERSION"""
        tasks_count = 0
        
        for task_info in tasks_data:
            # Validate task quality - very permissive
            if not task_info.get('description'):
                continue
            
            # VERY INCLUSIVE: Check confidence threshold - very low threshold
            confidence = task_info.get('confidence', 0.8)  # Default to 0.8 if missing
            if confidence < 0.3:  # Very low threshold
                continue
            
            # VERY INCLUSIVE: Check description length - very permissive
            description = task_info['description']
            if len(description) < 5:  # Very short minimum
                continue
            
            task_data = {
                'description': description,
                'assignee': task_info.get('assignee'),
                'due_date': self._parse_due_date(task_info.get('due_date')),
                'due_date_text': task_info.get('due_date_text'),
                'priority': task_info.get('priority', 'medium'),
                'category': task_info.get('category', 'action_item'),
                'confidence': confidence,
                'source_text': task_info.get('success_criteria', ''),
                'context': task_info.get('business_context', ''),
                'status': 'pending',
                'extractor_version': self.version,
                'model_used': self.model
            }
            
            get_db_manager().save_task(user_id, email_id, task_data)
            tasks_count += 1
            logger.info(f"Created task: {description[:50]}...")
        
        return tasks_count
    
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
- Recipients: {', '.join(email.recipients) if email.recipients else 'Not specified'}
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
                'official_topics': len([t for t in topics if t.is_official])
            }
            
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
                    ][:10]  # Top 10 substantial projects
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
    
    def _filter_quality_emails_debug(self, emails: List[Email], user_email: str) -> List[Email]:
        """Enhanced filtering for quality-focused email processing - DEBUG VERSION WITH RELAXED FILTERS"""
        quality_emails = []
        
        for email in emails:
            logger.debug(f"Evaluating email from {email.sender} with subject: {email.subject}")
            
            # Skip emails from the user themselves - check both email and name
            if email.sender and user_email.lower() in email.sender.lower():
                logger.debug(f"Skipping email from user themselves: {email.sender}")
                continue
            
            # Also check sender name to catch cases where user's name appears as sender
            user_name_parts = user_email.split('@')[0].lower()  # Get username part
            sender_name = (email.sender_name or '').lower()
            if (sender_name and len(user_name_parts) > 3 and 
                user_name_parts in sender_name.replace('.', '').replace('_', '')):
                logger.debug(f"Skipping email from user by name: {sender_name}")
                continue

            # RELAXED: Only skip the most obvious non-human senders
            if self._is_obviously_non_human_contact(email.sender or ''):
                logger.debug(f"Skipping obviously non-human sender: {email.sender}")
                continue
                
            # RELAXED: Skip only obvious newsletters and promotional content
            if self._is_obvious_newsletter_or_promotional(email):
                logger.debug(f"Skipping obvious newsletter/promotional content")
                continue
                
            # RELAXED: Very permissive content length - just need some content
            content = email.body_clean or email.snippet or ''
            if len(content.strip()) < 10:  # Very permissive
                logger.debug(f"Skipping email with minimal content: {len(content)} chars")
                continue
                
            # RELAXED: Only skip very obvious automated emails
            subject_lower = (email.subject or '').lower()
            automated_subjects = ['automated', 'automatic reply', 'out of office']
            if any(pattern in subject_lower for pattern in automated_subjects) and len(content) < 50:
                logger.debug(f"Skipping automated email with subject: {email.subject}")
                continue
                
            logger.debug(f"Email passed quality filters: {email.sender}")
            quality_emails.append(email)
        
        logger.info(f"Quality filtering: {len(quality_emails)} emails passed out of {len(emails)} total")
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
        """Validate that the analysis meets quality standards - VERY INCLUSIVE VERSION"""
        try:
            # VERY INCLUSIVE: Check strategic value score - very low threshold
            strategic_value = analysis.get('strategic_value_score', 0.7)  # Default to 0.7 if missing
            if strategic_value < 0.2:  # Only reject very low value
                logger.debug(f"Analysis rejected - very low strategic value: {strategic_value}")
                return False
            
            # VERY INCLUSIVE: Check summary quality - very reduced minimum length
            summary = analysis.get('summary', '')
            if len(summary) < 3:  # Almost any summary is acceptable
                logger.debug(f"Analysis rejected - summary too short: {len(summary)} chars")
                return False
            
            logger.debug(f"Analysis passed quality validation - strategic value: {strategic_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating analysis quality: {str(e)}")
            return True  # Default to accepting if validation fails

    def _process_human_contacts_only_debug(self, user_id: int, analysis: Dict, email: Email) -> int:
        """Process people information with RELAXED human contact filtering - DEBUG VERSION"""
        people_count = 0
        
        logger.debug(f"Processing contacts for email from {email.sender}")
        logger.debug(f"Analysis contains sender_analysis: {'sender_analysis' in analysis}")
        logger.debug(f"Analysis contains people: {'people' in analysis}")
        
        # Process sender first (with relaxed human validation)
        sender_analysis = analysis.get('sender_analysis')
        if sender_analysis and email.sender:
            logger.debug(f"Sender analysis: {sender_analysis}")
            
            # RELAXED: Don't require is_human_contact flag, infer from context
            is_human = (sender_analysis.get('is_human_contact', True) and  # Default to True
                       not self._is_obviously_non_human_contact(email.sender))
            
            if is_human:
                logger.debug(f"Processing sender as human contact: {email.sender}")
                
                # Get existing person to accumulate knowledge
                existing_person = get_db_manager().find_person_by_email(user_id, email.sender)
                
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
                
                person_data = {
                    'email_address': email.sender,
                    'name': sender_analysis.get('name', email.sender_name or email.sender),
                    'role': sender_analysis.get('role') or (existing_person.role if existing_person else None),
                    'company': sender_analysis.get('company') or (existing_person.company if existing_person else None),
                    'relationship_type': sender_analysis.get('relationship') or (existing_person.relationship_type if existing_person else None),
                    'notes': accumulated_notes,  # Accumulated knowledge
                    'importance_level': max(0.8, existing_person.importance_level if existing_person else 0.8),  # Increment importance
                    'ai_version': self.version,
                    'total_emails': (existing_person.total_emails if existing_person else 0) + 1  # Increment email count
                }
                get_db_manager().create_or_update_person(user_id, person_data)
                people_count += 1
                logger.info(f"Created/updated person: {person_data['name']} ({person_data['email_address']})")
            else:
                logger.debug(f"Sender not processed as human contact: {email.sender}")
        
        # Process mentioned people (with relaxed validation)
        people_data = analysis.get('people', [])
        if isinstance(people_data, list):
            logger.debug(f"Processing {len(people_data)} mentioned people")
            for person_info in people_data:
                if person_info.get('email') or person_info.get('name'):
                    # RELAXED: Additional human validation but more permissive
                    email_addr = person_info.get('email', '')
                    if email_addr and self._is_obviously_non_human_contact(email_addr):
                        logger.debug(f"Skipping obviously non-human mentioned person: {email_addr}")
                        continue
                    
                    # Get existing person to accumulate knowledge
                    existing_person = None
                    if email_addr:
                        existing_person = get_db_manager().find_person_by_email(user_id, email_addr)
                    
                    # Accumulate knowledge
                    existing_notes = existing_person.notes if existing_person else ""
                    new_relevance = person_info.get('business_relevance', '')
                    
                    accumulated_notes = existing_notes
                    if new_relevance and new_relevance not in accumulated_notes:
                        if accumulated_notes:
                            accumulated_notes += f"\n\nMentioned Context: {new_relevance}"
                        else:
                            accumulated_notes = new_relevance
                    
                    person_data = {
                        'email_address': person_info.get('email'),
                        'name': person_info['name'],
                        'role': person_info.get('role') or (existing_person.role if existing_person else None),
                        'company': person_info.get('company') or (existing_person.company if existing_person else None),
                        'relationship_type': person_info.get('relationship') or (existing_person.relationship_type if existing_person else None),
                        'notes': accumulated_notes,  # Accumulated knowledge
                        'ai_version': self.version
                    }
                    get_db_manager().create_or_update_person(user_id, person_data)
                    people_count += 1
                    logger.info(f"Created/updated mentioned person: {person_data['name']}")
        
        logger.info(f"Total people processed for this email: {people_count}")
        return people_count

    def _filter_quality_emails(self, emails: List[Email], user_email: str) -> List[Email]:
        """Enhanced filtering for quality-focused email processing - BUSINESS FOCUSED"""
        quality_emails = []
        
        for email in emails:
            # ENHANCED: Skip emails from the user themselves - check both email and name
            if email.sender and user_email.lower() in email.sender.lower():
                continue
            
            # ENHANCED: Also check sender name to catch cases where user's name appears as sender
            user_name_parts = user_email.split('@')[0].lower()  # Get username part
            sender_name = (email.sender_name or '').lower()
            if (sender_name and len(user_name_parts) > 3 and 
                user_name_parts in sender_name.replace('.', '').replace('_', '')):
                continue

            # Skip non-human senders
            if self._is_non_human_contact(email.sender or ''):
                continue
                
            # ENHANCED: Skip newsletters and promotional content
            if self._is_newsletter_or_promotional(email):
                continue
                
            # RELAXED: Reduced minimum content length from 50 to 25
            content = email.body_clean or email.snippet or ''
            if len(content.strip()) < 25:  # Much more permissive
                continue
                
            # RELAXED: More permissive automated subject filtering
            subject_lower = (email.subject or '').lower()
            automated_subjects = ['automatic', 'notification', 'alert']  # Removed 're:', 'fwd:', 'update', 'reminder'
            # Only skip if BOTH automated subject AND very short content
            if any(pattern in subject_lower for pattern in automated_subjects) and len(content) < 100:  # More lenient
                continue
                
            # EXPANDED: More business indicators to catch valuable emails
            business_indicators = [
                'meeting', 'project', 'proposal', 'contract', 'agreement',
                'decision', 'feedback', 'review', 'discussion', 'strategy',
                'client', 'customer', 'partner', 'collaboration', 'opportunity',
                'budget', 'funding', 'investment', 'deal', 'business',
                'follow up', 'followup', 'call', 'schedule', 'deadline',
                'urgent', 'important', 'action', 'update', 'progress',
                'team', 'work', 'development', 'launch', 'release'
            ]
            
            has_business_content = any(indicator in content.lower() or indicator in subject_lower 
                                     for indicator in business_indicators)
            
            # MORE INCLUSIVE: Accept if business content OR longer than 150 chars (reduced from 300)
            if has_business_content or len(content) > 150:
                quality_emails.append(email)
            # ADDED: Also include emails with meaningful sender names (not just email addresses)
            elif email.sender_name and len(email.sender_name) > 3 and len(content) > 50:
                quality_emails.append(email)
        
        # Sort by email date (newest first) and content length (longer = potentially more substantial)
        quality_emails.sort(key=lambda e: (e.email_date or datetime.min, len(e.body_clean or e.snippet or '')), reverse=True)
        
        return quality_emails

    def _is_newsletter_or_promotional(self, email: Email) -> bool:
        """Detect and filter out newsletters, promotional emails, and automated content"""
        if not email:
            return True
            
        sender = (email.sender or '').lower()
        subject = (email.subject or '').lower()
        content = (email.body_clean or email.snippet or '').lower()
        sender_name = (email.sender_name or '').lower()
        
        # Newsletter domains and patterns
        newsletter_domains = [
            'substack.com', 'mailchimp.com', 'constantcontact.com', 'campaign-archive.com',
            'beehiiv.com', 'ghost.org', 'medium.com', 'linkedin.com/pulse',
            'newsletter', 'mail.', 'noreply', 'no-reply', 'donotreply', 'marketing',
            'promotions', 'offers', 'deals', 'sales', 'campaigns'
        ]
        
        # Newsletter subject patterns
        newsletter_subjects = [
            'newsletter', 'weekly digest', 'daily digest', 'roundup', 'briefing',
            'this week in', 'weekly update', 'monthly update', 'startup digest',
            'tech digest', 'vc corner', 'venture capital', 'investment newsletter',
            'industry news', 'market update', 'funding round', 'startup funding'
        ]
        
        # Newsletter content patterns
        newsletter_content = [
            'unsubscribe', 'view in browser', 'manage preferences', 'update subscription',
            'forward to a friend', 'share this newsletter', 'subscriber', 'mailing list',
            'this email was sent to', 'you are receiving this', 'promotional email'
        ]
        
        # Newsletter sender name patterns
        newsletter_names = [
            'newsletter', 'digest', 'briefing', 'update', 'news', 'weekly',
            'daily', 'monthly', 'roundup', 'vc corner', 'startup', 'lenny',
            'substack', 'medium', 'ghost'
        ]
        
        # Check domain patterns
        for domain in newsletter_domains:
            if domain in sender:
                return True
        
        # Check subject patterns
        for pattern in newsletter_subjects:
            if pattern in subject:
                return True
            
        # Check content patterns
        for pattern in newsletter_content:
            if pattern in content:
                return True
        
        # Check sender name patterns
        for pattern in newsletter_names:
            if pattern in sender_name:
                return True
        
        # Additional heuristics for promotional content
        promotional_indicators = [
            'special offer', 'limited time', 'exclusive deal', 'discount',
            'sale ends', 'act now', 'don\'t miss', 'free trial', 'premium upgrade',
            'webinar invitation', 'event invitation', 'conference', 'summit'
        ]
        
        promotional_count = sum(1 for indicator in promotional_indicators 
                               if indicator in content or indicator in subject)
        
        # If multiple promotional indicators, likely promotional
        if promotional_count >= 2:
            return True
        
        # Check for mass email patterns
        mass_email_patterns = [
            'dear valued', 'dear customer', 'dear subscriber', 'dear member',
            'greetings', 'hello there', 'hi everyone', 'dear all'
        ]
        
        for pattern in mass_email_patterns:
            if pattern in content[:200]:  # Check first 200 chars
                return True
        
        return False

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

# Global instance
email_intelligence = EmailIntelligenceProcessor() 