import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.database import get_users, get_module
from utils.notifications import get_unseen_notification_count
import base64

# UI Helper Functions
def set_page_config(title="Production & Quality Tracker", layout="wide", menu_items=None):
    """Set Streamlit page configuration"""
    st.set_page_config(
        page_title=title,
        page_icon="🏭",
        layout=layout,
        initial_sidebar_state="expanded",
        menu_items=menu_items or {
            'Report a bug': "mailto:support@example.com",
            'About': "# Production & Quality Tracker\n An MVP inspired by Offsight's Production & Quality Tracking application."
        }
    )

def local_css(file_name=None):
    """Load and apply custom CSS"""
    css = """
    <style>
        /* Main styles */
        .main-header {
            font-size: 2.2rem;
            font-weight: 600;
            color: #1e3a8a;
            margin-bottom: 1.2rem;
            letter-spacing: -0.5px;
        }
        
        .sub-header {
            font-size: 1.6rem;
            color: #334155;
            margin-bottom: 1.2rem;
            font-weight: 500;
        }
        
        /* Card styles */
        .card {
            padding: 1.5rem;
            border-radius: 0.75rem;
            background-color: #ffffff;
            box-shadow: 0 0.3rem 1rem rgba(0, 0, 0, 0.08);
            margin-bottom: 1.5rem;
            border: 1px solid #f1f5f9;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.12);
        }
        
        .card-header {
            font-weight: 600;
            font-size: 1.25rem;
            color: #0f172a;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 0.75rem;
        }
        
        /* Status indicators */
        .status-indicator {
            display: inline-block;
            width: 0.75rem;
            height: 0.75rem;
            border-radius: 50%;
            margin-right: 0.5rem;
            box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.8);
        }
        
        .status-green {
            background-color: #10b981;
        }
        
        .status-yellow {
            background-color: #f59e0b;
        }
        
        .status-red {
            background-color: #ef4444;
        }
        
        /* Notification badge */
        .notification-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.75rem;
            height: 1.75rem;
            border-radius: 50%;
            background-color: #ef4444;
            color: white;
            font-size: 0.875rem;
            margin-left: 0.5rem;
            font-weight: 600;
            box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
        }
        
        /* Priority tags */
        .priority-tag {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .priority-low {
            background-color: #10b981;
        }
        
        .priority-medium {
            background-color: #f59e0b;
            color: #ffffff;
        }
        
        .priority-high {
            background-color: #f97316;
        }
        
        .priority-critical {
            background-color: #ef4444;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.8; }
            100% { opacity: 1; }
        }
        
        /* Navbar styling */
        .navbar {
            display: flex;
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem;
            background-color: #f8fafc;
            border-radius: 0.75rem;
            margin-bottom: 1.5rem;
            border: 1px solid #e2e8f0;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            background-color: #f1f5f9;
            padding: 0.5rem 0.75rem;
            border-radius: 0.5rem;
            border: 1px solid #e2e8f0;
        }
        
        /* Progress bar styling */
        .stProgress > div > div > div > div {
            background-color: #3b82f6;
            border-radius: 1rem;
        }
        
        .stProgress > div {
            border-radius: 1rem;
            height: 0.75rem;
        }
        
        /* Button styling */
        .stButton button {
            font-weight: 500;
            border-radius: 0.5rem;
            transition: all 0.2s;
        }
        
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Divider styling */
        hr {
            margin: 1.5rem 0;
            border: 0;
            height: 1px;
            background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0));
        }
        
        /* Table styling */
        .dataframe {
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 0.5rem;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
        
        .dataframe th {
            background-color: #f8fafc;
            padding: 0.75rem 1rem;
            text-align: left;
            font-weight: 600;
            color: #334155;
            border-bottom: 2px solid #e2e8f0;
        }
        
        .dataframe td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .dataframe tr:last-child td {
            border-bottom: none;
        }
        
        .dataframe tr:hover td {
            background-color: #f1f5f9;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def display_header(title, user_data=None):
    """Display page header with title and user info"""
    col1, col2 = st.columns([6, 3])
    
    with col1:
        st.markdown(f"<h1 class='main-header'>{title}</h1>", unsafe_allow_html=True)
    
    with col2:
        if user_data:
            notification_count = get_unseen_notification_count(user_data['user_id'])
            notification_badge = f"<span class='notification-badge'>{notification_count}</span>" if notification_count > 0 else ""
            
            st.markdown(
                f"""
                <div class='user-info'>
                    <span style='margin-right: 10px;'>
                        <i class="fas fa-user-circle" style="margin-right: 5px;"></i>
                        <strong>{user_data['username']}</strong> ({user_data['role'].capitalize()})
                    </span>
                    {notification_badge}
                </div>
                """, 
                unsafe_allow_html=True
            )
    
    # Add a subtle divider
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 2rem;'>", unsafe_allow_html=True)

def render_card(title, content, className=""):
    """Render a card with title and content"""
    st.markdown(
        f"""
        <div class='card {className}'>
            <div class='card-header'>{title}</div>
            {content}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_status_indicator(status):
    """Render a status indicator based on status value"""
    if status.lower() in ['completed', 'resolved', 'green']:
        color_class = 'status-green'
    elif status.lower() in ['in progress', 'assigned', 'yellow']:
        color_class = 'status-yellow'
    else:
        color_class = 'status-red'
    
    return f"<span class='status-indicator {color_class}'></span>{status}"

def render_priority_tag(priority):
    """Render a priority tag with appropriate color"""
    if priority.lower() == 'low':
        color_class = 'priority-low'
    elif priority.lower() == 'medium':
        color_class = 'priority-medium'
    elif priority.lower() == 'high':
        color_class = 'priority-high'
    elif priority.lower() == 'critical':
        color_class = 'priority-critical'
    else:
        color_class = 'priority-medium'
    
    return f"<span class='priority-tag {color_class}'>{priority}</span>"

# Data formatting and conversion helpers
def format_date(date_str):
    """Format date string to display format"""
    if not date_str or date_str == '' or pd.isna(date_str):
        return ''
    
    try:
        date_obj = pd.to_datetime(date_str)
        return date_obj.strftime('%b %d, %Y')
    except:
        return date_str

def calculate_days_remaining(due_date):
    """Calculate days remaining until due date"""
    if not due_date or due_date == '' or pd.isna(due_date):
        return None
    
    try:
        due_date_obj = pd.to_datetime(due_date)
        today = datetime.now().date()
        days_remaining = (due_date_obj.date() - today).days
        return days_remaining
    except:
        return None

def get_user_name(user_id):
    """Get username by user ID"""
    users_df = get_users()
    if users_df.empty:
        return f"User {user_id}"
    
    user = users_df[users_df['user_id'] == int(user_id)]
    if user.empty:
        return f"User {user_id}"
    
    return user.iloc[0]['username']

def get_module_name(module_id):
    """Get module name by module ID"""
    module = get_module(module_id)
    if not module:
        return f"Module {module_id}"
    
    return module['module_name']

# Visualization helpers
def create_progress_chart(data, title="Project Progress"):
    """Create a horizontal bar chart for project progress"""
    if data.empty:
        return None
    
    fig = px.bar(
        data,
        y='project_name',
        x='progress',
        title=title,
        labels={'progress': 'Completion %', 'project_name': 'Project'},
        color='progress',
        color_continuous_scale='Viridis',
        text='progress',
        orientation='h'
    )
    
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(
        xaxis_range=[0, 100],
        height=max(300, len(data) * 50)
    )
    
    return fig

def create_issues_by_category_chart(category_counts):
    """Create a pie chart for issues by category"""
    if not category_counts:
        return None
    
    fig = px.pie(
        values=list(category_counts.values()),
        names=list(category_counts.keys()),
        title="Issues by Category",
        hole=0.4
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_issues_by_severity_chart(severity_counts):
    """Create a bar chart for issues by severity"""
    if not severity_counts:
        return None
    
    severity_order = ['Low', 'Medium', 'High', 'Critical']
    
    # Ensure all severity levels exist in the data
    for severity in severity_order:
        if severity not in severity_counts:
            severity_counts[severity] = 0
    
    # Create dataframe with ordered severity levels
    df = pd.DataFrame({
        'Severity': severity_order,
        'Count': [severity_counts.get(severity, 0) for severity in severity_order]
    })
    
    colors = ['#28a745', '#ffc107', '#fd7e14', '#dc3545']
    
    fig = px.bar(
        df,
        x='Severity',
        y='Count',
        title="Issues by Severity",
        color='Severity',
        color_discrete_map={severity: color for severity, color in zip(severity_order, colors)},
        category_orders={"Severity": severity_order}
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_timeline_chart(df, date_col, title="Timeline"):
    """Create a timeline chart from dataframe with date column"""
    if df.empty:
        return None
    
    # Convert date strings to datetime objects
    df[date_col] = pd.to_datetime(df[date_col])
    
    # Sort by date
    df = df.sort_values(by=date_col)
    
    fig = px.timeline(
        df,
        x_start=date_col,
        y='module_name',
        title=title,
        color='status'
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=max(300, len(df) * 30))
    
    return fig 