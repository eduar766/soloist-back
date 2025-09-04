"""
Infrastructure layer for the Soloist freelancer management system.

This layer contains the implementation details for external systems integration:
- Database (SQLAlchemy with PostgreSQL)
- Authentication (Supabase Auth)
- File Storage (Supabase Storage)
- Email services
- External APIs

The infrastructure layer implements interfaces defined in the domain layer,
following the Dependency Inversion Principle of Clean Architecture.
"""