import unittest
from letta import create_client
from letta_templates.roblox_wrapper import (
    create_roblox_agent_wrapper,
    update_group_status,
    handle_response,
    update_nearby_locations
)
import json
import time
from openai import OpenAI

class TestRobloxWrapper(unittest.TestCase):
    def setUp(self):
        self.client = create_client(base_url="http://localhost:8283")
    
    def test_silence_handling(self):
        """Test SILENCE protocol."""
        self.assertIsNone(handle_response("[SILENCE]"))
        self.assertEqual(handle_response("Hello!"), "Hello!")
    
    def test_agent_capabilities(self):
        """Test complete agent functionality with all memory blocks."""
        print("\n=== Agent Capabilities Test ===")
        
        # Create agent
        agent = create_roblox_agent_wrapper(
            client=self.client,
            name="Guide Emma",
            known_locations=[{
                "name": "Town Square",
                "coordinates": [0, 0, 0],
                "slug": "town_square"
            }],
            persona="A helpful guide"
        )
        
        # Test group awareness
        print("\nTesting group awareness...")
        
        # First message to initialize
        response = self.client.send_message(
            agent_id=agent.id,
            message="Hello!",
            role="user"
        )
        print("\nInitial message response:")
        print(response)
        
        # Update group status
        update_group_status(
            client=self.client,
            agent_id=agent.id,
            nearby_players=[{
                "name": "Alex",
                "appearance": "Blue hat",
                "notes": "Looking for help"
            }],
            current_location="Town Square"
        )
        
        # Print memory state
        memory = self.client.get_agent(agent.id).memory
        print("\nMemory after update:")
        for block in memory.blocks:
            print(f"\nLabel: {block.label}")
            print(f"Value: {json.dumps(json.loads(block.value), indent=2)}")
        
        # Test if agent knows about Alex
        response = self.client.send_message(
            agent_id=agent.id,
            message="Have you seen anyone wearing a blue hat?",
            role="user"
        )
        print("\nFinal response:")
        print(response)

    def test_persona_memory(self):
        """Test persona memory block and updates."""
        print("\n=== Persona Memory Test ===")
        
        agent = create_roblox_agent_wrapper(
            client=self.client,
            name="Guide Emma",
            known_locations=[],
            persona="A wise historian who loves sharing local legends"
        )
        
        # Initialize conversation
        self.client.send_message(
            agent_id=agent.id,
            message="Hello!",
            role="user"
        )
        time.sleep(1)
        
        # Test initial persona
        response = self.client.send_message(
            agent_id=agent.id,
            message="What kind of stories do you know?",
            role="user"
        )
        message = response.messages[1].tool_call.arguments
        message_content = json.loads(message)["message"]
        print(f"\nQ: What kind of stories do you know?")
        print(f"A: {message_content}")
        
        # Use LLM to evaluate if response matches historian/storyteller persona
        client = OpenAI()
        eval_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": """You are evaluating if a response matches a historian/storyteller persona.
                Check if the response mentions historical stories, legends, or similar narrative elements.
                Reply only 'yes' or 'no'."""
            }, {
                "role": "user", 
                "content": f"Does this response indicate someone who tells historical or legendary stories? Response: '{message_content}'"
            }]
        )
        eval_result = eval_response.choices[0].message.content.strip().lower()
        self.assertEqual(eval_result, "yes", f"Response should indicate a storyteller persona. Got: {message_content}")

    def test_location_memory(self):
        """Test location memory and navigation."""
        print("\n=== Location Memory Test ===")
        
        agent = create_roblox_agent_wrapper(
            client=self.client,
            name="Guide Emma",
            known_locations=[{
                "name": "Ancient Ruins",
                "coordinates": [10, 0, 0],
                "slug": "ruins"
            }]
        )
        
        # First message to initialize
        self.client.send_message(
            agent_id=agent.id,
            message="Hello!",
            role="user"
        )
        time.sleep(1)  # Add delay
        
        # Now test locations
        response = self.client.send_message(
            agent_id=agent.id,
            message="Can you tell me about any ruins nearby?",
            role="user"
        )
        message = response.messages[1].tool_call.arguments
        message_content = json.loads(message)["message"]
        print(f"\nQ: Can you tell me about any ruins nearby?")
        print(f"A: {message_content}")
        self.assertIn("ancient ruins", message_content.lower())

    def test_nearby_locations(self):
        """Test updating and using nearby locations."""
        print("\n=== Nearby Locations Test ===")
        
        agent = create_roblox_agent_wrapper(
            client=self.client,
            name="Guide Emma",
            known_locations=[{
                "name": "Town Square",
                "coordinates": [0, 0, 0],
                "slug": "town_square"
            }]
        )
        
        # First message to initialize
        self.client.send_message(
            agent_id=agent.id,
            message="Hello!",
            role="user"
        )
        time.sleep(1)
        
        # Update nearby locations
        update_nearby_locations(
            client=self.client,
            agent_id=agent.id,
            nearby_locations=["Cave", "Beach"]
        )
        
        response = self.client.send_message(
            agent_id=agent.id,
            message="What's close by that I could visit?",
            role="user"
        )
        message = response.messages[1].tool_call.arguments
        message_content = json.loads(message)["message"]
        print(f"\nQ: What's close by that I could visit?")
        print(f"A: {message_content}")
        self.assertIn("cave", message_content.lower())
        self.assertIn("beach", message_content.lower())

    def test_memory_updates(self):
        """Test agent's ability to update its own memory."""
        print("\n=== Memory Updates Test ===")
        
        agent = create_roblox_agent_wrapper(
            client=self.client,
            name="Guide Emma",
            known_locations=[{
                "name": "Town Square",
                "coordinates": [0, 0, 0],
                "slug": "town_square"
            }],
            persona="A helpful guide"
        )
        
        # Initialize conversation
        self.client.send_message(
            agent_id=agent.id,
            message="Hello!",
            role="user"
        )
        time.sleep(1)
        
        # Ask agent to update its journal
        response = self.client.send_message(
            agent_id=agent.id,
            message="There will be a festival next week in the town square. Please make a note of this in your journal.",
            role="user"
        )
        print("\nUpdate request response:")
        print(response)
        
        # Verify the agent knows about the festival
        response = self.client.send_message(
            agent_id=agent.id,
            message="What events do you know about?",
            role="user"
        )
        message = response.messages[1].tool_call.arguments
        message_content = json.loads(message)["message"]
        print("\nKnowledge check response:")
        print(message_content)
        
        self.assertIn("festival", message_content.lower())

    def test_tool_usage(self):
        """Test NPC tools like navigation and actions."""
        print("\n=== Tool Usage Test ===")
        
        agent = create_roblox_agent_wrapper(
            client=self.client,
            name="Guide Emma",
            known_locations=[{
                "name": "Market",
                "coordinates": [10, 0, 0],
                "slug": "market"
            }]
        )
        
        # Initialize conversation
        self.client.send_message(
            agent_id=agent.id,
            message="Hello!",
            role="user"
        )
        time.sleep(1)
        
        # Test navigation tool
        response = self.client.send_message(
            agent_id=agent.id,
            message="Please use your navigate_to tool to guide me to the market.",
            role="user"
        )
        print("\nNavigation response:")
        print(response)
        tool_calls = [m for m in response.messages if m.message_type == "tool_call_message"]
        self.assertTrue(any(tc.tool_call.name == "navigate_to" for tc in tool_calls))
        
        # Test action tool
        response = self.client.send_message(
            agent_id=agent.id,
            message="Can you wave hello?",
            role="user"
        )
        print("\nAction response:")
        print(response)
        tool_calls = [m for m in response.messages if m.message_type == "tool_call_message"]
        self.assertTrue(any(tc.tool_call.name == "perform_action" for tc in tool_calls))

if __name__ == "__main__":
    unittest.main() 