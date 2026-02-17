"""
Thirsty-Lang Language Server Protocol
LSP server implementation for IDE integration

Provides:
- LSPServer: Language server implementation
- Diagnostics: Error and warning detection
- Completion: Auto-completion suggestions
- Formatting: Code formatting
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class Position:
    """Position in file"""
    line: int  # 0-indexed
    character: int  # 0-indexed


@dataclass
class Range:
    """Range in file"""
    start: Position
    end: Position


@dataclass
class Diagnostic:
    """Diagnostic message"""
    range: Range
    message: str
    severity: int  # 1=Error, 2=Warning, 3=Info, 4=Hint
    source: str = "tarl"


@dataclass
class CompletionItem:
    """Auto-completion item"""
    label: str
    kind: int  # 1=Text, 3=Function, 4=Variable, etc.
    detail: Optional[str] = None
    documentation: Optional[str] = None


class DocumentStore:
    """Store for open documents"""
    
    def __init__(self):
        self.documents: Dict[str, str] = {}
    
    def open_document(self, uri: str, text: str):
        """Open document"""
        self.documents[uri] = text
    
    def update_document(self, uri: str, text: str):
        """Update document"""
        self.documents[uri] = text
    
    def close_document(self, uri: str):
        """Close document"""
        if uri in self.documents:
            del self.documents[uri]
    
    def get_document(self, uri: str) -> Optional[str]:
        """Get document text"""
        return self.documents.get(uri)


class TarlAnalyzer:
    """Thirsty-Lang source analyzer"""
    
    @staticmethod
    def analyze(text: str) -> List[Diagnostic]:
        """Analyze source and return diagnostics"""
        diagnostics = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            # Check for undefined variables (simple heuristic)
            if '=' in line and 'def' not in line and 'class' not in line:
                # Check for undefined references
                match = re.match(r'\s*(\w+)\s*=\s*(\w+)', line)
                if match:
                    var_name = match.group(2)
                    if var_name not in ['True', 'False', 'None'] and not var_name[0].isupper():
                        # Check if variable is defined earlier
                        is_defined = any(f'{var_name} =' in lines[i] for i in range(line_num))
                        if not is_defined:
                            diagnostics.append(Diagnostic(
                                range=Range(
                                    start=Position(line_num, 0),
                                    end=Position(line_num, len(line))
                                ),
                                message=f"Variable '{var_name}' may be undefined",
                                severity=2  # Warning
                            ))
            
            # Check for missing colons
            if line.strip().startswith(('if ', 'for ', 'while ', 'def ', 'class ')):
                if not line.rstrip().endswith(':'):
                    diagnostics.append(Diagnostic(
                        range=Range(
                            start=Position(line_num, 0),
                            end=Position(line_num, len(line))
                        ),
                        message="Missing colon at end of statement",
                        severity=1  # Error
                    ))
        
        return diagnostics
    
    @staticmethod
    def get_completions(text: str, position: Position) -> List[CompletionItem]:
        """Get auto-completion suggestions"""
        completions = []
        
        # Built-in keywords
        keywords = [
            'if', 'else', 'elif', 'for', 'while', 'def', 'class',
            'return', 'import', 'from', 'as', 'try', 'except', 'finally',
            'with', 'True', 'False', 'None'
        ]
        
        # Add keywords
        for kw in keywords:
            completions.append(CompletionItem(
                label=kw,
                kind=14,  # Keyword
                detail=f"{kw} keyword"
            ))
        
        # Extract defined variables/functions
        lines = text.split('\n')
        for line in lines[:position.line]:
            # Find variable definitions
            var_match = re.match(r'\s*(\w+)\s*=', line)
            if var_match:
                var_name = var_match.group(1)
                completions.append(CompletionItem(
                    label=var_name,
                    kind=6,  # Variable
                    detail="Variable"
                ))
            
            # Find function definitions
            func_match = re.match(r'\s*def\s+(\w+)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                completions.append(CompletionItem(
                    label=func_name,
                    kind=3,  # Function
                    detail="Function"
                ))
        
        return completions


class TarlFormatter:
    """Code formatter"""
    
    @staticmethod
    def format(text: str, indent_size: int = 4) -> str:
        """Format source code"""
        lines = text.split('\n')
        formatted = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Decrease indent for else, elif, except, finally
            if stripped.startswith(('else:', 'elif ', 'except:', 'except ', 'finally:')):
                indent_level = max(0, indent_level - 1)
            
            # Add line with proper indentation
            if stripped:
                formatted.append(' ' * (indent_level * indent_size) + stripped)
            else:
                formatted.append('')
            
            # Increase indent after control structures
            if stripped.endswith(':') and not stripped.startswith('#'):
                indent_level += 1
            
            # Decrease indent for return, break, continue, pass
            if stripped in ('return', 'break', 'continue', 'pass'):
                indent_level = max(0, indent_level - 1)
        
        return '\n'.join(formatted)


class LSPServer:
    """Language Server Protocol server"""
    
    def __init__(self):
        self.documents = DocumentStore()
        self.analyzer = TarlAnalyzer()
        self.formatter = TarlFormatter()
    
    def initialize(self, params: dict) -> dict:
        """Initialize LSP server"""
        return {
            'capabilities': {
                'textDocumentSync': 1,  # Full sync
                'completionProvider': {},
                'diagnosticProvider': {},
                'documentFormattingProvider': True
            }
        }
    
    def open_document(self, uri: str, text: str):
        """Handle document open"""
        self.documents.open_document(uri, text)
        return self.get_diagnostics(uri)
    
    def update_document(self, uri: str, text: str):
        """Handle document update"""
        self.documents.update_document(uri, text)
        return self.get_diagnostics(uri)
    
    def get_diagnostics(self, uri: str) -> List[dict]:
        """Get diagnostics for document"""
        text = self.documents.get_document(uri)
        if not text:
            return []
        
        diagnostics = self.analyzer.analyze(text)
        return [
            {
                'range': {
                    'start': {'line': d.range.start.line, 'character': d.range.start.character},
                    'end': {'line': d.range.end.line, 'character': d.range.end.character}
                },
                'message': d.message,
                'severity': d.severity,
                'source': d.source
            }
            for d in diagnostics
        ]
    
    def get_completions(self, uri: str, position: dict) -> List[dict]:
        """Get completion suggestions"""
        text = self.documents.get_document(uri)
        if not text:
            return []
        
        pos = Position(position['line'], position['character'])
        items = self.analyzer.get_completions(text, pos)
        
        return [
            {
                'label': item.label,
                'kind': item.kind,
                'detail': item.detail,
                'documentation': item.documentation
            }
            for item in items
        ]
    
    def format_document(self, uri: str) -> str:
        """Format document"""
        text = self.documents.get_document(uri)
        if not text:
            return ""
        
        return self.formatter.format(text)


# Export LSP classes
__all__ = ['LSPServer', 'Diagnostic', 'CompletionItem', 'TarlFormatter']
