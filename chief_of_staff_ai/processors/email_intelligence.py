# Enhanced Email Intelligence Processor using Claude 4 Sonnet

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import anthropic

from config.settings import settings
from models.database import get_db_manager, Email, Person, Project, Task, User

logger = logging.getLogger(__name__)

class EmailIntelligenceProcessor:
    """Advanced email intelligence using Claude 4 Sonnet for comprehensive understanding"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"
        self.version = "2.0"
        
    def process_user_emails_intelligently(self, user_email: str, limit: int = None, force_refresh: bool = False) -> Dict:
        """
        Intelligently process emails with comprehensive Claude analysis
        
        Args:
            user_email: Email of the user
            limit: Maximum number of emails to process
            force_refresh: Whether to re-process already analyzed emails
            
        Returns:
            Dictionary with comprehensive processing results
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get emails that need intelligent processing (only unreplied emails)
            emails = self._get_unreplied_emails(user.id, limit or 50, force_refresh)
            
            if not emails:
                return {
                    'success': True,
                    'user_email': user_email,
                    'processed_emails': 0,
                    'message': 'No unreplied emails need processing'
                }
            
            processed_count = 0
            insights_extracted = 0
            people_identified = 0
            projects_identified = 0
            tasks_created = 0
            
            for email in emails:
                try:
                    # Get comprehensive email analysis from Claude
                    analysis = self._get_comprehensive_email_analysis(email, user)
                    
                    if analysis:
                        # Update email with insights
                        self._update_email_with_insights(email, analysis)
                        
                        # Extract and update people information
                        if analysis.get('people'):
                            people_count = self._process_people_insights(user.id, analysis, email)
                            people_identified += people_count
                        
                        # Extract and update project information
                        if analysis.get('project'):
                            project = self._process_project_insights(user.id, analysis['project'], email)
                            if project:
                                projects_identified += 1
                                email.project_id = project.id
                        
                        # Extract specific tasks for the user
                        if analysis.get('tasks'):
                            tasks_count = self._process_intelligent_tasks(user.id, email.id, analysis['tasks'])
                            tasks_created += tasks_count
                        
                        insights_extracted += 1
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to intelligently process email {email.gmail_id}: {str(e)}")
                    continue
            
            logger.info(f"Intelligently processed {processed_count} emails for {user_email}")
            
            return {
                'success': True,
                'user_email': user_email,
                'processed_emails': processed_count,
                'insights_extracted': insights_extracted,
                'people_identified': people_identified,
                'projects_identified': projects_identified,
                'tasks_created': tasks_created,
                'processor_version': self.version
            }
            
        except Exception as e:
            logger.error(f"Failed intelligent email processing for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_unreplied_emails(self, user_id: int, limit: int, force_refresh: bool) -> List[Email]:
        """Get emails that the user hasn't replied to and need processing"""
        with get_db_manager().get_session() as session:
            query = session.query(Email).filter(
                Email.user_id == user_id,
                Email.body_clean.isnot(None)  # Already normalized
            )
            
            if not force_refresh:
                # Only process emails that don't have AI analysis yet
                query = query.filter(Email.ai_summary.is_(None))
            
            emails = query.order_by(Email.email_date.desc()).limit(limit).all()
            
            # Filter to only unreplied emails (basic heuristic)
            unreplied_emails = []
            for email in emails:
                if self._is_unreplied_email(email):
                    unreplied_emails.append(email)
            
            return unreplied_emails
    
    def _is_unreplied_email(self, email: Email) -> bool:
        """Determine if an email is unreplied using heuristics"""
        # If email is from the user themselves, skip
        user_email = get_db_manager().get_session().query(User).filter(
            User.id == email.user_id
        ).first().email
        
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
    
    def _get_comprehensive_email_analysis(self, email: Email, user) -> Optional[Dict]:
        """Get comprehensive email analysis from Claude"""
        try:
            email_context = self._prepare_enhanced_email_context(email, user)
            
            system_prompt = f"""You are an expert AI Chief of Staff that provides comprehensive email analysis for business intelligence and productivity.

Your task is to analyze the email and provide a structured analysis covering:

1. **EMAIL SUMMARY**: A clear, concise summary of what this email is about
2. **PEOPLE ANALYSIS**: Identify and analyze people mentioned, their roles, relationships, and any insights about them
3. **PROJECT CLASSIFICATION**: Determine if this relates to a specific project, initiative, or business area
4. **BUSINESS INSIGHTS**: Extract business intelligence, trends, decisions, or important information
5. **ACTION ITEMS**: Identify specific, actionable tasks for the recipient (focus on tasks assigned to "{user.email}")
6. **SENTIMENT & URGENCY**: Assess the tone and urgency level

Return a JSON object with this structure:
{{
    "summary": "Clear summary of the email content and purpose",
    "sender_analysis": {{
        "name": "Sender's name",
        "role": "Their role/title if mentioned",
        "company": "Their company if mentioned",
        "relationship": "Their relationship to recipient",
        "communication_style": "Analysis of their communication style",
        "importance_level": 0.8  // 0.0 to 1.0
    }},
    "people": [
        {{
            "name": "Person Name",
            "email": "their_email@example.com",
            "role": "Their role",
            "company": "Their company",
            "relationship": "colleague/client/vendor/etc",
            "insights": "Key insights about this person",
            "mentioned_context": "How they were mentioned in email"
        }}
    ],
    "project": {{
        "name": "Project or Initiative Name",
        "description": "What this project is about",
        "category": "business/client_work/internal/personal",
        "priority": "high/medium/low",
        "status": "active/planning/completed",
        "key_topics": ["topic1", "topic2"],
        "stakeholders": ["person1", "person2"]
    }},
    "business_insights": {{
        "key_decisions": ["Important decisions mentioned"],
        "trends": ["Business trends or patterns"],
        "opportunities": ["Opportunities identified"],
        "challenges": ["Challenges or issues mentioned"],
        "metrics": ["Any numbers, dates, or metrics mentioned"],
        "strategic_value": 0.7  // 0.0 to 1.0
    }},
    "tasks": [
        {{
            "description": "Specific actionable task for the recipient",
            "assignee": "{user.email}",
            "due_date": "2025-06-15",  // If mentioned
            "due_date_text": "by end of week",
            "priority": "high/medium/low",
            "category": "follow-up/deadline/meeting/review/decision",
            "confidence": 0.9,
            "source_text": "Original text that led to this task",
            "context": "Why this task is needed"
        }}
    ],
    "sentiment_score": 0.6,  // -1.0 (negative) to 1.0 (positive)
    "urgency_score": 0.8,    // 0.0 (not urgent) to 1.0 (very urgent)
    "action_required": true,
    "follow_up_required": false,
    "topics": ["main topic 1", "main topic 2"],
    "ai_category": "business_communication/meeting_coordination/project_update/client_communication/etc"
}}

Only extract tasks that are clearly directed at or relevant to the email recipient. Be specific and actionable."""

            user_prompt = f"""Please analyze this email comprehensively:

{email_context}

Focus on extracting meaningful business intelligence and actionable insights."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Parse JSON response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                analysis = json.loads(json_text)
                return analysis
            
            logger.warning(f"Could not parse Claude response for email {email.gmail_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get email analysis from Claude: {str(e)}")
            return None
    
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
    
    def _process_people_insights(self, user_id: int, analysis: Dict, email: Email) -> int:
        """Process and update people information"""
        people_count = 0
        
        # Process sender first
        sender_analysis = analysis.get('sender_analysis')
        if sender_analysis and email.sender:
            person_data = {
                'email_address': email.sender,
                'name': sender_analysis.get('name', email.sender_name or email.sender),
                'role': sender_analysis.get('role'),
                'company': sender_analysis.get('company'),
                'relationship_type': sender_analysis.get('relationship'),
                'communication_style': sender_analysis.get('communication_style'),
                'importance_level': sender_analysis.get('importance_level', 0.5),
                'ai_version': self.version
            }
            get_db_manager().create_or_update_person(user_id, person_data)
            people_count += 1
        
        # Process mentioned people
        people_data = analysis.get('people', [])
        if isinstance(people_data, list):
            for person_info in people_data:
                if person_info.get('email') or person_info.get('name'):
                    person_data = {
                        'email_address': person_info.get('email'),
                        'name': person_info['name'],
                        'role': person_info.get('role'),
                        'company': person_info.get('company'),
                        'relationship_type': person_info.get('relationship'),
                        'notes': person_info.get('insights'),
                        'ai_version': self.version
                    }
                    get_db_manager().create_or_update_person(user_id, person_data)
                    people_count += 1
        
        return people_count
    
    def _process_project_insights(self, user_id: int, project_data: Dict, email: Email) -> Optional[Project]:
        """Process and update project information"""
        if not project_data or not project_data.get('name'):
            return None
        
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
    
    def _process_intelligent_tasks(self, user_id: int, email_id: int, tasks_data: List[Dict]) -> int:
        """Process and save intelligent tasks"""
        tasks_count = 0
        
        for task_info in tasks_data:
            if task_info.get('description'):
                task_data = {
                    'description': task_info['description'],
                    'assignee': task_info.get('assignee'),
                    'due_date': self._parse_due_date(task_info.get('due_date')),
                    'due_date_text': task_info.get('due_date_text'),
                    'priority': task_info.get('priority', 'medium'),
                    'category': task_info.get('category', 'action_item'),
                    'confidence': task_info.get('confidence', 0.8),
                    'source_text': task_info.get('source_text'),
                    'status': 'pending',
                    'extractor_version': self.version,
                    'model_used': self.model
                }
                
                get_db_manager().save_task(user_id, email_id, task_data)
                tasks_count += 1
        
        return tasks_count
    
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
        """Get comprehensive business knowledge summary"""
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get all processed emails
            emails = get_db_manager().get_user_emails(user.id, limit=1000)
            projects = get_db_manager().get_user_projects(user.id)
            people = get_db_manager().get_user_people(user.id)
            
            # Compile business insights
            key_topics = set()
            decisions = []
            opportunities = []
            challenges = []
            
            for email in emails:
                if email.key_insights:
                    insights = email.key_insights
                    if isinstance(insights, dict):
                        decisions.extend(insights.get('key_decisions', []))
                        opportunities.extend(insights.get('opportunities', []))
                        challenges.extend(insights.get('challenges', []))
                
                if email.topics:
                    key_topics.update(email.topics)
            
            return {
                'success': True,
                'user_email': user_email,
                'business_knowledge': {
                    'total_emails_analyzed': len([e for e in emails if e.ai_summary]),
                    'key_topics': list(key_topics)[:20],  # Top 20 topics
                    'key_decisions': decisions[:10],  # Recent 10 decisions
                    'opportunities': opportunities[:10],
                    'challenges': challenges[:10],
                    'projects_count': len(projects),
                    'people_network_size': len(people),
                    'active_projects': len([p for p in projects if p.status == 'active'])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get business knowledge for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global instance
email_intelligence = EmailIntelligenceProcessor() 