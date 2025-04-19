import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import os

# Add parent directory to sys.path to import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import is_authenticated, get_current_user
from utils.database import get_projects, get_project, get_modules, update_module_status, update_project_progress
from utils.helpers import display_header, format_date, render_status_indicator, create_timeline_chart
from utils.notifications import notify_project_complete

def load_project_details(project_id):
    """Load and display details for a specific project"""
    project = get_project(project_id)
    
    if not project:
        st.error(f"Project with ID {project_id} not found.")
        return
    
    # Add a Back button at the top
    if st.button("⬅️ Back to Projects", key="back_to_projects_btn"):
        # Clear the project_id parameter but keep the view parameter
        st.query_params.pop("project_id", None)
        st.query_params["view"] = "projects"
    
    # Display project header
    st.markdown(f"## {project['project_name']}")
    st.markdown(f"**Client:** {project['client_name']}")
    
    # Create columns for project details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Status", project['status'])
    
    with col2:
        progress = round((project['completed_modules'] / project['total_modules']) * 100, 1)
        st.metric("Progress", f"{progress}%")
    
    with col3:
        st.metric("Modules", f"{project['completed_modules']}/{project['total_modules']}")
    
    # Project timeline
    st.markdown("### Timeline")
    start_date = format_date(project['start_date'])
    end_date = format_date(project['end_date'])
    st.markdown(f"**Start Date:** {start_date} &nbsp;&nbsp; **End Date:** {end_date}")
    
    # Progress bar
    days_passed = (datetime.now().date() - pd.to_datetime(project['start_date']).date()).days
    total_days = (pd.to_datetime(project['end_date']).date() - pd.to_datetime(project['start_date']).date()).days
    time_progress = min(100, round((days_passed / total_days) * 100, 1))
    
    st.progress(time_progress / 100)
    st.caption(f"Timeline Progress: {time_progress}% of time elapsed")
    
    # Show modules for this project
    show_project_modules(project_id)

def show_project_modules(project_id):
    """Display modules for a specific project"""
    st.markdown("### Modules")
    
    # Get modules for this project
    modules_df = get_modules(project_id)
    
    if modules_df.empty:
        st.info("No modules found for this project.")
        return
    
    # Add user permissions check
    user_data = get_current_user()
    can_update = user_data['role'].lower() in ['manager', 'supervisor', 'operator']
    
    # Create tabs for different module views
    tab1, tab2 = st.tabs(["List View", "Timeline View"])
    
    with tab1:
        # Format dates for display
        modules_df['start_date'] = modules_df['start_date'].apply(format_date)
        modules_df['target_completion'] = modules_df['target_completion'].apply(format_date)
        modules_df['actual_completion'] = modules_df['actual_completion'].apply(format_date)
        
        # Enhance the status column with indicators
        modules_df['status_display'] = modules_df['status'].apply(
            lambda x: render_status_indicator(x)
        )
        
        # Display the modules in a dataframe
        st.dataframe(
            modules_df[['module_id', 'module_name', 'type', 'status_display', 'start_date', 'target_completion', 'actual_completion']],
            use_container_width=True,
            column_config={
                "module_id": "ID",
                "module_name": "Module",
                "type": "Type",
                "status_display": st.column_config.Column(
                    "Status",
                    width="medium",
                ),
                "start_date": "Start Date",
                "target_completion": "Target Completion",
                "actual_completion": "Actual Completion"
            },
            hide_index=True
        )
        
        # Module status update section (if user has permission)
        if can_update:
            st.divider()
            st.subheader("Update Module Status")
            
            # Create columns for input fields
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Drop-down to select module
                module_options = modules_df[['module_id', 'module_name']].values.tolist()
                module_options = [f"{m[0]} - {m[1]}" for m in module_options]
                selected_module = st.selectbox("Select Module", module_options)
                
                if selected_module:
                    module_id = selected_module.split(" - ")[0]
            
            with col2:
                # Status selection
                status_options = ["In Progress", "Completed", "On Hold", "Delayed"]
                new_status = st.selectbox("New Status", status_options)
            
            with col3:
                # Completion date (only shown if status is Completed)
                completion_date = None
                if new_status == "Completed":
                    completion_date = st.date_input("Completion Date", datetime.now())
                    completion_date = completion_date.strftime('%Y-%m-%d')
            
            # Update button
            if st.button("Update Module Status"):
                if selected_module and new_status:
                    # Update module status
                    if update_module_status(module_id, new_status, completion_date):
                        # If module is completed, update project progress
                        if new_status == "Completed":
                            # Recalculate completed modules count
                            updated_modules = get_modules(project_id)
                            completed_modules = len(updated_modules[updated_modules['status'] == 'Completed'])
                            
                            # Update project progress
                            if update_project_progress(project_id, completed_modules):
                                st.success(f"Module {module_id} status updated to {new_status} and project progress updated.")
                                
                                # Check if project is now complete
                                project = get_project(project_id)
                                if project['status'] == 'Completed':
                                    # Notify project completion
                                    notify_project_complete(project_id, project['project_name'])
                            else:
                                st.warning(f"Module {module_id} status updated but failed to update project progress.")
                        else:
                            st.success(f"Module {module_id} status updated to {new_status}.")
                    else:
                        st.error(f"Failed to update module {module_id} status.")
    
    with tab2:
        # Prepare data for timeline chart
        timeline_df = modules_df.copy()
        
        # Create timeline chart
        if not timeline_df.empty:
            fig = create_timeline_chart(timeline_df, 'start_date', "Module Timeline")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timeline data available.")

def projects_page():
    """Main projects page"""
    # Get all projects
    projects_df = get_projects()
    
    if projects_df.empty:
        st.info("No projects available.")
        return
    
    # Check if a specific project is selected
    query_params = st.query_params
    selected_project_id = query_params.get("project_id", [None])[0]
    
    if selected_project_id:
        # Show details for the selected project
        try:
            project_id = int(selected_project_id)
            load_project_details(project_id)
        except ValueError:
            st.error("Invalid project ID.")
    else:
        # Show projects overview
        st.subheader("Projects Overview")
        
        # Calculate progress percentage
        projects_df['progress'] = (projects_df['completed_modules'] / projects_df['total_modules'] * 100).round(1)
        
        # Format dates
        projects_df['start_date'] = projects_df['start_date'].apply(format_date)
        projects_df['end_date'] = projects_df['end_date'].apply(format_date)
        
        # Add status indicators
        projects_df['status_display'] = projects_df['status'].apply(
            lambda x: render_status_indicator(x)
        )
        
        # Display projects table
        st.dataframe(
            projects_df[['project_id', 'project_name', 'client_name', 'status_display', 'progress', 'start_date', 'end_date']],
            use_container_width=True,
            column_config={
                "project_id": "ID",
                "project_name": "Project",
                "client_name": "Client",
                "status_display": st.column_config.Column(
                    "Status",
                    width="medium"
                ),
                "progress": st.column_config.ProgressColumn(
                    "Progress",
                    format="%{value}%",
                    min_value=0,
                    max_value=100
                ),
                "start_date": "Start Date",
                "end_date": "End Date"
            },
            hide_index=True
        )
        
        # Project selection
        st.divider()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Drop-down to select project
            project_options = projects_df[['project_id', 'project_name']].values.tolist()
            project_options = [f"{p[0]} - {p[1]}" for p in project_options]
            selected_project = st.selectbox("Select a project to view details", project_options)
        
        with col2:
            # View button
            if selected_project and st.button("View Project", use_container_width=True):
                project_id = selected_project.split(" - ")[0]
                # Set query parameters directly
                st.query_params["project_id"] = project_id
                st.query_params["view"] = "projects"

# Run the page if this script is the main entry point
if __name__ == "__main__":
    if is_authenticated():
        projects_page()
    else:
        st.error("Please log in to access this page.")
        st.button("Go to Login", on_click=lambda: st.switch_page("app.py")) 