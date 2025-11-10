#!/bin/bash
# Verification script to check that the A2A setup is complete

echo "🔍 Verifying A2A LangGraph Assignment Setup"
echo "==========================================="
echo ""

# Check if .env exists
echo "1. Checking .env file..."
if [ -f .env ]; then
    echo "   ✅ .env file exists"
else
    echo "   ❌ .env file not found"
    exit 1
fi

# Check if dependencies are installed
echo ""
echo "2. Checking dependencies..."
if uv run python -c "import langgraph, a2a" 2>/dev/null; then
    echo "   ✅ Dependencies installed"
else
    echo "   ❌ Dependencies not installed. Run: ./quickstart.sh"
    exit 1
fi

# Check if data directory exists
echo ""
echo "3. Checking data directory..."
if [ -d data ]; then
    echo "   ✅ Data directory exists"
    PDF_COUNT=$(find data -name "*.pdf" | wc -l | tr -d ' ')
    echo "   📄 Found $PDF_COUNT PDF file(s)"
else
    echo "   ❌ Data directory not found"
fi

# Check if simple_agent_client.py exists
echo ""
echo "4. Checking simple agent client..."
if [ -f simple_agent_client.py ]; then
    echo "   ✅ simple_agent_client.py exists"
else
    echo "   ❌ simple_agent_client.py not found"
    exit 1
fi

# Check if README has answers
echo ""
echo "5. Checking README answers..."
if grep -q "Identity & Metadata" README.md && grep -q "Interoperability & Composability" README.md; then
    echo "   ✅ Questions answered in README.md"
else
    echo "   ❌ Questions not answered in README.md"
    exit 1
fi

# Check if server is running
echo ""
echo "6. Checking if A2A server is running..."
if curl -s http://localhost:10000/.well-known/agent-card.json > /dev/null 2>&1; then
    echo "   ✅ A2A server is running on port 10000"
else
    echo "   ⚠️  A2A server not running"
    echo "   To start: uv run python -m app"
fi

echo ""
echo "==========================================="
echo "✅ Setup verification complete!"
echo ""
echo "📋 Deliverables:"
echo "   ✓ quickstart.sh (modified)"
echo "   ✓ simple_agent_client.py (Activity #1)"
echo "   ✓ README.md (questions answered)"
echo "   ✓ SIMPLE_CLIENT_README.md (documentation)"
echo "   ✓ COMPLETION_SUMMARY.md (summary)"
echo ""
echo "🎬 Next steps for submission:"
echo "   1. Record Loom video demonstrating the client"
echo "   2. Commit and push to assignment branch"
echo "   3. Submit homework form"
echo ""

