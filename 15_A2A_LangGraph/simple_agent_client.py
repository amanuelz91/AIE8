#!/usr/bin/env python3
"""
Simple LangGraph Agent Client for A2A Protocol

This agent acts as a client that makes API calls to the A2A server,
demonstrating how agents can communicate through the A2A protocol.

Activity #1: Build a LangGraph Graph to "use" your application
"""
import logging
import asyncio
from typing import Any, TypedDict, Annotated
from uuid import uuid4

import httpx
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClientAgentState(TypedDict):
    """State for the client agent that uses A2A protocol."""
    messages: Annotated[list, add_messages]
    query: str
    response: str
    context_id: str | None
    task_id: str | None


class SimpleA2AClientAgent:
    """
    A simple LangGraph agent that acts as a client to the A2A server.
    
    This demonstrates how agents can discover and use other agents through
    the A2A protocol, enabling agent-to-agent communication.
    """
    
    def __init__(self, server_url: str = "http://localhost:10000"):
        """
        Initialize the client agent.
        
        Args:
            server_url: URL of the A2A server to connect to
        """
        self.server_url = server_url
        self.httpx_client = None
        self.agent_card = None
        self.a2a_client = None
        
    async def initialize(self):
        """Initialize the A2A client by fetching the agent card."""
        self.httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        
        # Discover the agent capabilities through A2A protocol
        resolver = A2ACardResolver(
            httpx_client=self.httpx_client,
            base_url=self.server_url
        )
        
        logger.info(f"🔍 Discovering agent at {self.server_url}")
        self.agent_card = await resolver.get_agent_card()
        
        logger.info(f"✅ Discovered agent: {self.agent_card.name}")
        logger.info(f"   Description: {self.agent_card.description}")
        logger.info(f"   Skills: {[skill.name for skill in self.agent_card.skills]}")
        
        # Initialize the A2A client
        self.a2a_client = A2AClient(
            httpx_client=self.httpx_client,
            agent_card=self.agent_card
        )
        
    async def cleanup(self):
        """Clean up resources."""
        if self.httpx_client:
            await self.httpx_client.aclose()
    
    def build_graph(self) -> StateGraph:
        """
        Build the LangGraph that defines the client agent's behavior.
        
        The graph has three nodes:
        1. start_conversation: Initiates communication with the A2A server
        2. send_query: Sends the user's query to the A2A server
        3. process_response: Processes and formats the server's response
        """
        
        # Define node functions
        async def start_conversation(state: ClientAgentState) -> dict[str, Any]:
            """Node: Start a new conversation."""
            logger.info("📝 Starting conversation with A2A agent")
            return {
                "messages": [HumanMessage(content="Starting conversation with A2A agent")],
            }
        
        async def send_query(state: ClientAgentState) -> dict[str, Any]:
            """Node: Send query to the A2A server."""
            query = state["query"]
            logger.info(f"📤 Sending query to A2A agent: {query}")
            
            # Create message payload following A2A protocol
            message_payload = {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": query}],
                    "message_id": uuid4().hex,
                }
            }
            
            # Add context if continuing a conversation
            if state.get("context_id") and state.get("task_id"):
                message_payload["message"]["context_id"] = state["context_id"]
                message_payload["message"]["task_id"] = state["task_id"]
            
            # Send request through A2A protocol
            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**message_payload)
            )
            
            response = await self.a2a_client.send_message(request)
            
            # Extract response data (following A2A protocol structure)
            result = response.root.result
            context_id = result.context_id
            task_id = result.id
            
            logger.info(f"   Task ID: {task_id}")
            logger.info(f"   Status: {result.status.state if hasattr(result, 'status') else 'unknown'}")
            
            # Get the response text from artifacts (following A2A protocol Part structure)
            response_text = ""
            if hasattr(result, 'artifacts') and result.artifacts:
                logger.info(f"   Found {len(result.artifacts)} artifact(s)")
                for artifact in result.artifacts:
                    if hasattr(artifact, 'parts') and artifact.parts:
                        for part in artifact.parts:
                            # The Part object has a 'root' field which could be TextPart
                            if hasattr(part, 'root'):
                                root_obj = part.root
                                # Check if root has text attribute (TextPart)
                                if hasattr(root_obj, 'text'):
                                    response_text += root_obj.text
                                    logger.info(f"   ✅ Extracted text from part.root.text")
                                elif hasattr(root_obj, '__dict__'):
                                    logger.debug(f"   Root object type: {type(root_obj)}, attrs: {list(root_obj.__dict__.keys())}")
                            elif hasattr(part, 'text'):
                                response_text += part.text
                                logger.info(f"   ✅ Extracted text from part.text")
            
            if not response_text:
                response_text = "No response text received (task may still be processing)"
                
            logger.info(f"📥 Received response from A2A agent ({len(response_text)} chars)")
            
            return {
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=response_text)
                ],
                "response": response_text,
                "context_id": context_id,
                "task_id": task_id,
            }
        
        async def process_response(state: ClientAgentState) -> dict[str, Any]:
            """Node: Process and format the response."""
            logger.info("✅ Processing response from A2A agent")
            
            response = state["response"]
            formatted_response = f"A2A Agent Response:\n\n{response}"
            
            return {
                "messages": [AIMessage(content=formatted_response)],
            }
        
        # Build the graph
        graph = StateGraph(ClientAgentState)
        
        # Add nodes
        graph.add_node("start_conversation", start_conversation)
        graph.add_node("send_query", send_query)
        graph.add_node("process_response", process_response)
        
        # Define edges
        graph.set_entry_point("start_conversation")
        graph.add_edge("start_conversation", "send_query")
        graph.add_edge("send_query", "process_response")
        graph.add_edge("process_response", END)
        
        return graph.compile()
    
    async def run(self, query: str) -> dict[str, Any]:
        """
        Run the client agent with a query.
        
        Args:
            query: The query to send to the A2A server
            
        Returns:
            The final state after processing
        """
        graph = self.build_graph()
        
        # Run the graph
        result = await graph.ainvoke({
            "messages": [],
            "query": query,
            "response": "",
            "context_id": None,
            "task_id": None,
        })
        
        return result


async def main():
    """
    Main function demonstrating the simple A2A client agent.
    
    This example shows:
    1. Agent discovery through AgentCard
    2. Sending queries through A2A protocol
    3. Processing structured responses
    """
    print("=" * 70)
    print("Simple LangGraph Agent Client for A2A Protocol")
    print("=" * 70)
    print()
    
    # Initialize the client agent
    client_agent = SimpleA2AClientAgent(server_url="http://localhost:10000")
    
    try:
        # Initialize A2A connection
        await client_agent.initialize()
        
        print("\n" + "=" * 70)
        print("Test Query 1: Web Search")
        print("=" * 70)
        
        # Test query 1: Web search
        result1 = await client_agent.run(
            "What are the top 3 AI trends in 2025? Be concise."
        )
        print(f"\nFinal Response:\n{result1['response']}")
        
        print("\n" + "=" * 70)
        print("Test Query 2: Academic Search")
        print("=" * 70)
        
        # Test query 2: Academic papers
        result2 = await client_agent.run(
            "Find recent papers on multimodal AI and summarize key findings."
        )
        print(f"\nFinal Response:\n{result2['response']}")
        
        print("\n" + "=" * 70)
        print("✅ Client agent completed successfully!")
        print("=" * 70)
        
    finally:
        # Cleanup
        await client_agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

