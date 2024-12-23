import pytest
from unittest.mock import patch, Mock
from letta_templates.npc_tools import navigate_to, find_location
import json

# Mock location service responses
MOCK_LOCATION_FOUND = {
    "message": "Found 1 matching locations",
    "locations": [{
        "name": "Pete's Merch Stand",
        "position_x": -12.0,
        "position_y": 18.9,
        "position_z": -127.0,
        "similarity": 0.9,
        "location_data": {
            "area": "town_center",
            "type": "shop"
        }
    }]
}

MOCK_LOW_CONFIDENCE = {
    "message": "Found 1 matching locations",
    "locations": [{
        "name": "Pete's Merch Stand",
        "position_x": -12.0,
        "position_y": 18.9,
        "position_z": -127.0,
        "similarity": 0.6,  # Below threshold
        "location_data": {}
    }]
}

MOCK_NOT_FOUND = {
    "message": "No matching locations found",
    "locations": []
}

@pytest.fixture
def mock_requests():
    with patch('letta_templates.npc_tools.requests.get') as mock_get:
        yield mock_get

def test_successful_navigation(mock_requests):
    """Test navigation to a valid location."""
    mock_response = Mock()
    mock_response.json.return_value = MOCK_LOCATION_FOUND
    mock_requests.return_value = mock_response
    
    result = navigate_to("Pete's stand")
    
    assert "Beginning navigation to Pete's Merch Stand" in result
    assert "Currently in transit" in result

def test_location_not_found(mock_requests):
    """Test navigation to an unknown location."""
    mock_response = Mock()
    mock_response.json.return_value = MOCK_NOT_FOUND
    mock_requests.return_value = mock_response
    
    result = navigate_to("nonexistent location")
    
    assert "Could you be more specific?" in result

def test_low_confidence_match(mock_requests):
    """Test navigation with low confidence match."""
    mock_response = Mock()
    mock_response.json.return_value = MOCK_LOW_CONFIDENCE
    mock_requests.return_value = mock_response
    
    result = navigate_to("petes")
    
    assert "Did you mean 'Pete's Merch Stand'" in result

def test_service_error(mock_requests):
    """Test handling of service errors."""
    mock_requests.side_effect = Exception("Service unavailable")
    
    result = navigate_to("Pete's stand")
    
    assert "try again" in result

def test_find_location():
    """Test the location service wrapper."""
    with patch('letta_templates.npc_tools.requests.get') as mock_get:
        # Test successful call
        mock_response = Mock()
        mock_response.json.return_value = MOCK_LOCATION_FOUND
        mock_get.return_value = mock_response
        
        result = find_location("Pete's stand")
        assert len(result["locations"]) == 1
        assert result["locations"][0]["name"] == "Pete's Merch Stand"
        
        # Test error handling
        mock_get.side_effect = Exception("Connection error")
        result = find_location("Pete's stand")
        assert result["locations"] == []
        assert "Service error" in result["message"] 