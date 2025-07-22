# Authentication API Endpoints - User Management and Security
# These endpoints provide comprehensive authentication, authorization, and user management

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
import json
import jwt
import hashlib
import secrets
import re
from email_validator import validate_email, EmailNotValidError

# Import the integration manager and models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'chief_of_staff_ai'))

from chief_of_staff_ai.models.database import User, UserSession, ApiKey, get_db_manager
from config.settings import settings

logger = logging.getLogger(__name__)

# Create Blueprint
auth_api_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')

# JWT Configuration
JWT_SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', secrets.token_urlsafe(32))
JWT_EXPIRATION_HOURS = getattr(settings, 'JWT_EXPIRATION_HOURS', 24)
JWT_REFRESH_DAYS = getattr(settings, 'JWT_REFRESH_DAYS', 30)

# =====================================================================
# AUTHENTICATION UTILITIES
# =====================================================================

def generate_password_hash(password: str) -> str:
    """Generate secure password hash"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{password_hash.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        salt, stored_hash = password_hash.split(':')
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return computed_hash.hex() == stored_hash
    except (ValueError, TypeError):
        return False

def generate_jwt_token(user_id: int, user_email: str, role: str = 'user', expires_in_hours: int = None) -> str:
    """Generate JWT access token"""
    expires_in = expires_in_hours or JWT_EXPIRATION_HOURS
    expiration = datetime.utcnow() + timedelta(hours=expires_in)
    
    payload = {
        'user_id': user_id,
        'email': user_email,
        'role': role,
        'exp': expiration,
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

def generate_refresh_token(user_id: int, user_email: str) -> str:
    """Generate JWT refresh token"""
    expiration = datetime.utcnow() + timedelta(days=JWT_REFRESH_DAYS)
    
    payload = {
        'user_id': user_id,
        'email': user_email,
        'exp': expiration,
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

def verify_jwt_token(token: str) -> Optional[Dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def validate_password_strength(password: str) -> List[str]:
    """Validate password strength and return list of issues"""
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        issues.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append("Password must contain at least one special character")
    
    return issues

def require_jwt_auth(roles: List[str] = None):
    """Decorator to require JWT authentication with optional role checking"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    'success': False,
                    'error': 'Authorization header required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            
            token = auth_header.split(' ')[1]
            payload = verify_jwt_token(token)
            
            if not payload:
                return jsonify({
                    'success': False,
                    'error': 'Invalid or expired token',
                    'code': 'INVALID_TOKEN'
                }), 401
            
            if payload.get('type') != 'access':
                return jsonify({
                    'success': False,
                    'error': 'Invalid token type',
                    'code': 'INVALID_TOKEN_TYPE'
                }), 401
            
            # Role checking
            if roles and payload.get('role') not in roles:
                return jsonify({
                    'success': False,
                    'error': 'Insufficient permissions',
                    'code': 'INSUFFICIENT_PERMISSIONS'
                }), 403
            
            # Store user info in g for easy access
            g.user_id = payload['user_id']
            g.user_email = payload['email']
            g.user_role = payload.get('role', 'user')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def success_response(data: Any, message: str = None) -> tuple:
    """Create standardized success response"""
    response = {
        'success': True,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    }
    if message:
        response['message'] = message
    return jsonify(response), 200

def error_response(error: str, code: str = None, status_code: int = 400) -> tuple:
    """Create standardized error response"""
    response = {
        'success': False,
        'error': error,
        'timestamp': datetime.utcnow().isoformat()
    }
    if code:
        response['code'] = code
    return jsonify(response), status_code

# =====================================================================
# USER REGISTRATION AND LOGIN ENDPOINTS
# =====================================================================

@auth_api_bp.route('/register', methods=['POST'])
def register_user():
    """
    Register a new user account.
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        required_fields = ['email', 'password', 'full_name']
        for field in required_fields:
            if not data.get(field):
                return error_response(f"Missing required field: {field}", "MISSING_FIELD")
        
        email = data['email'].lower().strip()
        password = data['password']
        full_name = data['full_name'].strip()
        
        # Validate email format
        try:
            validate_email(email)
        except EmailNotValidError:
            return error_response("Invalid email format", "INVALID_EMAIL")
        
        # Validate password strength
        password_issues = validate_password_strength(password)
        if password_issues:
            return error_response(f"Password validation failed: {', '.join(password_issues)}", "WEAK_PASSWORD")
        
        with get_db_manager().get_session() as session:
            # Check if user already exists
            existing_user = session.query(User).filter(User.email == email).first()
            if existing_user:
                return error_response("User with this email already exists", "USER_EXISTS", 409)
            
            # Create new user
            password_hash = generate_password_hash(password)
            
            new_user = User(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=data.get('role', 'user'),
                is_active=True,
                created_at=datetime.utcnow(),
                last_login=None,
                email_verified=False,
                preferences=data.get('preferences', {})
            )
            
            session.add(new_user)
            session.commit()
            
            # Generate tokens
            access_token = generate_jwt_token(new_user.id, new_user.email, new_user.role)
            refresh_token = generate_refresh_token(new_user.id, new_user.email)
            
            # Create user session
            user_session = UserSession(
                user_id=new_user.id,
                session_token=refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=JWT_REFRESH_DAYS),
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            session.add(user_session)
            session.commit()
            
            logger.info(f"New user registered: {email} (ID: {new_user.id})")
            
            return success_response({
                'user': {
                    'id': new_user.id,
                    'email': new_user.email,
                    'full_name': new_user.full_name,
                    'role': new_user.role,
                    'created_at': new_user.created_at.isoformat()
                },
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer',
                    'expires_in': JWT_EXPIRATION_HOURS * 3600
                }
            }, "User registered successfully")
            
    except Exception as e:
        logger.error(f"Error in user registration: {str(e)}")
        return error_response(f"Registration failed: {str(e)}", "REGISTRATION_ERROR", 500)

@auth_api_bp.route('/login', methods=['POST'])
def login_user():
    """
    Login user and return authentication tokens.
    """
    try:
        data = request.get_json() or {}
        
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        if not email or not password:
            return error_response("Email and password are required", "MISSING_CREDENTIALS")
        
        with get_db_manager().get_session() as session:
            # Find user
            user = session.query(User).filter(User.email == email).first()
            
            if not user or not verify_password(password, user.password_hash):
                return error_response("Invalid email or password", "INVALID_CREDENTIALS", 401)
            
            if not user.is_active:
                return error_response("Account is deactivated", "ACCOUNT_DEACTIVATED", 401)
            
            # Update last login
            user.last_login = datetime.utcnow()
            
            # Generate tokens
            token_expiry = JWT_EXPIRATION_HOURS * 24 if remember_me else JWT_EXPIRATION_HOURS
            access_token = generate_jwt_token(user.id, user.email, user.role, token_expiry)
            refresh_token = generate_refresh_token(user.id, user.email)
            
            # Create user session
            user_session = UserSession(
                user_id=user.id,
                session_token=refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=JWT_REFRESH_DAYS),
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            session.add(user_session)
            session.commit()
            
            logger.info(f"User logged in: {email} (ID: {user.id})")
            
            return success_response({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'last_login': user.last_login.isoformat(),
                    'preferences': user.preferences
                },
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer',
                    'expires_in': token_expiry * 3600
                }
            }, "Login successful")
            
    except Exception as e:
        logger.error(f"Error in user login: {str(e)}")
        return error_response(f"Login failed: {str(e)}", "LOGIN_ERROR", 500)

@auth_api_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh access token using refresh token.
    """
    try:
        data = request.get_json() or {}
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return error_response("Refresh token is required", "MISSING_REFRESH_TOKEN")
        
        # Verify refresh token
        payload = verify_jwt_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            return error_response("Invalid or expired refresh token", "INVALID_REFRESH_TOKEN", 401)
        
        with get_db_manager().get_session() as session:
            # Check if session exists and is valid
            user_session = session.query(UserSession).filter(
                UserSession.session_token == refresh_token,
                UserSession.expires_at > datetime.utcnow(),
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                return error_response("Invalid session", "INVALID_SESSION", 401)
            
            # Get user
            user = session.query(User).filter(User.id == payload['user_id']).first()
            if not user or not user.is_active:
                return error_response("User not found or inactive", "INVALID_USER", 401)
            
            # Generate new access token
            access_token = generate_jwt_token(user.id, user.email, user.role)
            
            # Update session activity
            user_session.last_activity = datetime.utcnow()
            session.commit()
            
            return success_response({
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': JWT_EXPIRATION_HOURS * 3600
            }, "Token refreshed successfully")
            
    except Exception as e:
        logger.error(f"Error in token refresh: {str(e)}")
        return error_response(f"Token refresh failed: {str(e)}", "REFRESH_ERROR", 500)

@auth_api_bp.route('/logout', methods=['POST'])
@require_jwt_auth()
def logout_user():
    """
    Logout user and invalidate session.
    """
    try:
        data = request.get_json() or {}
        refresh_token = data.get('refresh_token')
        
        with get_db_manager().get_session() as session:
            # Invalidate specific session if refresh token provided
            if refresh_token:
                user_session = session.query(UserSession).filter(
                    UserSession.session_token == refresh_token,
                    UserSession.user_id == g.user_id
                ).first()
                
                if user_session:
                    user_session.is_active = False
                    user_session.logged_out_at = datetime.utcnow()
            else:
                # Invalidate all sessions for user
                session.query(UserSession).filter(
                    UserSession.user_id == g.user_id,
                    UserSession.is_active == True
                ).update({
                    'is_active': False,
                    'logged_out_at': datetime.utcnow()
                })
            
            session.commit()
            
            logger.info(f"User logged out: {g.user_email} (ID: {g.user_id})")
            
            return success_response({}, "Logout successful")
            
    except Exception as e:
        logger.error(f"Error in user logout: {str(e)}")
        return error_response(f"Logout failed: {str(e)}", "LOGOUT_ERROR", 500)

# =====================================================================
# USER PROFILE AND MANAGEMENT ENDPOINTS
# =====================================================================

@auth_api_bp.route('/profile', methods=['GET'])
@require_jwt_auth()
def get_user_profile():
    """
    Get current user profile information.
    """
    try:
        with get_db_manager().get_session() as session:
            user = session.query(User).filter(User.id == g.user_id).first()
            
            if not user:
                return error_response("User not found", "USER_NOT_FOUND", 404)
            
            # Get active sessions count
            active_sessions = session.query(UserSession).filter(
                UserSession.user_id == g.user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).count()
            
            profile_data = {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'preferences': user.preferences,
                'active_sessions': active_sessions
            }
            
            return success_response(profile_data)
            
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return error_response(f"Profile retrieval failed: {str(e)}", "PROFILE_ERROR", 500)

@auth_api_bp.route('/profile', methods=['PUT'])
@require_jwt_auth()
def update_user_profile():
    """
    Update current user profile information.
    """
    try:
        data = request.get_json() or {}
        
        with get_db_manager().get_session() as session:
            user = session.query(User).filter(User.id == g.user_id).first()
            
            if not user:
                return error_response("User not found", "USER_NOT_FOUND", 404)
            
            # Update allowed fields
            if 'full_name' in data:
                user.full_name = data['full_name'].strip()
            
            if 'preferences' in data:
                # Merge preferences
                current_prefs = user.preferences or {}
                current_prefs.update(data['preferences'])
                user.preferences = current_prefs
            
            user.updated_at = datetime.utcnow()
            session.commit()
            
            return success_response({
                'id': user.id,
                'full_name': user.full_name,
                'preferences': user.preferences,
                'updated_at': user.updated_at.isoformat()
            }, "Profile updated successfully")
            
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return error_response(f"Profile update failed: {str(e)}", "PROFILE_UPDATE_ERROR", 500)

@auth_api_bp.route('/change-password', methods=['POST'])
@require_jwt_auth()
def change_password():
    """
    Change user password.
    """
    try:
        data = request.get_json() or {}
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return error_response("Current and new passwords are required", "MISSING_PASSWORDS")
        
        # Validate new password strength
        password_issues = validate_password_strength(new_password)
        if password_issues:
            return error_response(f"New password validation failed: {', '.join(password_issues)}", "WEAK_PASSWORD")
        
        with get_db_manager().get_session() as session:
            user = session.query(User).filter(User.id == g.user_id).first()
            
            if not user:
                return error_response("User not found", "USER_NOT_FOUND", 404)
            
            # Verify current password
            if not verify_password(current_password, user.password_hash):
                return error_response("Current password is incorrect", "INVALID_CURRENT_PASSWORD", 401)
            
            # Update password
            user.password_hash = generate_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            
            # Invalidate all existing sessions except current one
            current_token = request.headers.get('Authorization', '').replace('Bearer ', '')
            current_payload = verify_jwt_token(current_token)
            
            if current_payload:
                session.query(UserSession).filter(
                    UserSession.user_id == g.user_id,
                    UserSession.is_active == True,
                    UserSession.created_at < datetime.utcnow() - timedelta(minutes=5)  # Keep recent session
                ).update({
                    'is_active': False,
                    'logged_out_at': datetime.utcnow()
                })
            
            session.commit()
            
            logger.info(f"Password changed for user: {g.user_email} (ID: {g.user_id})")
            
            return success_response({}, "Password changed successfully")
            
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return error_response(f"Password change failed: {str(e)}", "PASSWORD_CHANGE_ERROR", 500)

# =====================================================================
# API KEY MANAGEMENT ENDPOINTS
# =====================================================================

@auth_api_bp.route('/api-keys', methods=['GET'])
@require_jwt_auth()
def get_api_keys():
    """
    Get user's API keys (without showing actual keys).
    """
    try:
        with get_db_manager().get_session() as session:
            api_keys = session.query(ApiKey).filter(
                ApiKey.user_id == g.user_id,
                ApiKey.is_active == True
            ).all()
            
            keys_data = []
            for key in api_keys:
                keys_data.append({
                    'id': key.id,
                    'name': key.name,
                    'key_prefix': key.key_hash[:8] + '...',  # Show only prefix
                    'permissions': key.permissions,
                    'created_at': key.created_at.isoformat() if key.created_at else None,
                    'last_used': key.last_used.isoformat() if key.last_used else None,
                    'expires_at': key.expires_at.isoformat() if key.expires_at else None
                })
            
            return success_response({
                'api_keys': keys_data,
                'count': len(keys_data)
            })
            
    except Exception as e:
        logger.error(f"Error getting API keys: {str(e)}")
        return error_response(f"API keys retrieval failed: {str(e)}", "API_KEYS_ERROR", 500)

@auth_api_bp.route('/api-keys', methods=['POST'])
@require_jwt_auth()
def create_api_key():
    """
    Create a new API key for the user.
    """
    try:
        data = request.get_json() or {}
        
        name = data.get('name', '').strip()
        permissions = data.get('permissions', ['read'])
        expires_in_days = data.get('expires_in_days', 365)
        
        if not name:
            return error_response("API key name is required", "MISSING_NAME")
        
        # Generate API key
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with get_db_manager().get_session() as session:
            # Check if name already exists for user
            existing_key = session.query(ApiKey).filter(
                ApiKey.user_id == g.user_id,
                ApiKey.name == name,
                ApiKey.is_active == True
            ).first()
            
            if existing_key:
                return error_response("API key with this name already exists", "NAME_EXISTS", 409)
            
            # Create new API key
            new_api_key = ApiKey(
                user_id=g.user_id,
                name=name,
                key_hash=key_hash,
                permissions=permissions,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
                is_active=True
            )
            
            session.add(new_api_key)
            session.commit()
            
            logger.info(f"API key created for user: {g.user_email} (ID: {g.user_id}, Key: {name})")
            
            return success_response({
                'api_key': {
                    'id': new_api_key.id,
                    'name': new_api_key.name,
                    'key': api_key,  # Only shown once during creation
                    'permissions': new_api_key.permissions,
                    'created_at': new_api_key.created_at.isoformat(),
                    'expires_at': new_api_key.expires_at.isoformat() if new_api_key.expires_at else None
                },
                'warning': 'Store this API key securely. It will not be shown again.'
            }, "API key created successfully")
            
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        return error_response(f"API key creation failed: {str(e)}", "API_KEY_CREATE_ERROR", 500)

@auth_api_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@require_jwt_auth()
def revoke_api_key(key_id: int):
    """
    Revoke (deactivate) an API key.
    """
    try:
        with get_db_manager().get_session() as session:
            api_key = session.query(ApiKey).filter(
                ApiKey.id == key_id,
                ApiKey.user_id == g.user_id
            ).first()
            
            if not api_key:
                return error_response("API key not found", "KEY_NOT_FOUND", 404)
            
            api_key.is_active = False
            api_key.revoked_at = datetime.utcnow()
            session.commit()
            
            logger.info(f"API key revoked: {api_key.name} for user {g.user_email}")
            
            return success_response({}, "API key revoked successfully")
            
    except Exception as e:
        logger.error(f"Error revoking API key: {str(e)}")
        return error_response(f"API key revocation failed: {str(e)}", "API_KEY_REVOKE_ERROR", 500)

# =====================================================================
# SESSION MANAGEMENT ENDPOINTS
# =====================================================================

@auth_api_bp.route('/sessions', methods=['GET'])
@require_jwt_auth()
def get_user_sessions():
    """
    Get user's active sessions.
    """
    try:
        with get_db_manager().get_session() as session:
            user_sessions = session.query(UserSession).filter(
                UserSession.user_id == g.user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).order_by(UserSession.last_activity.desc()).all()
            
            sessions_data = []
            for user_session in user_sessions:
                sessions_data.append({
                    'id': user_session.id,
                    'created_at': user_session.created_at.isoformat(),
                    'last_activity': user_session.last_activity.isoformat(),
                    'expires_at': user_session.expires_at.isoformat(),
                    'ip_address': user_session.ip_address,
                    'user_agent': user_session.user_agent[:100] if user_session.user_agent else None,
                    'is_current': True  # Would need to check against current session
                })
            
            return success_response({
                'sessions': sessions_data,
                'count': len(sessions_data)
            })
            
    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        return error_response(f"Sessions retrieval failed: {str(e)}", "SESSIONS_ERROR", 500)

@auth_api_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@require_jwt_auth()
def revoke_session(session_id: int):
    """
    Revoke a specific user session.
    """
    try:
        with get_db_manager().get_session() as session:
            user_session = session.query(UserSession).filter(
                UserSession.id == session_id,
                UserSession.user_id == g.user_id
            ).first()
            
            if not user_session:
                return error_response("Session not found", "SESSION_NOT_FOUND", 404)
            
            user_session.is_active = False
            user_session.logged_out_at = datetime.utcnow()
            session.commit()
            
            return success_response({}, "Session revoked successfully")
            
    except Exception as e:
        logger.error(f"Error revoking session: {str(e)}")
        return error_response(f"Session revocation failed: {str(e)}", "SESSION_REVOKE_ERROR", 500)

# =====================================================================
# ADMIN ENDPOINTS (ROLE-BASED ACCESS)
# =====================================================================

@auth_api_bp.route('/admin/users', methods=['GET'])
@require_jwt_auth(roles=['admin', 'super_admin'])
def admin_get_users():
    """
    Admin endpoint to list all users.
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        role_filter = request.args.get('role')
        is_active = request.args.get('is_active')
        
        with get_db_manager().get_session() as session:
            query = session.query(User)
            
            if role_filter:
                query = query.filter(User.role == role_filter)
            
            if is_active is not None:
                query = query.filter(User.is_active == (is_active.lower() == 'true'))
            
            total_count = query.count()
            users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
            
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'is_active': user.is_active,
                    'email_verified': user.email_verified,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                })
            
            return success_response({
                'users': users_data,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            })
            
    except Exception as e:
        logger.error(f"Error in admin get users: {str(e)}")
        return error_response(f"Admin user retrieval failed: {str(e)}", "ADMIN_ERROR", 500)

# =====================================================================
# UTILITY ENDPOINTS
# =====================================================================

@auth_api_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Verify if a token is valid.
    """
    try:
        data = request.get_json() or {}
        token = data.get('token')
        
        if not token:
            return error_response("Token is required", "MISSING_TOKEN")
        
        payload = verify_jwt_token(token)
        
        if payload:
            return success_response({
                'valid': True,
                'user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'role': payload.get('role'),
                'expires_at': datetime.fromtimestamp(payload.get('exp')).isoformat()
            })
        else:
            return success_response({'valid': False})
            
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return error_response(f"Token verification failed: {str(e)}", "VERIFY_ERROR", 500)

@auth_api_bp.route('/health', methods=['GET'])
def auth_health_check():
    """
    Health check for authentication endpoints.
    """
    try:
        health_status = {
            'status': 'healthy',
            'auth_endpoints': 'available',
            'jwt_configured': bool(JWT_SECRET_KEY),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test database connection
        try:
            with get_db_manager().get_session() as session:
                session.execute('SELECT 1')
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['database'] = f'error: {str(e)}'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Export the blueprint
__all__ = ['auth_api_bp', 'require_jwt_auth', 'verify_jwt_token'] 