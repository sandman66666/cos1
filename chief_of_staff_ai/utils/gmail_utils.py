"""
Gmail Utility Functions for AI Chief of Staff

Provides utilities for Gmail integration, including search URL generation
for linking back to original emails from tasks, insights, and people profiles.
"""

import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any


def generate_gmail_search_url(
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    thread_id: Optional[str] = None
) -> str:
    """
    Generate Gmail search URL for direct access to emails
    
    Args:
        sender: Email address of sender
        subject: Email subject (or part of it)
        keywords: Keywords to search for in email content
        date_from: Start date for date range search
        date_to: End date for date range search
        thread_id: Gmail thread ID for specific thread
    
    Returns:
        Gmail search URL that opens in Gmail web interface
    """
    search_parts = []
    
    # Add sender filter
    if sender:
        search_parts.append(f"from:{sender}")
    
    # Add subject filter
    if subject:
        # Clean subject for search (remove Re:, Fwd:, etc.)
        clean_subject = subject.replace("Re: ", "").replace("Fwd: ", "").replace("RE: ", "").replace("FWD: ", "")
        # Use quotes for exact phrase matching
        search_parts.append(f'subject:"{clean_subject}"')
    
    # Add keyword search
    if keywords:
        search_parts.append(keywords)
    
    # Add date range
    if date_from:
        search_parts.append(f"after:{date_from.strftime('%Y/%m/%d')}")
    
    if date_to:
        search_parts.append(f"before:{date_to.strftime('%Y/%m/%d')}")
    
    # Specific thread ID takes precedence
    if thread_id:
        search_parts = [f"rfc822msgid:{thread_id}"]
    
    # Combine search terms
    search_query = " ".join(search_parts)
    
    # URL encode the search query
    encoded_query = urllib.parse.quote(search_query)
    
    # Generate Gmail search URL
    gmail_url = f"https://mail.google.com/mail/u/0/#search/{encoded_query}"
    
    return gmail_url


def generate_email_link(email_data: Dict[str, Any]) -> str:
    """
    Generate Gmail link for a specific email using available metadata
    
    Args:
        email_data: Email data dictionary with sender, subject, date, etc.
    
    Returns:
        Gmail search URL for the specific email
    """
    return generate_gmail_search_url(
        sender=email_data.get('sender'),
        subject=email_data.get('subject'),
        date_from=email_data.get('email_date')
    )


def generate_sender_history_link(sender_email: str, days_back: int = 30) -> str:
    """
    Generate Gmail link to view email history with a specific sender
    
    Args:
        sender_email: Email address of the sender
        days_back: Number of days back to include in search
    
    Returns:
        Gmail search URL for sender's email history
    """
    date_from = datetime.now().replace(day=datetime.now().day - days_back)
    
    return generate_gmail_search_url(
        sender=sender_email,
        date_from=date_from
    )


def generate_topic_emails_link(topic: str, days_back: int = 90) -> str:
    """
    Generate Gmail link to view emails related to a specific topic
    
    Args:
        topic: Topic/keyword to search for
        days_back: Number of days back to include in search
    
    Returns:
        Gmail search URL for topic-related emails
    """
    date_from = datetime.now().replace(day=datetime.now().day - days_back)
    
    return generate_gmail_search_url(
        keywords=topic,
        date_from=date_from
    )


def create_task_gmail_link(task_data: Dict[str, Any], email_data: Dict[str, Any]) -> str:
    """
    Create Gmail link for a task based on its source email
    
    Args:
        task_data: Task information
        email_data: Source email data
    
    Returns:
        Gmail search URL for the source email
    """
    return generate_email_link(email_data)


def create_people_gmail_link(person_email: str, name: Optional[str] = None) -> str:
    """
    Create Gmail link for viewing all emails from a specific person
    
    Args:
        person_email: Person's email address
        name: Person's name (optional, for better search)
    
    Returns:
        Gmail search URL for person's email history
    """
    return generate_sender_history_link(person_email)


def extract_gmail_thread_id(gmail_message: Dict[str, Any]) -> Optional[str]:
    """
    Extract thread ID from Gmail API message for more precise linking
    
    Args:
        gmail_message: Raw Gmail message from API
    
    Returns:
        Thread ID if available, None otherwise
    """
    return gmail_message.get('threadId')


def clean_subject_for_search(subject: str) -> str:
    """
    Clean email subject for better Gmail search results
    
    Args:
        subject: Original email subject
    
    Returns:
        Cleaned subject suitable for Gmail search
    """
    if not subject:
        return ""
    
    # Remove common prefixes
    prefixes = ["Re: ", "RE: ", "Fwd: ", "FWD: ", "Fw: ", "FW: "]
    clean_subject = subject
    
    for prefix in prefixes:
        if clean_subject.startswith(prefix):
            clean_subject = clean_subject[len(prefix):]
    
    # Remove extra whitespace
    clean_subject = clean_subject.strip()
    
    return clean_subject 