"""
Thirsty-Lang Standard Library: WebSocket
Full-duplex WebSocket communication

Provides:
- WebSocketClient: Client-side WebSocket
- WebSocketServer: Server-side WebSocket
- Message framing and handshake handling
"""

import socket
import base64
import hashlib
import struct
import threading
from typing import Callable, Optional


class WebSocketClient:
    """WebSocket client"""
    
    def __init__(self, url: str):
        self.url = url
        self.socket = None
        self.connected = False
        self._receive_thread = None
        self.on_message: Optional[Callable] = None
        self.on_close: Optional[Callable] = None
    
    def connect(self):
        """Establish WebSocket connection"""
        # Parse URL
        if not self.url.startswith('ws://'):
            raise ValueError("URL must start with ws://")
        
        url_parts = self.url[5:].split('/', 1)
        host_port = url_parts[0]
        path = '/' + url_parts[1] if len(url_parts) > 1 else '/'
        
        if ':' in host_port:
            host, port = host_port.split(':')
            port = int(port)
        else:
            host = host_port
            port = 80
        
        # Create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        
        # Send handshake
        key = base64.b64encode(b'thirstylang-ws-key')
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key.decode()}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        self.socket.send(handshake.encode())
        
        # Receive handshake response
        response = self.socket.recv(1024).decode()
        if '101 Switching Protocols' not in response:
            raise ConnectionError("WebSocket handshake failed")
        
        self.connected = True
        
        # Start receive thread
        self._receive_thread = threading.Thread(target=self._receive_loop)
        self._receive_thread.daemon = True
        self._receive_thread.start()
    
    def send(self, message: str):
        """Send text message"""
        if not self.connected:
            raise ConnectionError("Not connected")
        
        # Frame message
        message_bytes = message.encode('utf-8')
        frame = self._create_frame(message_bytes)
        self.socket.send(frame)
    
    def _create_frame(self, payload: bytes) -> bytes:
        """Create WebSocket frame"""
        frame = bytearray()
        frame.append(0x81)  # Text frame, FIN=1
        
        length = len(payload)
        if length < 126:
            frame.append(0x80 | length)  # Masked, length
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack('>H', length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack('>Q', length))
        
        # Masking key
        mask = b'\x00\x00\x00\x00'
        frame.extend(mask)
        frame.extend(payload)
        
        return bytes(frame)
    
    def _receive_loop(self):
        """Receive messages continuously"""
        while self.connected:
            try:
                # Read frame header
                header = self.socket.recv(2)
                if not header:
                    break
                
                # Parse length
                length = header[1] & 0x7F
                if length == 126:
                    length = struct.unpack('>H', self.socket.recv(2))[0]
                elif length == 127:
                    length = struct.unpack('>Q', self.socket.recv(8))[0]
                
                # Read payload
                payload = self.socket.recv(length)
                message = payload.decode('utf-8')
                
                # Call handler
                if self.on_message:
                    self.on_message(message)
            
            except Exception:
                break
        
        self.connected = False
        if self.on_close:
            self.on_close()
    
    def close(self):
        """Close connection"""
        if self.socket:
            self.connected = False
            self.socket.close()


class WebSocketServer:
    """Simple WebSocket server"""
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.on_connect: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self._server_socket = None
        self._running = False
    
    def listen(self):
        """Start listening for connections"""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self._running = True
        
        print(f"WebSocket server listening on ws://{self.host}:{self.port}")
        
        while self._running:
            try:
                client_socket, address = self._server_socket.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                ).start()
            except Exception:
                break
    
    def _handle_client(self, client_socket, address):
        """Handle client connection"""
        # Perform handshake
        request = client_socket.recv(1024).decode()
        
        # Extract key
        key_line = [l for l in request.split('\r\n') if 'Sec-WebSocket-Key' in l][0]
        key = key_line.split(': ')[1]
        
        # Generate accept key
        accept = base64.b64encode(
            hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
        ).decode()
        
        # Send handshake response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        client_socket.send(response.encode())
        
        if self.on_connect:
            self.on_connect(address)
        
        # Receive messages
        while True:
            try:
                header = client_socket.recv(2)
                if not header:
                    break
                
                # Parse message (simplified)
                length = header[1] & 0x7F
                if length == 126:
                    length = struct.unpack('>H', client_socket.recv(2))[0]
                
                mask = client_socket.recv(4)
                payload = bytearray(client_socket.recv(length))
                
                # Unmask
                for i in range(len(payload)):
                    payload[i] ^= mask[i % 4]
                
                message = payload.decode('utf-8')
                
                if self.on_message:
                    self.on_message(message, client_socket)
            
            except Exception:
                break
        
        client_socket.close()
    
    def stop(self):
        """Stop server"""
        self._running = False
        if self._server_socket:
            self._server_socket.close()


# Export WebSocket classes
__all__ = ['WebSocketClient', 'WebSocketServer']
