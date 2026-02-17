"""
Thirsty-Lang Standard Library: Sockets & DNS
Low-level networking primitives

Provides:
- TcpSocket: TCP client and server
- UdpSocket: UDP datagram socket
- DNS: Name resolution utilities
"""

import socket as py_socket
import threading
from typing import Callable, Optional, Tuple


class TcpSocket:
    """TCP socket wrapper"""
    
    def __init__(self):
        self._socket = py_socket.socket(py_socket.AF_INET, py_socket.SOCK_STREAM)
        self.connected = False
    
    def connect(self, host: str, port: int, timeout: Optional[int] = None):
        """Connect to remote host"""
        if timeout:
            self._socket.settimeout(timeout)
        self._socket.connect((host, port))
        self.connected = True
    
    def bind(self, host: str, port: int):
        """Bind to address"""
        self._socket.setsockopt(py_socket.SOL_SOCKET, py_socket.SO_REUSEADDR, 1)
        self._socket.bind((host, port))
    
    def listen(self, backlog: int = 5):
        """Listen for connections"""
        self._socket.listen(backlog)
    
    def accept(self) -> Tuple['TcpSocket', Tuple[str, int]]:
        """Accept incoming connection"""
        client_socket, address = self._socket.accept()
        wrapped = TcpSocket.__new__(TcpSocket)
        wrapped._socket = client_socket
        wrapped.connected = True
        return wrapped, address
    
    def send(self, data: bytes) -> int:
        """Send data"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self._socket.send(data)
    
    def sendall(self, data: bytes):
        """Send all data"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._socket.sendall(data)
    
    def recv(self, bufsize: int = 4096) -> bytes:
        """Receive data"""
        return self._socket.recv(bufsize)
    
    def recv_text(self, bufsize: int = 4096) -> str:
        """Receive data as text"""
        return self.recv(bufsize).decode('utf-8')
    
    def close(self):
        """Close socket"""
        self.connected = False
        self._socket.close()
    
    def set_timeout(self, timeout: Optional[float]):
        """Set socket timeout"""
        self._socket.settimeout(timeout)
    
    def set_blocking(self, blocking: bool):
        """Set blocking mode"""
        self._socket.setblocking(blocking)


class UdpSocket:
    """UDP socket wrapper"""
    
    def __init__(self):
        self._socket = py_socket.socket(py_socket.AF_INET, py_socket.SOCK_DGRAM)
    
    def bind(self, host: str, port: int):
        """Bind to address"""
        self._socket.bind((host, port))
    
    def sendto(self, data: bytes, address: Tuple[str, int]) -> int:
        """Send datagram to address"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self._socket.sendto(data, address)
    
    def recvfrom(self, bufsize: int = 4096) -> Tuple[bytes, Tuple[str, int]]:
        """Receive datagram"""
        data, address = self._socket.recvfrom(bufsize)
        return data, address
    
    def recvfrom_text(self, bufsize: int = 4096) -> Tuple[str, Tuple[str, int]]:
        """Receive datagram as text"""
        data, address = self.recvfrom(bufsize)
        return data.decode('utf-8'), address
    
    def close(self):
        """Close socket"""
        self._socket.close()
    
    def set_timeout(self, timeout: Optional[float]):
        """Set socket timeout"""
        self._socket.settimeout(timeout)


class TcpServer:
    """High-level TCP server"""
    
    def __init__(self, host: str = 'localhost', port: int = 9000):
        self.host = host
        self.port = port
        self._socket = None
        self._running = False
        self.on_connect: Optional[Callable] = None
        self.on_data: Optional[Callable] = None
    
    def listen(self):
        """Start listening"""
        self._socket = TcpSocket()
        self._socket.bind(self.host, self.port)
        self._socket.listen()
        self._running = True
        
        print(f"TCP server listening on {self.host}:{self.port}")
        
        while self._running:
            try:
                client, address = self._socket.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client, address),
                    daemon=True
                ).start()
            except Exception:
                break
    
    def _handle_client(self, client: TcpSocket, address):
        """Handle client connection"""
        if self.on_connect:
            self.on_connect(address)
        
        while True:
            try:
                data = client.recv()
                if not data:
                    break
                
                if self.on_data:
                    response = self.on_data(data, client, address)
                    if response:
                        client.sendall(response)
            except Exception:
                break
        
        client.close()
    
    def stop(self):
        """Stop server"""
        self._running = False
        if self._socket:
            self._socket.close()


class DNS:
    """DNS resolution utilities"""
    
    @staticmethod
    def resolve(hostname: str) -> str:
        """Resolve hostname to IP address"""
        return py_socket.gethostbyname(hostname)
    
    @staticmethod
    def resolve_all(hostname: str) -> list:
        """Resolve hostname to all IP addresses"""
        _, _, addresses = py_socket.gethostbyname_ex(hostname)
        return addresses
    
    @staticmethod
    def reverse_lookup(ip: str) -> str:
        """Reverse DNS lookup"""
        return py_socket.gethostbyaddr(ip)[0]
    
    @staticmethod
    def get_hostname() -> str:
        """Get local hostname"""
        return py_socket.gethostname()
    
    @staticmethod
    def get_ip() -> str:
        """Get local IP address"""
        hostname = DNS.get_hostname()
        return DNS.resolve(hostname)


# Export socket classes
__all__ = ['TcpSocket', 'UdpSocket', 'TcpServer', 'DNS']
