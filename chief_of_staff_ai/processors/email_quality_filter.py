"""
🎯 Email Quality Filter - Intelligent Email Injection System
==========================================================

This module implements a sophisticated email quality filtering system based on user engagement patterns.
The system categorizes contacts into tiers and filters email injection accordingly.

TIER SYSTEM:
- Tier 1: People you respond to regularly (HIGH QUALITY - Always process)
- Tier 2: New contacts or occasional contacts (MEDIUM QUALITY - Process with caution)
- Tier LAST: Contacts you never respond to (LOW QUALITY - Ignore completely)

Author: AI Chief of Staff
Created: December 2024
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import re
from collections import defaultdict, Counter
from email.utils import parseaddr

from models.database import get_db_manager
from models.enhanced_models import Email, Person, Task
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

logger = logging.getLogger(__name__)

class ContactTier(Enum):
    """Contact tier classifications based on engagement patterns"""
    TIER_1 = "tier_1"           # High engagement - always respond to
    TIER_2 = "tier_2"           # Medium engagement - new or occasional 
    TIER_LAST = "tier_last"     # No engagement - consistently ignore
    UNCLASSIFIED = "unclassified"  # Not yet analyzed

@dataclass
class ContactEngagementStats:
    """Statistics for contact engagement analysis"""
    email_address: str
    name: Optional[str]
    emails_received: int
    emails_responded_to: int
    last_email_date: datetime
    first_email_date: datetime
    response_rate: float
    days_since_last_email: int
    avg_days_between_emails: float
    tier: ContactTier
    tier_reason: str
    should_process: bool

@dataclass
class EmailQualityResult:
    """Result of email quality assessment"""
    should_process: bool
    tier: ContactTier
    reason: str
    sender_stats: Optional[ContactEngagementStats]
    confidence: float

class EmailQualityFilter:
    """
    Intelligent email quality filtering system that categorizes contacts
    based on engagement patterns and filters email injection accordingly.
    """
    
    def __init__(self):
        """Initialize the EmailQualityFilter with configuration"""
        from models.database import get_db_manager
        
        self.db_manager = get_db_manager()
        self._contact_tiers: Dict[str, ContactEngagementStats] = {}
        self._last_tier_update: Optional[datetime] = None
        
        # Configuration for tier classification thresholds
        self.TIER_1_MIN_RESPONSE_RATE = 0.5  # 50% response rate for Tier 1
        self.TIER_LAST_MAX_RESPONSE_RATE = 0.1  # 10% max for Tier LAST
        self.TIER_LAST_MIN_EMAILS = 5  # Need at least 5 emails to classify as Tier LAST
        self.MIN_EMAILS_FOR_CLASSIFICATION = 3  # Minimum emails needed for tier classification
        self.NEW_CONTACT_GRACE_PERIOD = 30  # Days to give new contacts grace period
        self.MONTHLY_REVIEW_DAYS = 30  # Review tiers every 30 days
        
        # Clear any corrupted cache data on startup
        self.clear_corrupted_cache()
        
    def analyze_email_quality(self, email_data: Dict, user_id: int) -> EmailQualityResult:
        """
        Main entry point: Analyze if an email should be processed based on sender quality.
        
        Args:
            email_data: Email data dictionary with sender, subject, body, etc.
            user_id: User ID for analysis
            
        Returns:
            EmailQualityResult with processing decision and reasoning
        """
        try:
            sender_email = self._extract_sender_email(email_data)
            if not sender_email:
                return EmailQualityResult(
                    should_process=False,
                    tier=ContactTier.UNCLASSIFIED,
                    reason="No valid sender email found",
                    sender_stats=None,
                    confidence=1.0
                )
            
            # Check if we need to update contact tiers
            if self._should_refresh_tiers():
                logger.info(f"🔄 Refreshing contact tiers for user {user_id}")
                self._analyze_all_contacts(user_id)
            
            # Get sender engagement stats
            sender_stats = self._get_contact_stats(sender_email, user_id)
            
            # Make processing decision based on tier
            should_process, reason, confidence = self._make_processing_decision(sender_stats, email_data)
            
            logger.info(f"📧 Email quality check: {sender_email} -> {sender_stats.tier.value} -> {'PROCESS' if should_process else 'SKIP'}")
            
            return EmailQualityResult(
                should_process=should_process,
                tier=sender_stats.tier,
                reason=reason,
                sender_stats=sender_stats,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"❌ Email quality analysis error: {str(e)}")
            # Fail open - process email if analysis fails
            return EmailQualityResult(
                should_process=True,
                tier=ContactTier.UNCLASSIFIED,
                reason=f"Analysis error: {str(e)}",
                sender_stats=None,
                confidence=0.0
            )
    
    def _extract_sender_email(self, email_data: Dict) -> Optional[str]:
        """Extract and normalize sender email address"""
        sender = email_data.get('sender') or email_data.get('from') or email_data.get('From')
        if not sender:
            return None
        
        # Extract email from various formats: "Name <email@domain.com>" or "email@domain.com"
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender)
        if email_match:
            return email_match.group(0).lower().strip()
        
        return None
    
    def _should_refresh_tiers(self) -> bool:
        """Check if contact tiers need to be refreshed"""
        if not self._last_tier_update:
            return True
        
        days_since_update = (datetime.now() - self._last_tier_update).days
        return days_since_update >= self.MONTHLY_REVIEW_DAYS
    
    def _analyze_all_contacts(self, user_id: int):
        """
        Comprehensive analysis of all contacts to determine tiers.
        This is the core intelligence that implements your engagement-based tiering.
        """
        logger.info(f"🧠 Running comprehensive contact tier analysis for user {user_id}")
        
        with self.db_manager.get_session() as session:
            # Get all emails for analysis
            all_emails = session.query(Email).filter(Email.user_id == user_id).all()
            
            # Get user's sent emails to identify who they respond to
            sent_emails = [email for email in all_emails if self._is_sent_email(email)]
            received_emails = [email for email in all_emails if not self._is_sent_email(email)]
            
            logger.info(f"📊 Analyzing {len(received_emails)} received emails and {len(sent_emails)} sent emails")
            
            # Build engagement statistics
            contact_stats = self._build_engagement_statistics(received_emails, sent_emails)
            
            # Classify contacts into tiers
            self._classify_contacts_into_tiers(contact_stats)
            
            # Cache results
            self._contact_tiers = {stats.email_address: stats for stats in contact_stats.values()}
            self._last_tier_update = datetime.now()
            
            # Log tier summary
            self._log_tier_summary(contact_stats)
    
    def _is_sent_email(self, email: Email) -> bool:
        """Determine if an email was sent by the user"""
        # Heuristics to identify sent emails
        if hasattr(email, 'is_sent') and email.is_sent:
            return True
        
        # Check common sent folder indicators
        if hasattr(email, 'folder') and email.folder:
            sent_indicators = ['sent', 'outbox', 'drafts']
            return any(indicator in email.folder.lower() for indicator in sent_indicators)
        
        # Check subject for "Re:" or "Fwd:" patterns and check if it's a response
        if hasattr(email, 'subject') and email.subject:
            # This is a simplified heuristic - in real implementation you'd want more sophisticated detection
            return False
        
        return False
    
    def _build_engagement_statistics(self, received_emails: List[Email], sent_emails: List[Email]) -> Dict[str, ContactEngagementStats]:
        """Build comprehensive engagement statistics for all contacts"""
        contact_stats = {}
        
        # Group received emails by sender
        emails_by_sender = defaultdict(list)
        for email in received_emails:
            sender = self._extract_sender_email({'sender': email.sender})
            if sender:
                emails_by_sender[sender].append(email)
        
        # Build sent email lookup for response detection
        sent_subjects = set()
        sent_recipients = set()
        for email in sent_emails:
            if hasattr(email, 'recipient_emails') and email.recipient_emails:
                # Extract recipients from sent emails
                recipients = self._extract_email_addresses(email.recipient_emails)
                sent_recipients.update(recipients)
            
            if hasattr(email, 'subject') and email.subject:
                sent_subjects.add(email.subject.lower().strip())
        
        # Analyze each contact
        for sender_email, sender_emails in emails_by_sender.items():
            if len(sender_emails) == 0:
                continue
            
            # Calculate basic stats
            emails_received = len(sender_emails)
            first_email_date = min(email.email_date for email in sender_emails if email.email_date)
            last_email_date = max(email.email_date for email in sender_emails if email.email_date)
            
            # Calculate response rate (sophisticated heuristic)
            emails_responded_to = self._calculate_response_count(sender_emails, sent_subjects, sent_recipients, sender_email)
            response_rate = emails_responded_to / emails_received if emails_received > 0 else 0.0
            
            # Calculate timing statistics
            days_since_last = (datetime.now() - last_email_date).days if last_email_date else 999
            total_days = (last_email_date - first_email_date).days if first_email_date and last_email_date else 1
            avg_days_between = total_days / max(1, emails_received - 1) if emails_received > 1 else 0
            
            # Get contact name
            contact_name = sender_emails[0].sender_name if hasattr(sender_emails[0], 'sender_name') else None
            
            stats = ContactEngagementStats(
                email_address=sender_email,
                name=contact_name,
                emails_received=emails_received,
                emails_responded_to=emails_responded_to,
                last_email_date=last_email_date,
                first_email_date=first_email_date,
                response_rate=response_rate,
                days_since_last_email=days_since_last,
                avg_days_between_emails=avg_days_between,
                tier=ContactTier.UNCLASSIFIED,  # Will be set in classification step
                tier_reason="",
                should_process=True
            )
            
            contact_stats[sender_email] = stats
        
        return contact_stats
    
    def _extract_email_addresses(self, recipients_string: str) -> List[str]:
        """Extract email addresses from recipients string"""
        if not recipients_string:
            return []
        
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', recipients_string)
        return [email.lower().strip() for email in emails]
    
    def _calculate_response_count(self, sender_emails: List[Email], sent_subjects: Set[str], sent_recipients: Set[str], sender_email: str) -> int:
        """
        Calculate how many emails from this sender we responded to.
        Uses sophisticated heuristics to detect responses.
        """
        responses = 0
        
        # Check if we ever sent emails to this sender
        if sender_email in sent_recipients:
            responses += 1  # Basic engagement indicator
        
        # Check for subject-based response patterns
        for email in sender_emails:
            if not email.subject:
                continue
            
            subject = email.subject.lower().strip()
            
            # Look for response patterns in sent emails
            response_patterns = [
                f"re: {subject}",
                f"re:{subject}",
                subject  # Exact match might indicate a response
            ]
            
            for pattern in response_patterns:
                if pattern in sent_subjects:
                    responses += 1
                    break
        
        return min(responses, len(sender_emails))  # Cap at number of emails received
    
    def _classify_contacts_into_tiers(self, contact_stats: Dict[str, ContactEngagementStats]):
        """
        Classify contacts into tiers based on engagement patterns.
        This implements your core tiering logic.
        """
        for email_address, stats in contact_stats.items():
            tier, reason, should_process = self._determine_contact_tier(stats)
            
            stats.tier = tier
            stats.tier_reason = reason
            stats.should_process = should_process
    
    def _determine_contact_tier(self, stats: ContactEngagementStats) -> Tuple[ContactTier, str, bool]:
        """
        Core logic to determine contact tier based on engagement statistics.
        Implements your specified tiering rules.
        """
        # Get user's email addresses
        from models.database import get_db_manager
        user = get_db_manager().get_user_by_email(stats.email_address)
        
        # If this is one of the user's own email addresses, always Tier 1
        if user:
            return ContactTier.TIER_1, "User's own email address", True
            
        # Check for common variations of the user's email
        if user and stats.email_address.split('@')[0] in ['sandman', 'oudi', 'oudiantebi']:
            return ContactTier.TIER_1, "User's alias email address", True
        
        # Tier 1: People you respond to regularly (HIGH QUALITY)
        if stats.response_rate >= self.TIER_1_MIN_RESPONSE_RATE:
            return ContactTier.TIER_1, f"High response rate ({stats.response_rate:.1%})", True
        
        # Tier LAST: People you consistently ignore (LOW QUALITY)
        if (stats.emails_received >= self.TIER_LAST_MIN_EMAILS and 
            stats.response_rate <= self.TIER_LAST_MAX_RESPONSE_RATE and
            stats.days_since_last_email <= 60):  # Still actively emailing
            return ContactTier.TIER_LAST, f"Low response rate ({stats.response_rate:.1%}) with {stats.emails_received} emails", False
        
        # New contacts (grace period)
        if stats.days_since_last_email <= self.NEW_CONTACT_GRACE_PERIOD:
            return ContactTier.TIER_2, "New contact (grace period)", True
        
        # Insufficient data for classification
        if stats.emails_received < self.MIN_EMAILS_FOR_CLASSIFICATION:
            return ContactTier.TIER_2, f"Insufficient data ({stats.emails_received} emails)", True
        
        # Default to Tier 2 (MEDIUM QUALITY)
        return ContactTier.TIER_2, f"Medium engagement ({stats.response_rate:.1%})", True
    
    def _log_tier_summary(self, contact_stats: Dict[str, ContactEngagementStats]):
        """Log summary of tier classification results"""
        tier_counts = Counter(stats.tier for stats in contact_stats.values())
        
        logger.info("📊 Contact Tier Classification Summary:")
        logger.info(f"   👑 Tier 1 (High Quality): {tier_counts[ContactTier.TIER_1]} contacts")
        logger.info(f"   ⚖️  Tier 2 (Medium Quality): {tier_counts[ContactTier.TIER_2]} contacts")
        logger.info(f"   🗑️  Tier LAST (Low Quality): {tier_counts[ContactTier.TIER_LAST]} contacts")
        logger.info(f"   ❓ Unclassified: {tier_counts[ContactTier.UNCLASSIFIED]} contacts")
        
        # Log some examples
        tier_1_examples = [stats.email_address for stats in contact_stats.values() if stats.tier == ContactTier.TIER_1][:3]
        tier_last_examples = [stats.email_address for stats in contact_stats.values() if stats.tier == ContactTier.TIER_LAST][:3]
        
        if tier_1_examples:
            logger.info(f"   👑 Tier 1 examples: {', '.join(tier_1_examples)}")
        if tier_last_examples:
            logger.info(f"   🗑️  Tier LAST examples: {', '.join(tier_last_examples)}")
    
    def _get_contact_stats(self, sender_email: str, user_id: int) -> ContactEngagementStats:
        """Get cached contact statistics or analyze on-demand"""
        
        # Return cached stats if available
        if sender_email in self._contact_tiers:
            return self._contact_tiers[sender_email]
        
        # Analyze this specific contact on-demand
        logger.info(f"🔍 On-demand analysis for new contact: {sender_email}")
        
        with self.db_manager.get_session() as session:
            # Get emails from this sender
            sender_emails = session.query(Email).filter(
                and_(Email.user_id == user_id, Email.sender.ilike(f"%{sender_email}%"))
            ).all()
            
            if not sender_emails:
                # New contact - no history
                stats = ContactEngagementStats(
                    email_address=sender_email,
                    name=None,
                    emails_received=0,
                    emails_responded_to=0,
                    last_email_date=datetime.now(),
                    first_email_date=datetime.now(),
                    response_rate=0.0,
                    days_since_last_email=0,
                    avg_days_between_emails=0.0,
                    tier=ContactTier.TIER_2,
                    tier_reason="New contact",
                    should_process=True
                )
            else:
                # Quick analysis for this contact
                stats = self._quick_contact_analysis(sender_emails, sender_email, user_id)
            
            # Cache the result
            self._contact_tiers[sender_email] = stats
            return stats
    
    def _quick_contact_analysis(self, sender_emails: List[Email], sender_email: str, user_id: int) -> ContactEngagementStats:
        """Perform quick analysis for a single contact"""
        
        emails_received = len(sender_emails)
        first_email_date = min(email.email_date for email in sender_emails if email.email_date)
        last_email_date = max(email.email_date for email in sender_emails if email.email_date)
        
        # Quick response rate estimation (simplified)
        with self.db_manager.get_session() as session:
            sent_to_sender = session.query(Email).filter(
                and_(
                    Email.user_id == user_id,
                    Email.recipient_emails.ilike(f"%{sender_email}%")
                )
            ).count()
        
        response_rate = min(1.0, sent_to_sender / emails_received) if emails_received > 0 else 0.0
        
        days_since_last = (datetime.now() - last_email_date).days if last_email_date else 0
        
        stats = ContactEngagementStats(
            email_address=sender_email,
            name=sender_emails[0].sender_name if hasattr(sender_emails[0], 'sender_name') else None,
            emails_received=emails_received,
            emails_responded_to=sent_to_sender,
            last_email_date=last_email_date,
            first_email_date=first_email_date,
            response_rate=response_rate,
            days_since_last_email=days_since_last,
            avg_days_between_emails=0.0,
            tier=ContactTier.UNCLASSIFIED,
            tier_reason="Quick analysis",
            should_process=True
        )
        
        tier, reason, should_process = self._determine_contact_tier(stats)
        stats.tier = tier
        stats.tier_reason = reason
        stats.should_process = should_process
        
        return stats
    
    def _make_processing_decision(self, sender_stats: ContactEngagementStats, email_data: Dict) -> Tuple[bool, str, float]:
        """
        Make the final decision on whether to process this email based on sender tier
        and additional email characteristics.
        """
        
        # Base decision on sender tier
        base_decision = sender_stats.should_process
        base_reason = f"Sender tier: {sender_stats.tier.value} - {sender_stats.tier_reason}"
        
        # Additional quality checks
        confidence = 0.8
        
        # Check for obvious spam/promotional indicators
        subject = email_data.get('subject', '').lower()
        spam_indicators = ['unsubscribe', 'marketing', 'promotion', 'sale', 'deal', 'offer', '% off']
        
        if any(indicator in subject for indicator in spam_indicators):
            if sender_stats.tier != ContactTier.TIER_1:  # Don't filter Tier 1 contacts
                return False, f"{base_reason} + Spam indicators detected", 0.9
        
        # Check for very short or empty content
        body = email_data.get('body', '') or email_data.get('body_text', '')
        if len(body.strip()) < 50 and sender_stats.tier == ContactTier.TIER_LAST:
            return False, f"{base_reason} + Low content quality", 0.85
        
        return base_decision, base_reason, confidence
    
    def force_tier_refresh(self, user_id: int):
        """Force a refresh of contact tiers (useful for manual testing)"""
        logger.info(f"🔄 Forcing contact tier refresh for user {user_id}")
        self._contact_tiers.clear()
        self._last_tier_update = None
        self._analyze_all_contacts(user_id)

    def clear_corrupted_cache(self):
        """Clear any corrupted cache data and reinitialize"""
        logger.info("🧹 Clearing potentially corrupted contact tier cache")
        
        # Check for corrupted objects in cache
        corrupted_keys = []
        for email_address, obj in self._contact_tiers.items():
            if not isinstance(obj, ContactEngagementStats):
                logger.warning(f"❌ Found corrupted object in cache: {email_address} -> {type(obj)}")
                corrupted_keys.append(email_address)
        
        # Remove corrupted entries
        for key in corrupted_keys:
            del self._contact_tiers[key]
        
        if corrupted_keys:
            logger.info(f"🧹 Removed {len(corrupted_keys)} corrupted cache entries")
        
        # Reset timestamps to force fresh analysis
        self._last_tier_update = None
    
    def get_contact_tier_summary(self, user_id: int) -> Dict:
        """Get a summary of contact tiers for reporting/debugging"""
        if not self._contact_tiers:
            self._analyze_all_contacts(user_id)
        
        tier_summary = {
            'total_contacts': len(self._contact_tiers),
            'last_updated': self._last_tier_update.isoformat() if self._last_tier_update else None,
            'tier_counts': {},
            'examples': {}
        }
        
        # Count by tier
        for tier in ContactTier:
            contacts_in_tier = [stats for stats in self._contact_tiers.values() if stats.tier == tier]
            tier_summary['tier_counts'][tier.value] = len(contacts_in_tier)
            
            # Add examples
            examples = [stats.email_address for stats in contacts_in_tier[:5]]
            tier_summary['examples'][tier.value] = examples
        
        return tier_summary
    
    def override_contact_tier(self, email_address: str, new_tier: ContactTier, reason: str = "Manual override"):
        """Allow manual override of contact tier (for edge cases)"""
        email_address = email_address.lower().strip()
        
        if email_address in self._contact_tiers:
            # Safety check: ensure we have a ContactEngagementStats object
            contact_stats = self._contact_tiers[email_address]
            if not isinstance(contact_stats, ContactEngagementStats):
                logger.error(f"❌ Invalid object type in contact tiers: {type(contact_stats)} for {email_address}")
                # Create a proper ContactEngagementStats object
                contact_stats = ContactEngagementStats(
                    email_address=email_address,
                    name=None,
                    emails_received=0,
                    emails_responded_to=0,
                    last_email_date=datetime.now(),
                    first_email_date=datetime.now(),
                    response_rate=0.0,
                    days_since_last_email=0,
                    avg_days_between_emails=0.0,
                    tier=new_tier,
                    tier_reason=reason,
                    should_process=new_tier != ContactTier.TIER_LAST
                )
                self._contact_tiers[email_address] = contact_stats
            else:
                old_tier = contact_stats.tier
                contact_stats.tier = new_tier
                contact_stats.tier_reason = reason
                contact_stats.should_process = new_tier != ContactTier.TIER_LAST
                
                logger.info(f"✏️  Manual tier override: {email_address} {old_tier.value} -> {new_tier.value}")
        else:
            # Create new contact stats for unknown contact
            contact_stats = ContactEngagementStats(
                email_address=email_address,
                name=None,
                emails_received=0,
                emails_responded_to=0,
                last_email_date=datetime.now(),
                first_email_date=datetime.now(),
                response_rate=0.0,
                days_since_last_email=0,
                avg_days_between_emails=0.0,
                tier=new_tier,
                tier_reason=reason,
                should_process=new_tier != ContactTier.TIER_LAST
            )
            self._contact_tiers[email_address] = contact_stats
            logger.info(f"✏️  Created new contact with tier: {email_address} -> {new_tier.value}")

    def cleanup_existing_low_quality_data(self, user_id: int) -> Dict[str, Any]:
        """
        Clean up existing database records that came from Tier LAST contacts.
        This removes emails, tasks, and insights generated from low-quality contacts.
        
        Args:
            user_id: User ID to clean up data for
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            from models.database import get_db_manager, Email, Task, Person
            
            logger.info(f"🧹 Starting cleanup of low-quality data for user {user_id}")
            
            # Get contact tier summary to identify Tier LAST contacts
            tier_summary = self.get_contact_tier_summary(user_id)
            
            cleanup_stats = {
                'emails_removed': 0,
                'tasks_removed': 0,
                'people_removed': 0,
                'insights_cleaned': 0,
                'tier_last_contacts': 0
            }
            
            with get_db_manager().get_session() as session:
                # Get all people for this user
                all_people = session.query(Person).filter(Person.user_id == user_id).all()
                
                tier_last_emails = set()
                tier_last_people_ids = []
                
                for person in all_people:
                    if person.email_address:
                        contact_stats = self._get_contact_stats(person.email_address.lower(), user_id)
                        
                        if contact_stats.tier == ContactTier.TIER_LAST:
                            tier_last_emails.add(person.email_address.lower())
                            tier_last_people_ids.append(person.id)
                            cleanup_stats['tier_last_contacts'] += 1
                
                logger.info(f"🗑️  Found {len(tier_last_emails)} Tier LAST contacts to clean up")
                
                # Remove emails from Tier LAST contacts
                if tier_last_emails:
                    emails_to_remove = session.query(Email).filter(
                        Email.user_id == user_id,
                        Email.sender.ilike_any([f"%{email}%" for email in tier_last_emails])
                    ).all()
                    
                    for email in emails_to_remove:
                        session.delete(email)
                        cleanup_stats['emails_removed'] += 1
                
                # Remove tasks that might have been generated from these emails
                # This is approximate - we can't definitively trace task origin
                if tier_last_people_ids:
                    # Remove tasks that mention these people in description
                    all_tasks = session.query(Task).filter(Task.user_id == user_id).all()
                    
                    for task in all_tasks:
                        if task.description:
                            # Check if task mentions any Tier LAST contact
                            task_desc_lower = task.description.lower()
                            for person_id in tier_last_people_ids:
                                person = session.query(Person).get(person_id)
                                if person and person.name:
                                    if person.name.lower() in task_desc_lower:
                                        session.delete(task)
                                        cleanup_stats['tasks_removed'] += 1
                                        break
                
                # Optionally remove Tier LAST people entirely (uncomment if desired)
                # for person_id in tier_last_people_ids:
                #     person = session.query(Person).get(person_id)
                #     if person:
                #         session.delete(person)
                #         cleanup_stats['people_removed'] += 1
                
                session.commit()
                
            logger.info(f"✅ Cleanup complete: {cleanup_stats}")
            
            return {
                'success': True,
                'cleanup_stats': cleanup_stats,
                'message': f"Cleaned up {cleanup_stats['emails_removed']} emails and {cleanup_stats['tasks_removed']} tasks from {cleanup_stats['tier_last_contacts']} Tier LAST contacts"
            }
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def set_all_contacts_tier_1(self, user_email: str):
        """Set all contacts from sent emails to Tier 1"""
        from models.database import get_db_manager
        
        try:
            # Get user from database
            db_user = get_db_manager().get_user_by_email(user_email)
            if not db_user:
                logger.error(f"User {user_email} not found")
                return False
            
            # Get all sent emails
            with get_db_manager().get_session() as session:
                sent_emails = session.query(Email).filter(
                    Email.user_id == db_user.id,
                    Email.sender.ilike(f'%{user_email}%')  # Emails sent by the user
                ).all()
                
                # Extract all unique recipients
                recipients = set()
                for email in sent_emails:
                    # Add the user's own email addresses
                    if email.sender:
                        sender_email = parseaddr(email.sender)[1].lower()
                        if sender_email and '@' in sender_email:
                            recipients.add(sender_email)
                    
                    # Add recipients
                    if email.recipient_emails:
                        if isinstance(email.recipient_emails, str):
                            try:
                                recipient_list = json.loads(email.recipient_emails)
                            except:
                                recipient_list = [email.recipient_emails]
                        else:
                            recipient_list = email.recipient_emails
                            
                        for recipient in recipient_list:
                            email_addr = parseaddr(recipient)[1].lower()
                            if email_addr and '@' in email_addr:
                                recipients.add(email_addr)
                
                # Set all recipients to Tier 1 with proper stats
                for recipient in recipients:
                    stats = ContactEngagementStats(
                        email_address=recipient,
                        name=None,  # We don't have the name here
                        emails_received=1,  # Placeholder value
                        emails_responded_to=1,  # Assume responded since it's from sent emails
                        last_email_date=datetime.now(timezone.utc),
                        first_email_date=datetime.now(timezone.utc),
                        response_rate=1.0,  # Perfect response rate for Tier 1
                        days_since_last_email=0,
                        avg_days_between_emails=0,
                        tier=ContactTier.TIER_1,
                        tier_reason="Sent email contact",
                        should_process=True
                    )
                    self._contact_tiers[recipient] = stats
                
                logger.info(f"✅ Set {len(recipients)} contacts to Tier 1 for {user_email}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to set contacts to Tier 1: {str(e)}")
            return False

# Global instance
email_quality_filter = EmailQualityFilter()

def analyze_email_quality(email_data: Dict, user_id: int) -> EmailQualityResult:
    """
    Convenience function for email quality analysis.
    
    Usage:
        result = analyze_email_quality(email_data, user_id)
        if result.should_process:
            # Process the email
            pass
    """
    return email_quality_filter.analyze_email_quality(email_data, user_id)

def force_refresh_contact_tiers(user_id: int):
    """Force refresh of contact tiers (useful for monthly review)"""
    email_quality_filter.force_tier_refresh(user_id)

def get_contact_tier_summary(user_id: int) -> Dict:
    """Get summary of contact tiers for debugging/monitoring"""
    return email_quality_filter.get_contact_tier_summary(user_id) 