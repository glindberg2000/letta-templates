# 1. Update client configuration
direct_client = Client(
    api_key=settings.letta_api_key,
    enable_message_streaming=False,
    response_format="messages",  # Get full response objects
    minimal_response=False  # Don't simplify to strings
)

# 2. Add response type logging
@router.post("/chat/v3", response_model=ChatResponse)
async def chat_with_npc_v3(request: ChatRequest):
    try:
        # ... existing code ...
        
        response = chat_with_agent(
            client=direct_client,
            agent_id=mapping.letta_agent_id,
            message=request.message,
            role=message_role,
            name=request.context.get("participant_name")
        )
        
        logger.info(f"Response type: {type(response)}")
        
        # Extract navigation actions from tool calls
        action = {"type": "none"}
        if hasattr(response, 'messages'):
            for message in response.messages:
                if hasattr(message, 'tool_call'):
                    tool = message.tool_call
                    logger.info(f"Found tool call: {tool.name}")
                    
                    if tool.name == 'navigate_to':
                        action = {
                            "type": "navigate",
                            "destination": json.loads(tool.arguments).get('destination'),
                            "request_heartbeat": True
                        }
                        break  # Use first navigation action
        
        return ChatResponse(
            message=str(response),  # Get text content
            action=action,
            metadata={"debug": "V3 response with tool extraction"}
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return ChatResponse(
            message="Something went wrong!",
            action={"type": "none"},
            metadata={"error": str(e)}
        ) 