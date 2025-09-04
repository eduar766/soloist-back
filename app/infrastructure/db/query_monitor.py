"""
Query performance monitoring to detect and prevent N+1 queries.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QueryMonitor:
    """Monitor database queries to detect N+1 query patterns."""
    
    def __init__(self):
        self.queries: List[Dict[str, Any]] = []
        self.session_queries: Dict[str, List[Dict[str, Any]]] = {}
        self.monitoring_enabled = False
        self.n_plus_one_threshold = 5  # Alert if > 5 similar queries in one request
    
    def start_monitoring(self):
        """Start query monitoring."""
        self.monitoring_enabled = True
        self.queries = []
        logger.info("Query monitoring started")
    
    def stop_monitoring(self):
        """Stop query monitoring."""
        self.monitoring_enabled = False
        logger.info("Query monitoring stopped")
    
    def record_query(self, query: str, parameters: Dict[str, Any], execution_time: float, 
                     session_id: Optional[str] = None):
        """Record a database query."""
        if not self.monitoring_enabled:
            return
        
        query_record = {
            'query': self._normalize_query(query),
            'raw_query': query,
            'parameters': parameters,
            'execution_time': execution_time,
            'timestamp': time.time(),
            'session_id': session_id
        }
        
        self.queries.append(query_record)
        
        if session_id:
            if session_id not in self.session_queries:
                self.session_queries[session_id] = []
            self.session_queries[session_id].append(query_record)
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing parameters to detect similar patterns."""
        import re
        # Replace parameter placeholders with generic placeholder
        normalized = re.sub(r'%\([^)]+\)s', '?', query)
        normalized = re.sub(r'\$\d+', '?', normalized)
        normalized = re.sub(r'\?', 'PARAM', normalized)
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def detect_n_plus_one(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Detect potential N+1 query patterns."""
        queries_to_check = self.queries
        if session_id and session_id in self.session_queries:
            queries_to_check = self.session_queries[session_id]
        
        # Group queries by normalized pattern
        query_patterns = {}
        for query in queries_to_check:
            pattern = query['query']
            if pattern not in query_patterns:
                query_patterns[pattern] = []
            query_patterns[pattern].append(query)
        
        # Find patterns that repeat more than threshold
        n_plus_one_issues = []
        for pattern, queries in query_patterns.items():
            if len(queries) > self.n_plus_one_threshold:
                total_time = sum(q['execution_time'] for q in queries)
                n_plus_one_issues.append({
                    'pattern': pattern,
                    'count': len(queries),
                    'total_time': total_time,
                    'avg_time': total_time / len(queries),
                    'sample_query': queries[0]['raw_query'],
                    'queries': queries
                })
        
        return n_plus_one_issues
    
    def get_slow_queries(self, min_time: float = 0.1) -> List[Dict[str, Any]]:
        """Get queries that took longer than specified time."""
        return [q for q in self.queries if q['execution_time'] > min_time]
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of queries for a session."""
        if session_id not in self.session_queries:
            return {}
        
        queries = self.session_queries[session_id]
        total_time = sum(q['execution_time'] for q in queries)
        
        return {
            'session_id': session_id,
            'query_count': len(queries),
            'total_time': total_time,
            'avg_time': total_time / len(queries) if queries else 0,
            'slow_queries': [q for q in queries if q['execution_time'] > 0.1],
            'n_plus_one_issues': self.detect_n_plus_one(session_id)
        }
    
    def clear_session(self, session_id: str):
        """Clear queries for a specific session."""
        if session_id in self.session_queries:
            del self.session_queries[session_id]


# Global monitor instance
query_monitor = QueryMonitor()


@contextmanager
def monitor_session_queries(session_id: str):
    """Context manager to monitor queries for a specific session."""
    query_monitor.start_monitoring()
    try:
        yield query_monitor
        # Report findings
        summary = query_monitor.get_session_summary(session_id)
        
        if summary.get('n_plus_one_issues'):
            logger.warning(f"N+1 query detected in session {session_id}: {len(summary['n_plus_one_issues'])} issues")
            for issue in summary['n_plus_one_issues']:
                logger.warning(f"Pattern repeated {issue['count']} times: {issue['pattern'][:100]}...")
        
        if summary.get('slow_queries'):
            logger.info(f"Slow queries in session {session_id}: {len(summary['slow_queries'])} queries > 100ms")
    
    finally:
        query_monitor.clear_session(session_id)


def setup_query_monitoring(engine: Engine):
    """Set up SQLAlchemy event listeners for query monitoring."""
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if not query_monitor.monitoring_enabled:
            return
        
        total_time = time.time() - context._query_start_time
        
        # Get session ID if available
        session_id = getattr(context, 'session_id', None)
        
        query_monitor.record_query(
            query=statement,
            parameters=parameters if not executemany else {'executemany': True},
            execution_time=total_time,
            session_id=session_id
        )


class QueryOptimizationRecommendations:
    """Provide recommendations for query optimization."""
    
    @staticmethod
    def analyze_n_plus_one(issue: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze N+1 issue and provide recommendations."""
        pattern = issue['pattern']
        count = issue['count']
        
        recommendations = []
        
        if 'SELECT' in pattern and 'WHERE' in pattern:
            if 'client' in pattern.lower():
                recommendations.append("Consider using joinedload(ClientModel.projects) or joinedload(ClientModel.invoices)")
            elif 'project' in pattern.lower():
                recommendations.append("Consider using joinedload(ProjectModel.client) or joinedload(ProjectModel.tasks)")
            elif 'task' in pattern.lower():
                recommendations.append("Consider using joinedload(TaskModel.project) or joinedload(TaskModel.assignee)")
            elif 'time_entry' in pattern.lower():
                recommendations.append("Consider using joinedload(TimeEntryModel.project) and joinedload(TimeEntryModel.task)")
        
        if count > 10:
            recommendations.append("Consider implementing cursor-based pagination to reduce query load")
        
        if count > 20:
            recommendations.append("Consider caching this query result with Redis")
        
        return {
            'issue': issue,
            'recommendations': recommendations,
            'estimated_savings': f"Could reduce {count} queries to 1-2 queries",
            'performance_impact': 'HIGH' if count > 15 else 'MEDIUM'
        }
    
    @staticmethod
    def suggest_eager_loading(query_pattern: str) -> List[str]:
        """Suggest eager loading strategies based on query pattern."""
        suggestions = []
        
        if 'clients' in query_pattern.lower():
            suggestions.extend([
                "Use .options(joinedload(ClientModel.projects))",
                "Use .options(joinedload(ClientModel.invoices))",
                "Consider selectinload() for large collections"
            ])
        
        if 'projects' in query_pattern.lower():
            suggestions.extend([
                "Use .options(joinedload(ProjectModel.client))",
                "Use .options(joinedload(ProjectModel.tasks))",
                "Use .options(joinedload(ProjectModel.time_entries))"
            ])
        
        if 'tasks' in query_pattern.lower():
            suggestions.extend([
                "Use .options(joinedload(TaskModel.project))",
                "Use .options(joinedload(TaskModel.assignee))",
                "Use .options(joinedload(TaskModel.time_entries))"
            ])
        
        return suggestions


# Utility function to run optimization analysis
def analyze_query_performance(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Analyze query performance and provide optimization recommendations."""
    n_plus_one_issues = query_monitor.detect_n_plus_one(session_id)
    slow_queries = query_monitor.get_slow_queries()
    
    analysis = {
        'n_plus_one_issues': len(n_plus_one_issues),
        'slow_queries': len(slow_queries),
        'recommendations': []
    }
    
    for issue in n_plus_one_issues:
        recommendation = QueryOptimizationRecommendations.analyze_n_plus_one(issue)
        analysis['recommendations'].append(recommendation)
    
    return analysis