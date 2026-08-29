# Check overall platform services health status
echo "=================================================="
echo "   Aarogya Sahayak - Platform Health & Dev Env"
echo "=================================================="

echo "1. PostgreSQL Database..."
docker ps --filter "name=aarogya-postgres" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

echo "`n2. Milvus Vector Database..."
python -m app.ai.rag.verify_milvus

echo "`n3. Neo4j Graph database..."
python -m app.ai.rag.verify_neo4j

echo "`n4. FastAPI Backend Router & AI Integrations..."
python -m app.integrations.verify_all

echo "`nVerification COMPLETE."
