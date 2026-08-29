import pytest
import os
from app.ai.rag.clinical_rag import clinical_rag_service, ingest_manifest
from app.ai.rag.embeddings import embedding_service

def test_embeddings_generation():
    # Test real vector output and normalized length
    vec = embedding_service.embed_text("Severe headache and blurred vision in pregnancy")
    assert len(vec) == 384
    assert any(v != 0.0 for v in vec)

def test_idempotent_manifest_ingestion():
    manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge/clinical/manifest.yaml"))
    
    # First ingestion
    res1 = ingest_manifest(manifest_path)
    assert res1["status"] == "SUCCESS"
    assert res1["chunks_indexed"] >= 15
    count1 = clinical_rag_service.count()

    # Second ingestion (Idempotency test: total count must not double)
    res2 = ingest_manifest(manifest_path)
    assert res2["status"] == "SUCCESS"
    count2 = clinical_rag_service.count()
    assert count1 == count2, f"Idempotency failed: count increased from {count1} to {count2}"

def test_semantic_search_maternal_hypertension():
    manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge/clinical/manifest.yaml"))
    ingest_manifest(manifest_path)

    # Search query relevant to Sunita Devi's canonical case
    results = clinical_rag_service.search("blood pressure 150/100 pregnant headache blurred vision", top_k=3)
    assert len(results) >= 1
    top_hit = results[0]
    
    # Verify authoritative metadata presence
    assert "ICMR" in top_hit["authority"] or "MoHFW" in top_hit["authority"]
    assert "http" in top_hit["source_url"]
    assert top_hit["similarity_score"] > 0.3
    assert any(term in top_hit["content"].lower() for term in ["pre-eclampsia", "hypertension", "antihypertensive", "blood pressure"])

def test_empty_search_returns_clean_empty():
    results = clinical_rag_service.search("")
    assert results == []
