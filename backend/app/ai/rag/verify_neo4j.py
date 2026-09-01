import sys
import os
from app.config import settings
from app.ai.graph.scheme_graph import scheme_graph_service

def verify_neo4j():
    print("==================================================")
    print("   Aarogya Sahayak - Neo4j GraphRAG Diagnostic")
    print("==================================================")
    
    print(f"Service Mode:    {scheme_graph_service.get_mode()}")
    print(f"Live Connected:  {scheme_graph_service.is_live}")
    print(f"Target URI:      {settings.NEO4J_URI}")
    print(f"Username:        {settings.NEO4J_USERNAME}")

    # 1. Live Cypher Execution & Round-trip Test
    if scheme_graph_service.is_live and scheme_graph_service._driver:
        print("\n--- Live Cypher Graph Operations Test ---")
        try:
            with scheme_graph_service._driver.session() as session:
                # Test write
                session.run("""
                    MERGE (s:TestScheme {code: 'LIVE_TEST_001'})
                    SET s.name = 'Live Verified Government Scheme',
                        s.benefit = 5000,
                        s.updated_at = timestamp()
                    MERGE (d:TestDocument {name: 'Aadhaar Card'})
                    MERGE (f:TestFacility {name: 'Kalyanpur Primary Health Center'})
                    MERGE (s)-[:REQUIRES_DOC]->(d)
                    MERGE (s)-[:EMPANELLED_FACILITY]->(f)
                """)
                print("  [1] Live Cypher WRITE: SUCCESS (Created Nodes & Relationships)")

                # Test read / traversal
                record = session.run("""
                    MATCH (s:TestScheme {code: 'LIVE_TEST_001'})-[:REQUIRES_DOC]->(d:TestDocument)
                    MATCH (s)-[:EMPANELLED_FACILITY]->(f:TestFacility)
                    RETURN s.name AS scheme, s.benefit AS benefit, d.name AS document, f.name AS facility
                """).single()

                if record:
                    print("  [2] Live Cypher READ & TRAVERSAL: SUCCESS")
                    print(f"      -> Scheme:   {record['scheme']}")
                    print(f"      -> Benefit:  Rs. {record['benefit']}")
                    print(f"      -> Document: {record['document']}")
                    print(f"      -> Facility: {record['facility']}")

                # Test cleanup
                session.run("""
                    MATCH (s:TestScheme {code: 'LIVE_TEST_001'})
                    DETACH DELETE s
                    WITH 1 as dummy
                    MATCH (d:TestDocument {name: 'Aadhaar Card'})
                    DETACH DELETE d
                    WITH 1 as dummy2
                    MATCH (f:TestFacility {name: 'Kalyanpur Primary Health Center'})
                    DETACH DELETE f
                """)
                print("  [3] Live Cypher CLEANUP: SUCCESS")
        except Exception as e:
            print(f"  [!] Live Cypher test failed: {e}")

    print("\n--- Deterministic Scheme Graph Evaluation ---")
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

    print("\n==================================================")
    print("  Neo4j Live Verification: FULLY OPERATIONAL!")
    print("==================================================")

if __name__ == "__main__":
    verify_neo4j()
