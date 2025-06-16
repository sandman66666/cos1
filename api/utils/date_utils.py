"""
Date Utilities
=============

Date formatting and manipulation utilities.
"""

from datetime import datetime, timezone
from typing import Optional


def format_datetime(dt: datetime) -> str:
    """
    Format datetime for API responses.
    
    Args:
        dt: Datetime object
        
    Returns:
        ISO formatted string
    """
    return dt.isoformat() if dt else None


def parse_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse datetime string.
    
    Args:
        date_str: Date string in ISO format
        
    Returns:
        Datetime object or None if invalid
    """
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def get_time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        dt: Datetime object
        
    Returns:
        Human-readable time difference
    """
    if not dt:
        return "Unknown"
    
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds // 86400)
        if days < 7:
            return f"{days}d ago"
        elif days < 30:
            weeks = int(days // 7)
            return f"{weeks}w ago"
        else:
            months = int(days // 30)
            return f"{months}mo ago" 