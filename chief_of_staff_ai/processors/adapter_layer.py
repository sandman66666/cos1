# Adapter Layer - Stub Implementation for Legacy Compatibility
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TaskExtractor:
    """Stub implementation of legacy task extractor"""
    
    def extract_tasks_from_email(self, email_data: Dict, user_id: int) -> Dict[str, Any]:
        """Extract tasks from email - legacy adapter"""
        try:
            return {
                'success': True,
                'tasks_found': 0,
                'tasks': [],
                'processing_notes': ['Legacy adapter stub - no tasks extracted']
            }
        except Exception as e:
            logger.error(f"Error in legacy task extraction: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class EmailIntelligence:
    """Stub implementation of legacy email intelligence"""
    
    def process_email(self, email_data: Dict, user_id: int) -> Dict[str, Any]:
        """Process email intelligence - legacy adapter"""
        try:
            return {
                'success': True,
                'intelligence': {},
                'processing_notes': ['Legacy adapter stub - no intelligence extracted']
            }
        except Exception as e:
            logger.error(f"Error in legacy email intelligence: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class EmailNormalizer:
    """Stub implementation of legacy email normalizer"""
    
    def normalize_gmail_email(self, email_data: Dict) -> Dict[str, Any]:
        """Normalize Gmail email - legacy adapter"""
        try:
            # Basic normalization - just pass through the data
            normalized = email_data.copy()
            normalized['normalized'] = True
            normalized['processing_notes'] = ['Legacy adapter stub - basic normalization']
            return normalized
        except Exception as e:
            logger.error(f"Error in legacy email normalization: {str(e)}")
            return {
                'error': True,
                'error_message': str(e)
            }
    
    def normalize_user_emails(self, user_email: str, limit: int = 50) -> Dict[str, Any]:
        """Normalize user emails in batch - legacy adapter"""
        try:
            return {
                'success': True,
                'emails_normalized': 0,
                'processing_notes': ['Legacy adapter stub - no emails normalized']
            }
        except Exception as e:
            logger.error(f"Error in legacy batch normalization: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instances for legacy compatibility
task_extractor = TaskExtractor()
email_intelligence = EmailIntelligence()
email_normalizer = EmailNormalizer() 