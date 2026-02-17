"""
Thirsty-Lang Mobile Playground
Web-based REPL with code execution

Provides:
- WebREPL: Browser-based REPL
- CodeExecutor: Safe code execution
- SessionManager: User session management
- CodeSharing: Share code snippets
"""

import sys
import io
import traceback
import json
import hashlib
import time
from typing import Dict, List, Optional
from contextlib import redirect_stdout, redirect_stderr


class CodeExecutor:
    """Execute Thirsty-Lang code safely"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.globals = {}
    
    def execute(self, code: str) -> Dict[str, str]:
        """Execute code and return result"""
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        result = {
            'stdout': '',
            'stderr': '',
            'error': '',
            'success': True
        }
        
        try:
            # Redirect stdout/stderr
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # Compile and execute
                compiled = compile(code, '<repl>', 'exec')
                exec(compiled, self.globals)
        
        except SyntaxError as e:
            result['success'] = False
            result['error'] = f"SyntaxError: {e.msg} (line {e.lineno})"
        
        except Exception as e:
            result['success'] = False
            result['error'] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        
        finally:
            result['stdout'] = stdout_buffer.getvalue()
            result['stderr'] = stderr_buffer.getvalue()
        
        return result
    
    def reset(self):
        """Reset execution environment"""
        self.globals = {}


class REPLSession:
    """REPL session for a user"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.executor = CodeExecutor()
        self.history: List[Dict] = []
        self.created_at = time.time()
        self.last_active = time.time()
    
    def execute(self, code: str) -> Dict:
        """Execute code and store in history"""
        self.last_active = time.time()
        
        result = self.executor.execute(code)
        
        entry = {
            'code': code,
            'result': result,
            'timestamp': time.time()
        }
        
        self.history.append(entry)
        return result
    
    def get_history(self) -> List[Dict]:
        """Get execution history"""
        return self.history
    
    def reset(self):
        """Reset session"""
        self.executor.reset()
        self.history = []


class SessionManager:
    """Manage REPL sessions"""
    
    def __init__(self, max_sessions: int = 1000):
        self.sessions: Dict[str, REPLSession] = {}
        self.max_sessions = max_sessions
    
    def create_session(self) -> str:
        """Create new session and return ID"""
        session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        
        # Clean old sessions if needed
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_old_sessions()
        
        self.sessions[session_id] = REPLSession(session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[REPLSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def _cleanup_old_sessions(self):
        """Remove inactive sessions"""
        current_time = time.time()
        max_age = 3600  # 1 hour
        
        to_remove = []
        for sid, session in self.sessions.items():
            if current_time - session.last_active > max_age:
                to_remove.append(sid)
        
        for sid in to_remove:
            del self.sessions[sid]


class CodeSnippet:
    """Shareable code snippet"""
    
    def __init__(self, code: str, title: str = "", author: str = ""):
        self.id = hashlib.sha256(code.encode()).hexdigest()[:8]
        self.code = code
        self.title = title
        self.author = author
        self.created_at = time.time()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'title': self.title,
            'author': self.author,
            'created_at': self.created_at
        }


class CodeSharingService:
    """Service for sharing code snippets"""
    
    def __init__(self):
        self.snippets: Dict[str, CodeSnippet] = {}
    
    def create_snippet(self, code: str, title: str = "", author: str = "") -> str:
        """Create snippet and return ID"""
        snippet = CodeSnippet(code, title, author)
        self.snippets[snippet.id] = snippet
        return snippet.id
    
    def get_snippet(self, snippet_id: str) -> Optional[CodeSnippet]:
        """Get snippet by ID"""
        return self.snippets.get(snippet_id)
    
    def list_snippets(self, limit: int = 50) -> List[Dict]:
        """List recent snippets"""
        snippets = sorted(
            self.snippets.values(),
            key=lambda s: s.created_at,
            reverse=True
        )[:limit]
        
        return [s.to_dict() for s in snippets]


class WebREPL:
    """Web-based REPL server"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.code_sharing = CodeSharingService()
    
    def handle_execute(self, session_id: str, code: str) -> dict:
        """Handle code execution request"""
        session = self.session_manager.get_session(session_id)
        
        if not session:
            return {'error': 'Invalid session'}
        
        return session.execute(code)
    
    def handle_create_session(self) -> dict:
        """Handle session creation"""
        session_id = self.session_manager.create_session()
        return {'session_id': session_id}
    
    def handle_share_code(self, code: str, title: str = "", author: str = "") -> dict:
        """Handle code sharing"""
        snippet_id = self.code_sharing.create_snippet(code, title, author)
        return {'snippet_id': snippet_id, 'url': f'/snippets/{snippet_id}'}
    
    def handle_get_snippet(self, snippet_id: str) -> dict:
        """Handle snippet retrieval"""
        snippet = self.code_sharing.get_snippet(snippet_id)
        
        if not snippet:
            return {'error': 'Snippet not found'}
        
        return snippet.to_dict()


# Export playground classes
__all__ = [
    'CodeExecutor',
    'REPLSession',
    'SessionManager',
    'CodeSnippet',
    'CodeSharingService',
    'WebREPL'
]
