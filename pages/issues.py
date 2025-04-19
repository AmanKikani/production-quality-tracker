import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to sys.path to import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import is_authenticated, get_current_user
from utils.database import get_issues, get_modules, create_issue, update_issue_status, get_module, create_task
from utils.helpers import display_header, format_date, render_status_indicator, render_priority_tag, get_user_name, get_module_name
from utils.notifications import notify_new_issue, notify_issue_resolved

def load_issue_details(issue_id):
    """Load and display details for a specific issue"""
    issues_df = get_issues()
    
    if issues_df.empty:
        st.error("No issues found in the database.")
        return
    
    issue = issues_df[issues_df['issue_id'] == issue_id]
    
    if issue.empty:
        st.error(f"Issue with ID {issue_id} not found.")
        return
    
    issue = issue.iloc[0]
    
    # Get module information
    module = get_module(issue['module_id'])
    module_name = module['module_name'] if module else issue['module_id']
    
    # Display issue header
    st.markdown(f"## Issue: {issue['issue_id']}")
    st.markdown(f"**Module:** {module_name}")
    
    # Create columns for issue details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        severity_tag = render_priority_tag(issue['severity'])
        st.markdown(f"**Severity:** {severity_tag}", unsafe_allow_html=True)
    
    with col2:
        status_indicator = render_status_indicator(issue['status'])
        st.markdown(f"**Status:** {status_indicator}", unsafe_allow_html=True)
    
    with col3:
        category = issue['category']
        st.markdown(f"**Category:** {category}")
    
    # Issue description
    st.markdown("### Description")
    st.write(issue['description'])
    
    # Issue timeline
    st.markdown("### Timeline")
    
    # Format dates
    report_date = format_date(issue['report_date'])
    resolved_date = format_date(issue['resolved_date']) if pd.notna(issue['resolved_date']) else "Not resolved yet"
    
    # Create a timeline display
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Reported on:** {report_date}")
        reporter_name = get_user_name(issue['reported_by'])
        st.markdown(f"**Reported by:** {reporter_name}")
    
    with col2:
        st.markdown(f"**Resolved on:** {resolved_date}")
        if pd.notna(issue['resolved_by']):
            resolver_name = get_user_name(issue['resolved_by'])
            st.markdown(f"**Resolved by:** {resolver_name}")
    
    # Status update section
    st.subheader("Update Status")
    
    status_options = ["Open", "In Progress", "Resolved"]
    new_status = st.selectbox("New Status", status_options, index=status_options.index(issue['status']), key="issue_status")
    
    # Update button
    if st.button("Update Status"):
        status_update_success = False
        if update_issue_status(issue_id, new_status, user_data['user_id']):
            if new_status == 'Resolved':
                # Create notification for issue resolved
                notify_issue_resolved(issue_id, issue['module_id'], user_data['user_id'])
            
            st.success(f"Issue status updated to {new_status}.")
            status_update_success = True
        else:
            st.error("Failed to update issue status.")
        
        # Add a redirect script only on successful update
        if status_update_success:
            st.markdown(
                f"""
                <script>
                    setTimeout(function() {{
                        window.location.href = "?view=issues&issue_id={issue_id}";
                    }}, 1000);
                </script>
                """,
                unsafe_allow_html=True
            )

def report_issue_form():
    """Display and handle form for reporting a new issue"""
    st.subheader("Report New Quality Issue")
    
    # Get current user info
    user_data = get_current_user()
    
    # Get all modules for selection
    modules_df = get_modules()
    
    if modules_df.empty:
        st.warning("No modules available to report issues for.")
        return
    
    with st.form("report_issue_form"):
        # Create columns for form layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Module selection
            module_options = modules_df[['module_id', 'module_name']].values.tolist()
            module_options = [f"{m[0]} - {m[1]}" for m in module_options]
            selected_module = st.selectbox("Select Module", module_options)
            
            # Category selection
            category_options = ["Material", "Assembly", "Electrical", "Plumbing", "HVAC", "Finish", "Structural", "Safety", "Other"]
            category = st.selectbox("Issue Category", category_options)
        
        with col2:
            # Severity selection
            severity_options = ["Low", "Medium", "High", "Critical"]
            severity = st.selectbox("Severity", severity_options)
            
            # Description
            description = st.text_area("Issue Description", height=100)
        
        # Submit button
        submitted = st.form_submit_button("Report Issue", type="primary", use_container_width=True)
        
        if submitted:
            if selected_module and category and severity and description:
                # Extract module_id from selection
                module_id = selected_module.split(" - ")[0]
                
                # Create new issue
                new_issue_id = create_issue(module_id, user_data['user_id'], category, severity, description)
                
                if new_issue_id:
                    # Create notification for new issue
                    notify_new_issue(new_issue_id, module_id, severity, description, user_data['user_id'])
                    
                    st.success(f"Issue reported successfully. Issue ID: {new_issue_id}")
                    
                    # Prompt for task creation
                    st.info("Would you like to create a task to address this issue?")
                    return True, new_issue_id, module_id
                else:
                    st.error("Failed to report issue. Please try again.")
            else:
                st.warning("Please fill in all fields.")
    
    return False, None, None

def create_task_for_issue(issue_id, module_id):
    """Display and handle form for creating a task for an issue"""
    st.subheader("Create Task for Issue")
    
    # Get current user info
    user_data = get_current_user()
    
    # Get all users for assignment
    users_df = pd.read_csv('data/users.csv')
    
    with st.form("create_task_form"):
        # Create columns for form layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Assigned to selection
            user_options = users_df[['user_id', 'username']].values.tolist()
            user_options = [f"{u[0]} - {u[1]}" for u in user_options]
            assigned_to = st.selectbox("Assign To", user_options)
            
            # Due date selection
            due_date = st.date_input("Due Date", datetime.now() + pd.Timedelta(days=3))
            due_date = due_date.strftime('%Y-%m-%d')
        
        with col2:
            # Priority selection
            priority_options = ["Low", "Medium", "High", "Critical"]
            priority = st.selectbox("Priority", priority_options)
            
            # Description
            description = st.text_area("Task Description", height=100)
        
        # Submit button
        submitted = st.form_submit_button("Create Task", type="primary", use_container_width=True)
        
        if submitted:
            if assigned_to and due_date and priority and description:
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
                    st.success("Task created successfully.")
                    return True
                else:
                    st.error("Failed to create task. Please try again.")
            else:
                st.warning("Please fill in all fields.")
    
    return False

def issues_page():
    """Main issues page"""
    user_data = get_current_user()
    
    # Check if a specific issue is selected
    query_params = st.query_params
    selected_issue_id = query_params.get("issue_id", [None])[0]
    
    if selected_issue_id:
        # Show details for the selected issue
        load_issue_details(selected_issue_id)
        
        # Back button using URL navigation
        if st.button("⬅️ Back to Issues", key="back_to_issues_btn"):
            # Clear the issue_id parameter but keep the view parameter
            st.query_params.pop("issue_id", None)
            st.query_params["view"] = "issues"
    else:
        # Show issues overview
        tab1, tab2 = st.tabs(["All Issues", "Report Issue"])
        
        with tab1:
            st.subheader("Quality Issues")
            
            # Get all issues
            issues_df = get_issues()
            
            if issues_df.empty:
                st.info("No quality issues reported yet.")
            else:
                # Add human-readable columns
                issues_df['module_name'] = issues_df['module_id'].apply(get_module_name)
                issues_df['reported_by_name'] = issues_df['reported_by'].apply(get_user_name)
                issues_df['report_date_formatted'] = issues_df['report_date'].apply(format_date)
                
                # Enhance the status column with indicators
                issues_df['status_display'] = issues_df['status'].apply(
                    lambda x: render_status_indicator(x)
                )
                
                # Enhance the severity column with tags
                issues_df['severity_display'] = issues_df['severity'].apply(
                    lambda x: render_priority_tag(x)
                )
                
                # Filter controls
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Filter by status
                    status_filter = st.selectbox(
                        "Filter by Status", 
                        ["All"] + sorted(issues_df['status'].unique().tolist())
                    )
                
                with col2:
                    # Filter by severity
                    severity_filter = st.selectbox(
                        "Filter by Severity", 
                        ["All"] + sorted(issues_df['severity'].unique().tolist())
                    )
                
                with col3:
                    # Filter by category
                    category_filter = st.selectbox(
                        "Filter by Category", 
                        ["All"] + sorted(issues_df['category'].unique().tolist())
                    )
                
                # Apply filters
                filtered_df = issues_df.copy()
                
                if status_filter != "All":
                    filtered_df = filtered_df[filtered_df['status'] == status_filter]
                
                if severity_filter != "All":
                    filtered_df = filtered_df[filtered_df['severity'] == severity_filter]
                
                if category_filter != "All":
                    filtered_df = filtered_df[filtered_df['category'] == category_filter]
                
                # Display the issues in a dataframe
                st.dataframe(
                    filtered_df[[
                        'issue_id', 'module_name', 'category', 'severity_display', 
                        'status_display', 'description', 'reported_by_name', 'report_date_formatted'
                    ]],
                    use_container_width=True,
                    column_config={
                        "issue_id": "ID",
                        "module_name": "Module",
                        "category": "Category",
                        "severity_display": st.column_config.Column(
                            "Severity",
                            width="medium"
                        ),
                        "status_display": st.column_config.Column(
                            "Status",
                            width="medium"
                        ),
                        "description": "Description",
                        "reported_by_name": "Reported By",
                        "report_date_formatted": "Report Date"
                    },
                    hide_index=True
                )
                
                # Issue selection
                st.divider()
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Drop-down to select issue
                    issue_options = filtered_df[['issue_id', 'description']].values.tolist()
                    issue_options = [f"{i[0]} - {i[1][:50]}..." for i in issue_options]
                    selected_issue = st.selectbox("Select an issue to view details", issue_options)
                
                with col2:
                    # View button
                    if selected_issue and st.button("View Issue", use_container_width=True):
                        issue_id = selected_issue.split(" - ")[0]
                        # Set query parameters directly
                        st.query_params["issue_id"] = issue_id
                        st.query_params["view"] = "issues"
        
        with tab2:
            # Check if user has permission to report issues
            can_report = user_data['role'].lower() in ['manager', 'supervisor', 'inspector', 'operator']
            
            if can_report:
                issue_reported, new_issue_id, module_id = report_issue_form()
                
                if issue_reported:
                    # Show task creation form
                    create_task = st.button("Yes, Create Task Now")
                    skip_task = st.button("No, Skip for Now")
                    
                    if create_task:
                        st.session_state['show_task_form'] = True
                    elif skip_task:
                        # Refresh by updating query params
                        view_param = st.query_params.get("view", ["issues"])[0]
                        st.query_params["view"] = view_param
                    
                    # Show task form if requested
                    if 'show_task_form' in st.session_state and st.session_state['show_task_form']:
                        if create_task_for_issue(new_issue_id, module_id):
                            del st.session_state['show_task_form']
                            # Refresh by updating query params
                            view_param = st.query_params.get("view", ["issues"])[0]
                            st.query_params["view"] = view_param
            else:
                st.warning("You do not have permission to report issues.")

# Run the page if this script is the main entry point
if __name__ == "__main__":
    if is_authenticated():
        issues_page()
    else:
        st.error("Please log in to access this page.")
        st.button("Go to Login", on_click=lambda: st.switch_page("app.py")) 