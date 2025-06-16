"""
Validation Utilities
===================

Input validation helpers for API endpoints.
"""

import re
from datetime import datetime
from typing import Optional, Tuple


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate date range.
    
    Args:
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
        if start_date and end_date:
            if start >= end:
                return False, "Start date must be before end date"
                
        return True, None
        
    except ValueError as e:
        return False, f"Invalid date format: {str(e)}"


def validate_pagination(page: int, per_page: int) -> Tuple[bool, Optional[str]]:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number
        per_page: Items per page
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if page < 1:
        return False, "Page must be greater than 0"
    
    if per_page < 1 or per_page > 100:
        return False, "Per page must be between 1 and 100"
    
    return True, None 