"""Mock Firebase SSE server for testing the listener without a real Firebase backend."""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class MockFirebaseHandler(BaseHTTPRequestHandler):
    """Mock Firebase Realtime Database SSE endpoint."""
    
    def do_GET(self):
        """Handle GET requests for SSE streaming."""
        path = self.path
        parsed = urlparse(path)
        
        # Simulate authentication check
        query_params = parse_qs(parsed.query)
        if 'access_token' not in query_params and 'auth' not in query_params:
            self.send_error(401, "Unauthorized request.")
            return
        
        # Send SSE headers
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Send initial data
        self.send_sse_event("put", {
            "path": "/",
            "data": {"message": "Mock Firebase is running", "timestamp": time.time()}
        })
        
        # Send periodic updates
        for i in range(10):
            time.sleep(2)
            self.send_sse_event("patch", {
                "path": f"/update_{i}",
                "data": {"counter": i, "timestamp": time.time()}
            })
            
            # Check if client disconnected
            try:
                self.wfile.flush()
            except BrokenPipeError:
                break
        
        # Send keep-alive
        self.send_sse_event("keep-alive", None)
    
    def send_sse_event(self, event_type: str, data: dict | None):
        """Send an SSE event."""
        try:
            event_data = json.dumps(data) if data else ""
            message = f"event: {event_type}\ndata: {event_data}\n\n"
            self.wfile.write(message.encode('utf-8'))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
    
    def log_message(self, format, *args):
        """Override to reduce noise."""
        print(f"Mock Firebase: {format % args}")


def run_mock_server(port=8080):
    """Run the mock Firebase server."""
    server = HTTPServer(('localhost', port), MockFirebaseHandler)
    print(f"🎭 Mock Firebase server running on http://localhost:{port}")
    print("📡 Use this URL in your .env file: http://localhost:8080")
    print("🔑 Authentication: Any access_token or auth parameter will work")
    print("⏹️  Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Mock server stopped")
        server.shutdown()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_mock_server(port)