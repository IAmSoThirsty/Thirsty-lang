"""
Thirsty-Lang Standard Library: Database - SQL Interface
Universal database abstraction layer

Provides:
- Connection: Database connection management
- Query: SQL query builder
- Transaction: Transaction support
- Result: Query result handling
"""

from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod


class DatabaseResult:
    """Query result wrapper"""
    
    def __init__(self, rows: List[Tuple], columns: Optional[List[str]] = None):
        self.rows = rows
        self.columns = columns or []
        self._index = 0
    
    def fetchone(self) -> Optional[Tuple]:
        """Fetch single row"""
        if self._index < len(self.rows):
            row = self.rows[self._index]
            self._index += 1
            return row
        return None
    
    def fetchall(self) -> List[Tuple]:
        """Fetch all rows"""
        return self.rows
    
    def fetchmany(self, size: int) -> List[Tuple]:
        """Fetch multiple rows"""
        result = self.rows[self._index:self._index + size]
        self._index += size
        return result
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert rows to list of dictionaries"""
        if not self.columns:
            return []
        return [dict(zip(self.columns, row)) for row in self.rows]
    
    @property
    def rowcount(self) -> int:
        """Number of rows"""
        return len(self.rows)


class DatabaseConnection(ABC):
    """Abstract database connection"""
    
    @abstractmethod
    def execute(self, query: str, params: Optional[Tuple] = None) -> DatabaseResult:
        """Execute SQL query"""
        pass
    
    @abstractmethod
    def commit(self):
        """Commit transaction"""
        pass
    
    @abstractmethod
    def rollback(self):
        """Rollback transaction"""
        pass
    
    @abstractmethod
    def close(self):
        """Close connection"""
        pass


class QueryBuilder:
    """SQL query builder"""
    
    def __init__(self, table: str):
        self.table = table
        self._select_cols = []
        self._where_clauses = []
        self._order_by = []
        self._limit_val = None
        self._offset_val = None
    
    def select(self, *columns):
        """Select columns"""
        self._select_cols.extend(columns)
        return self
    
    def where(self, condition: str):
        """Add WHERE clause"""
        self._where_clauses.append(condition)
        return self
    
    def order_by(self, column: str, direction='ASC'):
        """Add ORDER BY"""
        self._order_by.append(f"{column} {direction}")
        return self
    
    def limit(self, count: int):
        """Add LIMIT"""
        self._limit_val = count
        return self
    
    def offset(self, count: int):
        """Add OFFSET"""
        self._offset_val = count
        return self
    
    def build(self) -> str:
        """Build SQL query"""
        # SELECT
        cols = ', '.join(self._select_cols) if self._select_cols else '*'
        query = f"SELECT {cols} FROM {self.table}"
        
        # WHERE
        if self._where_clauses:
            query += " WHERE " + " AND ".join(self._where_clauses)
        
        # ORDER BY
        if self._order_by:
            query += " ORDER BY " + ", ".join(self._order_by)
        
        # LIMIT
        if self._limit_val:
            query += f" LIMIT {self._limit_val}"
        
        # OFFSET
        if self._offset_val:
            query += f" OFFSET {self._offset_val}"
        
        return query
    
    @staticmethod
    def insert(table: str, data: Dict[str, Any]) -> Tuple[str, Tuple]:
        """Build INSERT query"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return query, tuple(data.values())
    
    @staticmethod
    def update(table: str, data: Dict[str, Any], where: str) -> Tuple[str, Tuple]:
        """Build UPDATE query"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        return query, tuple(data.values())
    
    @staticmethod
    def delete(table: str, where: str) -> str:
        """Build DELETE query"""
        return f"DELETE FROM {table} WHERE {where}"


# Export database classes
__all__ = ['DatabaseConnection', 'DatabaseResult', 'QueryBuilder']
