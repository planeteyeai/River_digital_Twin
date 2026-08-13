from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Simple test response
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                html = """
                <html>
                <head><title>NadiTwin Demo</title></head>
                <body>
                    <h1>NadiTwin Demo - Working!</h1>
                    <p><a href="/api/test">Test API</a></p>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
                return
                
            elif self.path == '/api/test':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {'status': 'working', 'message': 'API is functional'}
                self.wfile.write(json.dumps(response).encode())
                return
                
            elif self.path == '/api/meta':
                # Try to load the actual engine
                from naditwin.engine import TwinEngine
                engine = TwinEngine(seed=42)
                response = engine.meta()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                return
            
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Not found'}).encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error = {'error': str(e), 'type': type(e).__name__}
            self.wfile.write(json.dumps(error).encode())