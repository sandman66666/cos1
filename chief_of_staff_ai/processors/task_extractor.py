# Extract actionable tasks from emails using Claude 4 Sonnet

import json
import logging
from datetime import datetime, timedelta
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
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"
        self.version = "1.0"
        
    def extract_tasks_for_user(self, user_email: str, limit: int = None, force_refresh: bool = False) -> Dict:
        """
        Extract tasks from all normalized emails for a user
        
        Args:
            user_email: Email of the user
            limit: Maximum number of emails to process
            force_refresh: Whether to re-extract tasks for already processed emails
            
        Returns:
            Dictionary with extraction results
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
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
                logger.info(f"No emails to process for task extraction for {user_email}")
                return {
                    'success': True,
                    'user_email': user_email,
                    'processed_emails': 0,
                    'extracted_tasks': 0,
                    'message': 'No emails need task extraction'
                }
            
            processed_emails = 0
            total_tasks = 0
            error_count = 0
            
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
                        'priority_score': email.priority_score
                    }
                    
                    # Extract tasks from this email
                    extraction_result = self.extract_tasks_from_email(email_dict)
                    
                    if extraction_result['success'] and extraction_result['tasks']:
                        # Save tasks to database
                        for task_data in extraction_result['tasks']:
                            task_data['email_id'] = email.id
                            task_data['extractor_version'] = self.version
                            task_data['model_used'] = self.model
                            
                            get_db_manager().save_task(user.id, email.id, task_data)
                            total_tasks += 1
                    
                    processed_emails += 1
                    
                except Exception as e:
                    logger.error(f"Failed to extract tasks from email {email.gmail_id}: {str(e)}")
                    error_count += 1
                    continue
            
            logger.info(f"Extracted {total_tasks} tasks from {processed_emails} emails for {user_email} ({error_count} errors)")
            
            return {
                'success': True,
                'user_email': user_email,
                'processed_emails': processed_emails,
                'extracted_tasks': total_tasks,
                'errors': error_count,
                'extractor_version': self.version
            }
            
        except Exception as e:
            logger.error(f"Failed to extract tasks for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def extract_tasks_from_email(self, email_data: Dict) -> Dict:
        """
        Extract actionable tasks from a single email using Claude 4 Sonnet
        
        Args:
            email_data: Normalized email data dictionary
            
        Returns:
            Dictionary containing extracted tasks and metadata
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

            message = self.client.messages.create(
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

# Create global instance
task_extractor = TaskExtractor()