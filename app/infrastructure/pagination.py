"""
Efficient pagination utilities for SQLAlchemy queries.
Implements cursor-based and offset-based pagination with performance optimizations.
"""

from typing import Generic, TypeVar, List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from math import ceil
from sqlalchemy.orm import Query
from sqlalchemy import asc, desc, and_, or_, text
from pydantic import BaseModel, Field

T = TypeVar('T')


@dataclass
class PaginationMetadata:
    """Pagination metadata for responses."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    items: List[T]
    metadata: PaginationMetadata
    
    class Config:
        arbitrary_types_allowed = True


class CursorPagination:
    """
    Cursor-based pagination for better performance on large datasets.
    Uses a cursor (typically an ID or timestamp) to paginate through results.
    """
    
    def __init__(self, cursor_column: str = "id", page_size: int = 50):
        self.cursor_column = cursor_column
        self.page_size = page_size
    
    def paginate(
        self,
        query: Query,
        cursor: Optional[str] = None,
        direction: str = "next",
        order_desc: bool = True
    ) -> Tuple[List[Any], Optional[str], Optional[str]]:
        """
        Paginate query using cursor-based pagination.
        
        Args:
            query: SQLAlchemy query to paginate
            cursor: Current cursor position
            direction: "next" or "previous"
            order_desc: Whether to order in descending order
            
        Returns:
            Tuple of (items, next_cursor, previous_cursor)
        """
        # Get the cursor column from the query
        model = query.column_descriptions[0]['type']
        cursor_col = getattr(model, self.cursor_column)
        
        # Apply ordering
        if order_desc:
            query = query.order_by(desc(cursor_col))
        else:
            query = query.order_by(asc(cursor_col))
        
        # Apply cursor filter
        if cursor:
            try:
                cursor_value = int(cursor) if cursor.isdigit() else cursor
                if direction == "next":
                    if order_desc:
                        query = query.filter(cursor_col < cursor_value)
                    else:
                        query = query.filter(cursor_col > cursor_value)
                elif direction == "previous":
                    if order_desc:
                        query = query.filter(cursor_col > cursor_value)
                    else:
                        query = query.filter(cursor_col < cursor_value)
            except (ValueError, TypeError):
                # Invalid cursor, ignore
                pass
        
        # Get one extra item to check if there are more results
        items = query.limit(self.page_size + 1).all()
        
        has_more = len(items) > self.page_size
        if has_more:
            items = items[:-1]  # Remove the extra item
        
        # Determine cursors
        next_cursor = None
        previous_cursor = None
        
        if items:
            if direction == "previous":
                items.reverse()  # Reverse for previous pagination
            
            if has_more and direction == "next":
                next_cursor = str(getattr(items[-1], self.cursor_column))
            
            if cursor and direction == "next":
                previous_cursor = str(getattr(items[0], self.cursor_column))
            elif cursor and direction == "previous" and has_more:
                next_cursor = str(getattr(items[-1], self.cursor_column))
        
        return items, next_cursor, previous_cursor


class OffsetPagination:
    """
    Traditional offset-based pagination with optimizations.
    Better for smaller datasets where total count is needed.
    """
    
    def __init__(self, default_page_size: int = 50, max_page_size: int = 100):
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size
    
    def paginate(
        self,
        query: Query,
        page: int = 1,
        page_size: Optional[int] = None,
        count_query: Optional[Query] = None
    ) -> Tuple[List[Any], PaginationMetadata]:
        """
        Paginate query using offset-based pagination.
        
        Args:
            query: SQLAlchemy query to paginate
            page: Page number (1-based)
            page_size: Number of items per page
            count_query: Optional optimized count query
            
        Returns:
            Tuple of (items, pagination_metadata)
        """
        # Validate and set page size
        if page_size is None:
            page_size = self.default_page_size
        page_size = min(page_size, self.max_page_size)
        
        # Validate page number
        page = max(1, page)
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get total count (use optimized count query if provided)
        if count_query is not None:
            total_items = count_query.scalar()
        else:
            # Use optimized count query
            total_items = query.order_by(None).count()
        
        # Calculate pagination metadata
        total_pages = ceil(total_items / page_size) if page_size > 0 else 0
        has_next = page < total_pages
        has_previous = page > 1
        
        # Get paginated items
        items = query.offset(offset).limit(page_size).all()
        
        metadata = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
        return items, metadata


class SmartPagination:
    """
    Smart pagination that chooses the best strategy based on dataset characteristics.
    """
    
    def __init__(
        self,
        cursor_threshold: int = 1000,  # Use cursor pagination for large datasets
        default_page_size: int = 50,
        max_page_size: int = 100
    ):
        self.cursor_threshold = cursor_threshold
        self.offset_paginator = OffsetPagination(default_page_size, max_page_size)
        self.cursor_paginator = CursorPagination(page_size=default_page_size)
    
    def paginate(
        self,
        query: Query,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        cursor: Optional[str] = None,
        direction: str = "next",
        force_cursor: bool = False
    ) -> Dict[str, Any]:
        """
        Smart pagination that automatically chooses the best strategy.
        
        Args:
            query: SQLAlchemy query to paginate
            page: Page number for offset pagination
            page_size: Items per page
            cursor: Cursor for cursor-based pagination
            direction: Direction for cursor pagination
            force_cursor: Force cursor-based pagination
            
        Returns:
            Dictionary with paginated results and metadata
        """
        # Determine pagination strategy
        use_cursor = force_cursor or cursor is not None
        
        if not use_cursor and page is not None:
            # Use offset pagination
            items, metadata = self.offset_paginator.paginate(
                query, page, page_size
            )
            return {
                "items": items,
                "pagination": {
                    "type": "offset",
                    "page": metadata.page,
                    "page_size": metadata.page_size,
                    "total_items": metadata.total_items,
                    "total_pages": metadata.total_pages,
                    "has_next": metadata.has_next,
                    "has_previous": metadata.has_previous
                }
            }
        else:
            # Use cursor pagination
            items, next_cursor, previous_cursor = self.cursor_paginator.paginate(
                query, cursor, direction
            )
            return {
                "items": items,
                "pagination": {
                    "type": "cursor",
                    "cursor": cursor,
                    "next_cursor": next_cursor,
                    "previous_cursor": previous_cursor,
                    "page_size": self.cursor_paginator.page_size,
                    "has_next": next_cursor is not None,
                    "has_previous": previous_cursor is not None
                }
            }


class PaginationHelper:
    """Helper class with utility methods for pagination."""
    
    @staticmethod
    def optimize_count_query(query: Query) -> Query:
        """
        Optimize count query by removing unnecessary joins and selections.
        """
        # Remove ORDER BY clause for count
        count_query = query.order_by(None)
        
        # Use subquery for complex queries with joins
        if hasattr(count_query, 'statement') and len(count_query.statement.froms) > 1:
            # Create a subquery and count from it
            subquery = count_query.subquery()
            return query.session.query(subquery).count()
        
        return count_query
    
    @staticmethod
    def create_search_pagination(
        base_query: Query,
        search_term: Optional[str] = None,
        search_fields: List[str] = None,
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Create paginated search results with filters.
        
        Args:
            base_query: Base query to search within
            search_term: Search term to filter by
            search_fields: List of field names to search in
            filters: Additional filters to apply
            page: Page number
            page_size: Items per page
            
        Returns:
            Paginated search results
        """
        query = base_query
        
        # Apply search term
        if search_term and search_fields:
            model = query.column_descriptions[0]['type']
            search_conditions = []
            for field_name in search_fields:
                if hasattr(model, field_name):
                    field = getattr(model, field_name)
                    search_conditions.append(
                        field.ilike(f"%{search_term}%")
                    )
            
            if search_conditions:
                query = query.filter(or_(*search_conditions))
        
        # Apply additional filters
        if filters:
            model = query.column_descriptions[0]['type']
            for field_name, value in filters.items():
                if hasattr(model, field_name) and value is not None:
                    field = getattr(model, field_name)
                    if isinstance(value, list):
                        query = query.filter(field.in_(value))
                    else:
                        query = query.filter(field == value)
        
        # Apply pagination
        paginator = OffsetPagination()
        items, metadata = paginator.paginate(query, page, page_size)
        
        return {
            "items": items,
            "metadata": metadata,
            "search": {
                "term": search_term,
                "fields": search_fields,
                "filters": filters
            }
        }
    
    @staticmethod
    def get_pagination_links(
        base_url: str,
        current_page: int,
        total_pages: int,
        page_size: int,
        **query_params
    ) -> Dict[str, Optional[str]]:
        """
        Generate pagination links for API responses.
        
        Returns:
            Dictionary with pagination links
        """
        def build_url(page: int) -> str:
            params = {"page": page, "page_size": page_size, **query_params}
            param_string = "&".join(f"{k}={v}" for k, v in params.items())
            return f"{base_url}?{param_string}"
        
        links = {
            "self": build_url(current_page),
            "first": build_url(1) if total_pages > 0 else None,
            "last": build_url(total_pages) if total_pages > 0 else None,
            "next": build_url(current_page + 1) if current_page < total_pages else None,
            "previous": build_url(current_page - 1) if current_page > 1 else None
        }
        
        return links


# Global pagination instances
smart_paginator = SmartPagination()
offset_paginator = OffsetPagination()
cursor_paginator = CursorPagination()


# Pagination parameters for FastAPI
class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")
    cursor: Optional[str] = Field(None, description="Cursor for cursor-based pagination")
    direction: str = Field("next", description="Pagination direction")


class SearchParams(BaseModel):
    """Common search parameters."""
    search: Optional[str] = Field(None, description="Search term")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    
    class Config:
        extra = "allow"  # Allow additional filter parameters