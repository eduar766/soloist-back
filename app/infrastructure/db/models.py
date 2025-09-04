"""
SQLAlchemy models for the database.
Maps domain entities to database tables.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean, 
    Numeric, Date, ForeignKey, JSON, Enum as SQLEnum,
    Index, UniqueConstraint, CheckConstraint, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# Temporary simple enums for database creation
from enum import Enum

class ClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class PaymentTerms(str, Enum):
    NET_30 = "net_30"
    NET_15 = "net_15"
    NET_60 = "net_60"

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ProjectType(str, Enum):
    FIXED_PRICE = "fixed_price"
    TIME_AND_MATERIALS = "time_and_materials"
    RETAINER = "retainer"

class ProjectRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

class BillingType(str, Enum):
    HOURLY = "hourly"
    FIXED = "fixed"
    RETAINER = "retainer"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskType(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"

class TimeEntryStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVOICED = "invoiced"

class TimeEntryType(str, Enum):
    WORK = "work"
    MEETING = "meeting"
    BREAK = "break"

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class InvoiceType(str, Enum):
    STANDARD = "standard"
    RECURRING = "recurring"

class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    PARTIAL = "partial"

class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    CHECK = "check"
    CASH = "cash"

class ShareableType(str, Enum):
    PROJECT = "project"
    INVOICE = "invoice"

class ShareType(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class ShareStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

class UserRole(str, Enum):
    FREELANCER = "freelancer"
    CLIENT = "client"
    ADMIN = "admin"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

from .database import Base


# Association tables for many-to-many relationships
project_members = Table(
    'project_members',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('project_id', Integer, ForeignKey('projects.id'), nullable=False),
    Column('user_id', UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False),
    Column('role', SQLEnum(ProjectRole), nullable=False, default=ProjectRole.MEMBER),
    Column('hourly_rate', Numeric(10, 2)),
    Column('can_track_time', Boolean, default=True),
    Column('can_create_tasks', Boolean, default=True),
    Column('can_manage_members', Boolean, default=False),
    Column('joined_at', DateTime(timezone=True), server_default=func.now()),
    Column('is_active', Boolean, default=True),
    UniqueConstraint('project_id', 'user_id', name='unique_project_member')
)


class UserProfileModel(Base):
    """User profile table - extends Supabase auth.users"""
    __tablename__ = 'user_profiles'
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    phone = Column(String(50))
    role = Column(SQLEnum(UserRole), default=UserRole.FREELANCER)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    timezone = Column(String(50), default='UTC')
    language = Column(String(10), default='en')
    currency = Column(String(3), default='USD')
    
    # Billing information
    billing_name = Column(String(255))
    billing_email = Column(String(255))
    billing_address = Column(Text)
    billing_city = Column(String(100))
    billing_state = Column(String(100))
    billing_country = Column(String(100))
    billing_postal_code = Column(String(20))
    tax_id = Column(String(50))
    
    # Preferences
    preferences = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owned_clients = relationship("ClientModel", back_populates="owner")
    owned_projects = relationship("ProjectModel", back_populates="owner")
    time_entries = relationship("TimeEntryModel", back_populates="user")
    owned_invoices = relationship("InvoiceModel", back_populates="owner")
    owned_shares = relationship("ShareModel", back_populates="owner")
    task_assignments = relationship("TaskModel", foreign_keys="TaskModel.assignee_id", back_populates="assignee")
    created_tasks = relationship("TaskModel", foreign_keys="TaskModel.created_by", back_populates="creator")


class ClientModel(Base):
    """Client table"""
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(ClientStatus), default=ClientStatus.ACTIVE)
    
    # Contact information
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    mobile = Column(String(50))
    website = Column(String(500))
    
    # Address
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Business details
    tax_id = Column(String(50))
    company_type = Column(String(100))
    industry = Column(String(100))
    
    # Billing preferences
    default_currency = Column(String(3), default='USD')
    default_hourly_rate = Column(Numeric(10, 2))
    payment_terms = Column(SQLEnum(PaymentTerms), default=PaymentTerms.NET_30)
    custom_payment_terms = Column(String(255))
    
    # Metadata
    tags = Column(JSON)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True))
    
    # Relationships
    owner = relationship("UserProfileModel", back_populates="owned_clients")
    projects = relationship("ProjectModel", back_populates="client")
    invoices = relationship("InvoiceModel", back_populates="client")
    
    # Indexes
    __table_args__ = (
        Index('idx_clients_owner_name', 'owner_id', 'name'),
        Index('idx_clients_status', 'status'),
        UniqueConstraint('owner_id', 'name', name='unique_client_name_per_owner'),
    )


class ProjectModel(Base):
    """Project table"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    project_type = Column(SQLEnum(ProjectType), default=ProjectType.FIXED_PRICE)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING)
    
    # Dates
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Billing configuration
    billing_type = Column(SQLEnum(BillingType), default=BillingType.HOURLY)
    hourly_rate = Column(Numeric(10, 2))
    fixed_price = Column(Numeric(10, 2))
    budget_hours = Column(Numeric(8, 2))
    budget_amount = Column(Numeric(10, 2))
    auto_create_invoices = Column(Boolean, default=False)
    invoice_frequency = Column(String(20))  # weekly, monthly, etc.
    
    # Metadata
    tags = Column(JSON)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True))
    
    # Relationships
    owner = relationship("UserProfileModel", back_populates="owned_projects")
    client = relationship("ClientModel", back_populates="projects")
    tasks = relationship("TaskModel", back_populates="project")
    time_entries = relationship("TimeEntryModel", back_populates="project")
    invoices = relationship("InvoiceModel", back_populates="project")
    members = relationship("UserProfileModel", secondary=project_members, backref="member_projects")
    
    # Indexes
    __table_args__ = (
        Index('idx_projects_owner_client', 'owner_id', 'client_id'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_dates', 'start_date', 'end_date'),
    )


class TaskModel(Base):
    """Task table"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    parent_task_id = Column(Integer, ForeignKey('tasks.id'))
    created_by = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'))
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    task_type = Column(SQLEnum(TaskType), default=TaskType.FEATURE)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    
    # Time estimation
    estimated_hours = Column(Numeric(8, 2))
    actual_hours = Column(Numeric(8, 2))
    
    # Dates
    due_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Organization
    position = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSON)
    custom_fields = Column(JSON)
    blocked_reason = Column(Text)
    completion_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("ProjectModel", back_populates="tasks")
    creator = relationship("UserProfileModel", foreign_keys=[created_by], back_populates="created_tasks")
    assignee = relationship("UserProfileModel", foreign_keys=[assignee_id], back_populates="task_assignments")
    parent_task = relationship("TaskModel", remote_side=[id], backref="subtasks")
    time_entries = relationship("TimeEntryModel", back_populates="task")
    comments = relationship("TaskCommentModel", back_populates="task")
    attachments = relationship("TaskAttachmentModel", back_populates="task")
    
    # Indexes
    __table_args__ = (
        Index('idx_tasks_project_status', 'project_id', 'status'),
        Index('idx_tasks_assignee', 'assignee_id'),
        Index('idx_tasks_due_date', 'due_date'),
        Index('idx_tasks_position', 'project_id', 'position'),
    )


class TaskCommentModel(Base):
    """Task comment table"""
    __tablename__ = 'task_comments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    task = relationship("TaskModel", back_populates="comments")
    author = relationship("UserProfileModel")


class TaskAttachmentModel(Base):
    """Task attachment table"""
    __tablename__ = 'task_attachments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    description = Column(Text)
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("TaskModel", back_populates="attachments")
    uploader = relationship("UserProfileModel")


class TimeEntryModel(Base):
    """Time entry table"""
    __tablename__ = 'time_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    
    description = Column(Text)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_hours = Column(Numeric(8, 2))
    
    # Billing
    billable = Column(Boolean, default=True)
    hourly_rate = Column(Numeric(10, 2))
    total_amount = Column(Numeric(10, 2))
    
    # Type and status
    entry_type = Column(SQLEnum(TimeEntryType), default=TimeEntryType.WORK)
    status = Column(SQLEnum(TimeEntryStatus), default=TimeEntryStatus.DRAFT)
    
    # Approval workflow
    submitted_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'))
    approved_hours = Column(Numeric(8, 2))
    rejected_at = Column(DateTime(timezone=True))
    rejected_by = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'))
    rejection_reason = Column(Text)
    
    # Invoicing
    invoice_id = Column(Integer, ForeignKey('invoices.id'))
    invoiced_at = Column(DateTime(timezone=True))
    
    # Metadata
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("UserProfileModel", back_populates="time_entries", foreign_keys=[user_id])
    project = relationship("ProjectModel", back_populates="time_entries")
    task = relationship("TaskModel", back_populates="time_entries")
    approver = relationship("UserProfileModel", foreign_keys=[approved_by])
    rejector = relationship("UserProfileModel", foreign_keys=[rejected_by])
    invoice = relationship("InvoiceModel", back_populates="time_entries")
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_time_entries_user_project', 'user_id', 'project_id'),
        Index('idx_time_entries_date_range', 'started_at', 'ended_at'),
        Index('idx_time_entries_status', 'status'),
        Index('idx_time_entries_billable', 'billable'),
        CheckConstraint('started_at <= ended_at', name='time_entry_valid_range'),
        # Unique constraint for running timers (only one per user)
        Index('idx_time_entries_running', 'user_id', 'ended_at', 
              postgresql_where='ended_at IS NULL'),
    )


class InvoiceModel(Base):
    """Invoice table"""
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'))
    
    # Invoice details
    invoice_number = Column(String(50), nullable=False, unique=True)
    invoice_type = Column(SQLEnum(InvoiceType), default=InvoiceType.STANDARD)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.UNPAID)
    
    # Amounts and currency
    currency = Column(String(3), default='USD')
    subtotal = Column(Numeric(12, 2), default=0)
    discount_percentage = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    paid_amount = Column(Numeric(12, 2), default=0)
    
    # Dates
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date)
    sent_date = Column(DateTime(timezone=True))
    paid_date = Column(Date)
    
    # Content
    title = Column(String(255))
    description = Column(Text)
    notes = Column(Text)
    terms = Column(Text)
    
    # Addresses (JSON format)
    billing_address = Column(JSON)
    shipping_address = Column(JSON)
    
    # File storage
    pdf_url = Column(String(500))
    public_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("UserProfileModel", back_populates="owned_invoices")
    client = relationship("ClientModel", back_populates="invoices")
    project = relationship("ProjectModel", back_populates="invoices")
    line_items = relationship("InvoiceLineItemModel", back_populates="invoice", cascade="all, delete-orphan")
    tax_items = relationship("TaxLineItemModel", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("PaymentRecordModel", back_populates="invoice", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntryModel", back_populates="invoice")
    
    # Indexes
    __table_args__ = (
        Index('idx_invoices_owner_client', 'owner_id', 'client_id'),
        Index('idx_invoices_status', 'status'),
        Index('idx_invoices_payment_status', 'payment_status'),
        Index('idx_invoices_dates', 'issue_date', 'due_date'),
        Index('idx_invoices_number', 'invoice_number'),
    )


class InvoiceLineItemModel(Base):
    """Invoice line item table"""
    __tablename__ = 'invoice_line_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(10, 3), default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_percentage = Column(Numeric(5, 2), default=0)
    tax_rate = Column(Numeric(5, 2), default=0)
    item_type = Column(String(50))  # time, expense, product, etc.
    
    # Calculated fields (could be computed)
    subtotal = Column(Numeric(12, 2))
    tax_amount = Column(Numeric(12, 2))
    total = Column(Numeric(12, 2))
    
    # Position for ordering
    position = Column(Integer, default=0)
    
    # Relationships
    invoice = relationship("InvoiceModel", back_populates="line_items")


class TaxLineItemModel(Base):
    """Tax line item table"""
    __tablename__ = 'tax_line_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    name = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 2), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    invoice = relationship("InvoiceModel", back_populates="tax_items")


class PaymentRecordModel(Base):
    """Payment record table"""
    __tablename__ = 'payment_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    reference = Column(String(255))
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    invoice = relationship("InvoiceModel", back_populates="payments")


class ShareModel(Base):
    """Share table for sharing resources"""
    __tablename__ = 'shares'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=False)
    resource_type = Column(SQLEnum(ShareableType), nullable=False)
    resource_id = Column(Integer, nullable=False)
    share_type = Column(SQLEnum(ShareType), default=ShareType.PUBLIC)
    status = Column(SQLEnum(ShareStatus), default=ShareStatus.ACTIVE)
    
    # Share configuration
    share_token = Column(String(255), unique=True, nullable=False)
    share_url = Column(String(500))
    title = Column(String(255))
    description = Column(Text)
    custom_message = Column(Text)
    
    # Access control
    expires_at = Column(DateTime(timezone=True))
    max_access_count = Column(Integer)
    access_count = Column(Integer, default=0)
    password_hash = Column(String(255))
    require_email = Column(Boolean, default=False)
    allow_anonymous = Column(Boolean, default=True)
    
    # Permissions (JSON)
    permissions = Column(JSON)
    
    # Revocation
    revoked_at = Column(DateTime(timezone=True))
    revoke_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed = Column(DateTime(timezone=True))
    
    # Relationships
    owner = relationship("UserProfileModel", back_populates="owned_shares")
    access_logs = relationship("ShareAccessLogModel", back_populates="share", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_shares_owner', 'owner_id'),
        Index('idx_shares_resource', 'resource_type', 'resource_id'),
        Index('idx_shares_token', 'share_token'),
        Index('idx_shares_status', 'status'),
        Index('idx_shares_expires', 'expires_at'),
    )


class ShareAccessLogModel(Base):
    """Share access log table"""
    __tablename__ = 'share_access_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    share_id = Column(Integer, ForeignKey('shares.id'), nullable=False)
    accessor_email = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional metadata (JSON)
    extra_data = Column(JSON)  # location, device info, etc.
    
    # Relationships
    share = relationship("ShareModel", back_populates="access_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_share_access_logs_share', 'share_id'),
        Index('idx_share_access_logs_date', 'accessed_at'),
    )


# Create tables if they don't exist (for development)
def create_all_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)