from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import sys

# Add the parent directory to the path so we can import naditwin
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from naditwin.engine import TwinEngine, N_CELLS

# Global engine instance
engine = None

def get_engine():
    global engine
    if engine is None:
        engine = TwinEngine(seed=42)
    return engine

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        engine = get_engine()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        
        try:
            if u.path in ("/", "/index.html", "/dashboard"):
                # Serve the dashboard HTML
                static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "naditwin", "static", "dashboard.html")
                with open(static_path, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(f.read())
                    return
            
            elif u.path == "/api/meta":
                response = engine.meta()
            elif u.path == "/api/state":
                response = engine.state_now()
            elif u.path == "/api/forecast/profile":
                lead = int(q.get("lead", ["24"])[0])
                response = engine.forecast_profile(lead)
            elif u.path == "/api/hydrograph":
                cell = int(q.get("cell", [str(N_CELLS // 2)])[0])
                cell = max(0, min(N_CELLS - 1, cell))
                response = {
                    "cell": cell,
                    "observed": engine.observed_hydrograph(cell),
                    "forecast": engine.forecast_hydrograph(cell),
                }
            elif u.path == "/api/margins":
                response = engine.margins()
            elif u.path == "/api/alerts":
                response = engine.alerts()
            elif u.path == "/api/scorecard":
                response = engine.scorecard()
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "not found"}).encode())
                return
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_POST(self):
        engine = get_engine()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        
        if u.path == "/api/advance":
            hours = int(q.get("hours", ["6"])[0])
            response = engine.advance(hours)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not found"}).encode())