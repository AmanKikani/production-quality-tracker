"""
Data models for Volumod Production Tracker

This module defines the data model for the Volumod Production Tracker application.
It includes the schema definitions and utility functions for database operations.
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime
import json

# Ensure data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

DB_PATH = 'data/volumod_tracker.db'

def get_db_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table with expanded role system
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('operator', 'inspector', 'supervisor', 'manager', 'admin')),
        department TEXT,
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    ''')

    # Product units table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_units (
        unit_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        type TEXT NOT NULL,
        project_id TEXT,
        current_stage_id INTEGER,
        status TEXT NOT NULL DEFAULT 'not_started' 
            CHECK(status IN ('not_started', 'in_progress', 'blocked', 'completed')),
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(project_id),
        FOREIGN KEY (current_stage_id) REFERENCES production_stages(stage_id),
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    )
    ''')

    # Production workflows table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workflows (
        workflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    )
    ''')

    # Production stages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_stages (
        stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        workflow_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        sequence_number INTEGER NOT NULL,
        estimated_duration INTEGER, -- in hours
        requires_inspection BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
    )
    ''')

    # Unit stage tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS unit_stages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id TEXT NOT NULL,
        stage_id INTEGER NOT NULL,
        assigned_to INTEGER,
        status TEXT NOT NULL DEFAULT 'not_started'
            CHECK(status IN ('not_started', 'in_progress', 'blocked', 'completed')),
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (unit_id) REFERENCES product_units(unit_id),
        FOREIGN KEY (stage_id) REFERENCES production_stages(stage_id),
        FOREIGN KEY (assigned_to) REFERENCES users(user_id)
    )
    ''')

    # Checklist templates
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checklist_templates (
        template_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        stage_id INTEGER,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (stage_id) REFERENCES production_stages(stage_id),
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    )
    ''')

    # Checklist items
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checklist_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        sequence_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        item_type TEXT NOT NULL CHECK(item_type IN ('pass_fail', 'yes_no', 'text', 'photo', 'numeric')),
        required BOOLEAN DEFAULT 1,
        FOREIGN KEY (template_id) REFERENCES checklist_templates(template_id)
    )
    ''')

    # Checklist instances
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checklist_instances (
        instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        unit_id TEXT NOT NULL,
        stage_id INTEGER NOT NULL,
        assigned_to INTEGER,
        status TEXT NOT NULL DEFAULT 'pending' 
            CHECK(status IN ('pending', 'in_progress', 'completed', 'failed')),
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        completed_by INTEGER,
        FOREIGN KEY (template_id) REFERENCES checklist_templates(template_id),
        FOREIGN KEY (unit_id) REFERENCES product_units(unit_id),
        FOREIGN KEY (stage_id) REFERENCES production_stages(stage_id),
        FOREIGN KEY (assigned_to) REFERENCES users(user_id),
        FOREIGN KEY (completed_by) REFERENCES users(user_id)
    )
    ''')

    # Checklist item responses
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checklist_responses (
        response_id INTEGER PRIMARY KEY AUTOINCREMENT,
        instance_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        response_value TEXT,
        media_url TEXT,
        notes TEXT,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (instance_id) REFERENCES checklist_instances(instance_id),
        FOREIGN KEY (item_id) REFERENCES checklist_items(item_id),
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    )
    ''')

    # Quality issues
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quality_issues (
        issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id TEXT NOT NULL,
        stage_id INTEGER,
        checklist_instance_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        severity TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high', 'critical')),
        category TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open' 
            CHECK(status IN ('open', 'in_progress', 'resolved_pending_verification', 'verified', 'closed')),
        root_cause TEXT,
        corrective_action TEXT,
        reported_by INTEGER NOT NULL,
        reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        assigned_to INTEGER,
        resolved_by INTEGER,
        resolved_at TIMESTAMP,
        verified_by INTEGER,
        verified_at TIMESTAMP,
        FOREIGN KEY (unit_id) REFERENCES product_units(unit_id),
        FOREIGN KEY (stage_id) REFERENCES production_stages(stage_id),
        FOREIGN KEY (checklist_instance_id) REFERENCES checklist_instances(instance_id),
        FOREIGN KEY (reported_by) REFERENCES users(user_id),
        FOREIGN KEY (assigned_to) REFERENCES users(user_id),
        FOREIGN KEY (resolved_by) REFERENCES users(user_id),
        FOREIGN KEY (verified_by) REFERENCES users(user_id)
    )
    ''')

    # Tasks
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        task_type TEXT NOT NULL CHECK(task_type IN ('fix_issue', 'inspection', 'approval', 'documentation', 'other')),
        priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high', 'critical')),
        status TEXT NOT NULL DEFAULT 'assigned' 
            CHECK(status IN ('assigned', 'in_progress', 'on_hold', 'completed')),
        unit_id TEXT,
        issue_id INTEGER,
        stage_id INTEGER,
        assigned_by INTEGER NOT NULL,
        assigned_to INTEGER NOT NULL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TIMESTAMP,
        completed_at TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (unit_id) REFERENCES product_units(unit_id),
        FOREIGN KEY (issue_id) REFERENCES quality_issues(issue_id),
        FOREIGN KEY (stage_id) REFERENCES production_stages(stage_id),
        FOREIGN KEY (assigned_by) REFERENCES users(user_id),
        FOREIGN KEY (assigned_to) REFERENCES users(user_id)
    )
    ''')

    # Media attachments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media_attachments (
        attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        entity_type TEXT NOT NULL CHECK(entity_type IN ('unit', 'stage', 'issue', 'task', 'checklist')),
        entity_id TEXT NOT NULL,
        uploaded_by INTEGER NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
    )
    ''')

    # Notifications
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        notification_type TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    # Audit log
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        action_details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    # Projects table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        client_name TEXT,
        start_date TIMESTAMP,
        target_completion TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'planning' 
            CHECK(status IN ('planning', 'active', 'on_hold', 'completed')),
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    )
    ''')

    conn.commit()
    conn.close()

def seed_sample_data():
    """Seed the database with sample data for development"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if we already have users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return  # Skip seeding if data already exists
    
    # Insert sample users
    users = [
        ('john_doe', 'password123', 'john@example.com', 'John Doe', 'operator', 'Assembly'),
        ('jane_smith', 'pass456', 'jane@example.com', 'Jane Smith', 'inspector', 'Quality'),
        ('mike_jones', 'secure789', 'mike@example.com', 'Mike Jones', 'manager', 'Production'),
        ('rachel_kim', 'rachelpass', 'rachel@example.com', 'Rachel Kim', 'supervisor', 'Assembly'),
        ('admin_user', 'admin123', 'admin@example.com', 'Admin User', 'admin', 'Administration')
    ]
    
    cursor.executemany(
        "INSERT INTO users (username, password, email, full_name, role, department) VALUES (?, ?, ?, ?, ?, ?)",
        users
    )
    
    # Insert sample projects
    projects = [
        ('PRJ-2023-001', 'Residential Complex A', 'Multi-family housing modules', 'Acme Developers', '2023-07-01', '2023-12-15', 'active', 3),
        ('PRJ-2023-002', 'Commercial Building B', 'Office space modules', 'Business Properties Inc', '2023-08-15', '2024-03-30', 'planning', 3)
    ]
    
    cursor.executemany(
        "INSERT INTO projects (project_id, name, description, client_name, start_date, target_completion, status, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        projects
    )
    
    # Insert sample workflows
    workflows = [
        ('Residential Module Workflow', 'Standard workflow for residential modules', 3),
        ('Commercial Module Workflow', 'Workflow for commercial building modules', 3)
    ]
    
    cursor.executemany(
        "INSERT INTO workflows (name, description, created_by) VALUES (?, ?, ?)",
        workflows
    )
    
    # Get workflow IDs
    cursor.execute("SELECT workflow_id FROM workflows")
    workflow_ids = [row[0] for row in cursor.fetchall()]
    
    # Insert sample production stages for the first workflow
    stages_1 = [
        (workflow_ids[0], 'Frame Assembly', 'Construct the basic frame structure', 1, 8, 1),
        (workflow_ids[0], 'Electrical Wiring', 'Install electrical systems and wiring', 2, 6, 0),
        (workflow_ids[0], 'Plumbing Installation', 'Install plumbing systems', 3, 6, 0),
        (workflow_ids[0], 'Interior Finishing', 'Complete interior work including drywall and painting', 4, 12, 0),
        (workflow_ids[0], 'Quality Inspection', 'Final quality control inspection', 5, 4, 1)
    ]
    
    cursor.executemany(
        "INSERT INTO production_stages (workflow_id, name, description, sequence_number, estimated_duration, requires_inspection) VALUES (?, ?, ?, ?, ?, ?)",
        stages_1
    )
    
    # Insert sample production stages for the second workflow
    stages_2 = [
        (workflow_ids[1], 'Structural Frame', 'Build the structural frame', 1, 10, 1),
        (workflow_ids[1], 'MEP Systems', 'Mechanical, Electrical, and Plumbing installation', 2, 12, 1),
        (workflow_ids[1], 'Interior Systems', 'Install interior walls, ceilings, and floors', 3, 8, 0),
        (workflow_ids[1], 'Exterior Finishing', 'Complete exterior facade and finishes', 4, 10, 0),
        (workflow_ids[1], 'Final Inspection', 'Complete quality verification', 5, 6, 1)
    ]
    
    cursor.executemany(
        "INSERT INTO production_stages (workflow_id, name, description, sequence_number, estimated_duration, requires_inspection) VALUES (?, ?, ?, ?, ?, ?)",
        stages_2
    )
    
    # Insert sample product units
    cursor.execute("SELECT stage_id FROM production_stages WHERE workflow_id = ? AND sequence_number = 1", (workflow_ids[0],))
    first_stage_id = cursor.fetchone()[0]
    
    units = [
        ('UNIT-RA-101', 'Residential Module A101', 'Studio apartment module', 'residential', 'PRJ-2023-001', first_stage_id, 'in_progress', 3),
        ('UNIT-RA-102', 'Residential Module A102', 'One-bedroom apartment module', 'residential', 'PRJ-2023-001', first_stage_id, 'not_started', 3)
    ]
    
    cursor.executemany(
        "INSERT INTO product_units (unit_id, name, description, type, project_id, current_stage_id, status, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        units
    )
    
    # Insert sample checklist templates
    checklist_templates = [
        ('Frame Inspection', 'Checklist for frame assembly inspection', first_stage_id, 2),
        ('Electrical Safety Checklist', 'Safety checklist for electrical systems', None, 2)
    ]
    
    cursor.executemany(
        "INSERT INTO checklist_templates (name, description, stage_id, created_by) VALUES (?, ?, ?, ?)",
        checklist_templates
    )
    
    # Get template IDs
    cursor.execute("SELECT template_id FROM checklist_templates")
    template_ids = [row[0] for row in cursor.fetchall()]
    
    # Insert sample checklist items for the first template
    items_1 = [
        (template_ids[0], 1, 'Frame dimensions match specifications', 'Verify all dimensions are within tolerance', 'pass_fail', 1),
        (template_ids[0], 2, 'All connection points secure', 'Check that all bolts and fasteners are properly secured', 'pass_fail', 1),
        (template_ids[0], 3, 'Material quality acceptable', 'Inspect for material defects', 'pass_fail', 1),
        (template_ids[0], 4, 'Upload frame photos', 'Take photos of the completed frame from all angles', 'photo', 1),
        (template_ids[0], 5, 'Additional notes', 'Any additional observations', 'text', 0)
    ]
    
    cursor.executemany(
        "INSERT INTO checklist_items (template_id, sequence_number, title, description, item_type, required) VALUES (?, ?, ?, ?, ?, ?)",
        items_1
    )
    
    # Insert sample checklist items for the second template
    items_2 = [
        (template_ids[1], 1, 'Circuit breakers installed correctly', 'Verify circuit breaker installation', 'pass_fail', 1),
        (template_ids[1], 2, 'Wire gauge matches specifications', 'Check that the correct wire gauge is used', 'pass_fail', 1),
        (template_ids[1], 3, 'Ground connections complete', 'Verify all ground connections', 'pass_fail', 1),
        (template_ids[1], 4, 'Outlet voltage readings', 'Record voltage readings at all outlets', 'numeric', 1),
        (template_ids[1], 5, 'Upload testing documentation', 'Photos of testing equipment readings', 'photo', 1)
    ]
    
    cursor.executemany(
        "INSERT INTO checklist_items (template_id, sequence_number, title, description, item_type, required) VALUES (?, ?, ?, ?, ?, ?)",
        items_2
    )
    
    conn.commit()
    conn.close()

# Initialize and seed the database when the module is imported
init_database()
seed_sample_data()

# Helper functions for common database operations

def execute_query(query, params=(), fetchall=True):
    """Execute a database query with parameters and return results"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    result = None
    if fetchall:
        result = cursor.fetchall()
    else:
        result = cursor.fetchone()
    
    conn.close()
    return result

def execute_update(query, params=()):
    """Execute a database update query and return the number of affected rows"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return affected_rows

def get_last_insert_id():
    """Get the ID of the last inserted row"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_insert_rowid()")
    last_id = cursor.fetchone()[0]
    conn.close()
    return last_id

def log_audit(user_id, action, entity_type, entity_id, details=None):
    """Add an entry to the audit log"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO audit_log (user_id, action, entity_type, entity_id, action_details) VALUES (?, ?, ?, ?, ?)",
        (user_id, action, entity_type, entity_id, json.dumps(details) if details else None)
    )
    
    conn.commit()
    conn.close() 