"""Production caching utilities for embeddings and LLM calls."""

import hashlib
import json
import os
from typing import Optional, Any, Dict, List
import numpy as np

from langchain.embeddings import CacheBackedEmbeddings as LangChainCacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain_core.caches import InMemoryCache
from langchain_community.cache import SQLiteCache, RedisCache
from langchain_core.globals import set_llm_cache
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.caches import BaseCache
from langchain_core.language_models.llms import LLM
from langchain_core.runnables import RunnableConfig
import redis
from redis import Redis


class CacheBackedEmbeddings:
    """Production cache-backed embeddings using OpenAI."""
    
    def __init__(
        self, 
        model: str = "text-embedding-3-small",
        cache_dir: str = "./cache/embeddings",
        batch_size: int = 32,
        use_redis: bool = False,
        redis_url: Optional[str] = None
    ):
        """Initialize cache-backed embeddings.
        
        Args:
            model: OpenAI embedding model name
            cache_dir: Directory to store embedding cache
            batch_size: Batch size for embedding calls
            use_redis: Whether to use Redis for embedding cache
            redis_url: Redis connection URL
        """
        self.model = model
        self.cache_dir = cache_dir
        self.batch_size = batch_size
        self.use_redis = use_redis
        
        # Create base embeddings
        self.base_embeddings = OpenAIEmbeddings(model=model)
        
        # Create safe namespace from model name
        safe_namespace = hashlib.md5(model.encode()).hexdigest()
        
        if use_redis and redis_url:
            # Use Redis for embedding cache
            from langchain.storage import RedisStore
            store = RedisStore(redis_url=redis_url, namespace=f"embeddings:{safe_namespace}")
        else:
            # Use local file store
            store = LocalFileStore(cache_dir)
        
        self.cached_embeddings = LangChainCacheBackedEmbeddings.from_bytes_store(
            self.base_embeddings, 
            store, 
            namespace=safe_namespace,
            batch_size=batch_size
        )
    
    def get_embeddings(self):
        """Get the cached embeddings instance."""
        return self.cached_embeddings


class SemanticLLMCache(BaseCache):
    """Semantic LLM cache using Redis and embeddings for similarity matching."""
    
    def __init__(
        self,
        redis_client: Redis,
        embedding_model: OpenAIEmbeddings,
        similarity_threshold: float = 0.85,
        namespace: str = "semantic_cache"
    ):
        """Initialize semantic LLM cache.
        
        Args:
            redis_client: Redis client instance
            embedding_model: Embedding model for semantic similarity
            similarity_threshold: Cosine similarity threshold for cache hits (0-1)
            namespace: Redis namespace prefix
        """
        self.redis_client = redis_client
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.namespace = namespace
        # Store embeddings index for faster lookup
        self._embedding_index_key = f"{self.namespace}:index"
    
    def _get_key(self, prompt: str, llm_string: str) -> str:
        """Generate cache key."""
        cache_key = f"{self.namespace}:{hashlib.sha256((prompt + llm_string).encode()).hexdigest()}"
        return cache_key
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def _serialize_response(self, response: Any) -> str:
        """Serialize response for storage."""
        if hasattr(response, 'content'):
            # Handle AIMessage or similar
            return json.dumps({"type": "message", "content": response.content})
        elif isinstance(response, str):
            return json.dumps({"type": "str", "content": response})
        else:
            return json.dumps({"type": "other", "content": str(response)})
    
    def _deserialize_response(self, data: str) -> Any:
        """Deserialize response from storage."""
        try:
            parsed = json.loads(data)
            if parsed.get("type") == "message":
                from langchain_core.messages import AIMessage
                return AIMessage(content=parsed["content"])
            elif parsed.get("type") == "str":
                return parsed["content"]
            else:
                return parsed["content"]
        except Exception:
            return data
    
    def lookup(self, prompt: str, llm_string: str, llm: Optional[LLM] = None) -> Optional[Any]:
        """Look up cached response using semantic similarity."""
        try:
            # Get embedding for the prompt
            prompt_embedding = self.embedding_model.embed_query(prompt)
            
            # Search for similar cached prompts using SCAN for better performance
            best_match = None
            best_similarity = 0.0
            cursor = 0
            
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor,
                    match=f"{self.namespace}:*",
                    count=100
                )
                
                for key in keys:
                    # Skip the index key
                    if key.decode() == self._embedding_index_key:
                        continue
                    
                    try:
                        cached_data = self.redis_client.get(key)
                        if cached_data:
                            data = json.loads(cached_data)
                            cached_prompt_embedding = data.get("prompt_embedding")
                            cached_llm_string = data.get("llm_string")
                            
                            # Check if LLM string matches
                            if cached_llm_string != llm_string:
                                continue
                            
                            # Calculate similarity
                            similarity = self._cosine_similarity(prompt_embedding, cached_prompt_embedding)
                            
                            if similarity >= self.similarity_threshold and similarity > best_similarity:
                                best_similarity = similarity
                                response_data = data.get("response")
                                best_match = self._deserialize_response(response_data) if isinstance(response_data, str) else response_data
                    except Exception:
                        # Skip invalid cache entries
                        continue
                
                if cursor == 0:
                    break
            
            return best_match
        except Exception as e:
            # If lookup fails, return None (cache miss)
            return None
    
    def update(self, prompt: str, llm_string: str, return_val: Any, llm: Optional[LLM] = None) -> None:
        """Store response in cache with prompt embedding."""
        try:
            # Get embedding for the prompt
            prompt_embedding = self.embedding_model.embed_query(prompt)
            
            # Serialize response
            serialized_response = self._serialize_response(return_val)
            
            # Create cache entry
            cache_key = self._get_key(prompt, llm_string)
            cache_data = {
                "prompt": prompt,
                "prompt_embedding": prompt_embedding,
                "llm_string": llm_string,
                "response": serialized_response
            }
            
            # Store in Redis with 7 day expiration
            self.redis_client.setex(
                cache_key,
                7 * 24 * 60 * 60,  # 7 days
                json.dumps(cache_data, default=str)
            )
        except Exception as e:
            # If update fails, silently continue (cache is optional)
            pass
    
    def clear(self, **kwargs: Any) -> None:
        """Clear all cache entries."""
        try:
            cursor = 0
            keys_to_delete = []
            
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor,
                    match=f"{self.namespace}:*",
                    count=100
                )
                keys_to_delete.extend(keys)
                
                if cursor == 0:
                    break
            
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
        except Exception:
            pass


def setup_llm_cache(
    cache_type: str = "memory", 
    cache_path: Optional[str] = None,
    redis_url: Optional[str] = None,
    use_semantic: bool = False,
    similarity_threshold: float = 0.85
):
    """Set up LLM caching.
    
    Args:
        cache_type: Type of cache - "memory", "sqlite", or "redis"
        cache_path: Path for SQLite cache file
        redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
        use_semantic: Whether to use semantic caching (requires Redis)
        similarity_threshold: Similarity threshold for semantic caching (0-1)
    """
    if cache_type == "memory":
        set_llm_cache(InMemoryCache())
    elif cache_type == "sqlite":
        db_path = cache_path or "./cache/llm_cache.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        set_llm_cache(SQLiteCache(database_path=db_path))
    elif cache_type == "redis":
        if not redis_url:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        if use_semantic:
            # Use semantic caching
            redis_client = redis.from_url(redis_url)
            embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
            semantic_cache = SemanticLLMCache(
                redis_client=redis_client,
                embedding_model=embedding_model,
                similarity_threshold=similarity_threshold
            )
            set_llm_cache(semantic_cache)
        else:
            # Use standard Redis cache
            set_llm_cache(RedisCache(redis_url=redis_url))
    else:
        raise ValueError(f"Unsupported cache type: {cache_type}")

