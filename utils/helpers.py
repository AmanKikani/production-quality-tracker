import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.database import get_users, get_module
from utils.notifications import get_unseen_notification_count
import base64
import os

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
        
        /* Login page and demo accounts styling */
        .demo-credentials {
            margin-top: 2rem;
            padding: 1.5rem;
            background-color: #1e1e2e;
            border-radius: 0.5rem;
            border: 1px solid #2d3748;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        }
        
        .demo-heading {
            font-weight: 600;
            color: #e2e8f0;
            margin-bottom: 1rem;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .demo-heading svg {
            color: #3b82f6;
        }
        
        .account-card {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            border-radius: 0.375rem;
            background-color: #111827;
            margin-bottom: 0.75rem;
            border: 1px solid #374151;
            transition: all 0.2s ease;
        }
        
        .account-card:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
            border-color: #4b5563;
        }
        
        .account-card:last-child {
            margin-bottom: 0;
        }
        
        .account-icon {
            width: 2.5rem;
            height: 2.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #2d3748;
            color: #3b82f6;
            border-radius: 50%;
            margin-right: 0.75rem;
        }
        
        .account-details {
            flex: 1;
        }
        
        .account-role {
            font-weight: 600;
            color: #e2e8f0;
            margin-bottom: 0.25rem;
            font-size: 0.95rem;
        }
        
        .account-credentials {
            color: #a0aec0;
            font-size: 0.85rem;
            font-family: monospace;
            background-color: #111827;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            display: inline-block;
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
    
    # Title in the left column
    with col1:
        st.markdown(f"""
        <div style="display: flex; align-items: center;">
            <h1 style="margin: 0; padding: 0; font-size: 1.75rem; font-weight: 600; color: #3b82f6;">{title}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    # User info in the right column
    with col2:
        if user_data:
            notification_count = get_unseen_notification_count(user_data['user_id'])
            notification_badge = f'<span class="notification-badge">{notification_count}</span>' if notification_count > 0 else ''
            
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; align-items: center;">
                <div style="display: flex; align-items: center; background-color: #1e1e2e; 
                    padding: 0.5rem 0.75rem; border-radius: 0.5rem; border: 1px solid #2d3748;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.2);">
                    <div style="margin-right: 0.75rem;">
                        <div style="font-weight: 600; font-size: 0.875rem; color: #e2e8f0; margin-bottom: 0.125rem;">
                            {user_data['username']}
                        </div>
                        <div style="font-size: 0.75rem; color: #a0aec0;">
                            {user_data['role'].capitalize()}
                        </div>
                    </div>
                    <div style="width: 2.25rem; height: 2.25rem; background-color: #2d3748; 
                        border-radius: 50%; display: flex; align-items: center; justify-content: center;
                        color: #3b82f6; font-weight: 600; font-size: 0.875rem; border: 2px solid #4b5563;">
                        {user_data['username'][0].upper()}
                    </div>
                    {notification_badge}
                </div>
            </div>
            """, unsafe_allow_html=True)

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
    """Create a progress chart for projects"""
    # Create a bar chart showing project progress
    fig = px.bar(
        data,
        x='progress',
        y='project_name',
        title=title,
        labels={'progress': 'Completion Progress (%)', 'project_name': 'Project'},
        text='progress',  # Use the actual progress values as text
        orientation='h',
        color='progress',
        color_continuous_scale=["#3B82F6", "#4ade80"]
    )
    
    # Customize appearance
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(color="#e2e8f0")
    )
    
    # Add annotation for percentage - fix the texttemplate to properly display percentages
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    
    return fig

def create_issues_by_category_chart(category_counts):
    """Create a chart showing issues by category"""
    # Prepare data
    categories = list(category_counts.keys())
    counts = list(category_counts.values())
    
    # Create horizontal bar chart
    fig = px.bar(
        x=counts,
        y=categories,
        title="Issues by Category",
        labels={'x': 'Number of Issues', 'y': 'Category'},
        orientation='h',
        color=counts,
        text=counts,  # Add text values to display count numbers
        color_continuous_scale=["#3B82F6", "#dc2626"]
    )
    
    # Customize appearance
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(color="#e2e8f0")
    )
    
    # Ensure text displays properly
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    
    return fig

def create_issues_by_severity_chart(severity_counts):
    """Create a chart showing issues by severity"""
    # Define the order of severity levels
    severity_order = ['Critical', 'High', 'Medium', 'Low']
    
    # Filter and sort data based on defined order
    filtered_severity = {k: severity_counts.get(k, 0) for k in severity_order if k in severity_counts}
    
    # Prepare data
    severities = list(filtered_severity.keys())
    counts = list(filtered_severity.values())
    
    # Define colors for each severity level
    colors = {
        'Critical': '#dc2626',
        'High': '#f97316',
        'Medium': '#f59e0b',
        'Low': '#4ade80'
    }
    
    # Create pie chart
    fig = px.pie(
        values=counts,
        names=severities,
        title="Issues by Severity",
        color=severities,
        color_discrete_map=colors
    )
    
    # Customize appearance
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(color="#e2e8f0"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    # Fix textinfo to properly display labels and percentages
    fig.update_traces(textposition='inside', textinfo='label+percent')
    
    return fig

def create_timeline_chart(df, date_col, title="Timeline"):
    """Create a Gantt chart for timeline visualization"""
    # Create a copy of the dataframe to avoid modifying the original
    chart_df = df.copy()
    
    # Prepare data for Gantt chart
    if 'start_date' in chart_df.columns and 'target_completion' in chart_df.columns:
        chart_df['start_date'] = pd.to_datetime(chart_df['start_date'])
        chart_df['target_completion'] = pd.to_datetime(chart_df['target_completion'])
        
        # Define colors based on status
        colors = {
            'Completed': '#4ade80',
            'In Progress': '#3b82f6',
            'Delayed': '#dc2626',
            'On Hold': '#f59e0b',
            'Not Started': '#a0aec0'
        }
        
        # Create figure
        fig = px.timeline(
            chart_df,
            x_start='start_date',
            x_end='target_completion',
            y='module_name' if 'module_name' in chart_df.columns else 'project_name',
            color='status',
            title=title,
            color_discrete_map=colors
        )
        
        # Add current date vertical line
        today = datetime.now()
        fig.add_vline(x=today, line_width=1, line_color="#cbd5e1", line_dash="dash")
        
        # Add annotation for current date
        fig.add_annotation(
            x=today,
            y=1.05,
            text="Today",
            showarrow=False,
            xanchor="center",
            yshift=10,
            font=dict(color="#cbd5e1")
        )
        
        # Customize layout
        fig.update_layout(
            xaxis_title="Timeline",
            yaxis_title="",
            height=max(300, len(chart_df) * 40),
            template="plotly_dark",
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
            font=dict(color="#e2e8f0")
        )
        
        return fig
    else:
        # If required columns don't exist, return a basic chart
        st.error("Required date columns not found for timeline chart")
        return None

def load_image(image_path):
    """Load an image file and return its base64 representation for embedding in HTML"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        print(f"Error loading image from {image_path}: {e}")
        return None

def get_image_html(image_path, width=None, height=None, css_class=None, alt_text="Image"):
    """Return HTML markup for an image from a local path"""
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        # Return a fallback SVG image pattern instead of just a comment
        svg_color = "#3b82f6"  # Blue color matching the app theme
        fallback_svg = f"""
        <svg width="{width or '100'}" height="{height or '100'}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#2d3748"/>
            <path d="M30,20 L70,20 L70,80 L30,80 Z" fill="{svg_color}" fill-opacity="0.6"/>
            <circle cx="50" cy="40" r="15" fill="{svg_color}"/>
            <path d="M30,80 L70,80 L50,50 Z" fill="{svg_color}"/>
        </svg>
        """
        width_attr = f"width='{width}'" if width else ""
        height_attr = f"height='{height}'" if height else ""
        class_attr = f"class='{css_class}'" if css_class else ""
        return f"""<div {width_attr} {height_attr} {class_attr}>{fallback_svg}</div>"""
    
    encoded_image = load_image(image_path)
    if not encoded_image:
        # Return a fallback pattern for failed loads too
        print(f"Failed to load image: {image_path}")
        svg_color = "#3b82f6"  # Blue color matching the app theme
        fallback_svg = f"""
        <svg width="{width or '100'}" height="{height or '100'}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#2d3748"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#a0aec0" font-family="sans-serif">
                Image Error
            </text>
        </svg>
        """
        width_attr = f"width='{width}'" if width else ""
        height_attr = f"height='{height}'" if height else ""
        class_attr = f"class='{css_class}'" if css_class else ""
        return f"""<div {width_attr} {height_attr} {class_attr}>{fallback_svg}</div>"""
    
    width_attr = f"width='{width}'" if width else ""
    height_attr = f"height='{height}'" if height else ""
    class_attr = f"class='{css_class}'" if css_class else ""
    
    return f"""<img src="data:image/png;base64,{encoded_image}" {width_attr} {height_attr} {class_attr} alt="{alt_text}">""" 