import requests

def inspect_server_response():
    """Debug the server response format"""
    base_url = "http://localhost:8283"
    
    # Try to list agents first (simpler request)
    print("\nTrying to list agents...")
    response = requests.get(f"{base_url}/api/v1/agents")
    print(f"Status: {response.status_code}")
    print("Response:", response.json())
    
    # Try to create a minimal agent
    print("\nTrying to create minimal agent...")
    minimal_payload = {
        "name": "debug_agent",
        "description": "Testing agent schema",
        "include_base_tools": False,
        "tools": None
    }
    response = requests.post(f"{base_url}/api/v1/agents", json=minimal_payload)
    print(f"Status: {response.status_code}")
    print("Response:", response.json())

if __name__ == "__main__":
    inspect_server_response() 