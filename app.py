import streamlit as st
import pandas as pd
from datetime import datetime
import os
import importlib

# Import utility modules
from utils.auth import login, logout, is_authenticated, get_current_user
from utils.database import get_projects, get_modules, get_issues, get_tasks, get_overdue_tasks, get_project_progress, get_issue_statistics
from utils.notifications import get_notifications, mark_notification_as_seen, mark_all_notifications_as_seen, get_unseen_notification_count
from utils.helpers import set_page_config, local_css, display_header, render_status_indicator, render_priority_tag, format_date, calculate_days_remaining, get_user_name, get_module_name, create_progress_chart, create_issues_by_category_chart, create_issues_by_severity_chart

# Import page modules
from pages.projects import projects_page
from pages.issues import issues_page
from pages.tasks import tasks_page
from pages.reports import reports_page

# Set page configuration
set_page_config(title="Production & Quality Tracker")

# Apply custom CSS
local_css()

# Initialize session state variables if they don't exist
if 'page' not in st.session_state:
    st.session_state['page'] = 'dashboard'

# Sidebar menu
def sidebar_menu():
    st.sidebar.title("OffSight Tracker")
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Factory_icon_%28Noun_Project%29.svg/512px-Factory_icon_%28Noun_Project%29.svg.png", width=100)
    
    # Get current user info
    user_data = get_current_user()
    
    if user_data:
        st.sidebar.write(f"Welcome, **{user_data['username']}**!")
        st.sidebar.write(f"Role: **{user_data['role'].capitalize()}**")
        
        # Menu options
        st.sidebar.subheader("Navigation")
        
        # Dashboard
        if st.sidebar.button("📊 Dashboard", key="dashboard_btn", type="primary" if st.session_state['page'] == 'dashboard' else "secondary"):
            st.session_state['page'] = 'dashboard'
            st.rerun()
        
        # Projects
        if st.sidebar.button("🏗️ Projects", key="projects_btn", type="primary" if st.session_state['page'] == 'projects' else "secondary"):
            st.session_state['page'] = 'projects'
            st.rerun()
        
        # Issues
        notification_count = get_unseen_notification_count(user_data['user_id'])
        notification_badge = f" 🔴 {notification_count}" if notification_count > 0 else ""
        if st.sidebar.button(f"⚠️ Quality Issues{notification_badge}", key="issues_btn", type="primary" if st.session_state['page'] == 'issues' else "secondary"):
            st.session_state['page'] = 'issues'
            st.rerun()
        
        # Tasks
        if st.sidebar.button("✅ Tasks", key="tasks_btn", type="primary" if st.session_state['page'] == 'tasks' else "secondary"):
            st.session_state['page'] = 'tasks'
            st.rerun()
        
        # Reports
        if st.sidebar.button("📈 Reports", key="reports_btn", type="primary" if st.session_state['page'] == 'reports' else "secondary"):
            st.session_state['page'] = 'reports'
            st.rerun()
        
        # Settings (only for managers)
        if user_data['role'].lower() == 'manager':
            if st.sidebar.button("⚙️ Settings", key="settings_btn", type="primary" if st.session_state['page'] == 'settings' else "secondary"):
                st.session_state['page'] = 'settings'
                st.rerun()
        
        # Logout button
        if st.sidebar.button("Logout", key="logout_btn"):
            logout()
            st.session_state['page'] = 'login'
            st.rerun()
    
    # About section
    st.sidebar.markdown("---")
    st.sidebar.info("Production & Quality Tracker v1.0\nAn MVP inspired by OffSight's Production & Quality Tracking application.")

# Main login page
def login_page():
    """Login page with improved user experience and professional styling"""
    st.set_page_config(
        page_title="Production Quality Tracker - Login",
        page_icon="📊",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom styling
    local_css()
    
    # Custom CSS for login page specifically
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 3rem auto;
        padding: 2.5rem;
        border-radius: 0.75rem;
        background-color: #ffffff;
        box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.12);
        border: 1px solid #f1f5f9;
    }
    .app-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
        letter-spacing: -0.5px;
    }
    .login-header {
        font-size: 1.75rem;
        font-weight: 600;
        color: #334155;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .login-subheader {
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
        font-size: 1rem;
    }
    .input-container {
        margin-bottom: 1.25rem;
    }
    .stButton button {
        width: 100%;
        background-color: #2563eb;
        color: white;
        font-weight: 500;
        padding: 0.6rem 0;
        font-size: 1rem;
        border: none;
        margin-top: 1rem;
    }
    .stButton button:hover {
        background-color: #1d4ed8;
    }
    .demo-credentials {
        margin-top: 2rem;
        padding: 1rem;
        background-color: #f8fafc;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    .demo-heading {
        font-weight: 600;
        color: #334155;
        margin-bottom: 0.5rem;
        font-size: 0.875rem;
    }
    .error-message {
        color: #ef4444;
        font-size: 0.875rem;
        padding: 0.5rem;
        margin-bottom: 1rem;
        border-radius: 0.375rem;
        background-color: rgba(239, 68, 68, 0.1);
        border-left: 3px solid #ef4444;
    }
    .success-message {
        color: #10b981;
        font-size: 0.875rem;
        padding: 0.5rem;
        margin-bottom: 1rem;
        border-radius: 0.375rem;
        background-color: rgba(16, 185, 129, 0.1);
        border-left: 3px solid #10b981;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Container for login form
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # App title and login header
    st.markdown('<h1 class="app-title">Production Quality Tracker</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="login-header">Welcome Back</h2>', unsafe_allow_html=True)
    st.markdown('<p class="login-subheader">Sign in to continue to your dashboard</p>', unsafe_allow_html=True)
    
    # Get or initialize session state
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
        st.session_state.show_success = False
        st.session_state.show_error = False
        st.session_state.error_message = ""
    
    # Check for redirect from successful registration
    query_params = st.experimental_get_query_params()
    if query_params.get("registered") == ["true"] and not st.session_state.get("cleared_registered_param"):
        st.session_state.show_success = True
        st.session_state.cleared_registered_param = True
        # Clear the query parameter
        st.experimental_set_query_params()
    
    # Display success message if applicable
    if st.session_state.show_success:
        st.markdown('<div class="success-message">Registration successful! You can now log in.</div>', unsafe_allow_html=True)
        st.session_state.show_success = False
    
    # Display error message if applicable
    if st.session_state.show_error:
        st.markdown(f'<div class="error-message">{st.session_state.error_message}</div>', unsafe_allow_html=True)
        st.session_state.show_error = False
    
    # Login form
    with st.form("login_form"):
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        username = st.text_input("Username", key="username")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", key="password")
        st.markdown('</div>', unsafe_allow_html=True)
        
        submit_button = st.form_submit_button("Sign In")
    
    # Handle login attempt
    if submit_button:
        if not username or not password:
            st.session_state.show_error = True
            st.session_state.error_message = "Please provide both username and password."
            st.rerun()
        
        # Validate credentials
        user_data = validate_login(username, password)
        
        if user_data:
            # Clear login attempts on successful login
            st.session_state.login_attempts = 0
            
            # Set session data
            st.session_state['logged_in'] = True
            st.session_state['user_data'] = user_data
            
            # Redirect to dashboard
            st.rerun()
        else:
            # Increment login attempts
            st.session_state.login_attempts += 1
            
            # Show error message
            st.session_state.show_error = True
            st.session_state.error_message = "Invalid username or password. Please try again."
            
            # If too many failed attempts, suggest demo account
            if st.session_state.login_attempts >= 2:
                st.session_state.error_message += " You can use a demo account below."
            
            st.rerun()
    
    # Demo account section
    st.markdown("""
    <div class="demo-credentials">
        <div class="demo-heading">Demo Accounts</div>
        <p style="font-size: 0.875rem; margin-bottom: 0.5rem;"><strong>Admin:</strong> admin / admin123</p>
        <p style="font-size: 0.875rem; margin-bottom: 0.5rem;"><strong>Manager:</strong> manager / manager123</p>
        <p style="font-size: 0.875rem;"><strong>User:</strong> user / user123</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Close the container
    st.markdown('</div>', unsafe_allow_html=True)

def validate_login(username, password):
    """Validate login credentials and return user data if valid"""
    # In a real app, you would check against a database
    # For demo purposes, we'll use hardcoded values
    demo_users = {
        "admin": {
            "password": "admin123",
            "user_id": "admin001",
            "role": "admin",
            "name": "Admin User"
        },
        "manager": {
            "password": "manager123",
            "user_id": "manager001",
            "role": "manager",
            "name": "Manager User"
        },
        "user": {
            "password": "user123",
            "user_id": "user001",
            "role": "user",
            "name": "Regular User"
        }
    }
    
    if username in demo_users and demo_users[username]["password"] == password:
        user_data = {
            "username": username,
            "user_id": demo_users[username]["user_id"],
            "role": demo_users[username]["role"],
            "name": demo_users[username]["name"]
        }
        return user_data
    
    return None

# Dashboard page
def dashboard_page():
    user_data = get_current_user()
    display_header("Production Dashboard", user_data)
    
    # Create a 2x2 grid for dashboard widgets
    col1, col2 = st.columns(2)
    
    with col1:
        # Project Progress
        st.subheader("Project Progress")
        projects_df = get_project_progress()
        
        if not projects_df.empty:
            # Display a progress chart
            progress_chart = create_progress_chart(projects_df)
            st.plotly_chart(progress_chart, use_container_width=True)
        else:
            st.info("No project data available.")
        
        # Overdue Tasks
        st.subheader("Overdue Tasks")
        overdue_tasks = get_overdue_tasks()
        
        if not overdue_tasks.empty:
            overdue_tasks['Assigned To'] = overdue_tasks['assigned_to'].apply(get_user_name)
            overdue_tasks['Module'] = overdue_tasks['module_id'].apply(get_module_name)
            overdue_tasks['Due Date'] = overdue_tasks['due_date'].apply(format_date)
            
            st.dataframe(
                overdue_tasks[['task_id', 'Module', 'description', 'priority', 'Due Date', 'Assigned To']],
                use_container_width=True,
                column_config={
                    "task_id": "Task ID",
                    "description": "Description",
                    "priority": st.column_config.Column(
                        "Priority",
                        width="medium"
                    )
                }
            )
        else:
            st.success("No overdue tasks! Great job!")
    
    with col2:
        # Quality Issues
        st.subheader("Quality Issues")
        
        # Get issue statistics
        category_counts, severity_counts = get_issue_statistics()
        
        if category_counts and severity_counts:
            # Create tabs for different issue charts
            tab1, tab2 = st.tabs(["By Category", "By Severity"])
            
            with tab1:
                category_chart = create_issues_by_category_chart(category_counts)
                st.plotly_chart(category_chart, use_container_width=True)
            
            with tab2:
                severity_chart = create_issues_by_severity_chart(severity_counts)
                st.plotly_chart(severity_chart, use_container_width=True)
        else:
            st.info("No issue data available.")
        
        # Recent activity (notifications)
        st.subheader("Recent Activity")
        notifications = get_notifications(user_id=user_data['user_id'], max_count=5, include_seen=True)
        
        if notifications:
            for notification in notifications:
                with st.container():
                    st.markdown(f"""
                    **{notification['title']}** - {notification['timestamp']}
                    
                    {notification['message']}
                    """)
                    st.divider()
        else:
            st.info("No recent activity to display.")

# Notifications panel
def show_notifications_panel():
    user_data = get_current_user()
    
    with st.sidebar.expander("Notifications", expanded=True):
        st.write("### Recent Notifications")
        
        notifications = get_notifications(user_id=user_data['user_id'], max_count=10)
        
        if notifications:
            if st.button("Mark All as Read"):
                mark_all_notifications_as_seen(user_data['user_id'])
                st.rerun()
            
            for notification in notifications:
                with st.container():
                    st.markdown(f"""
                    **{notification['title']}** - {notification['timestamp']}
                    
                    {notification['message']}
                    """)
                    
                    if not notification['seen']:
                        if st.button("Mark as Read", key=f"read_{notification['id']}"):
                            mark_notification_as_seen(notification['id'])
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No new notifications.")

# Main app
def main():
    if not is_authenticated():
        login_page()
    else:
        # Show sidebar menu
        sidebar_menu()
        
        # Show notifications if there are any
        user_data = get_current_user()
        if get_unseen_notification_count(user_data['user_id']) > 0:
            show_notifications_panel()
        
        # Show the selected page
        if st.session_state['page'] == 'dashboard':
            dashboard_page()
        elif st.session_state['page'] == 'projects':
            projects_page()
        elif st.session_state['page'] == 'issues':
            issues_page()
        elif st.session_state['page'] == 'tasks':
            tasks_page()
        elif st.session_state['page'] == 'reports':
            reports_page()
        elif st.session_state['page'] == 'settings':
            st.title("Settings Page")
            st.info("Settings functionality will be implemented in future updates.")
        else:
            st.title("Page Not Found")
            st.error(f"The page '{st.session_state['page']}' does not exist.")
            st.session_state['page'] = 'dashboard'
            st.rerun()

if __name__ == "__main__":
    main() 