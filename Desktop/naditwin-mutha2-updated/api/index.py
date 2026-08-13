from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from naditwin.engine import TwinEngine, N_CELLS
    ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    ENGINE_AVAILABLE = False

# Global engine instance
_engine = None

def get_engine():
    global _engine
    if not ENGINE_AVAILABLE:
        raise Exception("Engine not available due to import error")
    if _engine is None:
        _engine = TwinEngine(seed=42)
    return _engine

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request('GET')
    
    def do_POST(self):
        self._handle_request('POST')
    
    def _handle_request(self, method):
        try:
            u = urlparse(self.path)
            query = parse_qs(u.query)
            path = u.path
            
            # Handle root/dashboard
            if path in ('/', '/index.html', '/dashboard'):
                try:
                    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "naditwin", "static", "dashboard.html")
                    with open(static_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._send_response(200, content, 'text/html; charset=utf-8')
                    return
                except FileNotFoundError:
                    self._send_json_response(404, {'error': 'Dashboard not found'})
                    return
            
            if not ENGINE_AVAILABLE:
                self._send_json_response(500, {'error': 'Server configuration error'})
                return
                
            engine = get_engine()
            
            # Handle API endpoints
            if path == '/api/meta':
                response = engine.meta()
            elif path == '/api/state':
                response = engine.state_now()
            elif path == '/api/forecast/profile':
                lead = int(query.get('lead', ['24'])[0])
                response = engine.forecast_profile(lead)
            elif path == '/api/hydrograph':
                cell = int(query.get('cell', [str(N_CELLS // 2)])[0])
                cell = max(0, min(N_CELLS - 1, cell))
                response = {
                    "cell": cell,
                    "observed": engine.observed_hydrograph(cell),
                    "forecast": engine.forecast_hydrograph(cell),
                }
            elif path == '/api/margins':
                response = engine.margins()
            elif path == '/api/alerts':
                response = engine.alerts()
            elif path == '/api/scorecard':
                response = engine.scorecard()
            elif path == '/api/advance' and method == 'POST':
                hours = int(query.get('hours', ['6'])[0])
                response = engine.advance(hours)
            else:
                self._send_json_response(404, {'error': 'Not found', 'path': path})
                return
                
            self._send_json_response(200, response)
            
        except Exception as e:
            print(f"Handler error: {e}")
            self._send_json_response(500, {'error': str(e), 'type': type(e).__name__})
    
    def _send_response(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)
    
    def _send_json_response(self, status, data):
        self._send_response(status, json.dumps(data), 'application/json')