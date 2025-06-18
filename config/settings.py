"""
Settings Configuration - Strategic Intelligence Platform Compatibility
====================================================================
"""

import os
from dataclasses import dataclass

@dataclass
class Settings:
    """Settings for Strategic Intelligence Platform"""
    
    # Flask Configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    SESSION_TIMEOUT_HOURS: int = 24
    
    # Claude Configuration
    ANTHROPIC_API_KEY: str = os.getenv('ANTHROPIC_API_KEY', '')
    CLAUDE_MODEL: str = "claude-opus-4-20250514"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET: str = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI: str = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8080/auth/callback')
    
    def create_directories(self):
        """Create necessary directories"""
        pass

# Global settings instance
settings = Settings() 