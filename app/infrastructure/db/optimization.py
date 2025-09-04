"""
Database optimization utilities and configuration.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database optimization utilities."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def analyze_table_performance(self, table_name: str) -> Dict[str, Any]:
        """Analyze table performance statistics."""
        with self.engine.connect() as conn:
            # Get table size
            size_query = text("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size(:table_name)) as total_size,
                    pg_size_pretty(pg_relation_size(:table_name)) as table_size,
                    pg_size_pretty(pg_total_relation_size(:table_name) - pg_relation_size(:table_name)) as indexes_size
            """)
            size_result = conn.execute(size_query, {"table_name": table_name}).fetchone()
            
            # Get row count
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            count_result = conn.execute(count_query).fetchone()
            
            # Get index usage
            index_query = text("""
                SELECT 
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE relname = :table_name
                ORDER BY idx_tup_read DESC
            """)
            index_results = conn.execute(index_query, {"table_name": table_name}).fetchall()
            
            return {
                "table_name": table_name,
                "total_size": size_result[0] if size_result else "Unknown",
                "table_size": size_result[1] if size_result else "Unknown",
                "indexes_size": size_result[2] if size_result else "Unknown",
                "row_count": count_result[0] if count_result else 0,
                "indexes": [
                    {
                        "name": idx.indexname,
                        "reads": idx.idx_tup_read,
                        "fetches": idx.idx_tup_fetch
                    }
                    for idx in index_results
                ]
            }
    
    def get_slow_queries(self, min_duration_ms: int = 1000) -> List[Dict[str, Any]]:
        """Get slow queries from pg_stat_statements (if available)."""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements
                    WHERE mean_exec_time > :min_duration
                    ORDER BY mean_exec_time DESC
                    LIMIT 20
                """)
                results = conn.execute(query, {"min_duration": min_duration_ms}).fetchall()
                
                return [
                    {
                        "query": result.query,
                        "calls": result.calls,
                        "total_time": result.total_exec_time,
                        "avg_time": result.mean_exec_time,
                        "rows": result.rows,
                        "hit_percent": result.hit_percent
                    }
                    for result in results
                ]
        except Exception as e:
            logger.warning(f"Could not retrieve slow queries: {e}")
            return []
    
    def vacuum_analyze_table(self, table_name: str) -> bool:
        """Run VACUUM ANALYZE on a specific table."""
        try:
            with self.engine.connect() as conn:
                # Use autocommit mode for VACUUM
                conn = conn.execution_options(autocommit=True)
                conn.execute(text(f"VACUUM ANALYZE {table_name}"))
                logger.info(f"VACUUM ANALYZE completed for table: {table_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to VACUUM ANALYZE table {table_name}: {e}")
            return False
    
    def update_table_statistics(self, table_name: str) -> bool:
        """Update table statistics for query planner."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"ANALYZE {table_name}"))
                logger.info(f"Statistics updated for table: {table_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to update statistics for table {table_name}: {e}")
            return False
    
    def check_index_usage(self) -> List[Dict[str, Any]]:
        """Check which indexes are not being used."""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE idx_tup_read = 0 AND idx_tup_fetch = 0
                    ORDER BY schemaname, tablename, indexname
                """)
                results = conn.execute(query).fetchall()
                
                return [
                    {
                        "schema": result.schemaname,
                        "table": result.tablename,
                        "index": result.indexname,
                        "reads": result.idx_tup_read,
                        "fetches": result.idx_tup_fetch
                    }
                    for result in results
                ]
        except Exception as e:
            logger.warning(f"Could not check index usage: {e}")
            return []


# Query optimization helpers
def optimize_pagination_query(base_query, page: int = 1, page_size: int = 50, 
                              order_by_column: str = "id"):
    """
    Optimize pagination using cursor-based pagination for better performance.
    """
    offset = (page - 1) * page_size
    
    # Add ordering and limit
    optimized_query = base_query.order_by(order_by_column).limit(page_size)
    
    # Add offset only if not on first page
    if offset > 0:
        optimized_query = optimized_query.offset(offset)
    
    return optimized_query


def add_query_hints(query, hints: List[str]):
    """Add PostgreSQL query hints for optimization."""
    # This is more relevant for other databases, PostgreSQL uses different approaches
    # but we can add query structure optimizations
    return query


# Connection pool optimization settings
DATABASE_POOL_SETTINGS = {
    "pool_size": 10,  # Number of connections to maintain in pool
    "max_overflow": 20,  # Additional connections beyond pool_size
    "pool_timeout": 30,  # Seconds to wait for connection
    "pool_recycle": 3600,  # Seconds to recycle connections (1 hour)
    "pool_pre_ping": True,  # Verify connections before use
}

# PostgreSQL-specific optimization settings
POSTGRESQL_OPTIMIZATION_SETTINGS = {
    "shared_buffers": "256MB",  # PostgreSQL shared memory
    "effective_cache_size": "4GB",  # Available memory for caching
    "maintenance_work_mem": "64MB",  # Memory for maintenance operations
    "checkpoint_completion_target": "0.9",  # Checkpoint completion target
    "wal_buffers": "16MB",  # WAL buffer size
    "default_statistics_target": "100",  # Statistics target for query planner
    "random_page_cost": "1.1",  # Cost of random page access (for SSDs)
}

# Commonly used query patterns for optimization
COMMON_QUERY_PATTERNS = {
    "user_projects": """
        SELECT p.* FROM projects p 
        WHERE p.owner_id = %s 
        ORDER BY p.updated_at DESC 
        LIMIT %s OFFSET %s
    """,
    
    "project_time_entries": """
        SELECT te.* FROM time_entries te 
        WHERE te.project_id = %s 
        AND te.started_at >= %s 
        AND te.started_at < %s 
        ORDER BY te.started_at DESC
    """,
    
    "client_active_projects": """
        SELECT p.* FROM projects p 
        WHERE p.client_id = %s 
        AND p.status IN ('active', 'planning') 
        ORDER BY p.start_date DESC
    """,
    
    "overdue_tasks": """
        SELECT t.* FROM tasks t 
        WHERE t.project_id = %s 
        AND t.due_date < CURRENT_DATE 
        AND t.status != 'completed' 
        ORDER BY t.due_date ASC
    """
}


def log_query_performance(session: Session, query_name: str, 
                         execution_time: float, row_count: int):
    """Log query performance metrics."""
    if execution_time > 1.0:  # Log slow queries (> 1 second)
        logger.warning(
            f"Slow query detected: {query_name} - "
            f"Execution time: {execution_time:.2f}s, Rows: {row_count}"
        )
    elif execution_time > 0.1:  # Log moderate queries (> 100ms)
        logger.info(
            f"Query performance: {query_name} - "
            f"Execution time: {execution_time:.2f}s, Rows: {row_count}"
        )