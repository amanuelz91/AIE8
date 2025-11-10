"""Test script to verify semantic caching is working."""

import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from langgraph_agent_lib.caching import setup_llm_cache, SemanticLLMCache
from langgraph_agent_lib.rag import ProductionRAGChain
from langchain_openai.embeddings import OpenAIEmbeddings
import redis

def test_semantic_cache():
    """Test semantic caching functionality."""
    print("🧪 Testing Semantic Caching...")
    
    # Set up Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"📦 Connecting to Redis: {redis_url}")
    
    try:
        redis_client = redis.from_url(redis_url)
        redis_client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Make sure Redis is running: docker run -d -p 6379:6379 redis:7-alpine")
        return False
    
    # Set up semantic cache
    try:
        embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
        semantic_cache = SemanticLLMCache(
            redis_client=redis_client,
            embedding_model=embedding_model,
            similarity_threshold=0.85
        )
        print("✅ Semantic cache initialized")
    except Exception as e:
        print(f"❌ Failed to initialize semantic cache: {e}")
        return False
    
    # Test cache operations
    test_prompt = "What is a Pell Grant?"
    test_llm_string = "gpt-4o-mini"
    test_response = "A Pell Grant is a federal grant program for students."
    
    # Store in cache
    print(f"\n📝 Storing test response in cache...")
    semantic_cache.update(test_prompt, test_llm_string, test_response)
    print("✅ Response stored")
    
    # Test exact match lookup
    print(f"\n🔍 Testing exact match lookup...")
    result = semantic_cache.lookup(test_prompt, test_llm_string)
    if result == test_response:
        print("✅ Exact match lookup successful")
    else:
        print(f"❌ Exact match lookup failed. Expected: {test_response}, Got: {result}")
        return False
    
    # Test semantic similarity lookup
    similar_prompts = [
        "Tell me about Pell Grants",
        "What are Pell Grants?",
        "Explain the Pell Grant program",
        "What is a federal student grant?"
    ]
    
    print(f"\n🔍 Testing semantic similarity lookup...")
    for similar_prompt in similar_prompts:
        result = semantic_cache.lookup(similar_prompt, test_llm_string)
        if result:
            print(f"✅ Found similar match for: '{similar_prompt}'")
        else:
            print(f"⚠️  No similar match found for: '{similar_prompt}'")
    
    # Clear cache
    print(f"\n🧹 Clearing cache...")
    semantic_cache.clear()
    print("✅ Cache cleared")
    
    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_semantic_cache()
    sys.exit(0 if success else 1)

