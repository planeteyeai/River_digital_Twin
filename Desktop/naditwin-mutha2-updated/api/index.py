import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from naditwin.engine import TwinEngine, N_CELLS
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback response
    def handler(request):
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Import failed: {str(e)}'})
        }

# Global engine instance
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        try:
            _engine = TwinEngine(seed=42)
        except Exception as e:
            print(f"Engine initialization error: {e}")
            raise
    return _engine

def handler(request):
    try:
        method = request.get('method', 'GET')
        url = request.get('url', '/')
        
        u = urlparse(url)
        path = u.path
        query = parse_qs(u.query)
        
        # Handle static dashboard
        if path in ('/', '/index.html', '/dashboard'):
            try:
                static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "naditwin", "static", "dashboard.html")
                with open(static_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'text/html; charset=utf-8'},
                    'body': content
                }
            except FileNotFoundError:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Dashboard not found'})
                }
        
        # Initialize engine
        engine = get_engine()
        
        # API endpoints
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
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response)
        }
        
    except Exception as e:
        print(f"Handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e), 'type': type(e).__name__})
        }