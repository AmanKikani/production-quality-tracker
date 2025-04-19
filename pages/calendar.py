"""
Calendar view for projects and their completion percentages.

This module provides a calendar view of all projects with their start and end dates,
along with visual indicators for project progress.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar
from utils.database import get_projects, get_project_progress, get_modules
from utils.helpers import format_date, render_status_indicator
import numpy as np

def calendar_page():
    """Main function to render the calendar view of projects"""
    st.markdown("<h1 style='font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;'>Project Calendar</h1>", unsafe_allow_html=True)
    
    # Get projects data with progress information
    projects_df = get_project_progress()
    
    if projects_df.empty:
        st.warning("No project data available. Please add projects first.")
        return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Timeline View", "Project Grid", "Monthly Calendar"])
    
    with tab1:
        display_timeline_view(projects_df)
        
    with tab2:
        display_project_grid(projects_df)
        
    with tab3:
        display_simple_calendar(projects_df)

def display_timeline_view(projects_df):
    """Display projects in a Gantt chart timeline view"""
    st.markdown("<h2 style='font-size: 1.2rem; margin-top: 0.5rem;'>Project Timeline</h2>", unsafe_allow_html=True)
    
    # Ensure datetime format for dates
    projects_df['start_date'] = pd.to_datetime(projects_df['start_date'])
    projects_df['end_date'] = pd.to_datetime(projects_df['end_date'])
    
    # Add current date for reference
    today = datetime.now().date()
    
    # Create a color scale based on progress
    # Convert progress to numeric
    projects_df['progress'] = pd.to_numeric(projects_df['progress'], errors='coerce')
    
    # Create figure
    fig = px.timeline(
        projects_df, 
        x_start='start_date', 
        x_end='end_date', 
        y='project_name',
        color='progress',
        color_continuous_scale=[(0, "red"), (0.5, "yellow"), (1, "green")],
        range_color=[0, 100],
        hover_name='project_name',
        hover_data={
            'start_date': True,
            'end_date': True,
            'progress': ':.1f%',
            'status': True,
            'client_name': True,
        }
    )
    
    # Add vertical line for current date
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="#ff6b6b")
    
    # Add annotation for current date
    fig.add_annotation(
        x=today,
        y=len(projects_df),
        yref="paper",
        text="Today",
        showarrow=False,
        arrowhead=1,
        xanchor="left",
        yanchor="bottom",
        bgcolor="#ff6b6b",
        font=dict(color="white", size=12),
        borderpad=4
    )
    
    # Update layout
    fig.update_layout(
        title="Project Timeline with Progress",
        xaxis_title="Date",
        yaxis_title="Project",
        coloraxis_colorbar=dict(
            title="Progress %",
            ticksuffix="%",
            showticksuffix="all"
        ),
        height=400 + (len(projects_df) * 30),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )
    )
    
    # Display figure
    st.plotly_chart(fig, use_container_width=True)
    
    # Display projects in a table
    st.markdown("### Projects List")
    
    # Format the dataframe for display
    display_df = projects_df[['project_id', 'project_name', 'status', 'progress', 'start_date', 'end_date', 'client_name']].copy()
    display_df['start_date'] = display_df['start_date'].dt.strftime('%Y-%m-%d')
    display_df['end_date'] = display_df['end_date'].dt.strftime('%Y-%m-%d')
    display_df['progress'] = display_df['progress'].apply(lambda x: f"{x:.1f}%")
    
    # Create clickable project links
    display_df['project_name'] = display_df.apply(
        lambda row: f"{row['project_name']}", 
        axis=1
    )
    
    # Display the table
    st.dataframe(display_df)

def display_project_grid(projects_df):
    """Display projects in a grid view with progress indicators"""
    st.markdown("<h2 style='font-size: 1.2rem; margin-top: 0.5rem;'>Project Progress Grid</h2>", unsafe_allow_html=True)
    
    # Create a session state variable to track selected project for sidebar
    if 'selected_project_id' not in st.session_state:
        st.session_state.selected_project_id = None
    
    # Check for URL parameters - an alternative to rerun
    # Using the new st.query_params API instead of experimental_get_query_params
    query_params = st.query_params
    if "project_id" in query_params:
        try:
            project_id = int(query_params["project_id"])
            if project_id in projects_df['project_id'].values:
                st.session_state.selected_project_id = project_id
        except ValueError:
            pass
    
    # Use columns layout - main grid and sidebar
    grid_col, sidebar_col = st.columns([3, 1])
    
    with grid_col:
        # Sort by start date
        projects_df = projects_df.sort_values(by=['start_date'])
        
        # Create grid layout
        col_count = 3  # Number of columns in the grid
        rows = []
        row = []
        
        # Group projects into rows
        for i, project in projects_df.iterrows():
            row.append(project)
            if len(row) == col_count:
                rows.append(row)
                row = []
        
        # Add any remaining projects to the last row
        if row:
            rows.append(row)
        
        # Display grid
        for row in rows:
            cols = st.columns(col_count)
            
            for i, project in enumerate(row):
                if i < len(cols):
                    with cols[i]:
                        # Determine color based on progress
                        progress = project['progress']
                        if progress < 25:
                            color = "#ef4444"  # Red
                        elif progress < 50:
                            color = "#f59e0b"  # Orange
                        elif progress < 75:
                            color = "#10b981"  # Green
                        else:
                            color = "#059669"  # Dark Green
                            
                        # Create card using Streamlit components
                        with st.container():
                            # Card container
                            
                            
                            # Project title
                            st.markdown(
                                f'<h3 style="margin: 0; font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 5px;">{project["project_name"]}</h3>',
                                unsafe_allow_html=True
                            )
                            
                            # Client name
                            st.markdown(
                                f'<div style="color: #a0aec0; font-size: 0.8rem; margin-bottom: 10px;">Client: {project["client_name"]}</div>',
                                unsafe_allow_html=True
                            )
                            
                            # Progress bar
                            st.markdown(
                                f'<div style="margin-bottom: 10px;">'
                                f'<div style="background-color: #4b5563; height: 10px; border-radius: 5px; overflow: hidden;">'
                                f'<div style="background-color: {color}; width: {progress}%; height: 100%;"></div>'
                                f'</div>'
                                f'<div style="display: flex; justify-content: space-between; margin-top: 3px;">'
                                f'<span style="font-size: 0.8rem; color: #a0aec0;">Progress</span>'
                                f'<span style="font-size: 0.8rem; color: #e2e8f0; font-weight: 600;">{progress:.1f}%</span>'
                                f'</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            
                            # Start date
                            st.markdown(
                                f'<div style="display: flex; justify-content: space-between; margin-bottom: 5px;">'
                                f'<span style="font-size: 0.8rem; color: #a0aec0;">Start:</span>'
                                f'<span style="font-size: 0.8rem; color: #e2e8f0;">{pd.to_datetime(project["start_date"]).strftime("%Y-%m-%d")}</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            
                            # End date
                            st.markdown(
                                f'<div style="display: flex; justify-content: space-between; margin-bottom: 75px;">'  # Increased bottom margin to make space for button
                                f'<span style="font-size: 0.8rem; color: #a0aec0;">End:</span>'
                                f'<span style="font-size: 0.8rem; color: #e2e8f0;">{pd.to_datetime(project["end_date"]).strftime("%Y-%m-%d")}</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            
                            # Close the card container div
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Create a button that will update the session state when clicked
                            if st.button(f"View Details", key=f"btn_{project['project_id']}"):
                                st.session_state.selected_project_id = project['project_id']
    
    # Show the sidebar if a project is selected
    with sidebar_col:
        if st.session_state.selected_project_id:
            display_project_sidebar(projects_df, st.session_state.selected_project_id)
        else:
            st.info("Select a project to view details")

def display_project_sidebar(projects_df, project_id):
    """Display a sidebar with detailed project information"""
    # Find the selected project
    selected_project = projects_df[projects_df['project_id'] == project_id].iloc[0]
    
    # Calculate days remaining
    today = datetime.now().date()
    end_date = pd.to_datetime(selected_project['end_date']).date()
    days_remaining = (end_date - today).days
    
    # Check if project is at 100% completion - if so, it's not overdue regardless of date
    progress = selected_project['progress']
    if progress >= 100:
        days_status = "completed"
    else:
        days_status = "overdue" if days_remaining < 0 else "remaining"
    
    # Get project modules data
    modules_df = get_modules(project_id)
    total_modules = len(modules_df) if not modules_df.empty else 0
    completed_modules = len(modules_df[modules_df['status'] == 'Completed']) if not modules_df.empty else 0
    modules_to_complete = total_modules - completed_modules
    
    # Get issues data (mock data for now, replace with actual database call)
    # TODO: Replace with actual database call when issues tracking is implemented
    total_issues = 12  # Example value
    solved_issues = 8   # Example value
    unsolved_issues = total_issues - solved_issues
    
    # Create the sidebar content
    st.markdown("### Project Overview")
    
    # Project name and close button in the same row
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"#### {selected_project['project_name']}")
    with col2:
        if st.button("X", key="close_sidebar"):
            # Simply clear the selection without forcing a rerun
            st.session_state.selected_project_id = None
    
    st.markdown(f"**Client:** {selected_project['client_name']}")
    st.markdown(f"**Status:** {selected_project['status']}")
    
    # Progress information
    st.markdown("### Progress")
    
    # Progress bar with color based on percentage
    if progress < 25:
        bar_color = "#ef4444"  # Red
    elif progress < 50:
        bar_color = "#f59e0b"  # Orange
    elif progress < 75:
        bar_color = "#10b981"  # Green
    else:
        bar_color = "#8b5cf6"  # Purple
    
    st.markdown(
        f"""
        <div style="margin: 10px 0;">
            <div style="background-color: #4b5563; height: 16px; border-radius: 5px; overflow: hidden;">
                <div style="background-color: {bar_color}; width: {progress}%; height: 100%;"></div>
            </div>
            <div style="text-align: center; margin-top: 3px;">
                <span style="font-size: 1rem; font-weight: 600;">{progress:.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Timeline information
    st.markdown("### Timeline")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Start Date:**")
        st.markdown(pd.to_datetime(selected_project['start_date']).strftime("%Y-%m-%d"))
    with col2:
        st.markdown("**End Date:**")
        st.markdown(pd.to_datetime(selected_project['end_date']).strftime("%Y-%m-%d"))
    
    # Customize the days remaining/overdue text
    if days_status == "completed":
        st.markdown(f"**Status:** Completed")
    else:
        st.markdown(f"**Days {days_status}:** {abs(days_remaining)}")
    
    # Modules information
    st.markdown("### Modules")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Total:**")
        st.markdown(f"{total_modules}")
    with col2:
        st.markdown("**To Complete:**")
        st.markdown(f"{modules_to_complete}")
    
    # Issues information
    st.markdown("### Issues")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Total:**")
        st.markdown(f"{total_issues}")
    with col2:
        st.markdown("**Solved:**")
        st.markdown(f"{solved_issues}")
    with col3:
        st.markdown("**Unsolved:**")
        st.markdown(f"{unsolved_issues}")
    
    # Actions
    st.markdown("### Actions")
    st.markdown(f"[Go to Project Details](/?view=projects&project_id={project_id})")
    st.markdown(f"[Manage Issues](/?view=issues&project_id={project_id})")

def display_simple_calendar(projects_df):
    """Display a simplified month view of projects with traditional calendar appearance"""
    st.markdown("<h2 style='font-size: 1.2rem; margin-top: 0.5rem;'>Project Calendar</h2>", unsafe_allow_html=True)
    
    # Get current date
    today = datetime.now()
    
    # Create month selector 
    col1, col2 = st.columns([1, 1])
    with col1:
        month = st.selectbox(
            "Month", 
            options=list(range(1, 13)), 
            format_func=lambda x: calendar.month_name[x],
            index=today.month - 1
        )
    with col2:
        year = st.selectbox(
            "Year", 
            options=list(range(today.year - 2, today.year + 3)),
            index=2
        )
    
    # Create projects map
    projects_df['start_date'] = pd.to_datetime(projects_df['start_date'])
    projects_df['end_date'] = pd.to_datetime(projects_df['end_date'])
    
    # Create a map of days to project lists
    day_projects = {}
    for _, project in projects_df.iterrows():
        if pd.isna(project['start_date']) or pd.isna(project['end_date']):
            continue
            
        # Check if project falls in the selected month
        if (project['start_date'].year > year or 
            (project['start_date'].year == year and project['start_date'].month > month) or
            project['end_date'].year < year or 
            (project['end_date'].year == year and project['end_date'].month < month)):
            continue
        
        # Add project to days
        start_day = 1
        end_day = 31
        
        if project['start_date'].year == year and project['start_date'].month == month:
            start_day = project['start_date'].day
        
        if project['end_date'].year == year and project['end_date'].month == month:
            end_day = project['end_date'].day
        
        for day in range(start_day, end_day + 1):
            if day not in day_projects:
                day_projects[day] = []
            # Add project info to the day
            day_projects[day].append({
                'id': project['project_id'],
                'name': project['project_name'],
                'progress': project['progress']
            })
    
    # Get calendar for the selected month
    cal = calendar.monthcalendar(year, month)
    
    # Add simple color legend
    st.markdown(f"### {calendar.month_name[month]} {year}")
    
    # Create legend with Streamlit components
    legend_cols = st.columns(4)
    with legend_cols[0]:
        st.markdown(
            '<div style="display: flex; align-items: center;">'
            '<div style="background-color: #ef4444; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px;"></div>'
            '<span style="font-size: 12px;">Low progress</span>'
            '</div>',
            unsafe_allow_html=True
        )
    with legend_cols[1]:
        st.markdown(
            '<div style="display: flex; align-items: center;">'
            '<div style="background-color: #f59e0b; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px;"></div>'
            '<span style="font-size: 12px;">Medium progress</span>'
            '</div>',
            unsafe_allow_html=True
        )
    with legend_cols[2]:
        st.markdown(
            '<div style="display: flex; align-items: center;">'
            '<div style="background-color: #10b981; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px;"></div>'
            '<span style="font-size: 12px;">High progress</span>'
            '</div>',
            unsafe_allow_html=True
        )
    with legend_cols[3]:
        st.markdown(
            '<div style="display: flex; align-items: center;">'
            '<div style="background-color: #8b5cf6; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px;"></div>'
            '<span style="font-size: 12px;">Complete</span>'
            '</div>',
            unsafe_allow_html=True
        )
    
    # Create days of week header
    day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    header_cols = st.columns(7)
    for i, name in enumerate(day_names):
        with header_cols[i]:
            st.markdown(f'<div style="background-color: #1e293b; color: white; text-align: center; padding: 8px 0; font-size: 14px; border-radius: 4px;">{name}</div>', unsafe_allow_html=True)
    
    # Current day for highlighting
    current_day = today.day if today.month == month and today.year == year else -1
    
    # Display calendar using Streamlit components
    for week in cal:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            with week_cols[i]:
                if day == 0:
                    # Empty day
                    st.markdown('<div style="height: 90px; border: 1px solid #334155;"></div>', unsafe_allow_html=True)
                else:
                    # Today highlighting
                    today_style = "background-color: rgba(59, 130, 246, 0.2);" if day == current_day else ""
                    today_border = "border: 2px solid #3b82f6;" if day == current_day else "border: 1px solid #334155;"
                    
                    # Start day container
                    st.markdown(
                        f'<div style="height: 90px; {today_border} border-radius: 4px; overflow: hidden;">'
                        f'<div style="font-weight: bold; font-size: 14px; padding: 3px 5px; text-align: right; {today_style}">{day}</div>'
                        f'<div style="padding: 2px;">', 
                        unsafe_allow_html=True
                    )
                    
                    # Add projects for this day using markdown
                    projects_for_day = day_projects.get(day, [])
                    if projects_for_day:
                        # Sort by progress
                        projects_for_day = sorted(projects_for_day, key=lambda x: x['progress'], reverse=True)
                        
                        # Show up to 3 projects
                        for proj in projects_for_day[:3]:
                            # Determine color based on progress
                            if proj['progress'] < 25:
                                dot_color = "#ef4444"  # Red
                            elif proj['progress'] < 50:
                                dot_color = "#f59e0b"  # Orange
                            elif proj['progress'] < 75:
                                dot_color = "#10b981"  # Green
                            else:
                                dot_color = "#8b5cf6"  # Purple
                            
                            # Add project name with color dot
                            proj_name = proj['name']
                            if len(proj_name) > 12:
                                proj_name = proj_name[:10] + '..'
                            
                            st.markdown(
                                f'<div style="font-size: 11px; padding: 2px 4px; margin: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">'
                                f'<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: {dot_color}; margin-right: 4px;"></span>'
                                f'{proj_name}'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                        
                        # Add more indicator if needed
                        if len(projects_for_day) > 3:
                            st.markdown(
                                f'<div style="font-size: 11px; text-align: center; color: #a0aec0; padding: 2px;">+{len(projects_for_day) - 3} more</div>',
                                unsafe_allow_html=True
                            )
                    
                    # Close day container
                    st.markdown('</div></div>', unsafe_allow_html=True)
    
    # Display monthly projects table
    with st.expander("View All Projects This Month", expanded=False):
        # Filter projects for the selected month
        monthly_projects = projects_df[
            ((projects_df['start_date'].dt.year < year) | 
             ((projects_df['start_date'].dt.year == year) & (projects_df['start_date'].dt.month <= month))) &
            ((projects_df['end_date'].dt.year > year) | 
             ((projects_df['end_date'].dt.year == year) & (projects_df['end_date'].dt.month >= month)))
        ]
        
        if not monthly_projects.empty:
            # Format for display
            display_df = monthly_projects[['project_id', 'project_name', 'status', 'progress', 'start_date', 'end_date']].copy()
            display_df['start_date'] = display_df['start_date'].dt.strftime('%Y-%m-%d')
            display_df['end_date'] = display_df['end_date'].dt.strftime('%Y-%m-%d')
            display_df['progress'] = display_df['progress'].apply(lambda x: f"{x:.1f}%")
            
            # Display as dataframe
            st.dataframe(display_df)
        else:
            st.info(f"No projects active in {calendar.month_name[month]} {year}") 