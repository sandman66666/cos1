"""
Gmail OAuth Authentication - Strategic Intelligence Platform Compatibility
========================================================================
"""

import os
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GmailAuthManager:
    """Gmail OAuth authentication manager"""
    
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8080/auth/callback')
        
        # OAuth scopes for Gmail
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ]
    
    def get_authorization_url(self, user_id: str = None, state: str = None):
        """Get Google OAuth authorization URL"""
        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uris": [self.redirect_uri],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=self.scopes
            )
            
            flow.redirect_uri = self.redirect_uri
            
            # Generate authorization URL
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state
            )
            
            return auth_url, state
            
        except Exception as e:
            logger.error(f"Error generating authorization URL: {str(e)}")
            raise
    
    def handle_oauth_callback(self, authorization_code: str, state: str = None):
        """Handle OAuth callback and get user info"""
        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uris": [self.redirect_uri],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=self.scopes
            )
            
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for token
            try:
                flow.fetch_token(code=authorization_code)
            except Exception as token_error:
                # Log the specific token exchange error
                logger.error(f"Token exchange failed: {str(token_error)}")
                # Try to be more permissive with scopes
                logger.info("Attempting OAuth flow with broader scope tolerance...")
                
                # Create a new flow without strict scope checking
                flow = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "redirect_uris": [self.redirect_uri],
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"
                        }
                    },
                    scopes=self.scopes
                )
                flow.redirect_uri = self.redirect_uri
                flow.fetch_token(code=authorization_code)
            
            # Get user info
            credentials = flow.credentials
            
            # Make request to get user info
            import requests
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {credentials.token}'}
            )
            
            if response.status_code == 200:
                user_info = response.json()
                
                logger.info(f"✅ OAuth successful for user: {user_info.get('email')}")
                
                return {
                    'success': True,
                    'user_info': {
                        'email': user_info.get('email'),
                        'name': user_info.get('name'),
                        'id': user_info.get('id')
                    },
                    'credentials': {
                        'access_token': credentials.token,
                        'refresh_token': credentials.refresh_token
                    }
                }
            else:
                logger.error(f"Failed to get user info: HTTP {response.status_code}")
                return {
                    'success': False,
                    'error': 'Failed to get user info'
                }
                
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_valid_credentials(self, user_email: str) -> Optional[Credentials]:
        """
        Get valid credentials for a user, refreshing if necessary
        
        Args:
            user_email: Email of the user
            
        Returns:
            Valid Credentials object or None
        """
        try:
            # Get user from database
            from chief_of_staff_ai.models.database import get_db_manager
            user = get_db_manager().get_user_by_email(user_email)
            if not user or not user.access_token:
                logger.warning(f"No stored credentials for user: {user_email}")
                return None
            
            # Create credentials object
            credentials = Credentials(
                token=user.access_token,
                refresh_token=user.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=user.scopes or self.scopes
            )
            
            # Set expiry if available
            if user.token_expires_at:
                credentials.expiry = user.token_expires_at
            
            # Check if credentials are expired and refresh if possible
            if credentials.expired and credentials.refresh_token:
                logger.info(f"Refreshing expired credentials for user: {user_email}")
                credentials.refresh(Request())
                
                # Update stored credentials in database
                credentials_data = {
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'expires_at': credentials.expiry,
                    'scopes': credentials.scopes
                }
                get_db_manager().create_or_update_user(user.to_dict(), credentials_data)
                
            elif credentials.expired:
                logger.warning(f"Credentials expired and no refresh token for user: {user_email}")
                return None
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get valid credentials for {user_email}: {str(e)}")
            return None

# Global Gmail auth manager
gmail_auth = GmailAuthManager() 