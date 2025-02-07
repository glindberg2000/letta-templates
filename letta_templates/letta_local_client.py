"""
Local API test client for debugging FastAPI endpoints.
"""
import time
import json
import requests
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class MessageLog:
    timestamp: float
    request: Dict
    response: Dict
    duration: float

class LocalAPIClient:
    """Client for testing local FastAPI endpoints with message tracking."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.message_history: List[MessageLog] = []
        self.last_message_time: Optional[float] = None
    
    def send_message(self, 
                    npc_id: str,
                    participant_id: str,
                    message: str,
                    system_prompt: Optional[str] = None,
                    context: Optional[str] = None) -> Dict:
        """
        Send message to local API endpoint with timing and duplicate tracking.
        
        Args:
            npc_id: ID of the NPC/agent
            participant_id: ID of the user
            message: Message content
            system_prompt: Optional system prompt
            context: Optional context
            
        Returns:
            Dict containing response and metadata
        """
        current_time = time.time()
        time_since_last = None  # Initialize here
        
        # Check for potential duplicates
        if self.last_message_time:
            time_since_last = current_time - self.last_message_time
            if time_since_last < 1.0:  # Alert on messages less than 1 second apart
                print(f"\nWARNING: Rapid message detected! {time_since_last:.3f}s since last message")
        
        payload = {
            "npc_id": npc_id,
            "participant_id": participant_id,
            "message": message,
            "system_prompt": system_prompt,
            "context": context
        }
        
        start_time = time.time()
        try:
            response = requests.post(self.endpoint, json=payload)
            response.raise_for_status()
            response_data = response.json()
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
        
        duration = time.time() - start_time
        
        # Log the interaction
        log_entry = MessageLog(
            timestamp=current_time,
            request=payload,
            response=response_data,
            duration=duration
        )
        self.message_history.append(log_entry)
        self.last_message_time = current_time
        
        return {
            "raw_response": response_data,
            "parsed_message": self._extract_message(response_data),
            "duration": duration,
            "time_since_last": time_since_last
        }
    
    def _extract_message(self, response: Dict) -> Optional[str]:
        """Extract message content from response based on format."""
        # Add logic to parse different response formats
        return response.get("message")
    
    def print_conversation_history(self):
        """Display full conversation history with timing details."""
        print("\nConversation History:")
        print("-" * 50)
        for i, log in enumerate(self.message_history, 1):
            print(f"\nMessage {i}:")
            print(f"Time: {time.strftime('%H:%M:%S', time.localtime(log.timestamp))}")
            print(f"Request: {json.dumps(log.request, indent=2)}")
            print(f"Response: {json.dumps(log.response, indent=2)}")
            print(f"Duration: {log.duration:.3f}s")
            if i > 1:
                time_gap = log.timestamp - self.message_history[i-2].timestamp
                print(f"Time since previous: {time_gap:.3f}s")
            print("-" * 50) 
    
    def get_messages(self, agent_id):
        """Get message history for an agent."""
        return self.message_history
    
    def get_agent(self, agent_id):
        """Get agent info."""
        return {
            'id': agent_id,
            'name': f'NPC_{agent_id[:8]}',  # Use first 8 chars of ID
            'description': 'Local test agent'
        }