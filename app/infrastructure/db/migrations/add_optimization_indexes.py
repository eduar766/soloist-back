"""
Database optimization indexes migration.
Adds additional indexes for common query patterns and performance optimization.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index, text

# Migration timestamp
revision = 'add_optimization_indexes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add optimization indexes."""
    
    # User profile optimizations
    with op.batch_alter_table('user_profiles') as batch_op:
        # Index for role-based queries
        batch_op.create_index('idx_user_profiles_role_status', ['role', 'status'])
        # Index for timezone-based queries
        batch_op.create_index('idx_user_profiles_timezone', ['timezone'])
        # Index for currency-based queries
        batch_op.create_index('idx_user_profiles_currency', ['currency'])
    
    # Client optimizations
    with op.batch_alter_table('clients') as batch_op:
        # Index for email searches
        batch_op.create_index('idx_clients_email', ['email'])
        # Index for company type filtering
        batch_op.create_index('idx_clients_company_type', ['company_type'])
        # Index for industry filtering
        batch_op.create_index('idx_clients_industry', ['industry'])
        # Index for archived clients
        batch_op.create_index('idx_clients_archived', ['archived_at'])
        # Partial index for active clients only
        batch_op.create_index('idx_clients_active_status', ['owner_id', 'status'],
                             postgresql_where="status = 'active'")
    
    # Project optimizations
    with op.batch_alter_table('projects') as batch_op:
        # Index for billing type queries
        batch_op.create_index('idx_projects_billing_type', ['billing_type'])
        # Index for project type filtering
        batch_op.create_index('idx_projects_project_type', ['project_type'])
        # Index for archived projects
        batch_op.create_index('idx_projects_archived', ['archived_at'])
        # Composite index for date range queries
        batch_op.create_index('idx_projects_owner_status_dates', 
                             ['owner_id', 'status', 'start_date', 'end_date'])
    
    # Task optimizations
    with op.batch_alter_table('tasks') as batch_op:
        # Index for priority-based queries
        batch_op.create_index('idx_tasks_priority', ['priority'])
        # Index for task type filtering
        batch_op.create_index('idx_tasks_type', ['task_type'])
        # Index for completion tracking
        batch_op.create_index('idx_tasks_completed', ['completed_at'])
        # Index for creator-based queries
        batch_op.create_index('idx_tasks_creator', ['created_by'])
        # Composite index for overdue tasks
        batch_op.create_index('idx_tasks_overdue', ['project_id', 'status', 'due_date'])
    
    # Time entry optimizations
    with op.batch_alter_table('time_entries') as batch_op:
        # Index for invoice-related queries
        batch_op.create_index('idx_time_entries_invoice', ['invoice_id'])
        # Index for approval workflow
        batch_op.create_index('idx_time_entries_approval', ['approved_by', 'approved_at'])
        # Index for billing calculations
        batch_op.create_index('idx_time_entries_billing', ['billable', 'hourly_rate'])
        # Index for time tracking reports
        batch_op.create_index('idx_time_entries_reporting', 
                             ['user_id', 'project_id', 'started_at', 'billable'])
    
    # Invoice optimizations
    with op.batch_alter_table('invoices') as batch_op:
        # Index for invoice number searches
        batch_op.create_index('idx_invoices_number', ['invoice_number'])
        # Index for payment tracking
        batch_op.create_index('idx_invoices_payment_status', ['payment_status'])
        # Index for overdue invoices
        batch_op.create_index('idx_invoices_overdue', ['due_date', 'payment_status'])
        # Index for date range queries
        batch_op.create_index('idx_invoices_date_range', ['issue_date', 'due_date'])
        # Index for financial reporting
        batch_op.create_index('idx_invoices_financial', 
                             ['owner_id', 'status', 'issue_date', 'total_amount'])
    
    # Task comments optimization
    with op.batch_alter_table('task_comments') as batch_op:
        # Index for task-based comment retrieval
        batch_op.create_index('idx_task_comments_task_date', ['task_id', 'created_at'])
        # Index for author-based queries
        batch_op.create_index('idx_task_comments_author', ['author_id', 'created_at'])
    
    # Task attachments optimization
    with op.batch_alter_table('task_attachments') as batch_op:
        # Index for file type filtering
        batch_op.create_index('idx_task_attachments_mime', ['mime_type'])
        # Index for upload tracking
        batch_op.create_index('idx_task_attachments_uploader', ['uploaded_by', 'uploaded_at'])
    
    print("✅ Optimization indexes created successfully")


def downgrade():
    """Remove optimization indexes."""
    
    # Remove user profile indexes
    with op.batch_alter_table('user_profiles') as batch_op:
        batch_op.drop_index('idx_user_profiles_role_status')
        batch_op.drop_index('idx_user_profiles_timezone')
        batch_op.drop_index('idx_user_profiles_currency')
    
    # Remove client indexes
    with op.batch_alter_table('clients') as batch_op:
        batch_op.drop_index('idx_clients_email')
        batch_op.drop_index('idx_clients_company_type')
        batch_op.drop_index('idx_clients_industry')
        batch_op.drop_index('idx_clients_archived')
        batch_op.drop_index('idx_clients_active_status')
    
    # Remove project indexes
    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_index('idx_projects_billing_type')
        batch_op.drop_index('idx_projects_project_type')
        batch_op.drop_index('idx_projects_archived')
        batch_op.drop_index('idx_projects_owner_status_dates')
    
    # Remove task indexes
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.drop_index('idx_tasks_priority')
        batch_op.drop_index('idx_tasks_type')
        batch_op.drop_index('idx_tasks_completed')
        batch_op.drop_index('idx_tasks_creator')
        batch_op.drop_index('idx_tasks_overdue')
    
    # Remove time entry indexes
    with op.batch_alter_table('time_entries') as batch_op:
        batch_op.drop_index('idx_time_entries_invoice')
        batch_op.drop_index('idx_time_entries_approval')
        batch_op.drop_index('idx_time_entries_billing')
        batch_op.drop_index('idx_time_entries_reporting')
    
    # Remove invoice indexes
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.drop_index('idx_invoices_number')
        batch_op.drop_index('idx_invoices_payment_status')
        batch_op.drop_index('idx_invoices_overdue')
        batch_op.drop_index('idx_invoices_date_range')
        batch_op.drop_index('idx_invoices_financial')
    
    # Remove task comments indexes
    with op.batch_alter_table('task_comments') as batch_op:
        batch_op.drop_index('idx_task_comments_task_date')
        batch_op.drop_index('idx_task_comments_author')
    
    # Remove task attachments indexes
    with op.batch_alter_table('task_attachments') as batch_op:
        batch_op.drop_index('idx_task_attachments_mime')
        batch_op.drop_index('idx_task_attachments_uploader')
    
    print("✅ Optimization indexes removed successfully")