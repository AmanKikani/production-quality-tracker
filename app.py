import streamlit as st
import pandas as pd
from datetime import datetime
import os
import importlib
import traceback

# Set page config at the beginning before any other streamlit calls
set_page_config = st.set_page_config
set_page_config(
    page_title="Production Quality Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import utility modules
from utils.auth import login, logout, is_authenticated, get_current_user
from utils.database import get_projects, get_modules, get_issues, get_tasks, get_overdue_tasks, get_project_progress, get_issue_statistics
from utils.notifications import get_notifications, mark_notification_as_seen, mark_all_notifications_as_seen, get_unseen_notification_count
from utils.helpers import local_css, display_header, render_status_indicator, render_priority_tag, format_date, calculate_days_remaining, get_user_name, get_module_name, create_progress_chart, create_issues_by_category_chart, create_issues_by_severity_chart, get_image_html

# Import page modules
from pages.projects import projects_page
from pages.issues import issues_page
from pages.tasks import tasks_page
from pages.reports import reports_page

# Image paths
LOGO_PATH = "assets/images/logo.png"
APP_ICON_PATH = "assets/images/app_icon.png"

# Sidebar menu
def sidebar_menu():
    st.sidebar.markdown("""
    <style>
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #3b82f6;
        margin-bottom: 0.5rem;
    }
    .sidebar-logo {
        background-color: #2d3748;
        border-radius: 12px;
        padding: 10px;
        width: 80px;
        height: 80px;
        margin-bottom: 1rem;
    }
    .sidebar-welcome {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #2d3748;
    }
    .sidebar-nav-header {
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #a0aec0;
        margin-bottom: 0.75rem;
        letter-spacing: 0.05em;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown('<div class="sidebar-title">OFFSIGHT TRACKER</div>', unsafe_allow_html=True)
    
    # Use local logo instead of Wikimedia URL
    logo_html = get_image_html(LOGO_PATH, css_class="sidebar-logo", alt_text="App Logo")
    st.sidebar.markdown(logo_html, unsafe_allow_html=True)
    
    # Get current user info
    user_data = get_current_user()
    
    if user_data:
        st.sidebar.markdown(f"""
        <div class="sidebar-welcome">
            <div style="font-weight: 600; font-size: 1.1rem; color: #e2e8f0; margin-bottom: 0.25rem;">Welcome, {user_data['username']}!</div>
            <div style="color: #a0aec0; font-size: 0.9rem;">Role: {user_data['role'].capitalize()}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Menu options
        st.sidebar.markdown('<div class="sidebar-nav-header">NAVIGATION</div>', unsafe_allow_html=True)
        
        # Function to render navigation buttons with URLs instead of callbacks
        def nav_button(label, page_name, icon=""):
            is_active = st.session_state['page'] == page_name
            button_type = "primary" if is_active else "secondary"
            
            # Use Streamlit buttons directly to change the view
            if st.sidebar.button(
                f"{icon} {label}", 
                key=f"nav_{page_name}",
                type=button_type if is_active else "secondary",
                use_container_width=True
            ):
                st.session_state['page'] = page_name
                # Don't modify query params directly to avoid issues with rerun
                return True
            return False
        
        # Navigation items
        nav_button("DASHBOARD", "dashboard", "📊")
        nav_button("PROJECTS", "projects", "🏗️")
        
        # Issues with notification badge
        notification_count = get_unseen_notification_count(user_data['user_id'])
        notification_badge = f" 🔴 {notification_count}" if notification_count > 0 else ""
        nav_button(f"QUALITY ISSUES{notification_badge}", "issues", "⚠️")
        
        nav_button("TASKS", "tasks", "✅")
        nav_button("REPORTS", "reports", "📈")
        
        # Settings (only for managers)
        if user_data['role'].lower() == 'manager':
            nav_button("SETTINGS", "settings", "⚙️")
        
        # Logout button - this needs a callback
        st.sidebar.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        logout_placeholder = st.sidebar.empty()
        logout_clicked = logout_placeholder.button("🚪 LOGOUT", key="logout_btn", type="secondary")
        
        if logout_clicked:
            # Call logout function to clear auth state
            logout()
            # Reset all critical session state variables to ensure complete logout
            for key in ['authenticated', 'user_data', 'permissions']:
                if key in st.session_state:
                    st.session_state[key] = False if key == 'authenticated' else None
            
            # Clear query parameters
            st.query_params.clear()
            # Replace the logout button with a message
            logout_placeholder.info("Logging out...")
            # Use JavaScript to directly reload the page which will show login screen
            # since authentication state is now False
            st.markdown(
                """
                <script>
                    // Force a complete page reload to get to login screen
                    window.location.href = window.location.origin;
                </script>
                """,
                unsafe_allow_html=True
            )
    
    # About section
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="background-color: #1e1e2e; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid #2d3748; font-size: 0.85rem; color: #a0aec0;">
        <div style="font-weight: 600; margin-bottom: 0.25rem; color: #e2e8f0;">PRODUCTION & QUALITY TRACKER v1.0</div>
        <div>An MVP inspired by OffSight's Production & Quality Tracking application.</div>
    </div>
    """, unsafe_allow_html=True)

# Main login page
def login_page():
    """Login page with improved user experience and professional styling"""
    
    # Temporarily modify the layout for login page
    st.markdown("""
    <style>
    .block-container {
        max-width: 500px;
        padding-top: 2rem;
        padding-bottom: 2rem;
        margin: 0 auto;
    }
    header {
        visibility: hidden;
    }
    #MainMenu {
        visibility: hidden;
    }
    footer {
        visibility: hidden;
    }
    /* Hide sidebar when not logged in */
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
        background-color: #1a1a2e;
        box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.3);
        border: 1px solid #2d3748;
    }
    .app-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #3b82f6;
        text-align: center;
        margin-bottom: 1.5rem;
        letter-spacing: -0.5px;
    }
    .login-header {
        font-size: 1.75rem;
        font-weight: 600;
        color: #e2e8f0;
        text-align: center;
        margin-bottom: 1rem;
    }
    .login-subheader {
        color: #a0aec0;
        text-align: center;
        margin-bottom: 2rem;
        font-size: 1rem;
    }
    .input-container {
        margin-bottom: 1.25rem;
    }
    .stButton button {
        width: 100%;
        background-color: #3b82f6;
        color: white;
        font-weight: 500;
        padding: 0.6rem 0;
        font-size: 1rem;
        border: none;
        margin-top: 1rem;
        border-radius: 0.375rem;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #2563eb;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
    }
    .error-message {
        color: #f87171;
        font-size: 0.875rem;
        padding: 0.75rem;
        margin-bottom: 1rem;
        border-radius: 0.375rem;
        background-color: rgba(239, 68, 68, 0.1);
        border-left: 3px solid #ef4444;
    }
    .success-message {
        color: #4ade80;
        font-size: 0.875rem;
        padding: 0.75rem;
        margin-bottom: 1rem;
        border-radius: 0.375rem;
        background-color: rgba(16, 185, 129, 0.1);
        border-left: 3px solid #10b981;
    }
    .app-logo {
        width: 70px;
        height: 70px;
        margin: 0 auto 1.5rem auto;
        display: block;
        background-color: #2d3748;
        border-radius: 18px;
        padding: 12px;
    }
    /* Input field styling */
    input[type="text"], input[type="password"] {
        background-color: #111827;
        border: 1px solid #374151;
        color: #e2e8f0;
    }
    input[type="text"]:focus, input[type="password"]:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
    }
    label {
        color: #a0aec0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Container for login form
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # App logo and title
    app_logo_html = get_image_html(APP_ICON_PATH, css_class="app-logo", alt_text="App Logo")
    st.markdown(app_logo_html, unsafe_allow_html=True)
    st.markdown('<h1 class="app-title">Production Quality Tracker</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="login-header">Welcome Back</h2>', unsafe_allow_html=True)
    st.markdown('<p class="login-subheader">Sign in to continue to your dashboard</p>', unsafe_allow_html=True)
    
    # Get or initialize session state
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
        st.session_state.show_success = False
        st.session_state.show_error = False
        st.session_state.error_message = ""
        st.session_state.login_submitted = False
    
    # Check for redirect from successful registration
    query_params = st.query_params
    if query_params.get("registered") == ["true"] and not st.session_state.get("cleared_registered_param"):
        st.session_state.show_success = True
        st.session_state.cleared_registered_param = True
        # Clear the query parameter
        st.query_params.clear()
    
    # Display success message if applicable
    if st.session_state.show_success:
        st.markdown('<div class="success-message">Registration successful! You can now log in.</div>', unsafe_allow_html=True)
        st.session_state.show_success = False
    
    # Display error message if applicable
    if st.session_state.show_error:
        st.markdown(f'<div class="error-message">{st.session_state.error_message}</div>', unsafe_allow_html=True)
        st.session_state.show_error = False
    
    # Create a function to handle form submission via session state
    def handle_login():
        # Get the form values from session state
        username = st.session_state.username
        password = st.session_state.password
        
        # Perform validation
        if not username or not password:
            st.session_state.show_error = True
            st.session_state.error_message = "Please provide both username and password."
            return
        
        # Try to login
        if login(username, password):
            # Login was successful, function will set session state
            pass
        else:
            # Login failed
            st.session_state.login_attempts += 1
            st.session_state.show_error = True
            st.session_state.error_message = "Invalid username or password. Please try again."
            
            # If too many failed attempts, suggest demo account
            if st.session_state.login_attempts >= 2:
                st.session_state.error_message += " You can use a demo account below."
    
    # Login form with direct session state access
    with st.form("login_form", clear_on_submit=False):
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        st.text_input("Username", key="username")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        st.text_input("Password", type="password", key="password")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button - when clicked it will trigger a page refresh, and the callback
        # will run before the page is rendered
        st.form_submit_button("Sign In", on_click=handle_login)
    
    # Demo credentials section with improved styling
    st.markdown('### Demo Accounts', unsafe_allow_html=False)
    st.markdown('<div class="demo-credentials">', unsafe_allow_html=True)
    
    # Demo heading
    st.markdown("""
        <div class="demo-heading">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
            </svg>
            Available Demo Accounts
        </div>
    """, unsafe_allow_html=True)
    
    # Simple account listing
    st.markdown("""
        <div class="account-card">
            <div class="account-icon">👨‍💼</div>
            <div class="account-details">
                <div class="account-role">Manager</div>
                <div class="account-credentials">Username: mike_jones | Password: secure789</div>
            </div>
        </div>
        
        <div class="account-card">
            <div class="account-icon">👩‍💼</div>
            <div class="account-details">
                <div class="account-role">Manager</div>
                <div class="account-credentials">Username: rachel_kim | Password: rachelpass</div>
            </div>
        </div>
        
        <div class="account-card">
            <div class="account-icon">👨‍🔧</div>
            <div class="account-details">
                <div class="account-role">Operator</div>
                <div class="account-credentials">Username: john_doe | Password: password123</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Close the demo credentials div
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Close the container
    st.markdown('</div>', unsafe_allow_html=True)

def validate_login(username, password):
    """Validate login credentials and return user data if valid"""
    # Check if users.csv exists
    try:
        if not os.path.exists('data/users.csv'):
            st.error("User database not found. Please check if data/users.csv exists.")
            return None
        
        # Use the login function from auth.py
        if login(username, password):
            return get_current_user()
        return None
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return None

# Dashboard page
def dashboard_page():
    user_data = get_current_user()
    
    # Create a header with custom styling
    st.markdown('<div class="dashboard-header">', unsafe_allow_html=True)
    display_header("Production Dashboard", user_data)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Wrap main content in a container
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Create a 2x2 grid for dashboard widgets
    col1, col2 = st.columns(2)
    
    with col1:
        # Project Progress
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📈 Project Progress</div>', unsafe_allow_html=True)
        projects_df = get_project_progress()
        
        if not projects_df.empty:
            # Display a progress chart
            progress_chart = create_progress_chart(projects_df)
            st.plotly_chart(progress_chart, use_container_width=True)
        else:
            st.info("No project data available.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Overdue Tasks
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⏰ Overdue Tasks</div>', unsafe_allow_html=True)
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
            st.markdown("""
            <div style="display: flex; align-items: center; justify-content: center; padding: 1.5rem; background-color: #1b3a2a; border-radius: 0.375rem; border: 1px solid #2c5e46; color: #4ade80; margin: 1rem 0;">
                <div style="margin-right: 0.5rem; font-size: 1.5rem;">✅</div>
                <div style="font-weight: 500;">No overdue tasks! Great job!</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Quality Issues
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔍 Quality Issues</div>', unsafe_allow_html=True)
        
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
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Recent activity (notifications)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔔 Recent Activity</div>', unsafe_allow_html=True)
        notifications = get_notifications(user_id=user_data['user_id'], max_count=5, include_seen=True)
        
        if notifications:
            for notification in notifications:
                st.markdown(f"""
                <div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #2d3748;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <div style="font-weight: 600; color: #e2e8f0;">{notification['title']}</div>
                        <div style="color: #a0aec0; font-size: 0.875rem;">{notification['timestamp']}</div>
                    </div>
                    <div style="color: #cbd5e1; font-size: 0.95rem;">{notification['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent activity to display.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Close main content wrapper
    st.markdown('</div>', unsafe_allow_html=True)

# Notifications panel
def show_notifications_panel():
    user_data = get_current_user()
    
    with st.sidebar.expander("📬 NOTIFICATIONS", expanded=True):
        st.markdown("""
        <style>
        .notification-header {
            font-weight: 600;
            font-size: 1rem;
            color: #e2e8f0;
            margin-bottom: 1rem;
        }
        .notification-item {
            margin-bottom: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #2d3748;
        }
        .notification-item:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }
        .notification-title {
            font-weight: 600;
            font-size: 0.875rem;
            color: #e2e8f0;
            margin-bottom: 0.25rem;
        }
        .notification-time {
            font-size: 0.75rem;
            color: #a0aec0;
            margin-bottom: 0.5rem;
        }
        .notification-message {
            font-size: 0.8125rem;
            color: #cbd5e1;
        }
        .mark-read-all {
            display: block;
            width: 100%;
            padding: 0.375rem;
            background-color: #1e1e2e;
            border: 1px solid #2d3748;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            text-align: center;
            cursor: pointer;
            color: #a0aec0;
            margin-bottom: 1rem;
            transition: all 0.2s ease;
        }
        .mark-read-all:hover {
            background-color: #2d3748;
            color: #e2e8f0;
        }
        .notification-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.125rem 0.375rem;
            background-color: #dc2626;
            color: white;
            border-radius: 1rem;
            font-size: 0.6875rem;
            font-weight: 600;
            margin-left: 0.375rem;
        }
        </style>
        <div class="notification-header">RECENT NOTIFICATIONS</div>
        """, unsafe_allow_html=True)
        
        notifications = get_notifications(user_id=user_data['user_id'], max_count=10)
        
        if notifications:
            # Use Streamlit buttons for the mark as read functionality
            if st.button("Mark All as Read", key="mark_all_read_btn"):
                mark_all_notifications_as_seen(user_data['user_id'])
            
            for notification in notifications:
                is_unread = not notification['seen']
                unread_badge = '<span class="notification-badge">New</span>' if is_unread else ''
                
                st.markdown(f"""
                <div class="notification-item">
                    <div class="notification-title">{notification['title']} {unread_badge}</div>
                    <div class="notification-time">{notification['timestamp']}</div>
                    <div class="notification-message">{notification['message']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if not notification['seen']:
                    # Use Streamlit buttons for marking individual notifications as read
                    if st.button("Mark as Read", key=f"mark_read_{notification['id']}"):
                        mark_notification_as_seen(notification['id'])
            
            # The old URL parameter handling is no longer needed
        else:
            st.markdown("""
            <div style="padding: 1rem; background-color: #1e1e2e; border-radius: 0.375rem; text-align: center; color: #a0aec0; font-size: 0.875rem;">
                No new notifications
            </div>
            """, unsafe_allow_html=True)

# Check if all required data files exist
def check_data_files():
    """Check if all required data files exist"""
    required_files = [
        'data/users.csv',
        'data/projects.csv',
        'data/modules.csv',
        'data/issues.csv',
        'data/tasks.csv'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        st.error(f"Missing required data files: {', '.join(missing_files)}")
        st.info("Please make sure all data files are in the correct location.")
        return False
    
    return True

# Wrapper function to apply consistent layout to all pages
def apply_page_layout(page_func, title, user_data):
    """Apply consistent layout wrapper to all pages"""
    # Create a header with custom styling
    st.markdown('<div class="dashboard-header">', unsafe_allow_html=True)
    display_header(title, user_data)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Wrap main content in a container
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Call the actual page function
    page_func()
    
    # Close main content wrapper
    st.markdown('</div>', unsafe_allow_html=True)

# Main app
def main():
    try:
        # Debug session state
        print("Session state at start of main():", st.session_state)
        print("Authenticated:", st.session_state.get('authenticated', False))
        print("User data:", st.session_state.get('user_data', None))
        
        # Session state persistence handling
        if 'session_expiry' in st.session_state:
            if pd.Timestamp.now() < st.session_state['session_expiry']:
                # Renew session
                print("Renewing existing session")
                st.session_state['session_expiry'] = pd.Timestamp.now() + pd.Timedelta(days=1)
            else:
                # Session expired
                print("Session expired")
                if 'authenticated' in st.session_state:
                    st.session_state['authenticated'] = False
                if 'user_data' in st.session_state:
                    del st.session_state['user_data']
        
        # Initialize session state variables if they don't exist
        if 'authenticated' not in st.session_state:
            st.session_state['authenticated'] = False
        if 'page' not in st.session_state:
            st.session_state['page'] = 'dashboard'
        
        # Get the current page from query params, with fallback to session state
        query_params = st.query_params
        if "view" in query_params and st.session_state.get('authenticated', False):
            # Only update page from query params if the user is authenticated
            view = query_params["view"][0] if isinstance(query_params["view"], list) else query_params["view"]
            # Ensure view is a valid page
            valid_pages = ["dashboard", "projects", "issues", "tasks", "reports", "settings"]
            if view in valid_pages:
                st.session_state['page'] = view
        
        # Check if data files exist
        if not check_data_files():
            return
            
        # Apply global styling
        st.markdown("""
        <style>
        /* Global Styling */
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #0e1117;
            color: #e0e0e0;
        }
        /* Remove default Streamlit spacing */
        .block-container {
            padding-top: 0;
            padding-bottom: 0;
        }
        /* Custom card styling */
        .card {
            background-color: #1e1e2e;
            border-radius: 0.5rem;
            padding: 1.25rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
            border: 1px solid #2d3748;
            margin-bottom: 1rem;
        }
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #e2e8f0;
            margin-bottom: 1rem;
        }
        /* Remove gap in column layout */
        div[data-testid="column"] {
            padding: 0 0.5rem;
        }
        /* Remove excessive spacing around components */
        div[data-testid="stVerticalBlock"] > div {
            padding-top: 0;
            padding-bottom: 0;
        }
        /* Make plotly charts fit better */
        .js-plotly-plot {
            margin-bottom: 0 !important;
        }
        /* Add a subtle background color */
        [data-testid="stAppViewContainer"] {
            background-color: #0e1117; 
        }
        /* Style the header section */
        .dashboard-header {
            background-color: #1a1a2e;
            padding: 1rem 1rem 0.5rem 1rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid #2d3748;
            box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }
        /* Layout container for main content */
        .main-content {
            padding: 0 1rem;
        }
        /* Fix tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background-color: #171722;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 16px;
            border-radius: 4px 4px 0px 0px;
            color: #a0aec0;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1e1e2e !important;
            border-bottom: none;
            border-top: 2px solid #3b82f6;
            color: #3b82f6;
        }
        /* Fix expander styling */
        .streamlit-expanderHeader {
            font-size: 1rem;
            font-weight: 600;
            color: #e2e8f0;
            background-color: #1a1a2e;
        }
        .streamlit-expanderContent {
            background-color: #1e1e2e;
            border: 1px solid #2d3748;
        }
        /* Fix dataframe styling */
        .stDataFrame {
            border-radius: 0.5rem;
            overflow: hidden;
            border: 1px solid #2d3748;
        }
        .stDataFrame [data-testid="stDataFrameResizable"] {
            background-color: #1a1a2e;
        }
        /* Style metrics */
        [data-testid="stMetric"] {
            background-color: #1e1e2e;
            padding: 10px;
            border-radius: 5px;
            color: #e0e0e0;
        }
        [data-testid="stMetricLabel"] {
            color: #a0aec0 !important;
        }
        [data-testid="stMetricValue"] {
            color: #e2e8f0 !important;
        }
        /* Style buttons */
        .stButton button {
            background-color: #3b82f6;
            color: white;
            border: none;
        }
        .stButton button:hover {
            background-color: #2563eb;
            color: white;
        }
        /* Style selectbox */
        .stSelectbox div[data-baseweb="select"] {
            background-color: #1a1a2e;
        }
        .stSelectbox div[data-baseweb="select"] > div {
            background-color: #1a1a2e;
            color: #e0e0e0;
            border-color: #2d3748;
        }
        /* General text color */
        p, span, div {
            color: #e0e0e0;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #e2e8f0;
        }
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1a1a2e;
        }
        [data-testid="stSidebarUserContent"] {
            background-color: #1a1a2e;
        }
        /* Navigation links */
        a.nav-link {
            text-decoration: none;
            display: block;
            margin-bottom: 0.5rem;
        }
        a.nav-link button {
            width: 100%;
            text-align: left;
            color: white;
            border: none;
            padding: 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.9rem;
            cursor: pointer;
        }
        a.nav-link button.active {
            background-color: #2563eb;
        }
        a.nav-link button.inactive {
            background-color: #3b82f6;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if not is_authenticated():
            login_page()
        else:
            # Apply custom styling for authenticated pages
            local_css()
            
            # Show sidebar menu
            sidebar_menu()
            
            # Show notifications if there are any
            user_data = get_current_user()
            
            if user_data and 'user_id' in user_data:
                try:
                    if get_unseen_notification_count(user_data['user_id']) > 0:
                        show_notifications_panel()
                except Exception as e:
                    st.sidebar.warning(f"Could not load notifications: {str(e)}")
            
            # Show the selected page with consistent layout
            page_title = {
                'dashboard': 'Production Dashboard',
                'projects': 'Projects Overview',
                'issues': 'Quality Issues',
                'tasks': 'Task Management',
                'reports': 'Analytics & Reports',
                'settings': 'System Settings'
            }.get(st.session_state['page'], 'Page Not Found')
            
            if st.session_state['page'] == 'dashboard':
                dashboard_page()
            elif st.session_state['page'] == 'projects':
                apply_page_layout(projects_page, page_title, user_data)
            elif st.session_state['page'] == 'issues':
                apply_page_layout(issues_page, page_title, user_data)
            elif st.session_state['page'] == 'tasks':
                apply_page_layout(tasks_page, page_title, user_data)
            elif st.session_state['page'] == 'reports':
                apply_page_layout(reports_page, page_title, user_data)
            elif st.session_state['page'] == 'settings':
                # Create a header with custom styling
                st.markdown('<div class="dashboard-header">', unsafe_allow_html=True)
                display_header("System Settings", user_data)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Wrap main content in a container
                st.markdown('<div class="main-content">', unsafe_allow_html=True)
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.info("Settings functionality will be implemented in future updates.")
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.title("Page Not Found")
                st.error(f"The page '{st.session_state['page']}' does not exist.")
                # Redirect to dashboard without using rerun
                st.session_state['page'] = 'dashboard'
                st.query_params["view"] = 'dashboard'
                
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error(traceback.format_exc())

if __name__ == "__main__":
    main() 