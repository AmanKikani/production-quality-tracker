"""
Notification system for the Volumod Production Tracker.

This module handles creating, retrieving, and managing notifications for users.
"""

import streamlit as st
from datetime import datetime
import json

# Import database functions
from utils.data_models import execute_query, execute_update, log_audit
from utils.auth import get_current_user

# Notification types and their display properties
NOTIFICATION_TYPES = {
    'task_assigned': {
        'icon': '📋',
        'color': '#4CAF50',  # Green
        'title_template': 'New Task Assigned',
        'message_template': 'You have been assigned a new task: {details}'
    },
    'task_updated': {
        'icon': '🔄',
        'color': '#2196F3',  # Blue
        'title_template': 'Task Updated',
        'message_template': 'Task has been updated: {details}'
    },
    'task_completed': {
        'icon': '✅',
        'color': '#4CAF50',  # Green
        'title_template': 'Task Completed',
        'message_template': 'Task has been marked as complete: {details}'
    },
    'issue_reported': {
        'icon': '⚠️',
        'color': '#FF9800',  # Orange
        'title_template': 'New Quality Issue',
        'message_template': 'A new quality issue has been reported: {details}'
    },
    'issue_updated': {
        'icon': '🔄',
        'color': '#2196F3',  # Blue
        'title_template': 'Quality Issue Updated',
        'message_template': 'A quality issue has been updated: {details}'
    },
    'issue_resolved': {
        'icon': '✅',
        'color': '#4CAF50',  # Green
        'title_template': 'Quality Issue Resolved',
        'message_template': 'A quality issue has been resolved: {details}'
    },
    'stage_completed': {
        'icon': '🏁',
        'color': '#4CAF50',  # Green
        'title_template': 'Production Stage Completed',
        'message_template': 'Production stage has been completed: {details}'
    },
    'inspection_required': {
        'icon': '🔍',
        'color': '#FF9800',  # Orange
        'title_template': 'Inspection Required',
        'message_template': 'Product unit requires inspection: {details}'
    },
    'inspection_completed': {
        'icon': '✓',
        'color': '#4CAF50',  # Green
        'title_template': 'Inspection Completed',
        'message_template': 'Product inspection has been completed: {details}'
    },
    'mention': {
        'icon': '@',
        'color': '#9C27B0',  # Purple
        'title_template': 'You were mentioned',
        'message_template': '{details}'
    },
    'system': {
        'icon': '🔔',
        'color': '#607D8B',  # Blue Grey
        'title_template': 'System Notification',
        'message_template': '{details}'
    }
}

def create_notification(user_id, notification_type, reference_type, reference_id, details=None, priority='normal'):
    """
    Creates a new notification for a user.
    
    Args:
        user_id (int): The ID of the user to receive the notification
        notification_type (str): The type of notification (see NOTIFICATION_TYPES)
        reference_type (str): The type of entity the notification refers to (e.g., 'task', 'issue')
        reference_id (int): The ID of the entity being referenced
        details (str, optional): Additional details about the notification
        priority (str, optional): Priority level ('low', 'normal', 'high', 'urgent')
        
    Returns:
        bool: True if notification created successfully, False otherwise
    """
    try:
        # Format title and message using templates if available
        type_info = NOTIFICATION_TYPES.get(notification_type, {
            'icon': '🔔',
            'color': '#607D8B',
            'title_template': 'Notification',
            'message_template': '{details}'
        })
        
        title = type_info['title_template']
        message = type_info['message_template'].format(details=details or '')
        
        # Insert notification into database - using corrected column names to match schema
        execute_update(
            """
            INSERT INTO notifications (
                user_id, notification_type, entity_type, entity_id, 
                title, message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, notification_type, reference_type, reference_id, 
             title, message)
        )
        
        # Log the creation
        current_user = get_current_user()
        creator_id = current_user['user_id'] if current_user else None
        log_audit(creator_id, 'create', 'notification', None)
        
        return True
        
    except Exception as e:
        st.error(f"Error creating notification: {str(e)}")
        return False

def notify_multiple_users(user_ids, notification_type, reference_type, reference_id, details=None, priority='normal'):
    """
    Creates notifications for multiple users.
    
    Args:
        user_ids (list): List of user IDs to notify
        notification_type (str): Type of notification
        reference_type (str): Type of entity referenced
        reference_id (int): ID of the entity referenced
        details (str, optional): Additional details
        priority (str, optional): Notification priority
        
    Returns:
        bool: True if all notifications created successfully
    """
    success = True
    for user_id in user_ids:
        if not create_notification(user_id, notification_type, reference_type, reference_id, details, priority):
            success = False
    return success

def notify_by_role(role, notification_type, reference_type, reference_id, details=None, priority='normal'):
    """
    Creates notifications for all users with a specific role.
    
    Args:
        role (str): The role to filter users by
        notification_type (str): Type of notification
        reference_type (str): Type of entity referenced
        reference_id (int): ID of the entity referenced
        details (str, optional): Additional details
        priority (str, optional): Notification priority
        
    Returns:
        bool: True if all notifications created successfully
    """
    try:
        # Get all users with the specified role
        users = execute_query(
            "SELECT user_id FROM users WHERE role = ?",
            (role,)
        )
        
        if not users:
            return False
        
        # Extract user IDs
        user_ids = [user['user_id'] for user in users]
        
        # Notify all the users
        return notify_multiple_users(user_ids, notification_type, reference_type, reference_id, details, priority)
        
    except Exception as e:
        st.error(f"Error notifying users by role: {str(e)}")
        return False

def get_user_notifications(user_id, limit=20, include_read=False, order_by='created_at DESC'):
    """
    Retrieves notifications for a specific user.
    
    Args:
        user_id (int): The ID of the user
        limit (int, optional): Maximum number of notifications to retrieve
        include_read (bool, optional): Whether to include read notifications
        order_by (str, optional): SQL ORDER BY clause
        
    Returns:
        list: List of notifications
    """
    try:
        # Build query conditions
        conditions = ["user_id = ?"]
        params = [user_id]
        
        if not include_read:
            conditions.append("read_at IS NULL")
        
        where_clause = " AND ".join(conditions)
        
        # Execute the query - Fix column names to match database schema
        notifications = execute_query(
            f"""
            SELECT notification_id, notification_type as type, entity_type as reference_type, 
                  entity_id as reference_id, title, message, created_at, read_at
            FROM notifications
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT ?
            """,
            (*params, limit)
        )
        
        # Enhance notifications with display properties
        for notification in notifications:
            notification_type = notification['type']
            type_info = NOTIFICATION_TYPES.get(notification_type, {
                'icon': '🔔',
                'color': '#607D8B'
            })
            
            notification['icon'] = type_info['icon']
            notification['color'] = type_info['color']
        
        return notifications
        
    except Exception as e:
        st.error(f"Error retrieving notifications: {str(e)}")
        return []

def mark_notification_read(notification_id):
    """
    Marks a notification as read.
    
    Args:
        notification_id (int): The ID of the notification
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        execute_update(
            "UPDATE notifications SET read_at = CURRENT_TIMESTAMP WHERE notification_id = ?",
            (notification_id,)
        )
        
        # Log the action
        current_user = get_current_user()
        if current_user:
            log_audit(current_user['user_id'], 'read', 'notification', notification_id)
        
        return True
        
    except Exception as e:
        st.error(f"Error marking notification as read: {str(e)}")
        return False

def mark_all_notifications_read(user_id):
    """
    Marks all notifications for a user as read.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        execute_update(
            "UPDATE notifications SET read_at = CURRENT_TIMESTAMP WHERE user_id = ? AND read_at IS NULL",
            (user_id,)
        )
        
        # Log the action
        log_audit(user_id, 'read_all', 'notification', None)
        
        return True
        
    except Exception as e:
        st.error(f"Error marking all notifications as read: {str(e)}")
        return False

def delete_notification(notification_id):
    """
    Deletes a notification.
    
    Args:
        notification_id (int): The ID of the notification
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        execute_update(
            "DELETE FROM notifications WHERE notification_id = ?",
            (notification_id,)
        )
        
        # Log the action
        current_user = get_current_user()
        if current_user:
            log_audit(current_user['user_id'], 'delete', 'notification', notification_id)
        
            return True
        
    except Exception as e:
        st.error(f"Error deleting notification: {str(e)}")
        return False

def delete_all_read_notifications(user_id):
    """
    Deletes all read notifications for a user.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        execute_update(
            "DELETE FROM notifications WHERE user_id = ? AND read_at IS NOT NULL",
            (user_id,)
        )
        
        # Log the action
        log_audit(user_id, 'delete_read', 'notification', None)
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting read notifications: {str(e)}")
    return False

def get_unread_notification_count(user_id):
    """
    Gets the count of unread notifications for a user.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        int: Number of unread notifications
    """
    try:
        result = execute_query(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND read_at IS NULL",
            (user_id,),
            fetchall=False
        )
        
        return result['count'] if result else 0
        
    except Exception as e:
        st.error(f"Error getting unread notification count: {str(e)}")
        return 0

def render_notification_badge(count):
    """
    Renders a notification badge with the unread count.
    
    Args:
        count (int): The number of unread notifications
        
    Returns:
        str: HTML for the notification badge
    """
    if count <= 0:
        return ""
    
    return f"""
    <div class="notification-badge">{count}</div>
    """

def render_notification_item(notification):
    """
    Renders an individual notification as HTML.
    
    Args:
        notification (dict): The notification to render
        
    Returns:
        str: HTML for the notification
    """
    # Format the created date
    created_at = notification['created_at']
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            pass
    
    if isinstance(created_at, datetime):
        time_diff = datetime.now() - created_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days}d ago"
        elif time_diff.seconds // 3600 > 0:
            time_str = f"{time_diff.seconds // 3600}h ago"
        else:
            time_str = f"{time_diff.seconds // 60}m ago"
    else:
        time_str = str(created_at)
    
    # Set priority marker
    priority_marker = ""
    if notification['priority'] == 'high':
        priority_marker = '<span class="priority-high">!</span>'
    elif notification['priority'] == 'urgent':
        priority_marker = '<span class="priority-urgent">!!</span>'
    
    # Create the notification HTML
    return f"""
    <div class="notification-item" data-id="{notification['notification_id']}">
        <div class="notification-icon" style="background-color: {notification['color']}">
            {notification['icon']}
        </div>
        <div class="notification-content">
            <div class="notification-header">
                <span class="notification-title">{notification['title']} {priority_marker}</span>
                <span class="notification-time">{time_str}</span>
            </div>
            <div class="notification-message">{notification['message']}</div>
        </div>
        <div class="notification-actions">
            <button class="mark-read-btn" data-id="{notification['notification_id']}">✓</button>
        </div>
    </div>
    """

def render_notification_panel():
    """
    Renders the notification panel for the current user.
    
    Returns:
        str: HTML for the notification panel
    """
    current_user = get_current_user()
    if not current_user:
        return ""
    
    user_id = current_user['user_id']
    notifications = get_user_notifications(user_id, limit=10)
    
    notifications_html = ""
    for notification in notifications:
        notifications_html += render_notification_item(notification)
    
    if not notifications:
        notifications_html = '<div class="no-notifications">No new notifications</div>'
    
    # Create the panel HTML
    panel_html = f"""
    <div class="notification-panel">
        <div class="notification-panel-header">
            <h3>Notifications</h3>
            <button id="mark-all-read-btn" data-userid="{user_id}">Mark all as read</button>
        </div>
        <div class="notification-list">
            {notifications_html}
        </div>
        <div class="notification-panel-footer">
            <a href="#" id="view-all-notifications">View all notifications</a>
        </div>
    </div>
    
    <script>
    /* JavaScript for notification interactions */
    document.addEventListener('DOMContentLoaded', function() {{
        /* Mark single notification as read */
        document.querySelectorAll('.mark-read-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                const notifId = this.getAttribute('data-id');
                /* Send to Streamlit via custom event */
                window.parent.postMessage({{
                    type: 'streamlit:customEvent',
                    event: 'mark_notification_read',
                    data: {{ notification_id: notifId }}
                }}, '*');
                
                /* Remove from UI */
                const notifItem = document.querySelector(`.notification-item[data-id="${{notifId}}"]`);
                if (notifItem) notifItem.remove();
                
                /* Update badge count */
                const badge = document.querySelector('.notification-badge');
                if (badge) {{
                    const count = parseInt(badge.textContent) - 1;
                    if (count <= 0) {{
                        badge.style.display = 'none';
                    }} else {{
                        badge.textContent = count;
                    }}
                }}
            }});
        }});
        
        /* Mark all as read */
        const markAllBtn = document.getElementById('mark-all-read-btn');
        if (markAllBtn) {{
            markAllBtn.addEventListener('click', function() {{
                const userId = this.getAttribute('data-userid');
                /* Send to Streamlit */
                window.parent.postMessage({{
                    type: 'streamlit:customEvent',
                    event: 'mark_all_notifications_read',
                    data: {{ user_id: userId }}
                }}, '*');
                
                /* Update UI */
                document.querySelectorAll('.notification-item').forEach(item => {{
                    item.remove();
                }});
                
                document.querySelector('.notification-list').innerHTML = 
                    '<div class="no-notifications">No new notifications</div>';
                
                /* Update badge */
                const badge = document.querySelector('.notification-badge');
                if (badge) badge.style.display = 'none';
            }});
        }}
    }});
    </script>
    """
    
    return panel_html

def initialize_notification_handlers():
    """
    Initializes Streamlit event handlers for notification actions.
    This should be called in the main app file.
    """
    # Register a custom component for handling notification interactions
    if 'notification_handlers_initialized' not in st.session_state:
        st.session_state.notification_handlers_initialized = True
        
        # Handle mark as read event
        def handle_mark_read(event_data):
            notification_id = event_data.get('notification_id')
            if notification_id:
                mark_notification_read(int(notification_id))
                
                # Update the unread count in session state
                if 'unread_notification_count' in st.session_state:
                    count = st.session_state.unread_notification_count
                    st.session_state.unread_notification_count = max(0, count - 1)
        
        # Handle mark all as read event
        def handle_mark_all_read(event_data):
            user_id = event_data.get('user_id')
            if user_id:
                mark_all_notifications_read(int(user_id))
                
                # Reset the unread count in session state
                st.session_state.unread_notification_count = 0
        
        # Register the handlers with Streamlit
        st.register_component_for_event("mark_notification_read", handle_mark_read)
        st.register_component_for_event("mark_all_notifications_read", handle_mark_all_read)

# Helper notification functions used by other modules
def notify_project_complete(project_id, project_name):
    """
    Creates notifications for managers when a project is completed.
    
    Args:
        project_id (int): The ID of the completed project
        project_name (str): The name of the completed project
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return notify_by_role(
            'manager', 
            'stage_completed', 
            'project', 
            project_id, 
            f"Project '{project_name}' has been marked as complete.", 
            'normal'
        )
    except Exception as e:
        st.error(f"Error notifying about project completion: {str(e)}")
        return False

def notify_task_assigned(task_id, task_description, assigned_to_id, due_date):
    """
    Creates a notification for a user when they are assigned a task.
    
    Args:
        task_id (str): The ID of the assigned task
        task_description (str): Description of the task
        assigned_to_id (int): User ID of the assignee
        due_date (str): Due date of the task
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return create_notification(
            assigned_to_id,
            'task_assigned',
            'task',
            task_id,
            f"Task: {task_description}. Due: {due_date}",
            'normal'
        )
    except Exception as e:
        st.error(f"Error notifying about task assignment: {str(e)}")
        return False

def notify_task_due_soon(task_id, task_description, assigned_to_id, days_remaining):
    """
    Creates a notification for a user when their task is due soon.
    
    Args:
        task_id (str): The ID of the task
        task_description (str): Description of the task
        assigned_to_id (int): User ID of the assignee
        days_remaining (int): Number of days remaining until due date
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        priority = 'urgent' if days_remaining <= 1 else 'high'
        return create_notification(
            assigned_to_id,
            'task_updated',
            'task',
            task_id,
            f"Task '{task_description}' is due in {days_remaining} day{'s' if days_remaining != 1 else ''}!",
            priority
        )
    except Exception as e:
        st.error(f"Error notifying about due date: {str(e)}")
        return False

def notify_new_issue(issue_id, module_id, severity, description, reporter_id):
    """
    Creates notifications for managers when a new quality issue is reported.
    
    Args:
        issue_id (int): The ID of the new issue
        module_id (int): The ID of the module with the issue
        severity (str): Severity level of the issue
        description (str): Description of the issue
        reporter_id (int): User ID who reported the issue
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get details for better notification
        from utils.database import get_module
        module = get_module(module_id)
        module_name = module.get('module_name', 'Unknown module') if module else 'Unknown module'
        
        priority = 'urgent' if severity.lower() == 'critical' else 'high' if severity.lower() == 'major' else 'normal'
        
        # Notify managers
        return notify_by_role(
            'manager',
            'issue_reported',
            'issue',
            issue_id,
            f"{severity.capitalize()} issue on {module_name}: {description}",
            priority
        )
    except Exception as e:
        st.error(f"Error notifying about new issue: {str(e)}")
        return False

def notify_issue_resolved(issue_id, module_id, resolver_id):
    """
    Creates notifications for managers when a quality issue is resolved.
    
    Args:
        issue_id (int): The ID of the resolved issue
        module_id (int): The ID of the module with the issue
        resolver_id (int): User ID who resolved the issue
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get details for better notification
        from utils.database import get_module
        module = get_module(module_id)
        module_name = module.get('module_name', 'Unknown module') if module else 'Unknown module'
        
        # Notify managers
        return notify_by_role(
            'manager',
            'issue_resolved',
            'issue',
            issue_id,
            f"Quality issue on {module_name} has been resolved.",
            'normal'
        )
    except Exception as e:
        st.error(f"Error notifying about resolved issue: {str(e)}")
        return False

# Create a wrapper function to adapt the parameters expected in app.py to the actual function
def get_notifications(user_id, max_count=10, include_seen=False):
    """
    Adapts parameters to work with get_user_notifications.
    
    Args:
        user_id (int): The ID of the user
        max_count (int, optional): Maximum number of notifications to retrieve
        include_seen (bool, optional): Whether to include seen notifications
        
    Returns:
        list: List of notifications with adapted fields
    """
    try:
        # Get raw notifications using the fixed get_user_notifications function
        notifications = get_user_notifications(
            user_id=user_id,
            limit=max_count,
            include_read=include_seen
        )
        
        # Process the notifications for display, adapting field names if needed
        for notification in notifications:
            # Ensure we have the right fields for display
            if 'read_at' in notification:
                notification['seen'] = notification['read_at'] is not None
            else:
                notification['seen'] = False
                
            # Map notification_id to id for backward compatibility
            notification['id'] = notification['notification_id']
                
            # Format times for display
            if 'created_at' in notification:
                created_dt = datetime.strptime(notification['created_at'], '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                delta = now - created_dt
                
                if delta.days == 0:
                    if delta.seconds < 3600:
                        minutes = delta.seconds // 60
                        notification['time'] = f"{minutes}m ago"
                    else:
                        hours = delta.seconds // 3600
                        notification['time'] = f"{hours}h ago"
                elif delta.days == 1:
                    notification['time'] = "Yesterday"
                else:
                    notification['time'] = created_dt.strftime('%b %d')
                
                # Also provide timestamp for backward compatibility
                notification['timestamp'] = notification['time']
            
        return notifications
    except Exception as e:
        st.error(f"Error in get_notifications adapter: {str(e)}")
        return []

# Wrapper function for mark_notification_read to maintain compatibility
def mark_notification_as_seen(notification_id):
    """
    Wrapper function to maintain compatibility with old code.
    Adapts parameters to work with mark_notification_read.
    
    Args:
        notification_id (int): The ID of the notification
        
    Returns:
        bool: True if successful, False otherwise
    """
    return mark_notification_read(notification_id)

# Wrapper function for mark_all_notifications_read to maintain compatibility
def mark_all_notifications_as_seen(user_id):
    """
    Wrapper function to maintain compatibility with old code.
    Adapts parameters to work with mark_all_notifications_read.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        bool: True if successful, False otherwise
    """
    return mark_all_notifications_read(user_id)

# Wrapper function for get_unread_notification_count to maintain compatibility
def get_unseen_notification_count(user_id):
    """
    Wrapper function to maintain compatibility with old code.
    Adapts parameters to work with get_unread_notification_count.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        int: Number of unseen notifications
    """
    return get_unread_notification_count(user_id) 