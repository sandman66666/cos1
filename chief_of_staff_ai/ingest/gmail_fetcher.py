# Handles fetching emails from Gmail API

import json
import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from email.utils import parsedate_to_datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.gmail_auth import gmail_auth
from models.database import get_db_manager, Email
from config.settings import settings

logger = logging.getLogger(__name__)

class GmailFetcher:
    """Fetches emails from Gmail API with intelligent batching and caching"""
    
    def __init__(self):
        self.batch_size = 50
        self.max_results = 500
        # Remove file-based caching as we now use database
        
    def fetch_recent_emails(
        self, 
        user_email: str, 
        days_back: int = 7, 
        limit: int = None,
        force_refresh: bool = False
    ) -> Dict:
        """
        Fetch recent emails for a user from their Gmail account
        
        Args:
            user_email: Gmail address of the user
            days_back: Number of days back to fetch emails
            limit: Maximum number of emails to fetch
            force_refresh: Whether to bypass database cache and fetch fresh data
            
        Returns:
            Dictionary containing fetched emails and metadata
        """
        try:
            # Get user from database
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return self._error_response(f"User {user_email} not found in database")
            
            # Check if we should use cached data
            if not force_refresh:
                cached_emails = get_db_manager().get_user_emails(user.id, limit or 50)
                if cached_emails:
                    logger.info(f"Using cached emails for {user_email}: {len(cached_emails)} emails")
                    return {
                        'success': True,
                        'user_email': user_email,
                        'emails': [email.to_dict() for email in cached_emails],
                        'count': len(cached_emails),
                        'source': 'database_cache',
                        'fetched_at': datetime.utcnow().isoformat()
                    }
            
            # Get valid credentials
            credentials = gmail_auth.get_valid_credentials(user_email)
            if not credentials:
                return self._error_response(f"No valid credentials for {user_email}")
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Calculate date range
            since_date = datetime.utcnow() - timedelta(days=days_back)
            query = f"after:{since_date.strftime('%Y/%m/%d')}"
            
            logger.info(f"Fetching emails for {user_email} with query: {query}")
            
            # Fetch email list
            email_list = self._fetch_email_list(service, query, limit)
            if not email_list:
                return {
                    'success': True,
                    'user_email': user_email,
                    'emails': [],
                    'count': 0,
                    'source': 'gmail_api',
                    'fetched_at': datetime.utcnow().isoformat(),
                    'message': 'No emails found in the specified time range'
                }
            
            # Fetch full email content in batches
            emails = self._fetch_emails_batch(service, email_list, user.id)
            
            logger.info(f"Successfully fetched {len(emails)} emails for {user_email}")
            
            return {
                'success': True,
                'user_email': user_email,
                'emails': emails,
                'count': len(emails),
                'source': 'gmail_api',
                'fetched_at': datetime.utcnow().isoformat(),
                'query_used': query,
                'days_back': days_back
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch emails for {user_email}: {str(e)}")
            return self._error_response(str(e))
    
    def _fetch_email_list(self, service, query: str, limit: int = None) -> List[Dict]:
        """
        Fetch list of email IDs matching the query
        
        Args:
            service: Gmail service object
            query: Gmail search query
            limit: Maximum number of emails to fetch
            
        Returns:
            List of email metadata
        """
        try:
            max_results = min(limit or self.max_results, self.max_results)
            
            result = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = result.get('messages', [])
            
            # Handle pagination if needed and no limit specified
            while 'nextPageToken' in result and (not limit or len(messages) < limit):
                result = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_results,
                    pageToken=result['nextPageToken']
                ).execute()
                
                messages.extend(result.get('messages', []))
                
                if len(messages) >= (limit or self.max_results):
                    break
            
            # Trim to limit if specified
            if limit:
                messages = messages[:limit]
            
            logger.info(f"Found {len(messages)} emails matching query: {query}")
            return messages
            
        except HttpError as e:
            logger.error(f"Gmail API error in fetch_email_list: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in fetch_email_list: {str(e)}")
            raise
    
    def _fetch_emails_batch(self, service, email_list: List[Dict], user_id: int) -> List[Dict]:
        """
        Fetch full email content in batches for efficiency
        
        Args:
            service: Gmail service object
            email_list: List of email metadata from list API
            user_id: Database user ID
            
        Returns:
            List of processed email dictionaries
        """
        emails = []
        processed_count = 0
        
        try:
            # Process emails in batches
            for i in range(0, len(email_list), self.batch_size):
                batch = email_list[i:i + self.batch_size]
                batch_emails = []
                
                for email_meta in batch:
                    email_id = email_meta['id']
                    
                    try:
                        # Check if email already exists in database
                        with get_db_manager().get_session() as session:
                            existing_email = session.query(Email).filter(
                                Email.user_id == user_id,
                                Email.gmail_id == email_id
                            ).first()
                            
                            if existing_email:
                                batch_emails.append(existing_email.to_dict())
                                continue
                        
                        # Fetch full email from Gmail API
                        full_email = service.users().messages().get(
                            userId='me',
                            id=email_id,
                            format='full'
                        ).execute()
                        
                        # Process the email
                        processed_email = self._process_gmail_message(full_email)
                        
                        # Save to database
                        email_record = get_db_manager().save_email(user_id, processed_email)
                        batch_emails.append(email_record.to_dict())
                        
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to process email {email_id}: {str(e)}")
                        continue
                
                emails.extend(batch_emails)
                
                # Log progress for large batches
                if len(email_list) > self.batch_size:
                    logger.info(f"Processed batch {i//self.batch_size + 1}/{(len(email_list)-1)//self.batch_size + 1}")
            
            logger.info(f"Successfully processed {processed_count} emails, {len(emails)} total returned")
            return emails
            
        except Exception as e:
            logger.error(f"Failed to fetch emails in batch: {str(e)}")
            raise
    
    def _process_gmail_message(self, gmail_message: Dict) -> Dict:
        """
        Process a Gmail message into our standard format
        
        Args:
            gmail_message: Raw Gmail message from API
            
        Returns:
            Processed email dictionary
        """
        try:
            headers = {h['name'].lower(): h['value'] for h in gmail_message['payload'].get('headers', [])}
            
            # Extract basic email info
            email_data = {
                'id': gmail_message['id'],
                'thread_id': gmail_message.get('threadId'),
                'label_ids': gmail_message.get('labelIds', []),
                'snippet': gmail_message.get('snippet', ''),
                'size_estimate': gmail_message.get('sizeEstimate', 0),
                
                # Headers
                'sender': headers.get('from', ''),
                'recipients': [headers.get('to', '')],
                'cc': [headers.get('cc', '')] if headers.get('cc') else [],
                'bcc': [headers.get('bcc', '')] if headers.get('bcc') else [],
                'subject': headers.get('subject', ''),
                'date': headers.get('date', ''),
                
                # Body content
                'body_text': '',
                'body_html': '',
                'attachments': [],
                
                # Metadata
                'is_read': 'UNREAD' not in gmail_message.get('labelIds', []),
                'is_important': 'IMPORTANT' in gmail_message.get('labelIds', []),
                'is_starred': 'STARRED' in gmail_message.get('labelIds', []),
                'has_attachments': False,
                
                # Processing metadata
                'processing_metadata': {
                    'fetcher_version': '1.0',
                    'processed_at': datetime.utcnow().isoformat(),
                    'gmail_labels': gmail_message.get('labelIds', [])
                }
            }
            
            # Parse timestamp
            if email_data['date']:
                try:
                    email_data['timestamp'] = parsedate_to_datetime(email_data['date'])
                except:
                    email_data['timestamp'] = datetime.utcnow()
            else:
                email_data['timestamp'] = datetime.utcnow()
            
            # Extract body content
            self._extract_email_body(gmail_message['payload'], email_data)
            
            # Extract sender name
            sender_full = email_data['sender']
            if '<' in sender_full and '>' in sender_full:
                email_data['sender_name'] = sender_full.split('<')[0].strip().strip('"')
                email_data['sender'] = sender_full.split('<')[1].split('>')[0]
            
            return email_data
            
        except Exception as e:
            logger.error(f"Failed to process Gmail message {gmail_message.get('id', 'unknown')}: {str(e)}")
            return {
                'id': gmail_message.get('id', 'unknown'),
                'error': True,
                'error_message': str(e),
                'timestamp': datetime.utcnow()
            }
    
    def _extract_email_body(self, payload: Dict, email_data: Dict):
        """
        Extract email body content from Gmail payload
        
        Args:
            payload: Gmail message payload
            email_data: Email data dictionary to populate
        """
        try:
            # Handle multipart messages
            if payload.get('parts'):
                for part in payload['parts']:
                    self._process_message_part(part, email_data)
            else:
                # Single part message
                self._process_message_part(payload, email_data)
                
        except Exception as e:
            logger.error(f"Failed to extract email body: {str(e)}")
    
    def _process_message_part(self, part: Dict, email_data: Dict):
        """
        Process a single part of a Gmail message
        
        Args:
            part: Message part from Gmail payload
            email_data: Email data dictionary to populate
        """
        try:
            mime_type = part.get('mimeType', '')
            
            # Handle attachments
            if part.get('filename'):
                attachment_info = {
                    'filename': part['filename'],
                    'mime_type': mime_type,
                    'size': part.get('body', {}).get('size', 0),
                    'attachment_id': part.get('body', {}).get('attachmentId')
                }
                email_data['attachments'].append(attachment_info)
                email_data['has_attachments'] = True
                return
            
            # Extract body content
            body = part.get('body', {})
            if body.get('data'):
                content = base64.urlsafe_b64decode(body['data']).decode('utf-8', errors='ignore')
                
                if mime_type == 'text/plain':
                    email_data['body_text'] = content
                elif mime_type == 'text/html':
                    email_data['body_html'] = content
            
            # Handle nested parts
            if part.get('parts'):
                for nested_part in part['parts']:
                    self._process_message_part(nested_part, email_data)
                    
        except Exception as e:
            logger.error(f"Failed to process message part: {str(e)}")
    
    def _error_response(self, error_message: str) -> Dict:
        """Create standardized error response"""
        return {
            'success': False,
            'error': error_message,
            'fetched_at': datetime.utcnow().isoformat()
        }
    
    def get_user_fetch_stats(self, user_email: str) -> Dict:
        """
        Get email fetch statistics for a user
        
        Args:
            user_email: Email of the user
            
        Returns:
            Dictionary with fetch statistics
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'error': 'User not found'}
            
            emails = get_db_manager().get_user_emails(user.id, limit=1000)
            
            if not emails:
                return {
                    'total_emails': 0,
                    'date_range': None,
                    'last_fetch': None
                }
            
            # Calculate statistics
            dates = [email.email_date for email in emails if email.email_date]
            
            return {
                'total_emails': len(emails),
                'date_range': {
                    'earliest': min(dates).isoformat() if dates else None,
                    'latest': max(dates).isoformat() if dates else None
                },
                'last_fetch': max([email.processed_at for email in emails]).isoformat() if emails else None,
                'has_attachments_count': sum(1 for email in emails if email.has_attachments),
                'unread_count': sum(1 for email in emails if not email.is_read),
                'important_count': sum(1 for email in emails if email.is_important)
            }
            
        except Exception as e:
            logger.error(f"Failed to get fetch stats for {user_email}: {str(e)}")
            return {'error': str(e)}

# Create global instance
gmail_fetcher = GmailFetcher()