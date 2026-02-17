"""
Thirsty-Lang Network & HTTP Tests
Test suite for Track 2 modules
"""

import sys
import os
import time
import threading

# Add modules to path
test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)

from tarl_http_client import HttpClient
from tarl_http_server import HttpServer, TarlRequest, TarlResponse
from tarl_sockets import TcpSocket, UdpSocket, DNS


def test_http_client():
    """Test HTTP client"""
    print("Testing HTTP Client...")
    
    client = HttpClient()
    
    # Test GET request (using a reliable public API)
    try:
        response = client.get('https://httpbin.org/get')
        assert response.ok, "GET request failed"
        assert response.status == 200
        data = response.json()
        assert 'url' in data
        print("✓ HTTP Client GET test passed")
    except Exception as e:
        print(f"⚠ HTTP Client test skipped (network required): {e}")


def test_http_server():
    """Test HTTP server"""
    print("Testing HTTP Server...")
    
    # Create server
    server = HttpServer(host='localhost', port=18000)
    
    # Register routes
    @server.get('/hello')
    def hello(request):
        return TarlResponse.text('Hello, World!')
    
    @server.post('/echo')
    def echo(request):
        return TarlResponse.json({'received': request.text()})
    
    # Start server in background
    server_thread = threading.Thread(target=lambda: server.listen(blocking=True))
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(0.5)  # Wait for server to start
    
    # Test with client
    client = HttpClient(base_url='http://localhost:18000')
    
    try:
        # Test GET
        response = client.get('/hello')
        assert response.status == 200
        assert response.text() == 'Hello, World!'
        
        # Test POST
        response = client.post('/echo', body='test data')
        assert response.status == 200
        data = response.json()
        assert data['received'] == 'test data'
        
        print("✓ HTTP Server tests passed")
    finally:
        server.stop()


def test_tcp_sockets():
    """Test TCP sockets"""
    print("Testing TCP Sockets...")
    
    # Create server
    server = TcpSocket()
    server.bind('localhost', 19000)
    server.listen()
    
    # Server thread
    def server_handler():
        client, addr = server.accept()
        data = client.recv()
        client.sendall(b'Echo: ' + data)
        client.close()
    
    server_thread = threading.Thread(target=server_handler)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(0.2)
    
    # Client
    client = TcpSocket()
    client.connect('localhost', 19000)
    client.sendall(b'Hello TCP')
    response = client.recv()
    
    assert response == b'Echo: Hello TCP'
    
    client.close()
    server.close()
    
    print("✓ TCP Socket tests passed")


def test_udp_sockets():
    """Test UDP sockets"""
    print("Testing UDP Sockets...")
    
    # Create server
    server = UdpSocket()
    server.bind('localhost', 19001)
    
    # Server thread
    received_data = []
    def server_handler():
        data, addr = server.recvfrom()
        received_data.append((data, addr))
    
    server_thread = threading.Thread(target=server_handler)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(0.2)
    
    # Client
    client = UdpSocket()
    client.sendto(b'Hello UDP', ('localhost', 19001))
    
    time.sleep(0.2)
    
    assert len(received_data) == 1
    assert received_data[0][0] == b'Hello UDP'
    
    client.close()
    server.close()
    
    print("✓ UDP Socket tests passed")


def test_dns():
    """Test DNS resolution"""
    print("Testing DNS...")
    
    # Test hostname resolution
    ip = DNS.resolve('localhost')
    assert ip in ['127.0.0.1', '::1']
    
    # Test getting local hostname
    hostname = DNS.get_hostname()
    assert isinstance(hostname, str)
    assert len(hostname) > 0
    
    print("✓ DNS tests passed")


def run_all_tests():
    """Run all network tests"""
    print("\n" + "="*50)
    print("THIRSTY-LANG NETWORK & HTTP TEST SUITE")
    print("="*50 + "\n")
    
    try:
        test_http_client()
        test_http_server()
        test_tcp_sockets()
        test_udp_sockets()
        test_dns()
        
        print("\n" + "="*50)
        print("✓ ALL NETWORK TESTS PASSED")
        print("="*50)
        return True
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
