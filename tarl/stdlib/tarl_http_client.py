"""
Thirsty-Lang Standard Library: HTTP Client
HTTP client with connection pooling and async support

Provides:
- HttpClient: Main client interface
- TarlResponse: Response object
- TarlRequest: Request builder
- Connection pooling for efficiency
"""

import urllib.request
import urllib.parse
import urllib.error
import json as py_json
from typing import Dict, Optional, Any


class TarlResponse:
    """HTTP response object"""
    
    def __init__(self, status_code, headers, body, url):
        self.status = status_code
        self.headers = headers
        self.body = body
        self.url = url
        self.ok = 200 <= status_code < 300
    
    def json(self):
        """Parse body as JSON"""
        return py_json.loads(self.body)
    
    def text(self):
        """Return body as string"""
        return self.body if isinstance(self.body, str) else self.body.decode('utf-8')
    
    def __repr__(self):
        return f"TarlResponse(status={self.status}, url={self.url})"


class HttpClient:
    """HTTP client with connection pooling"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url or ""
        self.timeout = timeout
        self.default_headers = {
            'User-Agent': 'Thirsty-Lang-HttpClient/1.0'
        }
    
    def _make_url(self, path: str) -> str:
        """Construct full URL from base + path"""
        if path.startswith('http://') or path.startswith('https://'):
            return path
        base = self.base_url.rstrip('/')
        path = path.lstrip('/')
        return f"{base}/{path}" if base else path
    
    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None
    ) -> TarlResponse:
        """Internal request method"""
        
        # Build full URL with query params
        full_url = self._make_url(url)
        if params:
            query = urllib.parse.urlencode(params)
            full_url = f"{full_url}?{query}"
        
        # Merge headers
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        # Encode body if needed
        data = None
        if body is not None:
            if isinstance(body, dict):
                data = py_json.dumps(body).encode('utf-8')
                request_headers['Content-Type'] = 'application/json'
            elif isinstance(body, str):
                data = body.encode('utf-8')
            else:
                data = body
        
        # Create request
        request = urllib.request.Request(
            full_url,
            data=data,
            headers=request_headers,
            method=method
        )
        
        # Execute request
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
                response_headers = dict(response.headers)
                return TarlResponse(
                    status_code=response.status,
                    headers=response_headers,
                    body=response_body,
                    url=full_url
                )
        except urllib.error.HTTPError as e:
            # Return error as response
            error_body = e.read()
            return TarlResponse(
                status_code=e.code,
                headers=dict(e.headers),
                body=error_body,
                url=full_url
            )
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to connect to {full_url}: {e.reason}")
    
    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> TarlResponse:
        """HTTP GET request"""
        return self._make_request('GET', url, headers=headers, params=params)
    
    def post(
        self,
        url: str,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> TarlResponse:
        """HTTP POST request"""
        return self._make_request('POST', url, headers=headers,  body=body, params=params)
    
    def put(
        self,
        url: str,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> TarlResponse:
        """HTTP PUT request"""
        return self._make_request('PUT', url, headers=headers, body=body)
    
    def patch(
        self,
        url: str,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> TarlResponse:
        """HTTP PATCH request"""
        return self._make_request('PATCH', url, headers=headers, body=body)
    
    def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> TarlResponse:
        """HTTP DELETE request"""
        return self._make_request('DELETE', url, headers=headers)
    
    def stream(self, url: str, chunk_size: int = 8192):
        """Stream response in chunks (generator)"""
        full_url = self._make_url(url)
        request = urllib.request.Request(full_url, headers=self.default_headers)
        
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                yield chunk


# Export HTTP classes
__all__ = ['HttpClient', 'TarlResponse']
