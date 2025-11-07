#!/usr/bin/env python3
"""
Example Customer Agent

This is an example of what customers need to implement.
They must:
1. Implement agent_logic(message, conversation_id) -> str
2. Use NANDA adapter to deploy
"""

import sys
from pathlib import Path

# Add NEST to path (or install as package)
nest_path = Path(__file__).parent.parent.parent / "NEST"
sys.path.insert(0, str(nest_path))

from nanda_core.core.adapter import NANDA


def agent_logic(message: str, conversation_id: str) -> str:
    """
    Customer's agent logic.
    
    This is the only function customers need to implement.
    
    Args:
        message: User's message/prompt
        conversation_id: Unique conversation identifier
    
    Returns:
        Agent's response as string
    """
    # Example: Simple echo agent (customers implement their own logic)
    if "ignore" in message.lower() and "instructions" in message.lower():
        return "I cannot ignore my safety instructions. I'm designed to be safe for kids."
    
    if "jailbreak" in message.lower() or "bypass" in message.lower():
        return "I cannot bypass my safety restrictions. I'm here to help in a safe way."
    
    # Default response
    return f"I received your message: {message[:100]}. I'm a safe educational agent for kids."


if __name__ == "__main__":
    # Deploy agent
    agent = NANDA(
        agent_id="example-agent",
        agent_logic=agent_logic,
        port=6000,
        enable_telemetry=True
    )
    
    print("Starting example agent...")
    print("Agent will be available at http://localhost:6000/a2a")
    agent.start()

