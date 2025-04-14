import pandas as pd
import streamlit as st
import os

# User authentication functions
def load_users():
    """Load user data from CSV file"""
    try:
        users_df = pd.read_csv('data/users.csv')
        return users_df
    except FileNotFoundError:
        st.error("User database not found. Please check the data directory.")
        return pd.DataFrame()

def authenticate(username, password):
    """Authenticate user credentials"""
    users_df = load_users()
    
    if users_df.empty:
        return False, None
    
    # Find user by username
    user = users_df[users_df['username'] == username]
    
    if user.empty:
        return False, None
    
    # Check password (in a real application, this would use secure password hashing)
    if user.iloc[0]['password'] == password:
        user_data = user.iloc[0].to_dict()
        return True, user_data
    
    return False, None

def is_authenticated():
    """Check if user is currently authenticated"""
    if 'authenticated' in st.session_state and st.session_state['authenticated']:
        return True
    return False

def get_current_user():
    """Get current authenticated user data"""
    if is_authenticated():
        return st.session_state['user_data']
    return None

def get_role_permissions(role):
    """Define permissions for different user roles"""
    permissions = {
        'operator': {
            'view_projects': True,
            'view_tasks': True,
            'update_tasks': True,
            'report_issues': True,
            'view_issues': True,
            'manage_users': False,
            'view_analytics': False,
            'manage_projects': False
        },
        'inspector': {
            'view_projects': True,
            'view_tasks': True,
            'update_tasks': True,
            'report_issues': True,
            'view_issues': True,
            'manage_users': False,
            'view_analytics': True,
            'manage_projects': False
        },
        'supervisor': {
            'view_projects': True,
            'view_tasks': True,
            'update_tasks': True,
            'report_issues': True,
            'view_issues': True,
            'manage_users': False,
            'view_analytics': True,
            'manage_projects': False
        },
        'manager': {
            'view_projects': True,
            'view_tasks': True,
            'update_tasks': True,
            'report_issues': True,
            'view_issues': True,
            'manage_users': True,
            'view_analytics': True,
            'manage_projects': True
        },
        'engineer': {
            'view_projects': True,
            'view_tasks': True,
            'update_tasks': True,
            'report_issues': True,
            'view_issues': True,
            'manage_users': False,
            'view_analytics': True,
            'manage_projects': False
        }
    }
    
    # Return permissions for the specified role, or a set of minimal permissions
    return permissions.get(role.lower(), {
        'view_projects': True,
        'view_tasks': True,
        'update_tasks': False,
        'report_issues': False,
        'view_issues': True,
        'manage_users': False,
        'view_analytics': False,
        'manage_projects': False
    })

def login(username, password):
    """Log in a user and set session state"""
    success, user_data = authenticate(username, password)
    
    if success:
        st.session_state['authenticated'] = True
        st.session_state['user_data'] = user_data
        st.session_state['permissions'] = get_role_permissions(user_data['role'])
        return True
    else:
        return False

def logout():
    """Log out a user and reset session state"""
    if 'authenticated' in st.session_state:
        st.session_state['authenticated'] = False
    
    if 'user_data' in st.session_state:
        del st.session_state['user_data']
    
    if 'permissions' in st.session_state:
        del st.session_state['permissions'] 