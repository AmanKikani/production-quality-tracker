import pandas as pd
import streamlit as st
import os
from datetime import datetime

# Data loading functions
def load_data(file_path):
    """Load data from CSV file"""
    try:
        data = pd.read_csv(file_path)
        return data
    except FileNotFoundError:
        st.error(f"Data file not found: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def save_data(data_df, file_path):
    """Save data to CSV file"""
    try:
        data_df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

# Project related functions
def get_projects():
    """Get all projects data"""
    return load_data('data/projects.csv')

def get_project(project_id):
    """Get a specific project by ID"""
    projects_df = get_projects()
    if projects_df.empty:
        return None
    
    project = projects_df[projects_df['project_id'] == project_id]
    if project.empty:
        return None
    
    return project.iloc[0].to_dict()

def update_project_progress(project_id, completed_modules):
    """Update project progress based on completed modules"""
    projects_df = get_projects()
    if projects_df.empty:
        return False
    
    # Find the project by ID
    idx = projects_df.index[projects_df['project_id'] == project_id]
    if len(idx) == 0:
        return False
    
    # Update completed modules count
    projects_df.at[idx[0], 'completed_modules'] = completed_modules
    
    # If all modules are completed, update status
    if completed_modules >= projects_df.at[idx[0], 'total_modules']:
        projects_df.at[idx[0], 'status'] = 'Completed'
    
    # Save updated data
    return save_data(projects_df, 'data/projects.csv')

# Module related functions
def get_modules(project_id=None):
    """Get all modules or filter by project_id"""
    modules_df = load_data('data/modules.csv')
    
    if project_id is not None:
        modules_df = modules_df[modules_df['project_id'] == project_id]
    
    return modules_df

def get_module(module_id):
    """Get a specific module by ID"""
    modules_df = get_modules()
    if modules_df.empty:
        return None
    
    module = modules_df[modules_df['module_id'] == module_id]
    if module.empty:
        return None
    
    return module.iloc[0].to_dict()

def update_module_status(module_id, status, completion_date=None):
    """Update module status and completion date"""
    modules_df = get_modules()
    if modules_df.empty:
        return False
    
    # Find the module by ID
    idx = modules_df.index[modules_df['module_id'] == module_id]
    if len(idx) == 0:
        return False
    
    # Update status
    modules_df.at[idx[0], 'status'] = status
    
    # Update completion date if provided
    if completion_date and status == 'Completed':
        modules_df.at[idx[0], 'actual_completion'] = completion_date
    
    # Save updated data
    return save_data(modules_df, 'data/modules.csv')

# Issue related functions
def get_issues(module_id=None, status=None):
    """Get all issues or filter by module_id and/or status"""
    issues_df = load_data('data/issues.csv')
    
    if issues_df.empty:
        return issues_df
    
    if module_id is not None:
        issues_df = issues_df[issues_df['module_id'] == module_id]
    
    if status is not None:
        issues_df = issues_df[issues_df['status'] == status]
    
    return issues_df

def create_issue(module_id, reported_by, category, severity, description):
    """Create a new issue"""
    issues_df = get_issues()
    
    # Generate new issue ID
    if issues_df.empty:
        new_id = "I001"
    else:
        # Extract numeric part of the last ID and increment
        last_id = issues_df['issue_id'].iloc[-1]
        num_part = int(last_id[1:])
        new_id = f"I{(num_part + 1):03d}"
    
    # Create new issue record
    new_issue = {
        'issue_id': new_id,
        'module_id': module_id,
        'reported_by': reported_by,
        'report_date': datetime.now().strftime('%Y-%m-%d'),
        'category': category,
        'severity': severity,
        'description': description,
        'status': 'Open',
        'resolved_date': '',
        'resolved_by': ''
    }
    
    # Append new issue to dataframe
    issues_df = pd.concat([issues_df, pd.DataFrame([new_issue])], ignore_index=True)
    
    # Save updated data
    return save_data(issues_df, 'data/issues.csv') and new_id

def update_issue_status(issue_id, status, resolved_by=None):
    """Update issue status and resolver"""
    issues_df = get_issues()
    if issues_df.empty:
        return False
    
    # Find the issue by ID
    idx = issues_df.index[issues_df['issue_id'] == issue_id]
    if len(idx) == 0:
        return False
    
    # Update status
    issues_df.at[idx[0], 'status'] = status
    
    # Update resolution info if resolved
    if status == 'Resolved' and resolved_by is not None:
        issues_df.at[idx[0], 'resolved_date'] = datetime.now().strftime('%Y-%m-%d')
        issues_df.at[idx[0], 'resolved_by'] = resolved_by
    
    # Save updated data
    return save_data(issues_df, 'data/issues.csv')

# Task related functions
def get_tasks(module_id=None, assigned_to=None, status=None):
    """Get all tasks or filter by module_id, assigned_to, and/or status"""
    tasks_df = load_data('data/tasks.csv')
    
    if tasks_df.empty:
        return tasks_df
    
    if module_id is not None:
        tasks_df = tasks_df[tasks_df['module_id'] == module_id]
    
    if assigned_to is not None:
        tasks_df = tasks_df[tasks_df['assigned_to'] == assigned_to]
    
    if status is not None:
        tasks_df = tasks_df[tasks_df['status'] == status]
    
    return tasks_df

def create_task(issue_id, module_id, assigned_to, assigned_by, due_date, description, priority):
    """Create a new task"""
    tasks_df = get_tasks()
    
    # Generate new task ID
    if tasks_df.empty:
        new_id = "T001"
    else:
        # Extract numeric part of the last ID and increment
        last_id = tasks_df['task_id'].iloc[-1]
        num_part = int(last_id[1:])
        new_id = f"T{(num_part + 1):03d}"
    
    # Create new task record
    new_task = {
        'task_id': new_id,
        'issue_id': issue_id if issue_id else '',
        'module_id': module_id,
        'assigned_to': assigned_to,
        'assigned_by': assigned_by,
        'assigned_date': datetime.now().strftime('%Y-%m-%d'),
        'due_date': due_date,
        'description': description,
        'priority': priority,
        'status': 'Assigned',
        'completion_date': ''
    }
    
    # Append new task to dataframe
    tasks_df = pd.concat([tasks_df, pd.DataFrame([new_task])], ignore_index=True)
    
    # Save updated data
    return save_data(tasks_df, 'data/tasks.csv')

def update_task_status(task_id, status):
    """Update task status and completion date"""
    tasks_df = get_tasks()
    if tasks_df.empty:
        return False
    
    # Find the task by ID
    idx = tasks_df.index[tasks_df['task_id'] == task_id]
    if len(idx) == 0:
        return False
    
    # Update status
    tasks_df.at[idx[0], 'status'] = status
    
    # Update completion date if completed
    if status == 'Completed':
        tasks_df.at[idx[0], 'completion_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # If the task is related to an issue, update the issue status
        issue_id = tasks_df.at[idx[0], 'issue_id']
        if issue_id and issue_id != '':
            update_issue_status(issue_id, 'Resolved', tasks_df.at[idx[0], 'assigned_to'])
    
    # Save updated data
    return save_data(tasks_df, 'data/tasks.csv')

# Analytics functions
def get_project_progress():
    """Calculate progress statistics for all projects"""
    projects_df = get_projects()
    
    if projects_df.empty:
        return pd.DataFrame()
    
    # Calculate progress percentage
    projects_df['progress'] = (projects_df['completed_modules'] / projects_df['total_modules'] * 100).round(2)
    
    return projects_df

def get_issue_statistics():
    """Get statistics on issues by category and severity"""
    issues_df = get_issues()
    
    if issues_df.empty:
        return {}, {}
    
    # Count issues by category
    category_counts = issues_df['category'].value_counts().to_dict()
    
    # Count issues by severity
    severity_counts = issues_df['severity'].value_counts().to_dict()
    
    return category_counts, severity_counts

def get_overdue_tasks():
    """Get all overdue tasks"""
    tasks_df = get_tasks()
    
    if tasks_df.empty:
        return pd.DataFrame()
    
    # Convert date strings to datetime objects for comparison
    tasks_df['due_date'] = pd.to_datetime(tasks_df['due_date'])
    
    # Get current date
    current_date = pd.to_datetime(datetime.now().date())
    
    # Filter for incomplete tasks that are past due date
    overdue_tasks = tasks_df[(tasks_df['status'] != 'Completed') & 
                             (tasks_df['due_date'] < current_date)]
    
    # Convert back to string format for display
    if not overdue_tasks.empty:
        overdue_tasks['due_date'] = overdue_tasks['due_date'].dt.strftime('%Y-%m-%d')
    
    return overdue_tasks

def get_users():
    """Get all users data"""
    return load_data('data/users.csv') 