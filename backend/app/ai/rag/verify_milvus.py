import sys
import os
from app.ai.rag.clinical_rag import clinical_rag_service, ingest_manifest
from app.ai.rag.embeddings import embedding_service

def verify_milvus():
    print("==================================================")
    print("   Aarogya Sahayak - Milvus Clinical RAG Diagnostic")
    print("==================================================")
    
    # 1. Embedding Provider Diagnostics
    print(f"Embedding Provider: {embedding_service.mode}")
    print(f"Model ID / Name:   {embedding_service.model_name}")
    print(f"Vector Dimension:   {embedding_service.dimension}")
    print(f"Normalization:      L2 Unit Vector (np.linalg.norm)")
    
    # 2. Ingestion & Collection State
    manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../knowledge/clinical/manifest.yaml"))
    ingest_res = ingest_manifest(manifest_path)
    print(f"\nIngestion Status:   {ingest_res['status']}")
    print(f"Total Chunks:       {clinical_rag_service.count()}")
    print(f"Collection Name:    {clinical_rag_service.COLLECTION_NAME}")
    print(f"Service Mode:       {clinical_rag_service.get_mode()}")
    print(f"Live Connected:     {clinical_rag_service.is_live}")

    # 3. Vector Query Search Verification
    query = "blood pressure 150/100 pregnant headache blurred vision"
    print(f"\nExecuting Vector Search for: '{query}'")
    results = clinical_rag_service.search(query=query, top_k=2)
    
    print(f"Retrieved Hits:     {len(results)}")
    for i, hit in enumerate(results, 1):
        print(f"\n[Hit {i}]")
        print(f"  Chunk ID:   {hit['chunk_id']}")
        print(f"  Title:      {hit['title']}")
        print(f"  Authority:  {hit['authority']}")
        print(f"  Section:    {hit['section']}")
        print(f"  Score:      {hit['similarity_score']}")
        print(f"  Source URL: {hit['source_url']}")
        print(f"  Preview:    {hit['content'][:120]}...")
        
    print("\nMilvus Diagnostic Verification COMPLETE.")

if __name__ == "__main__":
    verify_milvus()
