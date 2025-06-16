"""
Smart Contact Strategy Implementation

Revolutionary engagement-driven email processing that focuses AI resources
on content that actually matters to the user's business intelligence.

Core principle: "If I don't engage with it, it probably doesn't matter to my business intelligence."
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from email.utils import parseaddr
import json

from models.database import get_db_manager, TrustedContact, Person
from ingest.gmail_fetcher import gmail_fetcher

logger = logging.getLogger(__name__)

@dataclass
class ProcessingDecision:
    """Decision for how to process an incoming email"""
    action: str  # ANALYZE_WITH_AI, CONDITIONAL_ANALYZE, SKIP
    confidence: str  # HIGH, MEDIUM, LOW
    reason: str
    priority: float = 0.0
    estimated_tokens: int = 0

@dataclass
class EngagementMetrics:
    """Engagement metrics for a contact"""
    total_sent_emails: int
    total_received_emails: int
    bidirectional_threads: int
    first_sent_date: Optional[datetime]
    last_sent_date: Optional[datetime]
    topics_discussed: List[str]
    bidirectional_topics: List[str]
    communication_frequency: str  # daily, weekly, monthly, occasional
    relationship_strength: str  # high, medium, low

class SmartContactStrategy:
    """
    Revolutionary Smart Contact Strategy for engagement-driven email processing
    """
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.newsletter_patterns = [
            'noreply', 'no-reply', 'donotreply', 'newsletter', 'notifications',
            'automated', 'auto-', 'system@', 'support@', 'help@', 'info@',
            'marketing@', 'promo', 'deals@', 'offers@', 'sales@'
        ]
        self.automated_domains = [
            'mailchimp.com', 'constantcontact.com', 'sendgrid.net',
            'mailgun.org', 'amazonses.com', 'notifications.google.com'
        ]
    
    def build_trusted_contact_database(self, user_email: str, days_back: int = 365) -> Dict:
        """
        Analyze sent emails to build the Trusted Contact Database
        
        This is the foundation of the Smart Contact Strategy - analyze what 
        contacts the user actually engages with by looking at sent emails.
        """
        try:
            logger.info(f"Building trusted contact database for {user_email}")
            
            # Get user from database
            user = self.db_manager.get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Fetch sent emails from Gmail
            sent_emails_result = gmail_fetcher.fetch_sent_emails(
                user_email=user_email,
                days_back=days_back,
                max_emails=1000  # Analyze up to 1000 sent emails
            )
            
            if not sent_emails_result.get('success'):
                return {'success': False, 'error': 'Failed to fetch sent emails'}
            
            sent_emails = sent_emails_result.get('emails', [])
            logger.info(f"Analyzing {len(sent_emails)} sent emails")
            
            # Extract all recipients from sent emails
            contact_metrics = {}
            
            for email in sent_emails:
                # Ensure we have a valid datetime for email_date
                try:
                    if isinstance(email.get('timestamp'), str):
                        email_date = datetime.fromisoformat(email['timestamp'].replace('Z', '+00:00'))
                    elif isinstance(email.get('timestamp'), datetime):
                        email_date = email['timestamp']
                    elif isinstance(email.get('email_date'), str):
                        email_date = datetime.fromisoformat(email['email_date'].replace('Z', '+00:00'))
                    elif isinstance(email.get('email_date'), datetime):
                        email_date = email['email_date']
                    else:
                        email_date = None
                except Exception as e:
                    logger.warning(f"Failed to parse email date: {e}")
                    email_date = None

                recipients = self._extract_all_recipients(email)
                
                for recipient_email in recipients:
                    if recipient_email == user_email:
                        continue  # Skip self
                    
                    if recipient_email not in contact_metrics:
                        contact_metrics[recipient_email] = {
                            'email_address': recipient_email,
                            'total_sent_emails': 0,
                            'total_received_emails': 0,
                            'first_sent_date': email_date,
                            'last_sent_date': email_date,
                            'topics_discussed': set(),
                            'thread_ids': set(),
                            'sent_dates': []
                        }
                    
                    metrics = contact_metrics[recipient_email]
                    metrics['total_sent_emails'] += 1
                    if email_date:
                        metrics['sent_dates'].append(email_date)
                        
                        # Update first_sent_date if this is earlier
                        if not metrics['first_sent_date'] or (email_date and email_date < metrics['first_sent_date']):
                            metrics['first_sent_date'] = email_date
                        
                        # Update last_sent_date if this is later
                        if not metrics['last_sent_date'] or (email_date and email_date > metrics['last_sent_date']):
                            metrics['last_sent_date'] = email_date
                    
                    # Extract topics from subject and body
                    topics = self._extract_email_topics(email)
                    metrics['topics_discussed'].update(topics)
                    
                    # Track thread for bidirectional analysis
                    thread_id = email.get('thread_id')
                    if thread_id:
                        metrics['thread_ids'].add(thread_id)
            
            # Calculate engagement scores and save to database
            saved_contacts = 0
            for email_address, metrics in contact_metrics.items():
                engagement_score = self._calculate_engagement_score(metrics)
                relationship_strength = self._determine_relationship_strength(metrics, engagement_score)
                communication_frequency = self._determine_communication_frequency(metrics['sent_dates'])
                
                # Convert sets to lists for JSON storage
                topics_discussed = list(metrics['topics_discussed'])
                
                # Create trusted contact record
                contact_data = {
                    'email_address': email_address,
                    'name': self._extract_name_from_email(email_address),
                    'engagement_score': engagement_score,
                    'first_sent_date': metrics['first_sent_date'],
                    'last_sent_date': metrics['last_sent_date'],
                    'total_sent_emails': metrics['total_sent_emails'],
                    'total_received_emails': 0,  # Will be updated when analyzing received emails
                    'bidirectional_threads': 0,  # Will be calculated later
                    'topics_discussed': topics_discussed,
                    'bidirectional_topics': [],  # Will be calculated later
                    'relationship_strength': relationship_strength,
                    'communication_frequency': communication_frequency,
                    'last_analyzed': datetime.utcnow()
                }
                
                # Save to database
                trusted_contact = self.db_manager.create_or_update_trusted_contact(
                    user_id=user.id,
                    contact_data=contact_data
                )
                
                # Update corresponding Person record if exists
                person = self.db_manager.find_person_by_email(user.id, email_address)
                if person:
                    engagement_data = {
                        'is_trusted_contact': True,
                        'engagement_score': engagement_score,
                        'bidirectional_topics': []  # Will be updated later
                    }
                    self.db_manager.update_people_engagement_data(
                        user_id=user.id,
                        person_id=person.id,
                        engagement_data=engagement_data
                    )
                
                saved_contacts += 1
            
            logger.info(f"Built trusted contact database: {saved_contacts} contacts")
            
            return {
                'success': True,
                'contacts_analyzed': len(contact_metrics),
                'trusted_contacts_created': saved_contacts,
                'date_range': f"{days_back} days",
                'sent_emails_analyzed': len(sent_emails)
            }
            
        except Exception as e:
            logger.error(f"Error building trusted contact database: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def classify_incoming_email(self, user_email: str, email_data: Dict) -> ProcessingDecision:
        """
        Smart email classification using the engagement-driven decision tree
        
        Decision Tree:
        1. From trusted contact? → ANALYZE_WITH_AI (high confidence)
        2. Unknown sender + obvious newsletter/spam? → SKIP (high confidence)
        3. Unknown sender + business-like? → CONDITIONAL_ANALYZE (medium confidence)
        4. Default → SKIP (high confidence)
        """
        try:
            user = self.db_manager.get_user_by_email(user_email)
            if not user:
                return ProcessingDecision(
                    action="SKIP",
                    confidence="HIGH",
                    reason="User not found"
                )
            
            sender = email_data.get('sender', '')
            sender_email = parseaddr(sender)[1].lower() if sender else ''
            
            # Step 1: Check trusted contact database
            trusted_contact = self.db_manager.find_trusted_contact_by_email(
                user_id=user.id,
                email_address=sender_email
            )
            
            if trusted_contact:
                # Prioritize by engagement score
                priority = trusted_contact.engagement_score
                tokens = 4000 if trusted_contact.relationship_strength == 'high' else 3000
                
                return ProcessingDecision(
                    action="ANALYZE_WITH_AI",
                    confidence="HIGH",
                    reason=f"From trusted contact ({trusted_contact.relationship_strength} engagement)",
                    priority=priority,
                    estimated_tokens=tokens
                )
            
            # Step 2: Check for obvious newsletters/spam
            if self._is_obvious_newsletter(email_data):
                return ProcessingDecision(
                    action="SKIP",
                    confidence="HIGH",
                    reason="Newsletter/automated content detected",
                    estimated_tokens=0
                )
            
            # Step 3: Check if appears business relevant
            if self._appears_business_relevant(email_data):
                return ProcessingDecision(
                    action="CONDITIONAL_ANALYZE",
                    confidence="MEDIUM",
                    reason="Unknown sender but appears business relevant",
                    priority=0.3,
                    estimated_tokens=2000
                )
            
            # Step 4: Default skip
            return ProcessingDecision(
                action="SKIP",
                confidence="HIGH",
                reason="No engagement pattern, not business relevant",
                estimated_tokens=0
            )
            
        except Exception as e:
            logger.error(f"Error classifying email: {str(e)}")
            return ProcessingDecision(
                action="SKIP",
                confidence="LOW",
                reason=f"Classification error: {str(e)}",
                estimated_tokens=0
            )
    
    def calculate_processing_efficiency(self, user_email: str, emails: List[Dict]) -> Dict:
        """
        Calculate cost optimization and processing efficiency metrics
        """
        try:
            user = self.db_manager.get_user_by_email(user_email)
            if not user:
                return {'error': 'User not found'}
            
            decisions = []
            total_tokens = 0
            baseline_tokens = 0
            
            for email in emails:
                decision = self.classify_incoming_email(user_email, email)
                decisions.append({
                    'email_id': email.get('id'),
                    'sender': email.get('sender'),
                    'action': decision.action,
                    'confidence': decision.confidence,
                    'reason': decision.reason,
                    'estimated_tokens': decision.estimated_tokens
                })
                
                total_tokens += decision.estimated_tokens
                baseline_tokens += 4000  # Assume full analysis for all emails
            
            # Calculate savings
            tokens_saved = baseline_tokens - total_tokens
            efficiency_percent = (tokens_saved / baseline_tokens * 100) if baseline_tokens > 0 else 0
            
            # Breakdown by action
            action_counts = {}
            for decision in decisions:
                action = decision['action']
                action_counts[action] = action_counts.get(action, 0) + 1
            
            # Cost estimation (Claude Sonnet pricing)
            cost_per_token = 0.000015  # $15 per million tokens
            estimated_cost = total_tokens * cost_per_token
            baseline_cost = baseline_tokens * cost_per_token
            cost_savings = baseline_cost - estimated_cost
            
            return {
                'total_emails_analyzed': len(emails),
                'estimated_tokens': total_tokens,
                'baseline_tokens': baseline_tokens,
                'tokens_saved': tokens_saved,
                'efficiency_percent': round(efficiency_percent, 1),
                'estimated_cost_usd': round(estimated_cost, 4),
                'baseline_cost_usd': round(baseline_cost, 4),
                'cost_savings_usd': round(cost_savings, 4),
                'action_breakdown': action_counts,
                'processing_decisions': decisions
            }
            
        except Exception as e:
            logger.error(f"Error calculating processing efficiency: {str(e)}")
            return {'error': str(e)}
    
    def get_engagement_insights(self, user_email: str) -> Dict:
        """
        Get insights about user's engagement patterns for dashboard
        """
        try:
            user = self.db_manager.get_user_by_email(user_email)
            if not user:
                return {'error': 'User not found'}
            
            # Get analytics from database
            analytics = self.db_manager.get_engagement_analytics(user.id)
            
            # Get trusted contacts
            trusted_contacts = self.db_manager.get_trusted_contacts(user.id, limit=10)
            
            # Format top contacts for display
            top_contacts = []
            for contact in trusted_contacts[:5]:
                top_contacts.append({
                    'email': contact.email_address,
                    'name': contact.name or contact.email_address,
                    'engagement_score': round(contact.engagement_score, 2),
                    'relationship_strength': contact.relationship_strength,
                    'total_sent_emails': contact.total_sent_emails,
                    'communication_frequency': contact.communication_frequency,
                    'last_sent_date': contact.last_sent_date.isoformat() if contact.last_sent_date else None
                })
            
            return {
                'success': True,
                'analytics': analytics,
                'top_contacts': top_contacts,
                'total_trusted_contacts': analytics.get('total_trusted_contacts', 0),
                'high_engagement_contacts': analytics.get('high_engagement_contacts', 0),
                'engagement_rate': analytics.get('engagement_rate', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting engagement insights: {str(e)}")
            return {'error': str(e)}
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _extract_all_recipients(self, email: Dict) -> Set[str]:
        """Extract all email recipients (TO, CC, BCC) from an email"""
        recipients = set()
        
        if not email:
            logger.warning("Empty email data provided")
            return recipients
            
        logger.info(f"Processing email: {email.get('subject', 'No subject')}")
        logger.info(f"Raw email data: {email}")
        
        # Extract from recipient_emails field (primary)
        recipient_list = email.get('recipient_emails', [])
        if recipient_list:
            if isinstance(recipient_list, str):
                try:
                    recipient_list = json.loads(recipient_list)
                except:
                    recipient_list = [recipient_list]
            elif recipient_list is None:
                recipient_list = []
            
            for recipient in recipient_list:
                if isinstance(recipient, str) and '@' in recipient:
                    recipients.add(recipient.lower())

        # Extract from recipients field (legacy)
        legacy_recipients = email.get('recipients', [])
        if legacy_recipients:
            if isinstance(legacy_recipients, str):
                try:
                    legacy_recipients = json.loads(legacy_recipients)
                except:
                    legacy_recipients = [legacy_recipients]
            elif legacy_recipients is None:
                legacy_recipients = []
            
            for recipient in legacy_recipients:
                if isinstance(recipient, str) and '@' in recipient:
                    recipients.add(recipient.lower())

        # Extract from CC field
        cc_list = email.get('cc', [])
        if cc_list:
            if isinstance(cc_list, str):
                try:
                    cc_list = json.loads(cc_list)
                except:
                    cc_list = [cc_list]
            elif cc_list is None:
                cc_list = []
            
            for recipient in cc_list:
                if isinstance(recipient, str) and '@' in recipient:
                    recipients.add(recipient.lower())

        # Extract from BCC field
        bcc_list = email.get('bcc', [])
        if bcc_list:
            if isinstance(bcc_list, str):
                try:
                    bcc_list = json.loads(bcc_list)
                except:
                    bcc_list = [bcc_list]
            elif bcc_list is None:
                bcc_list = []
            
            for recipient in bcc_list:
                if isinstance(recipient, str) and '@' in recipient:
                    recipients.add(recipient.lower())

        logger.info(f"Final recipients set: {recipients}")
        return recipients
    
    def _extract_email_topics(self, email: Dict) -> Set[str]:
        """Extract topics/themes from email subject and content"""
        topics = set()
        
        # Extract from subject
        subject = email.get('subject', '').lower()
        if subject:
            # Simple keyword extraction - could be enhanced with NLP
            business_keywords = [
                'project', 'meeting', 'deadline', 'budget', 'proposal',
                'contract', 'invoice', 'report', 'review', 'planning',
                'strategy', 'launch', 'development', 'marketing', 'sales'
            ]
            
            for keyword in business_keywords:
                if keyword in subject:
                    topics.add(keyword)
        
        return topics
    
    def _calculate_engagement_score(self, metrics: Dict) -> float:
        """
        Calculate engagement score based on communication patterns
        
        Formula considers:
        - Frequency of sent emails (higher = more engagement)
        - Recency of communication (recent = higher score)
        - Communication span (longer relationship = higher score)
        """
        try:
            sent_count = metrics['total_sent_emails']
            first_date = metrics.get('first_sent_date')
            last_date = metrics.get('last_sent_date')
            
            if not first_date or not last_date:
                return 0.1
            
            # Convert dates to datetime if they're strings
            if isinstance(first_date, str):
                first_date = datetime.fromisoformat(first_date)
            if isinstance(last_date, str):
                last_date = datetime.fromisoformat(last_date)
            
            # Frequency score (0.0 to 0.5)
            frequency_score = min(sent_count / 50.0, 0.5)  # Cap at 50 emails
            
            # Recency score (0.0 to 0.3)
            days_since_last = (datetime.now(timezone.utc) - last_date).days if last_date else 999
            recency_score = max(0, 0.3 - (days_since_last / 365.0 * 0.3))
            
            # Relationship span score (0.0 to 0.2)
            relationship_days = (last_date - first_date).days if first_date and last_date else 0
            span_score = min(relationship_days / 365.0 * 0.2, 0.2)
            
            total_score = frequency_score + recency_score + span_score
            return min(total_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating engagement score: {str(e)}")
            return 0.1
    
    def _determine_relationship_strength(self, metrics: Dict, engagement_score: float) -> str:
        """Determine relationship strength based on engagement patterns"""
        if engagement_score > 0.7:
            return 'high'
        elif engagement_score > 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _determine_communication_frequency(self, sent_dates: List[datetime]) -> str:
        """Determine communication frequency pattern"""
        if not sent_dates or len(sent_dates) < 2:
            return 'occasional'
        
        # Calculate average days between emails
        sorted_dates = sorted(sent_dates)
        total_days = (sorted_dates[-1] - sorted_dates[0]).days
        avg_interval = total_days / len(sent_dates) if len(sent_dates) > 1 else 365
        
        if avg_interval <= 7:
            return 'weekly'
        elif avg_interval <= 30:
            return 'monthly'
        else:
            return 'occasional'
    
    def _extract_name_from_email(self, email_address: str) -> str:
        """Extract a readable name from email address"""
        if not email_address or '@' not in email_address:
            return email_address
        
        # Get the part before @
        local_part = email_address.split('@')[0]
        
        # Replace common separators with spaces and title case
        name = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        return name.title()
    
    def _is_obvious_newsletter(self, email_data: Dict) -> bool:
        """Detect obvious newsletters and automated messages"""
        sender = email_data.get('sender', '').lower()
        subject = email_data.get('subject', '').lower()
        
        # Check sender patterns
        for pattern in self.newsletter_patterns:
            if pattern in sender:
                return True
        
        # Check domain patterns
        sender_email = parseaddr(sender)[1] if sender else ''
        sender_domain = sender_email.split('@')[1] if '@' in sender_email else ''
        
        for domain in self.automated_domains:
            if domain in sender_domain:
                return True
        
        # Check subject patterns
        newsletter_subjects = [
            'newsletter', 'unsubscribe', 'promotional', 'sale', 'deal',
            'offer', 'discount', 'marketing', 'campaign'
        ]
        
        for pattern in newsletter_subjects:
            if pattern in subject:
                return True
        
        return False
    
    def _appears_business_relevant(self, email_data: Dict) -> bool:
        """Check if unknown sender appears business relevant"""
        sender = email_data.get('sender', '').lower()
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body_text', '').lower()[:500]  # First 500 chars
        
        # Business keywords that suggest relevance
        business_keywords = [
            'project', 'meeting', 'proposal', 'contract', 'invoice',
            'partnership', 'collaboration', 'opportunity', 'business',
            'professional', 'company', 'organization', 'enterprise'
        ]
        
        # Check if business keywords appear in subject or body
        for keyword in business_keywords:
            if keyword in subject or keyword in body:
                return True
        
        # Check if sender has professional domain
        sender_email = parseaddr(sender)[1] if sender else ''
        sender_domain = sender_email.split('@')[1] if '@' in sender_email else ''
        
        # Skip generic domains that are likely personal
        personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        if sender_domain not in personal_domains and '.' in sender_domain:
            return True
        
        return False

# Create global instance
smart_contact_strategy = SmartContactStrategy() 