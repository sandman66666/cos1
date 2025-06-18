# Extract actionable tasks from emails using Claude 4 Sonnet

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import re
from dateutil import parser
import anthropic

from config.settings import settings
from models.database import get_db_manager, Email, Task

logger = logging.getLogger(__name__)

class TaskExtractor:
    """Extracts actionable tasks from emails using Claude 4 Sonnet"""
    
    def __init__(self):
        from config.settings import settings
        
        self.claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL  # Now uses Claude 4 Opus from settings
        self.version = "1.0"
        
    def extract_tasks_for_user(self, user_email: str, limit: int = None, force_refresh: bool = False) -> Dict:
        """
        ENHANCED 360-CONTEXT TASK EXTRACTION
        
        Extract tasks with comprehensive business intelligence by cross-referencing:
        - Email communications & AI analysis
        - People relationships & interaction patterns
        - Project context & status
        - Calendar events & meeting intelligence
        - Topic analysis & business themes
        - Strategic decisions & opportunities
        
        Creates super relevant and actionable tasks with full business context
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # COMPREHENSIVE BUSINESS CONTEXT COLLECTION
            business_context = self._get_360_business_context(user.id)
            
            # Get normalized emails that need task extraction
            with get_db_manager().get_session() as session:
                query = session.query(Email).filter(
                    Email.user_id == user.id,
                    Email.body_clean.isnot(None)  # Already normalized
                )
                
                if not force_refresh:
                    # Only process emails that don't have tasks yet
                    query = query.filter(~session.query(Task).filter(
                        Task.email_id == Email.id
                    ).exists())
                
                emails = query.limit(limit or 50).all()
            
            if not emails:
                logger.info(f"No emails to process for 360-context task extraction for {user_email}")
                return {
                    'success': True,
                    'user_email': user_email,
                    'processed_emails': 0,
                    'extracted_tasks': 0,
                    'message': 'No emails need 360-context task extraction'
                }
            
            processed_emails = 0
            total_tasks = 0
            error_count = 0
            context_enhanced_tasks = 0
            
            for email in emails:
                try:
                    # Convert database email to dict for processing
                    email_dict = {
                        'id': email.gmail_id,
                        'subject': email.subject,
                        'sender': email.sender,
                        'sender_name': email.sender_name,
                        'body_clean': email.body_clean,
                        'body_preview': email.body_preview,
                        'timestamp': email.email_date,
                        'message_type': email.message_type,
                        'priority_score': email.priority_score,
                        'ai_summary': email.ai_summary,
                        'key_insights': email.key_insights,
                        'topics': email.topics
                    }
                    
                    # ENHANCED EXTRACTION with 360-context
                    extraction_result = self.extract_tasks_with_360_context(email_dict, business_context)
                    
                    if extraction_result['success'] and extraction_result['tasks']:
                        # Save tasks to database with enhanced context
                        for task_data in extraction_result['tasks']:
                            task_data['email_id'] = email.id
                            task_data['extractor_version'] = f"{self.version}_360_context"
                            task_data['model_used'] = self.model
                            
                            # Check if this task was context-enhanced
                            if task_data.get('context_enhanced'):
                                context_enhanced_tasks += 1
                            
                            get_db_manager().save_task(user.id, email.id, task_data)
                            total_tasks += 1
                    
                    processed_emails += 1
                    
                except Exception as e:
                    logger.error(f"Failed to extract 360-context tasks from email {email.gmail_id}: {str(e)}")
                    error_count += 1
                    continue
            
            logger.info(f"Extracted {total_tasks} tasks ({context_enhanced_tasks} context-enhanced) from {processed_emails} emails for {user_email} ({error_count} errors)")
            
            return {
                'success': True,
                'user_email': user_email,
                'processed_emails': processed_emails,
                'extracted_tasks': total_tasks,
                'context_enhanced_tasks': context_enhanced_tasks,
                'errors': error_count,
                'extractor_version': f"{self.version}_360_context"
            }
            
        except Exception as e:
            logger.error(f"Failed to extract 360-context tasks for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_360_business_context(self, user_id: int) -> Dict:
        """
        Collect comprehensive business intelligence context for task extraction
        """
        try:
            context = {
                'people': [],
                'projects': [],
                'topics': [],
                'calendar_events': [],
                'recent_decisions': [],
                'opportunities': [],
                'relationship_map': {},
                'project_map': {},
                'topic_keywords': {}
            }
            
            # Get business data
            people = get_db_manager().get_user_people(user_id, limit=100)
            projects = get_db_manager().get_user_projects(user_id, limit=50)
            topics = get_db_manager().get_user_topics(user_id, limit=50)
            calendar_events = get_db_manager().get_user_calendar_events(user_id, limit=50)
            emails = get_db_manager().get_user_emails(user_id, limit=100)
            
            # Process people for relationship context
            for person in people:
                if person.name and person.email_address:
                    person_info = {
                        'name': person.name,
                        'email': person.email_address,
                        'company': person.company,
                        'title': person.title,
                        'relationship': person.relationship_type,
                        'total_emails': person.total_emails or 0,
                        'importance': person.importance_level or 0.5
                    }
                    context['people'].append(person_info)
                    context['relationship_map'][person.email_address.lower()] = person_info
            
            # Process projects for context linking
            for project in projects:
                if project.name and project.status == 'active':
                    project_info = {
                        'name': project.name,
                        'description': project.description,
                        'status': project.status,
                        'priority': project.priority,
                        'stakeholders': project.stakeholders or []
                    }
                    context['projects'].append(project_info)
                    context['project_map'][project.name.lower()] = project_info
            
            # Process topics for keyword matching
            for topic in topics:
                if topic.name:
                    topic_info = {
                        'name': topic.name,
                        'description': topic.description,
                        'keywords': json.loads(topic.keywords) if topic.keywords else [],
                        'is_official': topic.is_official
                    }
                    context['topics'].append(topic_info)
                    # Build keyword map for topic detection
                    all_keywords = [topic.name.lower()] + [kw.lower() for kw in topic_info['keywords']]
                    for keyword in all_keywords:
                        if keyword not in context['topic_keywords']:
                            context['topic_keywords'][keyword] = []
                        context['topic_keywords'][keyword].append(topic_info)
            
            # Process calendar events for meeting context
            now = datetime.now(timezone.utc)
            upcoming_meetings = [e for e in calendar_events if e.start_time and e.start_time > now]
            for meeting in upcoming_meetings[:20]:  # Next 20 meetings
                meeting_info = {
                    'title': meeting.title,
                    'start_time': meeting.start_time,
                    'attendees': meeting.attendees or [],
                    'description': meeting.description
                }
                context['calendar_events'].append(meeting_info)
            
            # Extract recent decisions and opportunities from emails
            for email in emails[-30:]:  # Recent 30 emails
                if email.key_insights and isinstance(email.key_insights, dict):
                    decisions = email.key_insights.get('key_decisions', [])
                    context['recent_decisions'].extend(decisions[:2])  # Top 2 per email
                    
                    opportunities = email.key_insights.get('strategic_opportunities', [])
                    context['opportunities'].extend(opportunities[:2])  # Top 2 per email
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get 360-context for task extraction: {str(e)}")
            return {}
    
    def extract_tasks_with_360_context(self, email_data: Dict, business_context: Dict) -> Dict:
        """
        Extract actionable tasks with comprehensive 360-context intelligence
        
        Args:
            email_data: Normalized email data dictionary with AI analysis
            business_context: Comprehensive business intelligence context
            
        Returns:
            Dictionary containing extracted tasks with enhanced context
        """
        try:
            # Check if email has enough content for task extraction
            body_clean = email_data.get('body_clean', '')
            if not body_clean or len(body_clean.strip()) < 20:
                return {
                    'success': True,
                    'email_id': email_data.get('id'),
                    'tasks': [],
                    'reason': 'Email content too short for task extraction'
                }
            
            # Skip certain message types that unlikely contain tasks
            message_type = email_data.get('message_type', 'regular')
            if message_type in ['newsletter', 'automated']:
                return {
                    'success': True,
                    'email_id': email_data.get('id'),
                    'tasks': [],
                    'reason': f'Message type "{message_type}" skipped for task extraction'
                }
            
            # ANALYZE BUSINESS CONTEXT CONNECTIONS
            email_context = self._analyze_email_business_connections(email_data, business_context)
            
            # Prepare enhanced email context for Claude
            enhanced_email_context = self._prepare_360_email_context(email_data, email_context, business_context)
            
            # Call Claude for 360-context task extraction
            claude_response = self._call_claude_for_360_tasks(enhanced_email_context, email_context)
            
            if not claude_response:
                return {
                    'success': False,
                    'email_id': email_data.get('id'),
                    'error': 'Failed to get response from Claude for 360-context extraction'
                }
            
            # Parse Claude's response with context enhancement
            tasks = self._parse_claude_360_response(claude_response, email_data, email_context)
            
            # Enhance tasks with 360-context metadata
            enhanced_tasks = []
            for task in tasks:
                enhanced_task = self._enhance_task_with_360_context(task, email_data, email_context, business_context)
                enhanced_tasks.append(enhanced_task)
            
            return {
                'success': True,
                'email_id': email_data.get('id'),
                'tasks': enhanced_tasks,
                'extraction_metadata': {
                    'extracted_at': datetime.utcnow().isoformat(),
                    'extractor_version': f"{self.version}_360_context",
                    'model_used': self.model,
                    'email_priority': email_data.get('priority_score', 0.5),
                    'context_connections': email_context.get('connection_count', 0),
                    'business_intelligence_used': True
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to extract 360-context tasks from email {email_data.get('id', 'unknown')}: {str(e)}")
            return {
                'success': False,
                'email_id': email_data.get('id'),
                'error': str(e)
            }
    
    def _prepare_email_context(self, email_data: Dict) -> str:
        """
        Prepare email context for Claude task extraction
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            Formatted email context string
        """
        sender = email_data.get('sender_name') or email_data.get('sender', '')
        subject = email_data.get('subject', '')
        body = email_data.get('body_clean', '')
        timestamp = email_data.get('timestamp')
        
        # Format timestamp
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    timestamp = parser.parse(timestamp)
                date_str = timestamp.strftime('%Y-%m-%d %H:%M')
            except:
                date_str = 'Unknown date'
        else:
            date_str = 'Unknown date'
        
        context = f"""Email Details:
From: {sender}
Date: {date_str}
Subject: {subject}

Email Content:
{body}
"""
        return context
    
    def _call_claude_for_tasks(self, email_context: str) -> Optional[str]:
        """
        Call Claude 4 Sonnet to extract tasks from email
        
        Args:
            email_context: Formatted email context
            
        Returns:
            Claude's response or None if failed
        """
        try:
            system_prompt = """You are an expert AI assistant that extracts actionable tasks from emails. Your job is to identify specific tasks, action items, deadlines, and follow-ups from email content.

Please analyze the email and extract actionable tasks following these guidelines:

1. **Task Identification**: Look for:
   - Direct requests or assignments
   - Deadlines and due dates
   - Follow-up actions needed
   - Meetings to schedule or attend
   - Documents to review or create
   - Decisions to make
   - Items requiring response

2. **Task Details**: For each task, identify:
   - Clear description of what needs to be done
   - Who is responsible (assignee)
   - When it needs to be done (due date/deadline)
   - Priority level (high, medium, low)
   - Category (follow-up, deadline, meeting, review, etc.)

3. **Response Format**: Return a JSON array of tasks. Each task should have:
   - "description": Clear, actionable description
   - "assignee": Who should do this (if mentioned)
   - "due_date": Specific date if mentioned (YYYY-MM-DD format)
   - "due_date_text": Original due date text from email
   - "priority": high/medium/low based on urgency and importance
   - "category": type of task (follow-up, deadline, meeting, review, etc.)
   - "confidence": 0.0-1.0 confidence score
   - "source_text": Original text from email that led to this task

Return ONLY the JSON array. If no actionable tasks are found, return an empty array []."""

            user_prompt = f"""Please analyze this email and extract actionable tasks:

{email_context}

Remember to return only a JSON array of tasks, or an empty array [] if no actionable tasks are found."""

            message = self.claude_client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            response_text = message.content[0].text.strip()
            logger.debug(f"Claude response: {response_text}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to call Claude for task extraction: {str(e)}")
            return None
    
    def _parse_claude_response(self, response: str, email_data: Dict) -> List[Dict]:
        """
        Parse Claude's JSON response into task dictionaries
        
        Args:
            response: Claude's response text
            email_data: Original email data
            
        Returns:
            List of task dictionaries
        """
        try:
            # Try to find JSON in the response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON array found in Claude response")
                return []
            
            json_text = response[json_start:json_end]
            
            # Parse JSON
            tasks_data = json.loads(json_text)
            
            if not isinstance(tasks_data, list):
                logger.warning("Claude response is not a JSON array")
                return []
            
            tasks = []
            for task_data in tasks_data:
                if isinstance(task_data, dict) and task_data.get('description'):
                    tasks.append(task_data)
            
            logger.info(f"Parsed {len(tasks)} tasks from Claude response")
            return tasks
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {str(e)}")
            logger.error(f"Response was: {response}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {str(e)}")
            return []
    
    def _enhance_task(self, task: Dict, email_data: Dict) -> Dict:
        """
        Enhance task with additional metadata and processing
        
        Args:
            task: Task dictionary from Claude
            email_data: Original email data
            
        Returns:
            Enhanced task dictionary
        """
        try:
            # Start with Claude's task data
            enhanced_task = task.copy()
            
            # Parse due date if provided
            if task.get('due_date'):
                try:
                    # Try to parse various date formats
                    due_date = parser.parse(task['due_date'])
                    enhanced_task['due_date'] = due_date
                except:
                    # If parsing fails, try to extract from due_date_text
                    enhanced_task['due_date'] = self._extract_date_from_text(
                        task.get('due_date_text', '')
                    )
            elif task.get('due_date_text'):
                enhanced_task['due_date'] = self._extract_date_from_text(task['due_date_text'])
            
            # Set default values
            enhanced_task['priority'] = task.get('priority', 'medium').lower()
            enhanced_task['category'] = task.get('category', 'action_item')
            enhanced_task['confidence'] = min(1.0, max(0.0, task.get('confidence', 0.8)))
            enhanced_task['status'] = 'pending'
            
            # Determine assignee context
            if not enhanced_task.get('assignee'):
                # If no specific assignee mentioned, assume it's for the email recipient
                enhanced_task['assignee'] = 'me'
            
            # Enhance priority based on email priority and urgency
            email_priority = email_data.get('priority_score', 0.5)
            if email_priority > 0.8:
                if enhanced_task['priority'] == 'medium':
                    enhanced_task['priority'] = 'high'
            
            # Add contextual category if not specified
            if enhanced_task['category'] == 'action_item':
                enhanced_task['category'] = self._determine_category(
                    enhanced_task['description'], 
                    email_data
                )
            
            return enhanced_task
            
        except Exception as e:
            logger.error(f"Failed to enhance task: {str(e)}")
            return task
    
    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """
        Extract date from text using various patterns
        
        Args:
            text: Text that might contain a date
            
        Returns:
            Parsed datetime or None
        """
        if not text:
            return None
        
        try:
            # Try direct parsing first
            return parser.parse(text, fuzzy=True)
        except:
            pass
        
        # Try common patterns
        patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{1,2}-\d{1,2}-\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})',
            r'(next\s+\w+)',
            r'(tomorrow)',
            r'(today)',
            r'(this\s+week)',
            r'(next\s+week)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    return parser.parse(match.group(1), fuzzy=True)
                except:
                    continue
        
        return None
    
    def _determine_category(self, description: str, email_data: Dict) -> str:
        """
        Determine task category based on description and email context
        
        Args:
            description: Task description
            email_data: Email context
            
        Returns:
            Task category
        """
        description_lower = description.lower()
        subject = email_data.get('subject', '').lower()
        
        # Meeting-related tasks
        if any(keyword in description_lower for keyword in ['meeting', 'call', 'schedule', 'zoom', 'teams']):
            return 'meeting'
        
        # Review tasks
        if any(keyword in description_lower for keyword in ['review', 'check', 'look at', 'examine']):
            return 'review'
        
        # Response tasks
        if any(keyword in description_lower for keyword in ['reply', 'respond', 'answer', 'get back']):
            return 'follow-up'
        
        # Document tasks
        if any(keyword in description_lower for keyword in ['document', 'report', 'write', 'create', 'draft']):
            return 'document'
        
        # Decision tasks
        if any(keyword in description_lower for keyword in ['decide', 'choose', 'approve', 'confirm']):
            return 'decision'
        
        # Deadline tasks
        if any(keyword in description_lower for keyword in ['deadline', 'due', 'submit', 'deliver']):
            return 'deadline'
        
        return 'action_item'
    
    def get_user_tasks(self, user_email: str, status: str = None, limit: int = None) -> Dict:
        """
        Get extracted tasks for a user
        
        Args:
            user_email: Email of the user
            status: Filter by task status (pending, in_progress, completed)
            limit: Maximum number of tasks to return
            
        Returns:
            Dictionary with user tasks
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            tasks = get_db_manager().get_user_tasks(user.id, status)
            
            if limit:
                tasks = tasks[:limit]
            
            return {
                'success': True,
                'user_email': user_email,
                'tasks': [task.to_dict() for task in tasks],
                'count': len(tasks),
                'status_filter': status
            }
            
        except Exception as e:
            logger.error(f"Failed to get tasks for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_task_status(self, user_email: str, task_id: int, status: str) -> Dict:
        """
        Update task status
        
        Args:
            user_email: Email of the user
            task_id: ID of the task to update
            status: New status (pending, in_progress, completed, cancelled)
            
        Returns:
            Dictionary with update result
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            with get_db_manager().get_session() as session:
                task = session.query(Task).filter(
                    Task.id == task_id,
                    Task.user_id == user.id
                ).first()
                
                if not task:
                    return {'success': False, 'error': 'Task not found'}
                
                task.status = status
                task.updated_at = datetime.utcnow()
                
                if status == 'completed':
                    task.completed_at = datetime.utcnow()
                
                session.commit()
                
                return {
                    'success': True,
                    'task_id': task_id,
                    'new_status': status,
                    'updated_at': task.updated_at.isoformat()
                }
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id} for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _analyze_email_business_connections(self, email_data: Dict, business_context: Dict) -> Dict:
        """
        Analyze connections between email and business intelligence context
        """
        try:
            connections = {
                'related_people': [],
                'related_projects': [],
                'related_topics': [],
                'related_meetings': [],
                'connection_count': 0,
                'context_strength': 0.0
            }
            
            sender_email = email_data.get('sender', '').lower()
            subject = (email_data.get('subject') or '').lower()
            body = (email_data.get('body_clean') or '').lower()
            ai_summary = (email_data.get('ai_summary') or '').lower()
            email_topics = email_data.get('topics') or []
            
            # Find related people
            if sender_email in business_context.get('relationship_map', {}):
                person_info = business_context['relationship_map'][sender_email]
                connections['related_people'].append(person_info)
                connections['connection_count'] += 1
                connections['context_strength'] += person_info.get('importance', 0.5)
            
            # Find related projects
            for project_name, project_info in business_context.get('project_map', {}).items():
                if (project_name in subject or project_name in body or project_name in ai_summary):
                    connections['related_projects'].append(project_info)
                    connections['connection_count'] += 1
                    connections['context_strength'] += 0.8  # High value for project connection
            
            # Find related topics
            for topic in email_topics:
                topic_lower = topic.lower()
                if topic_lower in business_context.get('topic_keywords', {}):
                    topic_infos = business_context['topic_keywords'][topic_lower]
                    connections['related_topics'].extend(topic_infos)
                    connections['connection_count'] += len(topic_infos)
                    connections['context_strength'] += 0.6 * len(topic_infos)
            
            # Find related upcoming meetings
            for meeting in business_context.get('calendar_events', []):
                meeting_attendees = meeting.get('attendees', [])
                meeting_title = meeting.get('title', '').lower()
                
                # Check if sender is in meeting attendees
                if any(att.get('email', '').lower() == sender_email for att in meeting_attendees):
                    connections['related_meetings'].append(meeting)
                    connections['connection_count'] += 1
                    connections['context_strength'] += 0.7
                
                # Check if meeting title relates to email subject/content
                if any(keyword in meeting_title for keyword in subject.split() + body.split()[:20] if len(keyword) > 3):
                    if meeting not in connections['related_meetings']:
                        connections['related_meetings'].append(meeting)
                        connections['connection_count'] += 1
                        connections['context_strength'] += 0.5
            
            # Normalize context strength
            connections['context_strength'] = min(1.0, connections['context_strength'] / max(1, connections['connection_count']))
            
            return connections
            
        except Exception as e:
            logger.error(f"Failed to analyze email business connections: {str(e)}")
            return {'related_people': [], 'related_projects': [], 'related_topics': [], 'related_meetings': [], 'connection_count': 0, 'context_strength': 0.0}
    
    def _prepare_360_email_context(self, email_data: Dict, email_context: Dict, business_context: Dict) -> str:
        """
        Prepare comprehensive email context with business intelligence for Claude
        """
        try:
            sender = email_data.get('sender_name') or email_data.get('sender', '')
            subject = email_data.get('subject', '')
            body = email_data.get('body_clean', '')
            ai_summary = email_data.get('ai_summary', '')
            timestamp = email_data.get('timestamp')
            
            # Format timestamp
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        timestamp = parser.parse(timestamp)
                    date_str = timestamp.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = 'Unknown date'
            else:
                date_str = 'Unknown date'
            
            # Build business context summary
            context_elements = []
            
            # Add people context
            if email_context['related_people']:
                people_info = []
                for person in email_context['related_people']:
                    people_info.append(f"{person['name']} ({person.get('company', 'Unknown company')}) - {person.get('total_emails', 0)} previous interactions")
                context_elements.append(f"RELATED PEOPLE: {'; '.join(people_info)}")
            
            # Add project context
            if email_context['related_projects']:
                project_info = []
                for project in email_context['related_projects']:
                    project_info.append(f"{project['name']} (Status: {project.get('status', 'Unknown')}, Priority: {project.get('priority', 'Unknown')})")
                context_elements.append(f"RELATED PROJECTS: {'; '.join(project_info)}")
            
            # Add topic context
            if email_context['related_topics']:
                topic_names = [topic['name'] for topic in email_context['related_topics'] if topic.get('is_official')]
                if topic_names:
                    context_elements.append(f"RELATED BUSINESS TOPICS: {', '.join(topic_names)}")
            
            # Add meeting context
            if email_context['related_meetings']:
                meeting_info = []
                for meeting in email_context['related_meetings']:
                    meeting_date = meeting['start_time'].strftime('%Y-%m-%d %H:%M') if meeting.get('start_time') else 'TBD'
                    meeting_info.append(f"{meeting['title']} ({meeting_date})")
                context_elements.append(f"RELATED UPCOMING MEETINGS: {'; '.join(meeting_info)}")
            
            # Add strategic insights
            if business_context.get('recent_decisions'):
                recent_decisions = business_context['recent_decisions'][:3]
                context_elements.append(f"RECENT BUSINESS DECISIONS: {'; '.join(recent_decisions)}")
            
            if business_context.get('opportunities'):
                opportunities = business_context['opportunities'][:3]
                context_elements.append(f"STRATEGIC OPPORTUNITIES: {'; '.join(opportunities)}")
            
            business_intelligence = '\n'.join(context_elements) if context_elements else "No specific business context identified."
            
            enhanced_context = f"""Email Details:
From: {sender}
Date: {date_str}
Subject: {subject}

AI Summary: {ai_summary}

Email Content:
{body}

BUSINESS INTELLIGENCE CONTEXT:
{business_intelligence}

Context Strength: {email_context.get('context_strength', 0.0):.2f} (0.0 = no context, 1.0 = highly connected)
"""
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Failed to prepare 360-context email: {str(e)}")
            return self._prepare_email_context(email_data)
    
    def _call_claude_for_360_tasks(self, enhanced_email_context: str, email_context: Dict) -> Optional[str]:
        """
        Call Claude 4 Sonnet for 360-context task extraction with business intelligence
        """
        try:
            context_strength = email_context.get('context_strength', 0.0)
            connection_count = email_context.get('connection_count', 0)
            
            system_prompt = f"""You are an expert AI Chief of Staff that extracts actionable tasks from emails using comprehensive business intelligence context. You have access to the user's complete business ecosystem including relationships, projects, topics, and strategic insights.

BUSINESS INTELLIGENCE CAPABILITIES:
- Cross-reference people relationships and interaction history
- Connect tasks to active projects and strategic initiatives  
- Leverage topic analysis and business themes
- Consider upcoming meetings and calendar context
- Incorporate recent business decisions and opportunities

ENHANCED TASK EXTRACTION GUIDELINES:

1. **360-Context Task Identification**: Look for tasks that:
   - Connect to the business relationships and projects mentioned
   - Align with strategic opportunities and recent decisions
   - Prepare for upcoming meetings with related attendees
   - Advance active projects and business initiatives
   - Leverage the full business context for maximum relevance

2. **Business-Aware Task Details**: For each task, provide:
   - Clear, actionable description with business context
   - Connect to specific people, projects, or meetings when relevant
   - Priority based on business importance and relationships
   - Category that reflects business context (project_work, relationship_management, strategic_planning, etc.)
   - Due dates that consider business timing and meeting schedules

3. **Context Enhancement Indicators**: 
   - Mark tasks as "context_enhanced": true if they leverage business intelligence
   - Include "business_context" field explaining the connection
   - Add "stakeholders" field if specific people are involved
   - Include "project_connection" if tied to active projects

Current Email Context Strength: {context_strength:.2f} ({connection_count} business connections identified)

RESPONSE FORMAT: Return a JSON array of tasks. Each task should have:
- "description": Clear, actionable description with business context
- "assignee": Who should do this (considering business relationships)
- "due_date": Specific date if mentioned (YYYY-MM-DD format)
- "due_date_text": Original due date text from email
- "priority": high/medium/low (elevated if high business context)
- "category": business-aware category (project_work, relationship_management, meeting_prep, strategic_planning, etc.)
- "confidence": 0.0-1.0 confidence score (higher with business context)
- "source_text": Original text from email that led to this task
- "context_enhanced": true/false (true if business intelligence was used)
- "business_context": Explanation of business connections (if context_enhanced)
- "stakeholders": List of relevant people from business context
- "project_connection": Name of related project if applicable

Return ONLY the JSON array. If no actionable tasks are found, return an empty array []."""

            user_prompt = f"""Please analyze this email with full business intelligence context and extract actionable tasks:

{enhanced_email_context}

Focus on tasks that leverage the business context for maximum relevance and strategic value. Consider the relationships, projects, meetings, and strategic insights provided."""

            message = self.claude_client.messages.create(
                model=self.model,
                max_tokens=3000,  # More tokens for detailed context
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            response_text = message.content[0].text.strip()
            logger.debug(f"Claude 360-context response: {response_text}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to call Claude for 360-context task extraction: {str(e)}")
            return None
    
    def _parse_claude_360_response(self, response: str, email_data: Dict, email_context: Dict) -> List[Dict]:
        """
        Parse Claude's 360-context JSON response into enhanced task dictionaries
        """
        try:
            # Try to find JSON in the response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON array found in Claude 360-context response")
                return []
            
            json_text = response[json_start:json_end]
            
            # Parse JSON
            tasks_data = json.loads(json_text)
            
            if not isinstance(tasks_data, list):
                logger.warning("Claude 360-context response is not a JSON array")
                return []
            
            tasks = []
            for task_data in tasks_data:
                if isinstance(task_data, dict) and task_data.get('description'):
                    # Validate 360-context fields
                    if task_data.get('context_enhanced') and not task_data.get('business_context'):
                        task_data['business_context'] = f"Connected to {email_context.get('connection_count', 0)} business elements"
                    
                    tasks.append(task_data)
            
            logger.info(f"Parsed {len(tasks)} 360-context tasks from Claude response")
            return tasks
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude 360-context JSON response: {str(e)}")
            logger.error(f"Response was: {response}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse Claude 360-context response: {str(e)}")
            return []
    
    def _enhance_task_with_360_context(self, task: Dict, email_data: Dict, email_context: Dict, business_context: Dict) -> Dict:
        """
        Enhance task with comprehensive 360-context metadata and business intelligence
        """
        try:
            # Start with Claude's task data
            enhanced_task = task.copy()
            
            # Parse due date if provided
            if task.get('due_date'):
                try:
                    due_date = parser.parse(task['due_date'])
                    enhanced_task['due_date'] = due_date
                except:
                    enhanced_task['due_date'] = self._extract_date_from_text(
                        task.get('due_date_text', '')
                    )
            elif task.get('due_date_text'):
                enhanced_task['due_date'] = self._extract_date_from_text(task['due_date_text'])
            
            # Set default values with 360-context awareness
            enhanced_task['priority'] = task.get('priority', 'medium').lower()
            enhanced_task['category'] = task.get('category', 'action_item')
            enhanced_task['confidence'] = min(1.0, max(0.0, task.get('confidence', 0.8)))
            enhanced_task['status'] = 'pending'
            
            # Enhance based on business context strength
            context_strength = email_context.get('context_strength', 0.0)
            if context_strength > 0.7:  # High context strength
                if enhanced_task['priority'] == 'medium':
                    enhanced_task['priority'] = 'high'
                enhanced_task['confidence'] = min(1.0, enhanced_task['confidence'] + 0.1)
            
            # Determine assignee with business context
            if not enhanced_task.get('assignee'):
                # Check if specific people are mentioned in business context
                related_people = email_context.get('related_people', [])
                if related_people and len(related_people) == 1:
                    enhanced_task['assignee'] = related_people[0]['name']
                else:
                    enhanced_task['assignee'] = 'me'
            
            # Enhance category with business context
            if enhanced_task['category'] == 'action_item':
                enhanced_task['category'] = self._determine_360_category(
                    enhanced_task['description'], 
                    email_data,
                    email_context
                )
            
            # Add 360-context specific fields
            if task.get('context_enhanced'):
                enhanced_task['context_enhanced'] = True
                enhanced_task['business_context'] = task.get('business_context', 'Business intelligence context applied')
                enhanced_task['context_strength'] = context_strength
                enhanced_task['connection_count'] = email_context.get('connection_count', 0)
            
            # Add stakeholder information
            stakeholders = task.get('stakeholders', [])
            if not stakeholders and email_context.get('related_people'):
                stakeholders = [person['name'] for person in email_context['related_people']]
            enhanced_task['stakeholders'] = stakeholders
            
            # Add project connection
            if task.get('project_connection'):
                enhanced_task['project_connection'] = task['project_connection']
            elif email_context.get('related_projects'):
                enhanced_task['project_connection'] = email_context['related_projects'][0]['name']
            
            return enhanced_task
            
        except Exception as e:
            logger.error(f"Failed to enhance task with 360-context: {str(e)}")
            return task
    
    def _determine_360_category(self, description: str, email_data: Dict, email_context: Dict) -> str:
        """
        Determine task category with 360-context business intelligence
        """
        try:
            description_lower = description.lower()
            subject = email_data.get('subject', '').lower()
            
            # Business context-aware categorization
            if email_context.get('related_projects'):
                return 'project_work'
            
            if email_context.get('related_meetings'):
                return 'meeting_prep'
            
            if email_context.get('related_people') and len(email_context['related_people']) > 0:
                person = email_context['related_people'][0]
                if person.get('importance', 0) > 0.7:
                    return 'relationship_management'
            
            # Strategic context
            if any(keyword in description_lower for keyword in ['strategy', 'strategic', 'decision', 'opportunity']):
                return 'strategic_planning'
            
            # Default categorization with business awareness
            if any(keyword in description_lower for keyword in ['meeting', 'call', 'schedule', 'zoom', 'teams']):
                return 'meeting'
            
            if any(keyword in description_lower for keyword in ['review', 'check', 'look at', 'examine']):
                return 'review'
            
            if any(keyword in description_lower for keyword in ['reply', 'respond', 'answer', 'get back']):
                return 'follow-up'
            
            if any(keyword in description_lower for keyword in ['document', 'report', 'write', 'create', 'draft']):
                return 'document'
            
            if any(keyword in description_lower for keyword in ['decide', 'choose', 'approve', 'confirm']):
                return 'decision'
            
            if any(keyword in description_lower for keyword in ['deadline', 'due', 'submit', 'deliver']):
                return 'deadline'
            
            return 'action_item'
            
        except Exception as e:
            logger.error(f"Failed to determine 360-context category: {str(e)}")
            return 'action_item'
    
    def extract_tasks_from_email(self, email_data: Dict) -> Dict:
        """
        LEGACY METHOD: Extract actionable tasks from a single email using Claude 4 Sonnet
        This method is kept for backward compatibility but users should use extract_tasks_with_360_context
        """
        try:
            logger.warning("Using legacy task extraction - consider upgrading to 360-context extraction")
            
            # Check if email has enough content for task extraction
            body_clean = email_data.get('body_clean', '')
            if not body_clean or len(body_clean.strip()) < 20:
                return {
                    'success': True,
                    'email_id': email_data.get('id'),
                    'tasks': [],
                    'reason': 'Email content too short for task extraction'
                }
            
            # Skip certain message types that unlikely contain tasks
            message_type = email_data.get('message_type', 'regular')
            if message_type in ['newsletter', 'automated']:
                return {
                    'success': True,
                    'email_id': email_data.get('id'),
                    'tasks': [],
                    'reason': f'Message type "{message_type}" skipped for task extraction'
                }
            
            # Prepare email context for Claude
            email_context = self._prepare_email_context(email_data)
            
            # Call Claude for task extraction
            claude_response = self._call_claude_for_tasks(email_context)
            
            if not claude_response:
                return {
                    'success': False,
                    'email_id': email_data.get('id'),
                    'error': 'Failed to get response from Claude'
                }
            
            # Parse Claude's response
            tasks = self._parse_claude_response(claude_response, email_data)
            
            # Enhance tasks with additional metadata
            enhanced_tasks = []
            for task in tasks:
                enhanced_task = self._enhance_task(task, email_data)
                enhanced_tasks.append(enhanced_task)
            
            return {
                'success': True,
                'email_id': email_data.get('id'),
                'tasks': enhanced_tasks,
                'extraction_metadata': {
                    'extracted_at': datetime.utcnow().isoformat(),
                    'extractor_version': self.version,
                    'model_used': self.model,
                    'email_priority': email_data.get('priority_score', 0.5)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to extract tasks from email {email_data.get('id', 'unknown')}: {str(e)}")
            return {
                'success': False,
                'email_id': email_data.get('id'),
                'error': str(e)
            }

# Create global instance
task_extractor = TaskExtractor()