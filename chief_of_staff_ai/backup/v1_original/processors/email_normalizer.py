# Normalizes raw Gmail data into clean format

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
from html import unescape
from bs4 import BeautifulSoup

from models.database import get_db_manager, Email

logger = logging.getLogger(__name__)

class EmailNormalizer:
    """Normalizes emails into clean, standardized format with entity extraction"""
    
    def __init__(self):
        self.version = "1.0"
        
    def normalize_user_emails(self, user_email: str, limit: int = None) -> Dict:
        """
        Normalize all emails for a user that haven't been normalized yet
        
        Args:
            user_email: Email of the user
            limit: Maximum number of emails to process
            
        Returns:
            Dictionary with normalization results
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get emails that need normalization
            with get_db_manager().get_session() as session:
                emails = session.query(Email).filter(
                    Email.user_id == user.id,
                    Email.body_clean.is_(None)  # Not normalized yet
                ).limit(limit or 100).all()
            
            if not emails:
                logger.info(f"No emails to normalize for {user_email}")
                return {
                    'success': True,
                    'user_email': user_email,
                    'processed': 0,
                    'message': 'No emails need normalization'
                }
            
            processed_count = 0
            error_count = 0
            
            for email in emails:
                try:
                    # Convert database email to dict for processing
                    email_dict = {
                        'id': email.gmail_id,
                        'subject': email.subject,
                        'body_text': email.body_text,
                        'body_html': email.body_html,
                        'sender': email.sender,
                        'sender_name': email.sender_name,
                        'snippet': email.snippet,
                        'timestamp': email.email_date
                    }
                    
                    # Normalize the email
                    normalized = self.normalize_email(email_dict)
                    
                    # Update the database record
                    with get_db_manager().get_session() as session:
                        email_record = session.query(Email).filter(
                            Email.user_id == user.id,
                            Email.gmail_id == email.gmail_id
                        ).first()
                        
                        if email_record:
                            email_record.body_clean = normalized.get('body_clean')
                            email_record.body_preview = normalized.get('body_preview')
                            email_record.entities = normalized.get('entities', {})
                            email_record.message_type = normalized.get('message_type')
                            email_record.priority_score = normalized.get('priority_score')
                            email_record.normalizer_version = self.version
                            
                            session.commit()
                            processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to normalize email {email.gmail_id}: {str(e)}")
                    error_count += 1
                    continue
            
            logger.info(f"Normalized {processed_count} emails for {user_email} ({error_count} errors)")
            
            return {
                'success': True,
                'user_email': user_email,
                'processed': processed_count,
                'errors': error_count,
                'normalizer_version': self.version
            }
            
        except Exception as e:
            logger.error(f"Failed to normalize emails for {user_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def normalize_email(self, email_data: Dict) -> Dict:
        """
        Normalize a single email into clean format
        
        Args:
            email_data: Raw email data dictionary
            
        Returns:
            Normalized email data
        """
        try:
            # Start with original data
            normalized = email_data.copy()
            
            # Clean and extract body content
            body_clean = self._extract_clean_body(email_data)
            normalized['body_clean'] = body_clean
            
            # Create preview (first 300 chars)
            normalized['body_preview'] = self._create_preview(body_clean)
            
            # Extract entities
            normalized['entities'] = self._extract_entities(email_data, body_clean)
            
            # Determine message type
            normalized['message_type'] = self._classify_message_type(email_data, body_clean)
            
            # Calculate priority score
            normalized['priority_score'] = self._calculate_priority_score(email_data, body_clean)
            
            # Add processing metadata
            normalized['processing_metadata'] = {
                'normalizer_version': self.version,
                'normalized_at': datetime.utcnow().isoformat(),
                'body_length': len(body_clean) if body_clean else 0
            }
            
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to normalize email {email_data.get('id', 'unknown')}: {str(e)}")
            return {
                **email_data,
                'normalization_error': str(e),
                'processing_metadata': {
                    'normalizer_version': self.version,
                    'normalized_at': datetime.utcnow().isoformat(),
                    'error': True
                }
            }
    
    def _extract_clean_body(self, email_data: Dict) -> str:
        """
        Extract clean text from email body
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            Clean body text
        """
        try:
            body_text = email_data.get('body_text', '')
            body_html = email_data.get('body_html', '')
            
            # Prefer HTML if available, fallback to text
            if body_html:
                # Parse HTML and extract text
                soup = BeautifulSoup(body_html, 'html.parser')
                
                # Remove script and style elements
                for script in soup(['script', 'style']):
                    script.decompose()
                
                # Get text and clean it
                text = soup.get_text()
                
                # Break into lines and remove leading/trailing spaces
                lines = (line.strip() for line in text.splitlines())
                
                # Break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                
                # Drop blank lines
                clean_text = '\n'.join(chunk for chunk in chunks if chunk)
                
            elif body_text:
                clean_text = body_text
                
            else:
                # Fallback to snippet
                clean_text = email_data.get('snippet', '')
            
            if not clean_text:
                return ''
                
            # Remove quoted text (replies/forwards)
            clean_text = self._remove_quoted_text(clean_text)
            
            # Remove excessive whitespace
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
            clean_text = re.sub(r' +', ' ', clean_text)
            
            # Decode HTML entities
            clean_text = unescape(clean_text)
            
            return clean_text.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract clean body: {str(e)}")
            return email_data.get('snippet', '')
    
    def _remove_quoted_text(self, text: str) -> str:
        """
        Remove quoted text from emails (replies/forwards)
        
        Args:
            text: Email body text
            
        Returns:
            Text with quoted sections removed
        """
        try:
            # Common quote patterns
            quote_patterns = [
                r'On .* wrote:.*',
                r'From:.*\nSent:.*\nTo:.*\nSubject:.*',
                r'-----Original Message-----.*',
                r'> .*',  # Lines starting with >
                r'________________________________.*',  # Outlook separator
                r'From: .*<.*>.*',
                r'Sent from my .*',
                r'\n\n.*On.*\d{4}.*at.*\d{1,2}:\d{2}.*wrote:'
            ]
            
            cleaned_text = text
            
            for pattern in quote_patterns:
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove excessive newlines created by quote removal
            cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
            
            return cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"Failed to remove quoted text: {str(e)}")
            return text
    
    def _create_preview(self, body_text: str) -> str:
        """
        Create a preview of the email body
        
        Args:
            body_text: Clean email body text
            
        Returns:
            Preview text (first 300 characters)
        """
        if not body_text:
            return ''
        
        # Take first 300 characters
        preview = body_text[:300]
        
        # If we cut in the middle of a word, cut to last complete word
        if len(body_text) > 300:
            last_space = preview.rfind(' ')
            if last_space > 250:  # Only if we have a reasonable amount of text
                preview = preview[:last_space] + '...'
            else:
                preview += '...'
        
        return preview
    
    def _extract_entities(self, email_data: Dict, body_text: str) -> Dict:
        """
        Extract entities from email content
        
        Args:
            email_data: Email data dictionary
            body_text: Clean email body text
            
        Returns:
            Dictionary of extracted entities
        """
        try:
            entities = {
                'people': [],
                'companies': [],
                'dates': [],
                'times': [],
                'urls': [],
                'emails': [],
                'phone_numbers': [],
                'amounts': []
            }
            
            # Extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            entities['emails'] = list(set(re.findall(email_pattern, body_text)))
            
            # Extract URLs
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            entities['urls'] = list(set(re.findall(url_pattern, body_text)))
            
            # Extract phone numbers (US format)
            phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            phone_matches = re.findall(phone_pattern, body_text)
            entities['phone_numbers'] = ['-'.join(match) for match in phone_matches]
            
            # Extract dates (simple patterns)
            date_patterns = [
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',
                r'\b\d{1,2}-\d{1,2}-\d{4}\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
            ]
            for pattern in date_patterns:
                entities['dates'].extend(re.findall(pattern, body_text, re.IGNORECASE))
            
            # Extract times
            time_pattern = r'\b\d{1,2}:\d{2}(?:\s?[AP]M)?\b'
            entities['times'] = list(set(re.findall(time_pattern, body_text, re.IGNORECASE)))
            
            # Extract monetary amounts
            amount_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
            entities['amounts'] = list(set(re.findall(amount_pattern, body_text)))
            
            # Remove empty lists and duplicates
            for key in entities:
                entities[key] = list(set(entities[key])) if entities[key] else []
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to extract entities: {str(e)}")
            return {}
    
    def _classify_message_type(self, email_data: Dict, body_text: str) -> str:
        """
        Classify the type of email message
        
        Args:
            email_data: Email data dictionary
            body_text: Clean email body text
            
        Returns:
            Message type classification
        """
        try:
            subject = email_data.get('subject', '').lower()
            body_lower = body_text.lower() if body_text else ''
            sender = email_data.get('sender', '').lower()
            
            # Meeting/Calendar invites
            meeting_keywords = ['meeting', 'call', 'zoom', 'teams', 'webex', 'conference', 'invite', 'calendar']
            if any(keyword in subject for keyword in meeting_keywords):
                return 'meeting'
            
            # Automated/System emails
            system_domains = ['noreply', 'no-reply', 'donotreply', 'mailer-daemon', 'bounce']
            if any(domain in sender for domain in system_domains):
                return 'automated'
            
            # Newsletters/Marketing
            newsletter_keywords = ['unsubscribe', 'newsletter', 'marketing', 'promotional']
            if any(keyword in body_lower for keyword in newsletter_keywords):
                return 'newsletter'
            
            # Action required
            action_keywords = ['urgent', 'asap', 'deadline', 'required', 'please review', 'action needed']
            if any(keyword in subject for keyword in action_keywords):
                return 'action_required'
            
            # FYI/Information
            fyi_keywords = ['fyi', 'for your information', 'heads up', 'update', 'status']
            if any(keyword in subject for keyword in fyi_keywords):
                return 'informational'
            
            # Default to regular
            return 'regular'
            
        except Exception as e:
            logger.error(f"Failed to classify message type: {str(e)}")
            return 'regular'
    
    def _calculate_priority_score(self, email_data: Dict, body_text: str) -> float:
        """
        Calculate priority score for email (0.0 to 1.0)
        
        Args:
            email_data: Email data dictionary
            body_text: Clean email body text
            
        Returns:
            Priority score between 0.0 and 1.0
        """
        try:
            score = 0.5  # Base score
            
            subject = email_data.get('subject', '').lower()
            body_lower = body_text.lower() if body_text else ''
            
            # High priority keywords
            urgent_keywords = ['urgent', 'asap', 'emergency', 'critical', 'deadline']
            for keyword in urgent_keywords:
                if keyword in subject or keyword in body_lower:
                    score += 0.2
            
            # Medium priority keywords
            important_keywords = ['important', 'priority', 'please review', 'action needed']
            for keyword in important_keywords:
                if keyword in subject or keyword in body_lower:
                    score += 0.1
            
            # Questions increase priority slightly
            if '?' in subject or '?' in body_text:
                score += 0.05
            
            # Direct communication (personal emails)
            if '@' in email_data.get('sender', '') and 'noreply' not in email_data.get('sender', ''):
                score += 0.1
            
            # Reduce score for automated emails
            automated_keywords = ['unsubscribe', 'automated', 'noreply', 'notification']
            for keyword in automated_keywords:
                if keyword in email_data.get('sender', '').lower():
                    score -= 0.2
            
            # Ensure score is between 0.0 and 1.0
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Failed to calculate priority score: {str(e)}")
            return 0.5

# Create global instance
email_normalizer = EmailNormalizer()