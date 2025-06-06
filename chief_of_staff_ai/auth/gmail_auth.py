# Handles Gmail OAuth setup

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings
from models.database import get_db_manager

logger = logging.getLogger(__name__)

class GmailAuthHandler:
    """Handles Gmail OAuth authentication and token management with database persistence"""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = settings.GMAIL_SCOPES
        
    def get_authorization_url(self, user_id: str, state: str = None) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL for Gmail access
        
        Args:
            user_id: Unique identifier for the user
            state: Optional state parameter for security
            
        Returns:
            Tuple of (authorization_url, state)
        """
        try:
            flow = Flow.from_client_config(
                settings.get_gmail_auth_config(),
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state or user_id,
                prompt='consent'  # Force consent to get refresh token
            )
            
            logger.info(f"Generated authorization URL for user {user_id}")
            return auth_url, state
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {str(e)}")
            raise
    
    def handle_oauth_callback(self, authorization_code: str, state: str = None) -> Dict:
        """
        Handle OAuth callback and exchange authorization code for tokens
        
        Args:
            authorization_code: Authorization code from OAuth callback
            state: State parameter from OAuth callback
            
        Returns:
            Dictionary containing success status and user info or error
        """
        try:
            flow = Flow.from_client_config(
                settings.get_gmail_auth_config(),
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange authorization code for tokens
            # Note: Google automatically adds 'openid' scope when requesting profile/email
            # We need to handle this gracefully
            try:
                flow.fetch_token(code=authorization_code)
            except Exception as token_error:
                # If there's a scope mismatch due to automatic 'openid' scope, try a more permissive approach
                if "scope" in str(token_error).lower():
                    logger.warning(f"Scope validation issue, retrying with relaxed validation: {str(token_error)}")
                    # Create a new flow with additional scopes including openid
                    extended_scopes = self.scopes + ['openid']
                    flow = Flow.from_client_config(
                        settings.get_gmail_auth_config(),
                        scopes=extended_scopes
                    )
                    flow.redirect_uri = self.redirect_uri
                    flow.fetch_token(code=authorization_code)
                else:
                    raise token_error
            
            credentials = flow.credentials
            
            # Get user information
            user_info = self._get_user_info(credentials)
            
            if not user_info.get('email'):
                raise Exception("Failed to get user email from Google")
            
            # Prepare credentials for database storage
            credentials_data = {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'expires_at': credentials.expiry,
                'scopes': credentials.scopes
            }
            
            # Create or update user in database
            user = get_db_manager().create_or_update_user(user_info, credentials_data)
            
            logger.info(f"Successfully authenticated user: {user.email}")
            
            return {
                'success': True,
                'user_info': user_info,
                'user_email': user.email,
                'access_token': credentials.token,
                'has_refresh_token': bool(credentials.refresh_token),
                'user_id': user.id
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
    
    def revoke_credentials(self, user_email: str) -> bool:
        """
        Revoke stored credentials for a user
        
        Args:
            user_email: Email of the user
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user from database
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return False
            
            # Clear credentials in database
            credentials_data = {
                'access_token': None,
                'refresh_token': None,
                'expires_at': None,
                'scopes': []
            }
            get_db_manager().create_or_update_user(user.to_dict(), credentials_data)
            
            logger.info(f"Revoked credentials for user: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials for {user_email}: {str(e)}")
            return False
    
    def is_authenticated(self, user_email: str) -> bool:
        """
        Check if user has valid authentication
        
        Args:
            user_email: Email of the user
            
        Returns:
            True if user has valid credentials, False otherwise
        """
        credentials = self.get_valid_credentials(user_email)
        return credentials is not None
    
    def test_gmail_access(self, user_email: str) -> bool:
        """
        Test if Gmail access is working for a user
        
        Args:
            user_email: Email of the user
            
        Returns:
            True if Gmail access is working, False otherwise
        """
        try:
            credentials = self.get_valid_credentials(user_email)
            if not credentials:
                return False
            
            # Build Gmail service and test with a simple call
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            
            logger.info(f"Gmail access test successful for {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Gmail access test failed for {user_email}: {str(e)}")
            return False
    
    def get_user_by_email(self, user_email: str) -> Optional[Dict]:
        """
        Get user information by email
        
        Args:
            user_email: Email of the user
            
        Returns:
            User dictionary or None
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Failed to get user {user_email}: {str(e)}")
            return None
    
    def _get_user_info(self, credentials: Credentials) -> Dict:
        """
        Get user information from Google OAuth2 API
        
        Args:
            credentials: Valid Google credentials
            
        Returns:
            Dictionary containing user information
        """
        try:
            oauth2_service = build('oauth2', 'v2', credentials=credentials)
            user_info = oauth2_service.userinfo().get().execute()
            return user_info
            
        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            return {}
    
    def get_authentication_status(self, user_email: str) -> Dict:
        """
        Get detailed authentication status for a user
        
        Args:
            user_email: Email of the user
            
        Returns:
            Dictionary with authentication status details
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {
                    'authenticated': False,
                    'gmail_access': False,
                    'error': 'User not found'
                }
            
            credentials = self.get_valid_credentials(user_email)
            if not credentials:
                return {
                    'authenticated': False,
                    'gmail_access': False,
                    'error': 'No valid credentials'
                }
            
            gmail_access = self.test_gmail_access(user_email)
            
            return {
                'authenticated': True,
                'gmail_access': gmail_access,
                'has_refresh_token': bool(user.refresh_token),
                'token_expired': credentials.expired if credentials else True,
                'scopes': user.scopes or [],
                'user_info': user.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Failed to get authentication status for {user_email}: {str(e)}")
            return {
                'authenticated': False,
                'gmail_access': False,
                'error': str(e)
            }

# Create global instance
gmail_auth = GmailAuthHandler()