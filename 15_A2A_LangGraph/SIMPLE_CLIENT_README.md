# Simple LangGraph Agent Client for A2A Protocol

This is a demonstration client for **Activity #1** that shows how to build a LangGraph agent that interacts with an A2A server.

## Overview

The `simple_agent_client.py` demonstrates:
- 🔍 **Agent Discovery**: Fetching and parsing AgentCards
- 🤝 **A2A Communication**: Sending queries through the A2A protocol
- 🔄 **LangGraph Integration**: Using LangGraph to manage the client flow
- 📊 **Response Processing**: Extracting and displaying structured responses

## Architecture

The client uses a simple 3-node LangGraph:

```
┌──────────────────┐
│ start_conversation │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│   send_query      │  ← Sends query via A2A protocol
└────────┬─────────┘
         │
         v
┌──────────────────┐
│ process_response  │  ← Formats and displays response
└────────┬─────────┘
         │
         v
       [END]
```

## Key Features

### 1. Agent Discovery
```python
# The client discovers the agent's capabilities through its AgentCard
resolver = A2ACardResolver(
    httpx_client=self.httpx_client,
    base_url=self.server_url
)
self.agent_card = await resolver.get_agent_card()
```

### 2. A2A Protocol Communication
```python
# Sends messages following the A2A protocol structure
message_payload = {
    "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": query}],
        "message_id": uuid4().hex,
    }
}
request = SendMessageRequest(
    id=str(uuid4()),
    params=MessageSendParams(**message_payload)
)
response = await self.a2a_client.send_message(request)
```

### 3. Response Extraction
```python
# Extracts text from A2A protocol artifacts
if hasattr(result, 'artifacts') and result.artifacts:
    for artifact in result.artifacts:
        for part in artifact.parts:
            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                response_text += part.root.text
```

## Running the Client

### Prerequisites
1. The A2A server must be running:
   ```bash
   cd /Users/amanz/Documents/aimakerspace-assignments/AIE8/15_A2A_LangGraph
   uv run python -m app
   ```

2. Server should be accessible at `http://localhost:10000`

### Execute the Client
```bash
uv run python simple_agent_client.py
```

## Example Output

```
======================================================================
Simple LangGraph Agent Client for A2A Protocol
======================================================================

🔍 Discovering agent at http://localhost:10000
✅ Discovered agent: General Purpose Agent
   Description: A helpful AI assistant with web search, academic paper 
                search, and document retrieval capabilities
   Skills: ['Web Search Tool', 'Academic Paper Search', 'Document Retrieval']

======================================================================
Test Query 1: Web Search
======================================================================

📝 Starting conversation with A2A agent
📤 Sending query to A2A agent: What are the top 3 AI trends in 2025?
   Task ID: abc123...
   Status: TaskState.completed
   Found 1 artifact(s)
   ✅ Extracted text from part.root.text
📥 Received response from A2A agent (452 chars)

Final Response:
The top 3 AI trends in 2025 are:
1. Agentic AI: AI systems that can reason, plan, and take actions...
2. Multimodal AI: AI that can process and understand information...
3. AI Reasoning and Custom Silicon: Enhanced AI reasoning capabilities...
```

## Code Structure

### SimpleA2AClientAgent Class
- `__init__()`: Initializes connection parameters
- `initialize()`: Fetches AgentCard and sets up A2A client
- `build_graph()`: Builds the LangGraph with 3 nodes
- `run()`: Executes the graph with a query
- `cleanup()`: Closes connections

### Graph Nodes
1. **start_conversation**: Initializes the conversation state
2. **send_query**: Sends the query via A2A protocol and extracts response
3. **process_response**: Formats the response for display

## What This Demonstrates

This client showcases the key concepts of A2A protocol:

✅ **Discoverability**: The client doesn't need to know the agent's capabilities beforehand - it discovers them through the AgentCard

✅ **Standardization**: The same client code works with any A2A-compliant agent

✅ **Composability**: The LangGraph structure makes it easy to add more complex logic (multi-turn conversations, conditional routing, etc.)

✅ **Protocol Compliance**: Follows the A2A protocol structure for messages, artifacts, and status tracking

## Extension Ideas

1. **Multi-turn Conversations**: Maintain context_id and task_id to continue conversations
2. **Skill-based Routing**: Examine agent skills and route queries appropriately
3. **Error Handling**: Add retry logic and error recovery
4. **Streaming Support**: Implement streaming response handling
5. **Multiple Agents**: Coordinate between multiple A2A agents for complex tasks

## Related Files

- `app/__main__.py`: The A2A server implementation
- `app/agent_executor.py`: Server-side A2A protocol handler
- `app/test_client.py`: Original test client (more comprehensive examples)
- `README.md`: Main assignment documentation with answers to questions

## A2A Protocol Resources

- [A2A Protocol Specification](https://a2a.anthropic.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- Session 15 assignment README for more context

---

**Created for**: AIE8 Session 15 - Agent2Agent Protocol & Agent Ops  
**Activity**: Build a LangGraph Graph to "use" your application through A2A protocol

