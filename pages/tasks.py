import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to sys.path to import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import is_authenticated, get_current_user
from utils.database import get_tasks, update_task_status, create_task, get_issues, get_modules, get_issue_statistics
from utils.helpers import display_header, format_date, render_status_indicator, render_priority_tag, get_user_name, get_module_name, calculate_days_remaining
from utils.notifications import notify_task_assigned, notify_task_due_soon

def load_task_details(task_id):
    """Load and display details for a specific task"""
    tasks_df = get_tasks()
    
    if tasks_df.empty:
        st.error("No tasks found in the database.")
        return
    
    task = tasks_df[tasks_df['task_id'] == task_id]
    
    if task.empty:
        st.error(f"Task with ID {task_id} not found.")
        return
    
    task = task.iloc[0]
    
    # Get module information
    module_name = get_module_name(task['module_id'])
    
    # Display task header
    st.markdown(f"## Task: {task['task_id']}")
    st.markdown(f"**Module:** {module_name}")
    
    # Create columns for task details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        priority_tag = render_priority_tag(task['priority'])
        st.markdown(f"**Priority:** {priority_tag}", unsafe_allow_html=True)
    
    with col2:
        status_indicator = render_status_indicator(task['status'])
        st.markdown(f"**Status:** {status_indicator}", unsafe_allow_html=True)
    
    with col3:
        # Display related issue if exists
        if pd.notna(task['issue_id']) and task['issue_id'] != '':
            st.markdown(f"**Related Issue:** {task['issue_id']}")
        else:
            st.markdown("**Related Issue:** None")
    
    # Task description
    st.markdown("### Description")
    st.write(task['description'])
    
    # Task timeline
    st.markdown("### Timeline")
    
    # Format dates
    assigned_date = format_date(task['assigned_date'])
    due_date = format_date(task['due_date'])
    completion_date = format_date(task['completion_date']) if pd.notna(task['completion_date']) else "Not completed yet"
    
    # Calculate days remaining or overdue
    days_remaining = calculate_days_remaining(task['due_date'])
    
    # Create a timeline display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Assigned on:** {assigned_date}")
        assigner_name = get_user_name(task['assigned_by'])
        st.markdown(f"**Assigned by:** {assigner_name}")
    
    with col2:
        st.markdown(f"**Due on:** {due_date}")
        assignee_name = get_user_name(task['assigned_to'])
        st.markdown(f"**Assigned to:** {assignee_name}")
    
    with col3:
        st.markdown(f"**Completed on:** {completion_date}")
        
        # Display days remaining or overdue
        if task['status'] != 'Completed':
            if days_remaining is not None:
                if days_remaining > 0:
                    st.markdown(f"**Days remaining:** {days_remaining}")
                elif days_remaining == 0:
                    st.markdown("**Due today!**")
                else:
                    st.markdown(f"**Overdue by:** {abs(days_remaining)} days", unsafe_allow_html=True)
    
    # Status update section (if task is not completed)
    if task['status'] != 'Completed':
        st.divider()
        
        # Get current user info
        user_data = get_current_user()
        
        # Check if user has permission to update task status
        can_update = (user_data['user_id'] == task['assigned_to']) or (user_data['role'].lower() in ['manager', 'supervisor'])
        
        if can_update:
            st.subheader("Update Task Status")
            
            col1, col2 = st.columns(2)
            
            with col1:
                status_options = ["In Progress", "On Hold", "Completed"]
                new_status = st.selectbox("New Status", status_options)
            
            # Update button
            update_placeholder = st.empty()
            if update_placeholder.button("Update Status"):
                if update_task_status(task_id, new_status):
                    update_placeholder.success(f"Task status updated to {new_status}.")
                    # Add a redirect script instead of st.rerun()
                    st.markdown(
                        f"""
                        <script>
                            setTimeout(function() {{
                                window.location.href = "?view=tasks&task_id={task_id}";
                            }}, 1000);
                        </script>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    update_placeholder.error("Failed to update task status.")

def create_new_task():
    """Display and handle form for creating a new task"""
    st.subheader("Create New Task")
    
    # Get current user info
    user_data = get_current_user()
    
    # Get all modules for selection
    modules_df = get_modules()
    
    # Get all users for assignment
    users_df = pd.read_csv('data/users.csv')
    
    # Get all issues for possible relation
    issues_df = get_issues(status="Open")
    
    with st.form("create_task_form"):
        # Create columns for form layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Module selection
            module_options = modules_df[['module_id', 'module_name']].values.tolist()
            module_options = [f"{m[0]} - {m[1]}" for m in module_options]
            selected_module = st.selectbox("Select Module", module_options)
            
            # Issue selection (optional)
            issue_options = [("", "No Related Issue")] + \
                [(i['issue_id'], f"{i['issue_id']} - {i['description'][:30]}...") for _, i in issues_df.iterrows()]
            selected_issue = st.selectbox(
                "Related Issue (Optional)", 
                options=[f"{i[0]}" if i[0] == "" else f"{i[0]} - {i[1]}" for i in issue_options],
                format_func=lambda x: "No Related Issue" if x == "" else x
            )
            
            # Assigned to selection
            user_options = users_df[['user_id', 'username']].values.tolist()
            user_options = [f"{u[0]} - {u[1]}" for u in user_options]
            assigned_to = st.selectbox("Assign To", user_options)
        
        with col2:
            # Due date selection
            due_date = st.date_input("Due Date", datetime.now() + pd.Timedelta(days=3))
            due_date = due_date.strftime('%Y-%m-%d')
            
            # Priority selection
            priority_options = ["Low", "Medium", "High", "Critical"]
            priority = st.selectbox("Priority", priority_options)
            
            # Description
            description = st.text_area("Task Description", height=100)
        
        # Submit button
        submitted = st.form_submit_button("Create Task", type="primary", use_container_width=True)
        
        if submitted:
            if selected_module and assigned_to and due_date and priority and description:
                # Extract module_id from selection
                module_id = selected_module.split(" - ")[0]
                
                # Extract issue_id from selection (if any)
                issue_id = ""
                if selected_issue and selected_issue != "":
                    issue_id = selected_issue.split(" - ")[0] if " - " in selected_issue else selected_issue
                
                # Extract user_id from selection
                assigned_to_id = int(assigned_to.split(" - ")[0])
                
                # Create new task
                task_created = create_task(
                    issue_id, 
                    module_id, 
                    assigned_to_id, 
                    user_data['user_id'], 
                    due_date, 
                    description, 
                    priority
                )
                
                if task_created:
                    # Create notification for task assignment
                    notify_task_assigned("T" + str(task_created), description, assigned_to_id, due_date)
                    
                    st.success("Task created successfully.")
                    return True
                else:
                    st.error("Failed to create task. Please try again.")
            else:
                st.warning("Please fill in all required fields.")
    
    return False

def show_tasks_dashboard(user_data):
    """Show the tasks dashboard with tabs for My Tasks, All Tasks, and Create Task"""
    # Show tasks overview with tabs
    tab1, tab2, tab3 = st.tabs(["My Tasks", "All Tasks", "Create Task"])
    
    with tab1:
        
        st.markdown('<div class="section-title">My Tasks</div>', unsafe_allow_html=True)
        
        # Get tasks assigned to current user
        my_tasks_df = get_tasks(assigned_to=user_data['user_id'])
        
        if my_tasks_df.empty:
            st.info("No tasks assigned to you.")
        else:
            # Add human-readable columns
            my_tasks_df['module_name'] = my_tasks_df['module_id'].apply(get_module_name)
            my_tasks_df['assigned_by_name'] = my_tasks_df['assigned_by'].apply(get_user_name)
            my_tasks_df['assigned_date_formatted'] = my_tasks_df['assigned_date'].apply(format_date)
            my_tasks_df['due_date_formatted'] = my_tasks_df['due_date'].apply(format_date)
            
            # Calculate days remaining
            my_tasks_df['days_remaining'] = my_tasks_df['due_date'].apply(calculate_days_remaining)
            
            # Enhance columns with indicators
            my_tasks_df['status_display'] = my_tasks_df['status'].apply(
                lambda x: render_status_indicator(x)
            )
            
            my_tasks_df['priority_display'] = my_tasks_df['priority'].apply(
                lambda x: render_priority_tag(x)
            )
            
            # Filter controls
            status_filter = st.selectbox(
                "Filter by Status", 
                ["All"] + sorted(my_tasks_df['status'].unique().tolist())
            )
            
            # Apply filters
            filtered_df = my_tasks_df.copy()
            
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df['status'] == status_filter]
            
            # Display the tasks in a dataframe
            st.dataframe(
                filtered_df[[
                    'task_id', 'module_name', 'description', 'priority_display', 
                    'status_display', 'due_date_formatted', 'days_remaining'
                ]],
                use_container_width=True,
                column_config={
                    "task_id": "ID",
                    "module_name": "Module",
                    "description": "Description",
                    "priority_display": st.column_config.Column(
                        "Priority",
                        width="medium"
                    ),
                    "status_display": st.column_config.Column(
                        "Status",
                        width="medium"
                    ),
                    "due_date_formatted": "Due Date",
                    "days_remaining": st.column_config.NumberColumn(
                        "Days Remaining",
                        format="%d",
                        help="Negative values indicate overdue tasks"
                    )
                },
                hide_index=True
            )
            
            # Task selection
            st.divider()
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Drop-down to select task
                task_options = filtered_df[['task_id', 'description']].values.tolist()
                task_options = [f"{t[0]} - {t[1][:50]}..." for t in task_options]
                selected_task = st.selectbox("Select a task to view details", task_options, key="my_tasks_select")
            
            with col2:
                # View button
                if selected_task and st.button("View Task", use_container_width=True, key="my_tasks_view"):
                    task_id = selected_task.split(" - ")[0]
                    # Set query parameters directly
                    st.query_params["task_id"] = task_id
                    st.query_params["view"] = "tasks"
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">All Tasks</div>', unsafe_allow_html=True)
        
        # Get all tasks
        all_tasks_df = get_tasks()
        
        if all_tasks_df.empty:
            st.info("No tasks available.")
        else:
            # Add human-readable columns
            all_tasks_df['module_name'] = all_tasks_df['module_id'].apply(get_module_name)
            all_tasks_df['assigned_to_name'] = all_tasks_df['assigned_to'].apply(get_user_name)
            all_tasks_df['assigned_by_name'] = all_tasks_df['assigned_by'].apply(get_user_name)
            all_tasks_df['due_date_formatted'] = all_tasks_df['due_date'].apply(format_date)
            
            # Calculate days remaining
            all_tasks_df['days_remaining'] = all_tasks_df['due_date'].apply(calculate_days_remaining)
            
            # Enhance columns with indicators
            all_tasks_df['status_display'] = all_tasks_df['status'].apply(
                lambda x: render_status_indicator(x)
            )
            
            all_tasks_df['priority_display'] = all_tasks_df['priority'].apply(
                lambda x: render_priority_tag(x)
            )
            
            # Filter controls
            col1, col2 = st.columns(2)
            
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status", 
                    ["All"] + sorted(all_tasks_df['status'].unique().tolist()),
                    key="all_status_filter"
                )
            
            with col2:
                priority_filter = st.selectbox(
                    "Filter by Priority", 
                    ["All"] + sorted(all_tasks_df['priority'].unique().tolist())
                )
            
            # Apply filters
            filtered_df = all_tasks_df.copy()
            
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df['status'] == status_filter]
            
            if priority_filter != "All":
                filtered_df = filtered_df[filtered_df['priority'] == priority_filter]
            
            # Display the tasks in a dataframe
            st.dataframe(
                filtered_df[[
                    'task_id', 'module_name', 'description', 'priority_display', 
                    'status_display', 'assigned_to_name', 'due_date_formatted', 'days_remaining'
                ]],
                use_container_width=True,
                column_config={
                    "task_id": "ID",
                    "module_name": "Module",
                    "description": "Description",
                    "priority_display": st.column_config.Column(
                        "Priority",
                        width="medium"
                    ),
                    "status_display": st.column_config.Column(
                        "Status",
                        width="medium"
                    ),
                    "assigned_to_name": "Assigned To",
                    "due_date_formatted": "Due Date",
                    "days_remaining": st.column_config.NumberColumn(
                        "Days Remaining",
                        format="%d",
                        help="Negative values indicate overdue tasks"
                    )
                },
                hide_index=True
            )
            
            # Task selection
            st.divider()
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Drop-down to select task
                task_options = filtered_df[['task_id', 'description']].values.tolist()
                task_options = [f"{t[0]} - {t[1][:50]}..." for t in task_options]
                selected_task = st.selectbox("Select a task to view details", task_options, key="all_tasks_select")
            
            with col2:
                # View button
                if selected_task and st.button("View Task", use_container_width=True, key="all_tasks_view"):
                    task_id = selected_task.split(" - ")[0]
                    # Set query parameters directly
                    st.query_params["task_id"] = task_id
                    st.query_params["view"] = "tasks"
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Create New Task</div>', unsafe_allow_html=True)
        # Check if user has permission to create tasks
        can_create = user_data['role'].lower() in ['manager', 'supervisor', 'inspector']
        
        if can_create:
            if create_new_task():
                # Refresh the page by setting the same view parameter
                view_param = st.query_params.get("view", ["tasks"])[0]
                st.query_params["view"] = view_param
        else:
            st.warning("You do not have permission to create tasks.")
        st.markdown('</div>', unsafe_allow_html=True)

def tasks_page():
    """Main tasks page"""
    # Get current user info
    user_data = get_current_user()
    
    # Check if a specific task is selected
    query_params = st.query_params
    selected_task_id = query_params.get("task_id", [None])[0]
    
    if selected_task_id:
        # Show details for the selected task
        load_task_details(selected_task_id)
        
        # Back button using URL navigation
        if st.button("⬅️ Back to Tasks", key="back_to_tasks_btn"):
            # Clear the task_id parameter but keep the view parameter
            st.query_params.pop("task_id", None)
            st.query_params["view"] = "tasks"
    else:
        show_tasks_dashboard(user_data)

# Run the page if this script is the main entry point
if __name__ == "__main__":
    if is_authenticated():
        tasks_page()
    else:
        st.error("Please log in to access this page.")
        st.button("Go to Login", on_click=lambda: st.switch_page("app.py")) 