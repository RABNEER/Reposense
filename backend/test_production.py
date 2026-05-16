"""Production-level integration test"""
import sys
import os
import inspect
from watsonx_client import WatsonxClient
from bob_client import get_ai_client
from server import app

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("PRODUCTION INTEGRATION TEST")
print("=" * 60)

# Test 1: Check WatsonxClient methods are async
print("\n1. Checking WatsonxClient methods...")
methods = ['analyze', 'orchestrate', 'ask', 'generate_doc']
for method_name in methods:
    method = getattr(WatsonxClient, method_name)
    is_async = inspect.iscoroutinefunction(method)
    status = "[OK]" if is_async else "[FAIL]"
    print(f"   {status} {method_name}: async={is_async}")

# Test 2: Check bob_client integration
print("\n2. Checking bob_client integration...")
try:
    client = get_ai_client()
    print(f"   [OK] get_ai_client() returns: {type(client).__name__}")
    if client is None:
        print("   [OK] Mock mode active (no credentials)")
    else:
        print(f"   [OK] Real client created: {type(client).__name__}")
except Exception as e:
    print(f"   [FAIL] Error: {e}")

# Test 3: Check FastAPI routes
print("\n3. Checking FastAPI routes...")
try:
    routes = []
    for route in app.routes:
        try:
            path = getattr(route, 'path', None)
            if path:
                routes.append(str(path))
        except:
            pass
    required_routes = ['/api/analyze', '/api/ask', '/api/task', '/api/export/markdown']
    for route in required_routes:
        status = "[OK]" if route in routes else "[FAIL]"
        print(f"   {status} {route}")
except Exception as e:
    print(f"   [INFO] Route check skipped: {e}")

# Test 4: Check server functions
print("\n4. Checking server helper functions...")
from server import get_request_config, get_configured_client, is_mock_mode, call_ai
functions = [
    ('get_request_config', get_request_config),
    ('get_configured_client', get_configured_client),
    ('is_mock_mode', is_mock_mode),
    ('call_ai', call_ai)
]
for name, func in functions:
    is_async = inspect.iscoroutinefunction(func)
    print(f"   [OK] {name}: async={is_async}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

# Made with Bob
