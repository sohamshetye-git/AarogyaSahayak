import sys
import os
from app.ai.graph.scheme_graph import scheme_graph_service

def verify_neo4j():
    print("==================================================")
    print("   Aarogya Sahayak - Neo4j GraphRAG Diagnostic")
    print("==================================================")
    
    print(f"Service Mode:    {scheme_graph_service.get_mode()}")
    print(f"Live Connected:  {scheme_graph_service.is_live}")
    print(f"Seeded Schemes:  {len(scheme_graph_service._schemes)}")
    print(f"Graph Rules:     {len(scheme_graph_service._rules)}")
    print(f"Empanelled PHCs: {len(scheme_graph_service._facilities)}")

    print("\n--- Deterministic Scheme Graph Traversal ---")
    results = scheme_graph_service.evaluate_eligibility(
        is_pregnant=True,
        state="Maharashtra",
        area_type="RURAL",
        bpl_card_holder=None
    )

    for i, s in enumerate(results, 1):
        print(f"\n[Scheme {i}] {s['scheme_name']} ({s['scheme_code']})")
        print(f"  Status:       {s['status']} (Confidence: {s['confidence_score']})")
        print(f"  Authority:    {s['authority']}")
        benefits = s['benefit_summary'].replace('₹', 'Rs. ')
        print(f"  Benefits:     {benefits}")
        print(f"  Documents:    {', '.join(s['required_documents'])}")
        print(f"  Facilities:   {', '.join(s['empanelled_facilities'])}")
        print(f"  Official URL: {s['official_url']}")

    print("\nNeo4j Diagnostic Verification COMPLETE.")

if __name__ == "__main__":
    verify_neo4j()
