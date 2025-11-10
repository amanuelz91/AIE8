"""Production RAG application with semantic caching via Docker."""

import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from langgraph_agent_lib.caching import setup_llm_cache, CacheBackedEmbeddings
from langgraph_agent_lib.rag import ProductionRAGChain
from langgraph_agent_lib.agents import create_langgraph_agent

# Initialize FastAPI app
app = FastAPI(
    title="Production RAG with Semantic Caching",
    description="RAG application with Redis-based semantic LLM caching",
    version="1.0.0"
)


class QueryRequest(BaseModel):
    """Request model for RAG queries."""
    question: str
    use_agent: bool = False


class QueryResponse(BaseModel):
    """Response model for RAG queries."""
    answer: str
    cached: bool = False
    similarity: Optional[float] = None


# Global variables for RAG chain and agent
rag_chain: Optional[ProductionRAGChain] = None
agent = None


@app.on_event("startup")
async def startup_event():
    """Initialize the RAG chain and caching on startup."""
    import sys
    global rag_chain, agent
    
    print("🚀 Starting Production RAG Application with Semantic Caching...", flush=True)
    sys.stdout.flush()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not set. RAG functionality will not work.", flush=True)
        print("   Set it with: export OPENAI_API_KEY=your_key", flush=True)
        sys.stdout.flush()
    
    # Set up semantic caching with Redis
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    print(f"📦 Setting up semantic LLM cache with Redis: {redis_url}", flush=True)
    sys.stdout.flush()
    
    try:
        setup_llm_cache(
            cache_type="redis",
            redis_url=redis_url,
            use_semantic=True,
            similarity_threshold=0.85
        )
        print("✅ Semantic LLM cache configured successfully", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"⚠️  Warning: Could not set up Redis cache: {e}", flush=True)
        print("   Falling back to in-memory cache", flush=True)
        sys.stdout.flush()
        try:
            setup_llm_cache(cache_type="memory")
        except Exception as e2:
            print(f"⚠️  Could not set up in-memory cache either: {e2}", flush=True)
            sys.stdout.flush()
    
    # Find a PDF file in the data directory
    data_dir = Path(__file__).parent / "data"
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("⚠️  Warning: No PDF files found in data directory", flush=True)
        print("   Application will start but RAG queries will fail", flush=True)
        sys.stdout.flush()
        return
    
    # Use the first PDF file
    pdf_file = pdf_files[0]
    print(f"📄 Loading RAG chain with document: {pdf_file.name}", flush=True)
    sys.stdout.flush()
    
    try:
        # Initialize RAG chain with Redis-backed embeddings
        print("   Initializing embeddings and vector store...", flush=True)
        sys.stdout.flush()
        rag_chain = ProductionRAGChain(
            file_path=str(pdf_file),
            embedding_model="text-embedding-3-small",
            llm_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            cache_dir="./cache"
        )
        print("✅ RAG chain initialized successfully", flush=True)
        sys.stdout.flush()
        
        # Create LangGraph agent with RAG tool
        print("   Creating LangGraph agent...", flush=True)
        sys.stdout.flush()
        agent = create_langgraph_agent(
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            rag_chain=rag_chain
        )
        print("✅ LangGraph agent initialized successfully", flush=True)
        sys.stdout.flush()
        
    except Exception as e:
        import traceback
        print(f"❌ Error initializing RAG chain: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        sys.stdout.flush()
        # Don't raise - allow app to start even if RAG fails
        print("⚠️  Application will start but RAG queries will fail", flush=True)
        sys.stdout.flush()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Production RAG Application with Semantic Caching",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/query": "POST - Query the RAG system",
            "/docs": "API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    try:
        import redis
        redis_client = redis.from_url(redis_url)
        redis_client.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "rag_chain": "initialized" if rag_chain is not None else "not_initialized"
    }


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query the RAG system."""
    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain not initialized. Please check the startup logs."
        )
    
    try:
        if request.use_agent and agent is not None:
            # Use LangGraph agent
            from langchain_core.messages import HumanMessage
            messages = [HumanMessage(content=request.question)]
            result = agent.invoke({"messages": messages})
            
            # Extract the final answer from agent messages
            if result.get("messages"):
                last_message = result["messages"][-1]
                answer = last_message.content if hasattr(last_message, "content") else str(last_message)
            else:
                answer = str(result)
        else:
            # Use direct RAG chain
            result = rag_chain.invoke(request.question)
            answer = result.content if hasattr(result, "content") else str(result)
        
        # Note: We can't easily detect if the response was cached in this implementation
        # The caching happens at the LangChain level, so we'll return cached=False
        # In a production system, you might want to add logging or metrics to track this
        
        return QueryResponse(
            answer=answer,
            cached=False,  # Semantic cache detection would require additional instrumentation
            similarity=None
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )

