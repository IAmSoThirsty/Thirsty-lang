"""
Thirsty-Lang Standard Library: HTTP Server
Lightweight HTTP server framework with routing

Provides:
- HttpServer: Main server class with routing
- TarlRequest: Incoming request object
- TarlHandler: Base request handler
- Route decorators for clean API
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json as py_json
import threading
from typing import Callable, Dict, Optional, Any, List, Tuple


class TarlRequest:
    """Incoming HTTP request"""
    
    def __init__(self, handler):
        self.method = handler.command
        self.path = handler.path
        parsed = urlparse(handler.path)
        self.url = parsed.path
        self.query = parse_qs(parsed.query)
        self.headers = dict(handler.headers)
        
        # Read body if present
        content_length = int(handler.headers.get('Content-Length', 0))
        self.body = handler.rfile.read(content_length) if content_length > 0 else b''
    
    def json(self):
        """Parse body as JSON"""
        return py_json.loads(self.body)
    
    def text(self):
        """Get body as text"""
        return self.body.decode('utf-8') if self.body else ''
    
    def get_query(self, key: str, default=None):
        """Get query parameter"""
        values = self.query.get(key, [])
        return values[0] if values else default


class TarlResponse:
    """HTTP response builder"""
    
    def __init__(self, body='', status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}
    
    @staticmethod
    def json(data: Any, status=200):
        """Create JSON response"""
        body = py_json.dumps(data)
        return TarlResponse(body, status, {'Content-Type': 'application/json'})
    
    @staticmethod
    def text(text: str, status=200):
        """Create text response"""
        return TarlResponse(text, status, {'Content-Type': 'text/plain'})
    
    @staticmethod
    def html(html: str, status=200):
        """Create HTML response"""
        return TarlResponse(html, status, {'Content-Type': 'text/html'})


class HttpServer:
    """HTTP server with routing"""
    
    def __init__(self, host='localhost', port=8000):
        self.host = host
        self.port = port
        self.routes: Dict[Tuple[str, str], Callable] = {}
        self._server = None
        self._thread = None
    
    def route(self, path: str, method: str = 'GET'):
        """Decorator to register route handler"""
        def decorator(handler: Callable):
            self.routes[(method.upper(), path)] = handler
            return handler
        return decorator
    
    def get(self, path: str):
        """Decorator for GET routes"""
        return self.route(path, 'GET')
    
    def post(self, path: str):
        """Decorator for POST routes"""
        return self.route(path, 'POST')
    
    def put(self, path: str):
        """Decorator for PUT routes"""
        return self.route(path, 'PUT')
    
    def delete(self, path: str):
        """Decorator for DELETE routes"""
        return self.route(path, 'DELETE')
    
    def _create_handler(self):
        """Create request handler class"""
        routes = self.routes
        
        class TarlRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self._handle_request('GET')
            
            def do_POST(self):
                self._handle_request('POST')
            
            def do_PUT(self):
                self._handle_request('PUT')
            
            def do_DELETE(self):
                self._handle_request('DELETE')
            
            def _handle_request(self, method):
                # Create request object
                request = TarlRequest(self)
                
                # Find matching route
                handler = routes.get((method, request.url))
                
                if handler:
                    try:
                        # Call handler
                        response = handler(request)
                        
                        # Send response
                        if isinstance(response, TarlResponse):
                            self.send_response(response.status)
                            for key, value in response.headers.items():
                                self.send_header(key, value)
                            self.end_headers()
                            body = response.body
                            if isinstance(body, str):
                                body = body.encode('utf-8')
                            self.wfile.write(body)
                        else:
                            # Return plain text
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/plain')
                            self.end_headers()
                            self.wfile.write(str(response).encode('utf-8'))
                    
                    except Exception as e:
                        # Error response
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        error = {'error': str(e), 'type': type(e).__name__}
                        self.wfile.write(py_json.dumps(error).encode('utf-8'))
                else:
                    # 404 Not Found
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    error = {'error': f'Route not found: {method} {request.url}'}
                    self.wfile.write(py_json.dumps(error).encode('utf-8'))
            
            def log_message(self, format, *args):
                """Override to customize logging"""
                print(f"[{self.address_string()}] {format % args}")
        
        return TarlRequestHandler
    
    def listen(self, blocking=True):
        """Start server"""
        handler_class = self._create_handler()
        self._server = HTTPServer((self.host, self.port), handler_class)
        
        print(f"Server listening on http://{self.host}:{self.port}")
        
        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever)
            self._thread.daemon = True
            self._thread.start()
    
    def stop(self):
        """Stop server"""
        if self._server:
            self._server.shutdown()
            print("Server stopped")


# Export server classes
__all__ = ['HttpServer', 'TarlRequest', 'TarlResponse']
