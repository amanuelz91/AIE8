# Advanced Build: Semantic Caching with Docker

This directory contains a production-ready RAG application with **semantic LLM caching** using Redis, running in Docker.

## 🎯 Features

- **Semantic LLM Caching**: Uses embeddings to find similar queries instead of exact matches
- **Redis-based Storage**: Persistent, scalable caching with Redis
- **Docker Deployment**: Easy local deployment with Docker Compose
- **FastAPI API**: RESTful API for querying the RAG system
- **LangGraph Agent Integration**: Optional agent-based querying

## 🏗️ Architecture

### Caching Strategy

**Before (Inefficient):**
- In-memory exact-match caching
- Lost on restart
- No semantic similarity

**After (Advanced):**
- Redis-based persistent storage
- Semantic similarity matching (85% threshold)
- Embedding-based query matching
- Survives restarts

### How Semantic Caching Works

1. **Query Embedding**: When a query comes in, it's embedded using OpenAI's embedding model
2. **Similarity Search**: The cache searches for previously cached queries with similar embeddings
3. **Threshold Matching**: If similarity ≥ 0.85, return cached response
4. **Cache Miss**: If no similar query found, call LLM and cache the result

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

### Setup

1. **Set your OpenAI API key:**
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

2. **Start the application:**
   ```bash
   docker-compose up --build
   ```

3. **The application will be available at:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### Usage

#### Query the RAG System

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the Federal Pell Grant Program?",
    "use_agent": false
  }'
```

#### Query with LangGraph Agent

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the Federal Pell Grant Program?",
    "use_agent": true
  }'
```

#### Check Health

```bash
curl http://localhost:8000/health
```

## 📁 Project Structure

```
16_Production_RAG_and_Guardrails/
├── app.py                    # FastAPI application entry point
├── Dockerfile               # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── langgraph_agent_lib/
│   ├── caching.py          # Semantic caching implementation
│   ├── rag.py              # RAG chain implementation
│   └── agents.py           # LangGraph agent
├── data/                    # PDF documents for RAG
└── pyproject.toml          # Python dependencies
```

## 🔧 Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: Model to use (default: `gpt-4o-mini`)
- `REDIS_URL`: Redis connection URL (default: `redis://redis:6379/0`)
- `PORT`: Application port (default: `8000`)

### Cache Settings

In `langgraph_agent_lib/caching.py`, you can adjust:

- `similarity_threshold`: Minimum similarity for cache hits (default: 0.85)
- Cache expiration: Currently set to 7 days

## 🧪 Testing Semantic Caching

1. **First Query** (cache miss):
   ```bash
   curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is a Pell Grant?"}'
   ```

2. **Similar Query** (should hit cache):
   ```bash
   curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "Tell me about the Pell Grant program"}'
   ```

The second query should return faster because it matches semantically with the first query.

## 📊 Monitoring

### Redis Cache Status

You can check Redis directly:

```bash
docker-compose exec redis redis-cli
> KEYS semantic_cache:*
> GET semantic_cache:<key>
```

### Application Logs

```bash
docker-compose logs -f app
```

## 🛠️ Development

### Running Locally (without Docker)

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Start Redis:
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. Set environment variables:
   ```bash
   export REDIS_URL=redis://localhost:6379/0
   export OPENAI_API_KEY=your_key
   ```

4. Run the application:
   ```bash
   uv run python app.py
   ```

## 🐛 Troubleshooting

### Redis Connection Issues

If you see Redis connection errors:
1. Check that Redis container is running: `docker-compose ps`
2. Verify Redis URL: `echo $REDIS_URL`
3. Check Redis logs: `docker-compose logs redis`

### Cache Not Working

1. Check Redis is accessible: `docker-compose exec redis redis-cli ping`
2. Verify semantic cache is enabled in `app.py`
3. Check application logs for cache-related errors

### PDF Loading Issues

1. Ensure PDF files exist in `data/` directory
2. Check application startup logs for PDF loading messages
3. Verify file permissions

## 📝 Notes

- The semantic cache uses cosine similarity with a threshold of 0.85
- Cache entries expire after 7 days
- Embeddings are computed using `text-embedding-3-small`
- The cache is shared across all queries to the same LLM model

## 🎓 Learning Points

1. **Semantic vs Exact Match**: Semantic caching finds similar queries, not just identical ones
2. **Redis for Persistence**: Cache survives application restarts
3. **Embedding-based Similarity**: Uses vector similarity to find related queries
4. **Production-ready**: Docker deployment makes it easy to scale and deploy

## 📚 References

- [LangChain Caching](https://python.langchain.com/docs/modules/model_io/caching/)
- [Redis Documentation](https://redis.io/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

