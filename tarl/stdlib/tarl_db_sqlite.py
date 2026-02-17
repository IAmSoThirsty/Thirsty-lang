"""
Thirsty-Lang Standard Library: SQLite Database
SQLite embedded database support

Provides:
- SQLiteConnection: SQLite database connection
- Full CRUD operations
- Transaction support
"""

import sqlite3
from typing import Optional, Tuple, List
from tarl_db_interface import DatabaseConnection, DatabaseResult


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection"""
    
    def __init__(self, database: str = ':memory:'):
        """Create SQLite connection
        
        database: Path to database file or ':memory:' for in-memory DB
        """
        self.database = database
        self._conn = sqlite3.connect(database)
        self._conn.row_factory = sqlite3.Row
    
    def execute(self, query: str, params: Optional[Tuple] = None) -> DatabaseResult:
        """Execute SQL query"""
        cursor = self._conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Fetch results if available
        try:
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return DatabaseResult([tuple(row) for row in rows], columns)
        except Exception:
            # No results (INSERT, UPDATE, DELETE)
            return DatabaseResult([], [])
    
    def executemany(self, query: str, params_list: List[Tuple]) -> DatabaseResult:
        """Execute query with multiple parameter sets"""
        cursor = self._conn.cursor()
        cursor.executemany(query, params_list)
        return DatabaseResult([], [])
    
    def commit(self):
        """Commit transaction"""
        self._conn.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self._conn.rollback()
    
    def close(self):
        """Close connection"""
        self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


class SQLiteDatabase:
    """High-level SQLite operations"""
    
    def __init__(self, database: str = ':memory:'):
        self.database = database
        self.conn = SQLiteConnection(database)
    
    def create_table(self, table: str, schema: str):
        """Create table"""
        query = f"CREATE TABLE IF NOT EXISTS {table} ({schema})"
        self.conn.execute(query)
        self.conn.commit()
    
    def insert(self, table: str, data: dict) -> int:
        """Insert row and return ID"""
        from tarl_db_interface import QueryBuilder
        query, params = QueryBuilder.insert(table, data)
        self.conn.execute(query, params)
        self.conn.commit()
        
        # Get last inserted ID
        result = self.conn.execute("SELECT last_insert_rowid()")
        return result.fetchone()[0]
    
    def select(self, table: str, where: Optional[str] = None) -> List[dict]:
        """Select rows as dictionaries"""
        query = f"SELECT * FROM {table}"
        if where:
            query += f" WHERE {where}"
        
        result = self.conn.execute(query)
        return result.to_dict_list()
    
    def update(self, table: str, data: dict, where: str) -> int:
        """Update rows"""
        from tarl_db_interface import QueryBuilder
        query, params = QueryBuilder.update(table, data, where)
        self.conn.execute(query, params)
        self.conn.commit()
        return self.conn._conn.total_changes
    
    def delete(self, table: str, where: str) -> int:
        """Delete rows"""
        from tarl_db_interface import QueryBuilder
        query = QueryBuilder.delete(table, where)
        self.conn.execute(query)
        self.conn.commit()
        return self.conn._conn.total_changes
    
    def close(self):
        """Close database"""
        self.conn.close()


# Export SQLite classes
__all__ = ['SQLiteConnection', 'SQLiteDatabase']
