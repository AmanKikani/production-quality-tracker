"""
Authentication utilities for the Volumod Production Tracker application.

This module provides authentication and authorization functionality.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Import database functions from the new data models
from utils.data_models import get_db_connection, execute_query, execute_update, log_audit

# Define permission levels for various actions
PERMISSIONS = {
    'operator': {
        'view_dashboard': True,
        'view_projects': True,
        'view_issues': True,
        'create_issues': True,
        'edit_issues': False,
        'close_issues': False,
        'view_tasks': True,
        'create_tasks': False,
        'edit_tasks': False,
        'complete_tasks': True,
        'view_reports': False,
        'manage_users': False,
        'manage_settings': False,
        'update_production': True,
        'perform_inspections': False,
        'verify_resolutions': False,
    },
    'inspector': {
        'view_dashboard': True,
        'view_projects': True,
        'view_issues': True,
        'create_issues': True,
        'edit_issues': True,
        'close_issues': False,
        'view_tasks': True,
        'create_tasks': True,
        'edit_tasks': True,
        'complete_tasks': True,
        'view_reports': True,
        'manage_users': False,
        'manage_settings': False,
        'update_production': False,
        'perform_inspections': True,
        'verify_resolutions': True,
    },
    'supervisor': {
        'view_dashboard': True,
        'view_projects': True,
        'view_issues': True,
        'create_issues': True,
        'edit_issues': True,
        'close_issues': True,
        'view_tasks': True,
        'create_tasks': True,
        'edit_tasks': True,
        'complete_tasks': True,
        'view_reports': True,
        'manage_users': False,
        'manage_settings': False,
        'update_production': True,
        'perform_inspections': True,
        'verify_resolutions': True,
    },
    'manager': {
        'view_dashboard': True,
        'view_projects': True,
        'view_issues': True,
        'create_issues': True,
        'edit_issues': True,
        'close_issues': True,
        'view_tasks': True,
        'create_tasks': True,
        'edit_tasks': True,
        'complete_tasks': True,
        'view_reports': True,
        'manage_users': True,
        'manage_settings': True,
        'update_production': True,
        'perform_inspections': True,
        'verify_resolutions': True,
    },
    'admin': {
        'view_dashboard': True,
        'view_projects': True,
        'view_issues': True,
        'create_issues': True,
        'edit_issues': True,
        'close_issues': True,
        'view_tasks': True,
        'create_tasks': True,
        'edit_tasks': True,
        'complete_tasks': True,
        'view_reports': True,
        'manage_users': True,
        'manage_settings': True,
        'update_production': True,
        'perform_inspections': True,
        'verify_resolutions': True,
    }
}

def login(username, password):
    """
    Authenticates a user based on username and password.
    
    Args:
        username (str): The username to authenticate
        password (str): The password to verify
        
    Returns:
        bool: True if authentication successful, False otherwise
    """
    try:
        # Query the users table
        user = execute_query(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
            fetchall=False
        )
        
        if user:
            # Update last login timestamp
            execute_update(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user['user_id'],)
            )
            
            # Set session state
            st.session_state['authenticated'] = True
            st.session_state['user_data'] = {
                'user_id': user['user_id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role'],
                'department': user['department'],
                'avatar_url': user['avatar_url']
            }
            
            # Set permissions based on role
            st.session_state['permissions'] = PERMISSIONS.get(user['role'].lower(), {})
            
            # Set session expiry
            st.session_state['session_expiry'] = datetime.now() + timedelta(hours=8)
            
            # Log the login action
            log_audit(user['user_id'], 'login', 'user', user['user_id'])
            
            return True
        
        return False
    
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return False

def logout():
    """
    Logs out the current user by clearing session state.
    """
    if 'user_data' in st.session_state and st.session_state['user_data']:
        # Log the logout action
        user_id = st.session_state['user_data']['user_id']
        log_audit(user_id, 'logout', 'user', user_id)
    
    # Reset authentication state
    st.session_state['authenticated'] = False
    
    # Clear user data
    if 'user_data' in st.session_state:
        st.session_state['user_data'] = None
    
    # Clear permissions
    if 'permissions' in st.session_state:
        st.session_state['permissions'] = None
    
    # Clear session expiry
    if 'session_expiry' in st.session_state:
        st.session_state['session_expiry'] = None
    
    # Clear query parameters on logout for a cleaner URL
    st.query_params.clear()

def is_authenticated():
    """
    Checks if the current user is authenticated.
    
    Returns:
        bool: True if authenticated, False otherwise
    """
    # Check if authenticated flag is set
    if not st.session_state.get('authenticated', False):
        return False
    
    # Check if session has expired
    if 'session_expiry' in st.session_state:
        if datetime.now() > st.session_state['session_expiry']:
            # Session expired, log the user out
            logout()
            return False
        else:
            # Renew session expiry on activity
            st.session_state['session_expiry'] = datetime.now() + timedelta(hours=8)
    
    return True

def get_current_user():
    """
    Gets the current authenticated user's data.
    
    Returns:
        dict: User data if authenticated, None otherwise
    """
    if is_authenticated() and 'user_data' in st.session_state:
        return st.session_state['user_data']
    return None

def has_permission(permission):
    """
    Checks if the current user has a specific permission.
    
    Args:
        permission (str): The permission to check
        
    Returns:
        bool: True if the user has the permission, False otherwise
    """
    if not is_authenticated():
        return False
    
    if 'permissions' not in st.session_state:
        return False
    
    return st.session_state['permissions'].get(permission, False)

def require_permission(permission):
    """
    Decorator function to require a specific permission for a page or function.
    Redirects to the login page if the user doesn't have the required permission.
    
    Args:
        permission (str): The permission required
        
    Returns:
        function: The decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not has_permission(permission):
                st.error("You don't have permission to access this feature.")
                return
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_user_by_id(user_id):
    """
    Gets user data by ID.
    
    Args:
        user_id (int): The user ID to look up
        
    Returns:
        dict: User data if found, None otherwise
    """
    user = execute_query(
        "SELECT user_id, username, full_name, email, role, department, avatar_url FROM users WHERE user_id = ?",
        (user_id,),
        fetchall=False
    )
    return user

def get_users_by_role(role):
    """
    Gets users with a specific role.
    
    Args:
        role (str): The role to filter by
        
    Returns:
        list: List of users with the specified role
    """
    users = execute_query(
        "SELECT user_id, username, full_name, email, role, department FROM users WHERE role = ?",
        (role,)
    )
    return users

def register_user(username, password, email, full_name, role, department=None):
    """
    Registers a new user.
    
    Args:
        username (str): The username for the new user
        password (str): The password for the new user
        email (str): The email for the new user
        full_name (str): The full name of the new user
        role (str): The role for the new user
        department (str, optional): The department for the new user
        
    Returns:
        bool: True if registration successful, False otherwise
    """
    try:
        # Check if username or email already exists
        existing_user = execute_query(
            "SELECT user_id FROM users WHERE username = ? OR email = ?",
            (username, email),
            fetchall=False
        )
        
        if existing_user:
            return False
        
        # Insert new user
        execute_update(
            """
            INSERT INTO users (username, password, email, full_name, role, department)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, password, email, full_name, role, department)
        )
        
        return True
    
    except Exception as e:
        st.error(f"Registration error: {str(e)}")
        return False

def update_user_profile(user_id, email=None, full_name=None, department=None, avatar_url=None):
    """
    Updates a user's profile information.
    
    Args:
        user_id (int): The ID of the user to update
        email (str, optional): The new email
        full_name (str, optional): The new full name
        department (str, optional): The new department
        avatar_url (str, optional): The new avatar URL
        
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Collect update fields and values
        update_fields = []
        update_values = []
        
        if email is not None:
            update_fields.append("email = ?")
            update_values.append(email)
        
        if full_name is not None:
            update_fields.append("full_name = ?")
            update_values.append(full_name)
        
        if department is not None:
            update_fields.append("department = ?")
            update_values.append(department)
        
        if avatar_url is not None:
            update_fields.append("avatar_url = ?")
            update_values.append(avatar_url)
        
        if not update_fields:
            return False  # No fields to update
        
        # Build and execute the update query
        update_values.append(user_id)  # Add user_id for the WHERE clause
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
        
        execute_update(query, tuple(update_values))
        
        # Update session state if it's the current user
        if (is_authenticated() and 
            'user_data' in st.session_state and 
            st.session_state['user_data'].get('user_id') == user_id):
            
            if email is not None:
                st.session_state['user_data']['email'] = email
            if full_name is not None:
                st.session_state['user_data']['full_name'] = full_name
            if department is not None:
                st.session_state['user_data']['department'] = department
            if avatar_url is not None:
                st.session_state['user_data']['avatar_url'] = avatar_url
        
        return True
    
    except Exception as e:
        st.error(f"Update profile error: {str(e)}")
        return False

def change_password(user_id, current_password, new_password):
    """
    Changes a user's password.
    
    Args:
        user_id (int): The ID of the user
        current_password (str): The current password for verification
        new_password (str): The new password
        
    Returns:
        bool: True if password change successful, False otherwise
    """
    try:
        # Verify current password
        user = execute_query(
            "SELECT user_id FROM users WHERE user_id = ? AND password = ?",
            (user_id, current_password),
            fetchall=False
        )
        
        if not user:
            return False  # Current password is incorrect
        
        # Update password
        execute_update(
            "UPDATE users SET password = ? WHERE user_id = ?",
            (new_password, user_id)
        )
        
        # Log the password change action
        log_audit(user_id, 'change_password', 'user', user_id)
        
        return True
    
    except Exception as e:
        st.error(f"Change password error: {str(e)}")
        return False 