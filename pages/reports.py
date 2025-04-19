import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import io
import base64
from pathlib import Path

# Add parent directory to sys.path to import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import is_authenticated, get_current_user
from utils.database import get_projects, get_modules, get_issues, get_tasks, get_overdue_tasks, get_project_progress, get_issue_statistics, get_module
from utils.helpers import display_header, format_date, render_status_indicator, create_progress_chart, create_issues_by_category_chart, create_issues_by_severity_chart, get_user_name, get_module_name

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
        
        # Fix: Calculate days_passed using apply to avoid the .dt accessor error
        projects_df['days_passed'] = projects_df['start_date'].apply(
            lambda x: (datetime.now().date() - x.date()).days if pd.notna(x) else 0
        )
        
        projects_df['total_days'] = projects_df.apply(
            lambda row: (row['end_date'].date() - row['start_date'].date()).days if pd.notna(row['start_date']) and pd.notna(row['end_date']) else 1, 
            axis=1
        )
        
        # Avoid division by zero
        projects_df['time_progress'] = projects_df.apply(
            lambda row: (row['days_passed'] / row['total_days'] * 100) if row['total_days'] > 0 else 0,
            axis=1
        ).round(1)
        
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
        
        # Calculate remaining days first while we still have datetime objects
        display_df['days_remaining'] = (display_df['end_date'] - pd.Timestamp.now()).dt.days
        
        # Then format dates for display
        display_df['start_date'] = display_df['start_date'].dt.strftime('%Y-%m-%d')
        display_df['end_date'] = display_df['end_date'].dt.strftime('%Y-%m-%d')
        
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
        
        # Fix: Calculate days_overdue without using .dt accessor on the result
        incomplete_tasks['days_overdue'] = incomplete_tasks['due_date'].apply(
            lambda x: (datetime.now().date() - x.date()).days if pd.notna(x) else 0
        )
        
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

def advanced_reporting():
    """
    Advanced Reporting feature inspired by Offsight's reporting capabilities.
    This allows users to create customized reports, track production progress,
    and share with stakeholders.
    """
    st.subheader("Advanced Reporting")
    
    # Get project and module data
    projects_df = get_project_progress()
    
    if projects_df.empty:
        st.info("No project data available for advanced reporting.")
        return
        
    # Create tabs for different report types
    tab1, tab2, tab3, tab4 = st.tabs([
        "Production Status", 
        "Delivery Planning", 
        "Quality Verification", 
        "Custom Reports"
    ])
    
    with tab1:
        st.markdown("### Production Status Report")
        st.markdown(
            """
            Track real-time production status across all components. This report provides
            comprehensive visibility into current production status, helps identify bottlenecks,
            and allows for efficient resource allocation.
            """
        )
        
        # Select project for detailed status report
        selected_project = st.selectbox(
            "Select Project", 
            options=projects_df['project_name'].tolist(),
            key="prod_status_project"
        )
        
        project_data = projects_df[projects_df['project_name'] == selected_project].iloc[0]
        project_id = project_data['project_id']
        
        # Get modules for selected project
        modules_df = get_modules(project_id)
        
        if not modules_df.empty:
            # Add completion status indicators
            modules_df['status_display'] = modules_df['status'].apply(render_status_indicator)
            
            # Check if creation_date exists, if not add it with default values
            if 'creation_date' not in modules_df.columns:
                # Add creation_date with a default value based on project start date
                project_start = pd.to_datetime(project_data['start_date'])
                modules_df['creation_date'] = project_start
            else:
                # Convert existing creation_date to datetime
                modules_df['creation_date'] = pd.to_datetime(modules_df['creation_date'])
                
            # Calculate days in production
            modules_df['days_in_production'] = (datetime.now() - modules_df['creation_date']).dt.days
            
            # Calculate percent complete based on stages
            if 'current_stage_sequence' in modules_df.columns and 'total_stages' in modules_df.columns:
                modules_df['percent_complete'] = (modules_df['current_stage_sequence'] / modules_df['total_stages'] * 100).round(1)
            else:
                # If stage data isn't available, estimate from status
                status_map = {'Not Started': 0, 'In Progress': 50, 'Quality Check': 80, 'Completed': 100}
                modules_df['percent_complete'] = modules_df['status'].map(status_map)
            
            # Create summary stats
            total_modules = len(modules_df)
            completed_modules = len(modules_df[modules_df['status'] == 'Completed'])
            in_progress_modules = len(modules_df[modules_df['status'] == 'In Progress'])
            not_started_modules = len(modules_df[modules_df['status'] == 'Not Started'])
            
            # Display summary metrics in columns
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Components", total_modules)
            with col2:
                st.metric("Completed", f"{completed_modules} ({completed_modules/total_modules*100:.1f}%)" if total_modules > 0 else "0 (0%)")
            with col3:
                st.metric("In Progress", f"{in_progress_modules} ({in_progress_modules/total_modules*100:.1f}%)" if total_modules > 0 else "0 (0%)")
            with col4:
                st.metric("Not Started", f"{not_started_modules} ({not_started_modules/total_modules*100:.1f}%)" if total_modules > 0 else "0 (0%)")
            
            # Create a progress chart by module
            modules_chart = px.bar(
                modules_df,
                y='module_name',
                x='percent_complete',
                title=f"Module Completion Progress - {selected_project}",
                labels={'percent_complete': 'Completion Progress (%)', 'module_name': 'Module'},
                text='percent_complete',
                orientation='h',
                color='percent_complete',
                color_continuous_scale=["#dc3545", "#ffc107", "#28a745"]
            )
            
            modules_chart.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            modules_chart.update_layout(height=400)
            st.plotly_chart(modules_chart, use_container_width=True)
            
            # Display detailed table
            st.markdown("#### Component Details")
            
            # Format data for display
            display_df = modules_df.copy()
            display_df['creation_date'] = display_df['creation_date'].dt.strftime('%Y-%m-%d')
            
            # Check which columns exist in the dataframe to avoid KeyError
            available_columns = [col for col in ['module_name', 'description', 'status', 'percent_complete', 
                     'days_in_production', 'creation_date'] if col in display_df.columns]
                     
            # Add description column if not present
            if 'description' not in display_df.columns:
                display_df['description'] = 'No description available'
            
            st.dataframe(
                display_df[[
                    'module_name', 'description', 'status', 'percent_complete', 
                    'days_in_production', 'creation_date'
                ]],
                use_container_width=True,
                column_config={
                    "module_name": "Component",
                    "description": "Description",
                    "status": "Status",
                    "percent_complete": st.column_config.ProgressColumn(
                        "Completion",
                        format="%{value}%",
                        min_value=0,
                        max_value=100
                    ),
                    "days_in_production": "Days in Production",
                    "creation_date": "Start Date"
                },
                hide_index=True
            )
            
            # Export functionality
            st.download_button(
                "Export Production Status Report",
                data=convert_df_to_excel(display_df),
                file_name=f"production_status_{selected_project}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=convert_df_to_excel(display_df) is None,
                help="Download the data as an Excel file"
            )
        else:
            st.info("No modules found for this project.")
    
    with tab2:
        st.markdown("### Delivery Planning Report")
        st.markdown(
            """
            Coordinate jobsite delivery and installation by tracking expected completion dates
            and shipping status. This report helps teams plan logistics and ensure on-time delivery.
            """
        )
        
        # Select project for delivery planning
        selected_project = st.selectbox(
            "Select Project", 
            options=projects_df['project_name'].tolist(),
            key="delivery_project"
        )
        
        project_data = projects_df[projects_df['project_name'] == selected_project].iloc[0]
        project_id = project_data['project_id']
        
        # Get modules for selected project
        modules_df = get_modules(project_id)
        
        if not modules_df.empty:
            # For demo purposes, generate shipping and delivery dates
            np.random.seed(42)  # For consistent demo data
            
            # Check if creation_date exists, if not add it with default values
            if 'creation_date' not in modules_df.columns:
                # Add creation_date with a default value based on project start date
                project_start = pd.to_datetime(project_data['start_date'])
                modules_df['creation_date'] = project_start
            else:
                # Convert existing creation_date to datetime
                modules_df['creation_date'] = pd.to_datetime(modules_df['creation_date'])
                
            modules_df['estimated_completion'] = modules_df.apply(
                lambda row: row['creation_date'] + timedelta(days=np.random.randint(14, 45)) 
                if row['status'] != 'Completed' else row['creation_date'] + timedelta(days=10),
                axis=1
            )
            
            modules_df['shipping_status'] = modules_df.apply(
                lambda row: 'Shipped' if row['status'] == 'Completed' 
                else ('Ready to Ship' if np.random.random() > 0.7 and row['status'] != 'Not Started' 
                else 'In Production'),
                axis=1
            )
            
            modules_df['shipping_date'] = modules_df.apply(
                lambda row: row['estimated_completion'] + timedelta(days=2) 
                if row['shipping_status'] in ['Shipped', 'Ready to Ship'] 
                else None,
                axis=1
            )
            
            # Calculate days until shipping
            modules_df['days_until_shipping'] = modules_df.apply(
                lambda row: (row['shipping_date'] - datetime.now()).days 
                if row['shipping_status'] == 'Ready to Ship' and pd.notna(row['shipping_date'])
                else (0 if row['shipping_status'] == 'Shipped' else np.nan),
                axis=1
            )
            
            # Group by shipping status
            shipping_stats = modules_df['shipping_status'].value_counts().reset_index()
            shipping_stats.columns = ['status', 'count']
            
            # Create shipping status chart
            fig = px.pie(
                shipping_stats, 
                values='count', 
                names='status',
                title="Component Shipping Status",
                color='status',
                color_discrete_map={
                    'Shipped': '#28a745',
                    'Ready to Ship': '#ffc107',
                    'In Production': '#17a2b8'
                }
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
            # Display components ready for shipping
            if len(modules_df[modules_df['shipping_status'] == 'Ready to Ship']) > 0:
                st.markdown("#### Components Ready for Shipment")
                ready_df = modules_df[modules_df['shipping_status'] == 'Ready to Ship'].copy()
                ready_df['estimated_completion'] = ready_df['estimated_completion'].dt.strftime('%Y-%m-%d')
                ready_df['shipping_date'] = ready_df['shipping_date'].dt.strftime('%Y-%m-%d')
                
                # Add description column if not present
                if 'description' not in ready_df.columns:
                    ready_df['description'] = 'No description available'
                
                st.dataframe(
                    ready_df[['module_name', 'description', 'estimated_completion', 'shipping_date', 'days_until_shipping']],
                    use_container_width=True,
                    column_config={
                        "module_name": "Component",
                        "description": "Description",
                        "estimated_completion": "Completion Date",
                        "shipping_date": "Scheduled Shipping",
                        "days_until_shipping": "Days Until Shipping"
                    },
                    hide_index=True
                )
            
            # Display shipping schedule
            st.markdown("#### Delivery Schedule")
            
            # Format for display
            display_df = modules_df.copy()
            display_df['creation_date'] = display_df['creation_date'].dt.strftime('%Y-%m-%d')
            display_df['estimated_completion'] = display_df['estimated_completion'].dt.strftime('%Y-%m-%d')
            display_df['shipping_date'] = display_df['shipping_date'].dt.strftime('%Y-%m-%d')
            
            # Sort by shipping date
            display_df = display_df.sort_values(by='shipping_date')
            
            st.dataframe(
                display_df[[
                    'module_name', 'shipping_status', 'estimated_completion', 
                    'shipping_date', 'days_until_shipping'
                ]],
                use_container_width=True,
                column_config={
                    "module_name": "Component",
                    "shipping_status": "Status",
                    "estimated_completion": "Completion Date",
                    "shipping_date": "Shipping Date",
                    "days_until_shipping": "Days Until Shipping"
                },
                hide_index=True
            )
            
            # Export functionality
            st.download_button(
                "Export Delivery Schedule",
                data=convert_df_to_excel(display_df),
                file_name=f"delivery_schedule_{selected_project}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=convert_df_to_excel(display_df) is None,
                help="Download the data as an Excel file"
            )
        else:
            st.info("No modules found for this project.")

    with tab3:
        st.markdown("### Quality Verification Report")
        st.markdown(
            """
            Ensure all prefabrication meets specifications before shipment. Track inspection results,
            quality checks, and compliance documentation to maintain high quality standards.
            """
        )
        
        # Select project for quality verification
        selected_project = st.selectbox(
            "Select Project", 
            options=projects_df['project_name'].tolist(),
            key="quality_project"
        )
        
        project_data = projects_df[projects_df['project_name'] == selected_project].iloc[0]
        project_id = project_data['project_id']
        
        # Get modules and quality issues for selected project
        modules_df = get_modules(project_id)
        
        # Get all issues and then filter them for the modules in this project
        all_issues_df = get_issues()
        
        # If we have modules and issues, filter issues for this project's modules
        if not modules_df.empty and not all_issues_df.empty:
            module_ids = modules_df['module_id'].tolist()
            issues_df = all_issues_df[all_issues_df['module_id'].isin(module_ids)]
        else:
            issues_df = pd.DataFrame()  # Empty DataFrame if no modules or issues
        
        if not modules_df.empty:
            # Create quality inspection checklist status (for demo purposes)
            np.random.seed(43)  # For consistent demo data
            
            modules_df['inspection_status'] = modules_df['status'].apply(
                lambda x: 'Passed' if x == 'Completed' 
                else ('Failed' if np.random.random() < 0.15 and x != 'Not Started' 
                else ('In Progress' if x == 'In Progress' else 'Not Started'))
            )
            
            # Count issues by module
            if not issues_df.empty:
                issue_counts = issues_df.groupby('module_id').size().reset_index(name='issue_count')
                modules_df = pd.merge(modules_df, issue_counts, left_on='module_id', right_on='module_id', how='left')
                modules_df['issue_count'] = modules_df['issue_count'].fillna(0).astype(int)
            else:
                modules_df['issue_count'] = 0
            
            # Generate quality metrics
            total_inspections = len(modules_df[modules_df['inspection_status'] != 'Not Started'])
            passed_inspections = len(modules_df[modules_df['inspection_status'] == 'Passed'])
            failed_inspections = len(modules_df[modules_df['inspection_status'] == 'Failed'])
            
            # Display quality metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Components", len(modules_df))
            with col2:
                st.metric("Inspected", total_inspections)
            with col3:
                st.metric("Passed", passed_inspections)
            with col4:
                st.metric("Failed", failed_inspections)
            
            if total_inspections > 0:
                pass_rate = (passed_inspections / total_inspections) * 100
                st.markdown(f"#### Quality Pass Rate: {pass_rate:.1f}%")
                
                # Create pass/fail chart
                status_counts = modules_df['inspection_status'].value_counts().reset_index()
                status_counts.columns = ['status', 'count']
                
                fig = px.pie(
                    status_counts,
                    values='count',
                    names='status',
                    title="Inspection Status",
                    color='status',
                    color_discrete_map={
                        'Passed': '#28a745',
                        'Failed': '#dc3545',
                        'In Progress': '#ffc107',
                        'Not Started': '#6c757d'
                    }
                )
                
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            # Display detailed quality report
            st.markdown("#### Component Quality Status")
            
            # Format for display
            display_df = modules_df.copy()
            if 'creation_date' in display_df.columns:
                display_df['creation_date'] = pd.to_datetime(display_df['creation_date']).dt.strftime('%Y-%m-%d')
            
            st.dataframe(
                display_df[[
                    'module_name', 'status', 'inspection_status', 'issue_count'
                ]],
                use_container_width=True,
                column_config={
                    "module_name": "Component",
                    "status": "Production Status",
                    "inspection_status": "Inspection Status",
                    "issue_count": "Issues Found"
                },
                hide_index=True
            )
            
            # Export functionality
            st.download_button(
                "Export Quality Verification Report",
                data=convert_df_to_excel(display_df),
                file_name=f"quality_report_{selected_project}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=convert_df_to_excel(display_df) is None,
                help="Download the data as an Excel file"
            )
        else:
            st.info("No modules found for this project.")
    
    with tab4:
        st.markdown("### Custom Report Builder")
        st.markdown(
            """
            Build customized reports to meet specific stakeholder needs. Select data points,
            choose visualization types, and generate shareable reports for project teams.
            """
        )
        
        # Select project
        selected_project = st.selectbox(
            "Select Project", 
            options=projects_df['project_name'].tolist(),
            key="custom_project"
        )
        
        project_data = projects_df[projects_df['project_name'] == selected_project].iloc[0]
        project_id = project_data['project_id']
        
        # Report configuration
        st.markdown("#### Configure Report")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_name = st.text_input("Report Name", f"{selected_project} Status Report")
            include_sections = st.multiselect(
                "Include Sections",
                options=["Project Overview", "Production Status", "Quality Issues", "Schedule Performance"],
                default=["Project Overview", "Production Status"]
            )
        
        with col2:
            report_format = st.selectbox(
                "Report Format",
                options=["PDF", "Excel", "Dashboard View"],
                index=2
            )
            
            stakeholders = st.multiselect(
                "Share with Stakeholders",
                options=["Project Manager", "Client", "Site Team", "Quality Control"],
                default=["Project Manager"]
            )
        
        # Generate preview based on selections
        if st.button("Generate Report Preview"):
            st.markdown(f"### {report_name} Preview")
            
            # Get data
            modules_df = get_modules(project_id)
            
            # Get all issues and then filter them for the modules in this project
            all_issues_df = get_issues()
            
            # If we have modules and issues, filter issues for this project's modules
            if not modules_df.empty and not all_issues_df.empty:
                module_ids = modules_df['module_id'].tolist()
                issues_df = all_issues_df[all_issues_df['module_id'].isin(module_ids)]
            else:
                issues_df = pd.DataFrame()  # Empty DataFrame if no modules or issues
            
            # Display selected sections
            if "Project Overview" in include_sections:
                st.markdown("#### Project Overview")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Project Completion", f"{project_data['progress']:.1f}%")
                with col2:
                    st.metric("Modules Complete", f"{project_data['completed_modules']} of {project_data['total_modules']}")
                with col3:
                    days_remaining = (pd.to_datetime(project_data['end_date']) - datetime.now()).days
                    st.metric("Days Remaining", days_remaining)
                
                # Project timeline
                if pd.notna(project_data['start_date']) and pd.notna(project_data['end_date']):
                    start_date = pd.to_datetime(project_data['start_date'])
                    end_date = pd.to_datetime(project_data['end_date'])
                    total_days = (end_date - start_date).days
                    elapsed_days = (datetime.now() - start_date).days
                    timeline_progress = min(100, max(0, (elapsed_days / total_days * 100)))
                    
                    st.markdown("##### Project Timeline")
                    st.progress(timeline_progress / 100)
                    st.markdown(f"Project started on {start_date.strftime('%Y-%m-%d')}, scheduled to end on {end_date.strftime('%Y-%m-%d')}")
            
            if "Production Status" in include_sections and not modules_df.empty:
                st.markdown("#### Production Status")
                
                # Add status counts
                status_counts = modules_df['status'].value_counts().reset_index()
                status_counts.columns = ['status', 'count']
                
                # Create status chart
                fig = px.bar(
                    status_counts,
                    x='status',
                    y='count',
                    title="Component Status",
                    color='status',
                    color_discrete_map={
                        'Completed': '#28a745',
                        'In Progress': '#ffc107',
                        'Not Started': '#6c757d',
                        'Quality Check': '#17a2b8'
                    }
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            if "Quality Issues" in include_sections and not issues_df.empty:
                st.markdown("#### Quality Issues")
                
                # Add severity counts
                severity_counts = issues_df['severity'].value_counts().reset_index()
                severity_counts.columns = ['severity', 'count']
                
                # Create severity chart
                fig = px.pie(
                    severity_counts,
                    values='count',
                    names='severity',
                    title="Issues by Severity",
                    color='severity',
                    color_discrete_map={
                        'Low': '#28a745',
                        'Medium': '#ffc107',
                        'High': '#fd7e14',
                        'Critical': '#dc3545'
                    }
                )
                
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            if "Schedule Performance" in include_sections:
                st.markdown("#### Schedule Performance")
                
                # Calculate if ahead or behind schedule
                if 'time_progress' not in project_data:
                    project_data['start_date'] = pd.to_datetime(project_data['start_date'])
                    project_data['end_date'] = pd.to_datetime(project_data['end_date'])
                    project_data['days_passed'] = (datetime.now() - project_data['start_date']).days
                    project_data['total_days'] = (project_data['end_date'] - project_data['start_date']).days
                    project_data['time_progress'] = (project_data['days_passed'] / project_data['total_days'] * 100)
                
                schedule_diff = project_data['progress'] - project_data['time_progress']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Completion Progress", f"{project_data['progress']:.1f}%")
                with col2:
                    st.metric("Timeline Progress", f"{project_data['time_progress']:.1f}%")
                
                status = "Ahead of Schedule" if schedule_diff > 5 else "Behind Schedule" if schedule_diff < -5 else "On Schedule"
                color = "#28a745" if schedule_diff > 5 else "#dc3545" if schedule_diff < -5 else "#ffc107"
                
                st.markdown(f"""
                <div style="padding: 1rem; background-color: {color}20; border-radius: 0.5rem; border: 1px solid {color}; margin: 1rem 0;">
                    <div style="font-weight: 600; color: {color}; font-size: 1.2rem;">{status}</div>
                    <div>Project is {abs(schedule_diff):.1f}% {"ahead of" if schedule_diff > 0 else "behind"} schedule</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Show share options
            st.markdown("#### Share Options")
            st.markdown(f"This report will be shared with: {', '.join(stakeholders)}")
            
            if report_format != "Dashboard View":
                st.info(f"A {report_format} report would be generated and sent to stakeholders in a real implementation.")
            
            # Export to Excel option for demo
            if modules_df is not None and not modules_df.empty:
                excel_data = convert_df_to_excel(modules_df)
                st.download_button(
                    f"Export Sample Report ({report_format})",
                    data=excel_data,
                    file_name=f"{report_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    disabled=excel_data is None,
                    help="Download the data as an Excel file"
                )

def convert_df_to_excel(df):
    """Convert a dataframe to Excel binary data for download"""
    try:
        # Ensure we have pandas and io available
        import pandas as pd
        import io
        
        # Try to import xlsxwriter, which is needed for Excel export
        try:
            import xlsxwriter
        except ImportError:
            st.error("Missing required package: xlsxwriter. Please install it using pip install xlsxwriter.")
            return None
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Report', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Report']
            
            # Add formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'bg_color': '#2d3748',
                'font_color': 'white',
                'border': 1
            })
            
            # Write the column headers with the defined format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Adjust column widths
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                worksheet.set_column(i, i, max_len)
        
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        st.error(f"Error generating Excel file: {str(e)}")
        return None

def show_reports_dashboard():
    """Show the reports dashboard with tabs for different report types"""
    user_data = get_current_user()
    
    # Check permissions
    can_view_analytics = user_data['role'].lower() in ['manager', 'supervisor', 'inspector', 'engineer']
    
    if not can_view_analytics:
        st.warning("You do not have permission to view analytics and reports.")
        return
    
    # Create tabs for different report types
    tab1, tab2, tab3, tab4 = st.tabs(["Project Reports", "Quality Reports", "Task Reports", "Advanced Reports"])
    
    with tab1:
        
        project_completion_report()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        
        quality_issues_report()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        
        task_performance_report()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab4:
        
        advanced_reporting()
        st.markdown('</div>', unsafe_allow_html=True)

def reports_page():
    """Main function to render the reports page"""
    show_reports_dashboard()

# Run the page if this script is the main entry point
if __name__ == "__main__":
    if is_authenticated():
        reports_page()
    else:
        st.error("Please log in to access this page.")
        st.button("Go to Login", on_click=lambda: st.switch_page("app.py")) 