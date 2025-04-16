import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to sys.path to import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import is_authenticated, get_current_user
from utils.database import get_projects, get_modules, get_issues, get_tasks, get_overdue_tasks, get_project_progress, get_issue_statistics
from utils.helpers import display_header, format_date, render_status_indicator, create_progress_chart, create_issues_by_category_chart, create_issues_by_severity_chart, get_user_name

def project_completion_report():
    """Generate and display project completion report"""
    st.subheader("Project Completion Status")
    
    # Get project progress data
    projects_df = get_project_progress()
    
    if projects_df.empty:
        st.info("No project data available.")
        return
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Bar Chart", "Table View"])
    
    with tab1:
        # Progress chart
        progress_chart = create_progress_chart(projects_df)
        st.plotly_chart(progress_chart, use_container_width=True)
        
        # Add time-based analysis
        st.subheader("Timeline Adherence")
        
        # Calculate days passed and total duration for each project
        projects_df['start_date'] = pd.to_datetime(projects_df['start_date'])
        projects_df['end_date'] = pd.to_datetime(projects_df['end_date'])
        projects_df['days_passed'] = (datetime.now().date() - projects_df['start_date'].dt.date).dt.days
        projects_df['total_days'] = (projects_df['end_date'].dt.date - projects_df['start_date'].dt.date).dt.days
        projects_df['time_progress'] = (projects_df['days_passed'] / projects_df['total_days'] * 100).round(1)
        
        # Calculate if project is ahead or behind schedule
        projects_df['schedule_diff'] = (projects_df['progress'] - projects_df['time_progress']).round(1)
        projects_df['status'] = np.where(
            projects_df['schedule_diff'] > 5, 'Ahead of Schedule',
            np.where(projects_df['schedule_diff'] < -5, 'Behind Schedule', 'On Schedule')
        )
        
        # Create a colored bar chart
        fig = px.bar(
            projects_df,
            y='project_name',
            x='schedule_diff',
            color='status',
            title="Project Schedule Performance",
            labels={'schedule_diff': 'Ahead/Behind Schedule (%)', 'project_name': 'Project'},
            color_discrete_map={
                'Ahead of Schedule': '#28a745',
                'On Schedule': '#ffc107',
                'Behind Schedule': '#dc3545'
            },
            text='schedule_diff',
            orientation='h'
        )
        
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Format dates for display
        display_df = projects_df.copy()
        display_df['start_date'] = display_df['start_date'].dt.strftime('%Y-%m-%d')
        display_df['end_date'] = display_df['end_date'].dt.strftime('%Y-%m-%d')
        
        # Calculate remaining days
        display_df['days_remaining'] = (display_df['end_date'].apply(pd.to_datetime).dt.date - datetime.now().date()).dt.days
        
        # Create a dataframe with relevant columns
        report_df = display_df[[
            'project_name', 'client_name', 'status', 'progress', 'completed_modules', 
            'total_modules', 'time_progress', 'schedule_diff', 'days_remaining'
        ]]
        
        # Display dataframe
        st.dataframe(
            report_df,
            use_container_width=True,
            column_config={
                "project_name": "Project",
                "client_name": "Client",
                "status": "Status",
                "progress": st.column_config.ProgressColumn(
                    "Completion Progress",
                    format="%{value}%",
                    min_value=0,
                    max_value=100
                ),
                "completed_modules": "Completed Modules",
                "total_modules": "Total Modules",
                "time_progress": st.column_config.ProgressColumn(
                    "Timeline Progress",
                    format="%{value}%",
                    min_value=0,
                    max_value=100
                ),
                "schedule_diff": st.column_config.NumberColumn(
                    "Schedule Performance",
                    format="%.1f%%",
                    help="Positive values indicate ahead of schedule, negative values indicate behind schedule"
                ),
                "days_remaining": "Days Remaining"
            },
            hide_index=True
        )

def quality_issues_report():
    """Generate and display quality issues report"""
    st.subheader("Quality Issues Analysis")
    
    # Get issues data
    issues_df = get_issues()
    
    if issues_df.empty:
        st.info("No quality issues data available.")
        return
    
    # Get category and severity statistics
    category_counts, severity_counts = get_issue_statistics()
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["By Category & Severity", "By Status", "Trends"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Issues by category chart
            category_chart = create_issues_by_category_chart(category_counts)
            st.plotly_chart(category_chart, use_container_width=True)
        
        with col2:
            # Issues by severity chart
            severity_chart = create_issues_by_severity_chart(severity_counts)
            st.plotly_chart(severity_chart, use_container_width=True)
    
    with tab2:
        # Issues by status
        status_counts = issues_df['status'].value_counts().to_dict()
        
        # Create pie chart for status
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="Issues by Status",
            color=list(status_counts.keys()),
            color_discrete_map={
                'Open': '#dc3545',
                'In Progress': '#ffc107',
                'Resolved': '#28a745'
            }
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
        # Calculate resolution rate
        total_issues = len(issues_df)
        resolved_issues = len(issues_df[issues_df['status'] == 'Resolved'])
        resolution_rate = (resolved_issues / total_issues * 100) if total_issues > 0 else 0
        
        # Calculate average resolution time for resolved issues
        if resolved_issues > 0:
            resolved_df = issues_df[issues_df['status'] == 'Resolved'].copy()
            resolved_df['report_date'] = pd.to_datetime(resolved_df['report_date'])
            resolved_df['resolved_date'] = pd.to_datetime(resolved_df['resolved_date'])
            resolved_df['resolution_days'] = (resolved_df['resolved_date'] - resolved_df['report_date']).dt.days
            avg_resolution_time = resolved_df['resolution_days'].mean()
        else:
            avg_resolution_time = 0
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Issues", total_issues)
        
        with col2:
            st.metric("Resolution Rate", f"{resolution_rate:.1f}%")
        
        with col3:
            st.metric("Avg. Resolution Time", f"{avg_resolution_time:.1f} days")
    
    with tab3:
        # Issues over time
        issues_df['report_date'] = pd.to_datetime(issues_df['report_date'])
        issues_by_date = issues_df.groupby(issues_df['report_date'].dt.to_period('M')).size().reset_index(name='count')
        issues_by_date['month'] = issues_by_date['report_date'].dt.strftime('%Y-%m')
        
        # If there's only one month, add some empty months for better visualization
        if len(issues_by_date) <= 1:
            last_date = issues_df['report_date'].max()
            if pd.notna(last_date):
                for i in range(1, 4):
                    new_date = last_date + pd.DateOffset(months=i)
                    issues_by_date = pd.concat([
                        issues_by_date,
                        pd.DataFrame({
                            'report_date': [pd.Period(new_date, freq='M')],
                            'count': [0],
                            'month': [new_date.strftime('%Y-%m')]
                        })
                    ])
        
        # Create line chart for issues over time
        fig = px.line(
            issues_by_date,
            x='month',
            y='count',
            title="Issues Reported Over Time",
            markers=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Issues by severity over time (stacked area)
        severity_by_date = issues_df.groupby([issues_df['report_date'].dt.to_period('M'), 'severity']).size().reset_index(name='count')
        severity_by_date['month'] = severity_by_date['report_date'].dt.strftime('%Y-%m')
        
        # Create stacked area chart
        fig = px.area(
            severity_by_date,
            x='month',
            y='count',
            color='severity',
            title="Issues by Severity Over Time",
            color_discrete_map={
                'Low': '#28a745',
                'Medium': '#ffc107',
                'High': '#fd7e14',
                'Critical': '#dc3545'
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)

def task_performance_report():
    """Generate and display task performance report"""
    st.subheader("Task Performance Analysis")
    
    # Get tasks data
    tasks_df = get_tasks()
    
    if tasks_df.empty:
        st.info("No tasks data available.")
        return
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Status & Priority", "User Performance"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Tasks by status
            status_counts = tasks_df['status'].value_counts().to_dict()
            
            # Create pie chart for status
            fig = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="Tasks by Status",
                color=list(status_counts.keys()),
                color_discrete_map={
                    'Assigned': '#ffc107',
                    'In Progress': '#17a2b8',
                    'On Hold': '#6c757d',
                    'Completed': '#28a745'
                }
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Tasks by priority
            priority_counts = tasks_df['priority'].value_counts().to_dict()
            
            # Ensure consistent order
            priority_order = ['Low', 'Medium', 'High', 'Critical']
            ordered_counts = {priority: priority_counts.get(priority, 0) for priority in priority_order}
            
            # Create bar chart for priority
            fig = px.bar(
                x=list(ordered_counts.keys()),
                y=list(ordered_counts.values()),
                title="Tasks by Priority",
                color=list(ordered_counts.keys()),
                color_discrete_map={
                    'Low': '#28a745',
                    'Medium': '#ffc107',
                    'High': '#fd7e14',
                    'Critical': '#dc3545'
                }
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Overdue tasks analysis
        st.subheader("Overdue Tasks")
        
        # Convert due_date to datetime for comparison
        tasks_df['due_date'] = pd.to_datetime(tasks_df['due_date'])
        
        # Calculate days overdue for incomplete tasks
        incomplete_tasks = tasks_df[tasks_df['status'] != 'Completed'].copy()
        incomplete_tasks['days_overdue'] = (datetime.now().date() - incomplete_tasks['due_date'].dt.date).dt.days
        overdue_tasks = incomplete_tasks[incomplete_tasks['days_overdue'] > 0]
        
        if overdue_tasks.empty:
            st.success("No overdue tasks!")
        else:
            # Add human-readable columns
            overdue_tasks['module_name'] = overdue_tasks['module_id'].apply(get_module_name)
            overdue_tasks['assigned_to_name'] = overdue_tasks['assigned_to'].apply(get_user_name)
            
            # Display overdue tasks
            st.dataframe(
                overdue_tasks[[
                    'task_id', 'module_name', 'description', 'priority', 
                    'status', 'assigned_to_name', 'days_overdue'
                ]],
                use_container_width=True,
                column_config={
                    "task_id": "ID",
                    "module_name": "Module",
                    "description": "Description",
                    "priority": "Priority",
                    "status": "Status",
                    "assigned_to_name": "Assigned To",
                    "days_overdue": st.column_config.NumberColumn(
                        "Days Overdue",
                        format="%d",
                        help="Number of days past the due date"
                    )
                },
                hide_index=True
            )
    
    with tab2:
        # User task performance
        
        # Get completed tasks with completion data
        completed_tasks = tasks_df[tasks_df['status'] == 'Completed'].copy()
        
        if completed_tasks.empty:
            st.info("No completed tasks available for analysis.")
        else:
            # Convert date columns to datetime
            completed_tasks['assigned_date'] = pd.to_datetime(completed_tasks['assigned_date'])
            completed_tasks['due_date'] = pd.to_datetime(completed_tasks['due_date'])
            completed_tasks['completion_date'] = pd.to_datetime(completed_tasks['completion_date'])
            
            # Calculate completion time and on-time status
            completed_tasks['completion_days'] = (completed_tasks['completion_date'] - completed_tasks['assigned_date']).dt.days
            completed_tasks['on_time'] = completed_tasks['completion_date'] <= completed_tasks['due_date']
            
            # Group by assigned user
            user_performance = completed_tasks.groupby('assigned_to').agg(
                total_tasks=('task_id', 'count'),
                avg_completion_days=('completion_days', 'mean'),
                on_time_rate=('on_time', 'mean')
            ).reset_index()
            
            # Add user names
            user_performance['user_name'] = user_performance['assigned_to'].apply(get_user_name)
            
            # Create bar chart for completion metrics
            fig = go.Figure()
            
            # Add bar for average completion days
            fig.add_trace(go.Bar(
                x=user_performance['user_name'],
                y=user_performance['avg_completion_days'],
                name='Avg. Completion Days',
                marker_color='#17a2b8'
            ))
            
            # Add bar for on-time rate
            fig.add_trace(go.Bar(
                x=user_performance['user_name'],
                y=user_performance['on_time_rate'] * 100,  # Convert to percentage
                name='On-Time Rate (%)',
                marker_color='#28a745',
                yaxis='y2'
            ))
            
            # Update layout with dual y-axis
            fig.update_layout(
                title="User Task Performance",
                yaxis=dict(
                    title="Average Completion Days",
                    side="left"
                ),
                yaxis2=dict(
                    title="On-Time Rate (%)",
                    side="right",
                    overlaying="y",
                    range=[0, 100]
                ),
                legend=dict(
                    x=0.5,
                    y=1.15,
                    xanchor="center",
                    yanchor="top",
                    orientation="h"
                ),
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display user performance table
            user_performance['on_time_rate'] = (user_performance['on_time_rate'] * 100).round(1)
            user_performance['avg_completion_days'] = user_performance['avg_completion_days'].round(1)
            
            st.dataframe(
                user_performance[['user_name', 'total_tasks', 'avg_completion_days', 'on_time_rate']],
                use_container_width=True,
                column_config={
                    "user_name": "User",
                    "total_tasks": "Total Completed Tasks",
                    "avg_completion_days": st.column_config.NumberColumn(
                        "Avg. Completion Days",
                        format="%.1f days"
                    ),
                    "on_time_rate": st.column_config.ProgressColumn(
                        "On-Time Rate",
                        format="%{value}%",
                        min_value=0,
                        max_value=100
                    )
                },
                hide_index=True
            )

def show_reports_dashboard():
    """Show the reports dashboard with tabs for different report types"""
    user_data = get_current_user()
    
    # Check permissions
    can_view_analytics = user_data['role'].lower() in ['manager', 'supervisor', 'inspector', 'engineer']
    
    if not can_view_analytics:
        st.warning("You do not have permission to view analytics and reports.")
        return
    
    # Create tabs for different report types
    tab1, tab2, tab3 = st.tabs(["Project Reports", "Quality Reports", "Task Reports"])
    
    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        project_completion_report()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        quality_issues_report()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        task_performance_report()
        st.markdown('</div>', unsafe_allow_html=True)

def reports_page():
    """Main reports page"""
    # Show reports dashboard
    show_reports_dashboard()

# Run the page if this script is the main entry point
if __name__ == "__main__":
    if is_authenticated():
        reports_page()
    else:
        st.error("Please log in to access this page.")
        st.button("Go to Login", on_click=lambda: st.switch_page("app.py")) 