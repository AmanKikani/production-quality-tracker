import pandas as pd
import streamlit as st
from datetime import datetime
import json

# Notification related functions
def initialize_notifications():
    """Initialize notifications in session state if not already present"""
    if 'notifications' not in st.session_state:
        st.session_state['notifications'] = []
    if 'seen_notifications' not in st.session_state:
        st.session_state['seen_notifications'] = set()

def add_notification(title, message, category, user_id=None, link=None):
    """Add a new notification to the session state"""
    initialize_notifications()
    
    # Create notification object
    notification = {
        'id': len(st.session_state['notifications']) + 1,
        'title': title,
        'message': message,
        'category': category,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': user_id,  # can be None for all users
        'link': link,        # can be None
        'seen': False
    }
    
    # Add to notifications list
    st.session_state['notifications'].append(notification)
    
    return notification['id']

def get_notifications(user_id=None, max_count=None, include_seen=False):
    """Get notifications for a user"""
    initialize_notifications()
    
    # Filter notifications for the user or all users (if user_id is None)
    filtered_notifications = []
    for notification in st.session_state['notifications']:
        if (notification['user_id'] is None or notification['user_id'] == user_id) and \
           (include_seen or not notification['seen']):
            filtered_notifications.append(notification)
    
    # Sort by timestamp, newest first
    filtered_notifications.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Limit to max_count if specified
    if max_count is not None:
        filtered_notifications = filtered_notifications[:max_count]
    
    return filtered_notifications

def mark_notification_as_seen(notification_id):
    """Mark a notification as seen"""
    initialize_notifications()
    
    for notification in st.session_state['notifications']:
        if notification['id'] == notification_id:
            notification['seen'] = True
            st.session_state['seen_notifications'].add(notification_id)
            return True
    
    return False

def mark_all_notifications_as_seen(user_id=None):
    """Mark all notifications for a user as seen"""
    initialize_notifications()
    
    marked_count = 0
    for notification in st.session_state['notifications']:
        if (notification['user_id'] is None or notification['user_id'] == user_id) and not notification['seen']:
            notification['seen'] = True
            st.session_state['seen_notifications'].add(notification['id'])
            marked_count += 1
    
    return marked_count

def get_unseen_notification_count(user_id=None):
    """Get count of unseen notifications for a user"""
    initialize_notifications()
    
    count = 0
    for notification in st.session_state['notifications']:
        if (notification['user_id'] is None or notification['user_id'] == user_id) and not notification['seen']:
            count += 1
    
    return count

# Notification generator functions for specific events
def notify_new_issue(issue_id, module_id, severity, description, reported_by):
    """Generate notification for a new issue"""
    title = f"New {severity} Issue Reported"
    message = f"Issue {issue_id} on module {module_id}: {description}"
    category = "issue"
    link = f"issues?issue_id={issue_id}"
    
    # Add notification for managers and supervisors
    return add_notification(title, message, category, None, link)

def notify_issue_resolved(issue_id, module_id, resolved_by):
    """Generate notification for resolved issue"""
    title = "Issue Resolved"
    message = f"Issue {issue_id} on module {module_id} has been resolved"
    category = "issue"
    link = f"issues?issue_id={issue_id}"
    
    # Add notification
    return add_notification(title, message, category, None, link)

def notify_task_assigned(task_id, description, assigned_to, due_date):
    """Generate notification for new task assignment"""
    title = "New Task Assigned"
    message = f"Task {task_id}: {description}. Due: {due_date}"
    category = "task"
    link = f"tasks?task_id={task_id}"
    
    # Add notification for the assigned user
    return add_notification(title, message, category, assigned_to, link)

def notify_task_due_soon(task_id, description, assigned_to, due_date):
    """Generate notification for task due soon"""
    title = "Task Due Soon"
    message = f"Task {task_id}: {description} is due on {due_date}"
    category = "task"
    link = f"tasks?task_id={task_id}"
    
    # Add notification for the assigned user
    return add_notification(title, message, category, assigned_to, link)

def notify_project_complete(project_id, project_name):
    """Generate notification for project completion"""
    title = "Project Completed"
    message = f"Project {project_name} (ID: {project_id}) has been completed"
    category = "project"
    link = f"projects?project_id={project_id}"
    
    # Add notification for all users
    return add_notification(title, message, category, None, link)

def notify_quality_alert(module_id, issue, recommended_action):
    """Generate notification for quality alert"""
    title = "Quality Alert"
    message = f"Quality issue on module {module_id}: {issue}. Recommended action: {recommended_action}"
    category = "quality"
    link = f"modules?module_id={module_id}"
    
    # Add notification for all users
    return add_notification(title, message, category, None, link) 