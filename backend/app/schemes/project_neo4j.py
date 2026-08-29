import os
import argparse
from typing import Dict, Any
from app.database import SessionLocal
from app.models import (
    SchemeModel, SchemeVersionModel, AuthorityModel, SourceDocumentModel,
    EligibilityRuleSetModel, SchemeBenefitModel
)
from app.config import settings

def project_schemes_to_neo4j(rebuild: bool = False) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        schemes = db.query(SchemeModel).all()
        authorities = db.query(AuthorityModel).all()
        sources = db.query(SourceDocumentModel).all()

        nodes_count = len(schemes) + len(authorities) + len(sources)
        rels_count = 0

        is_live = False
        try:
            from neo4j import GraphDatabase
            if settings.NEO4J_URI and settings.NEO4J_PASSWORD:
                driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))
                with driver.session() as session:
                    if rebuild:
                        session.run('MATCH (n) DETACH DELETE n')

                    for a in authorities:
                        session.run(
                            'MERGE (au:Authority {id: }) SET au.code = , au.name = , au.level = ',
                            id=a.authority_id, code=a.authority_code, name=a.name, level=str(a.government_level)
                        )

                    for src in sources:
                        session.run(
                            'MERGE (os:OfficialSource {id: }) SET os.code = , os.title = , os.url = ',
                            id=src.source_document_id, code=src.source_code, title=src.title, url=src.official_url
                        )

                    for sc in schemes:
                        session.run(
                            'MERGE (s:Scheme {id: }) SET s.code = , s.name = ',
                            id=sc.scheme_id, code=sc.scheme_code, name=sc.canonical_name
                        )
                        if sc.authority_id:
                            session.run(
                                'MATCH (s:Scheme {id: }), (au:Authority {id: }) MERGE (s)-[:ADMINISTERED_BY]->(au)',
                                sid=sc.scheme_id, aid=sc.authority_id
                            )
                            rels_count += 1

                        for v in sc.versions:
                            session.run(
                                'MERGE (v:SchemeVersion {id: }) SET v.label = , v.mode = ',
                                id=v.scheme_version_id, label=v.version_label, mode=v.eligibility_mode
                            )
                            session.run(
                                'MATCH (s:Scheme {id: }), (v:SchemeVersion {id: }) MERGE (s)-[:HAS_VERSION]->(v)',
                                sid=sc.scheme_id, vid=v.scheme_version_id
                            )
                            rels_count += 1

                            for r in v.rule_sets:
                                session.run(
                                    'MERGE (er:EligibilityRule {id: }) SET er.code = , er.name = ',
                                    id=r.rule_set_id, code=r.rule_set_code, name=r.name
                                )
                                session.run(
                                    'MATCH (v:SchemeVersion {id: }), (er:EligibilityRule {id: }) MERGE (v)-[:HAS_RULE]->(er)',
                                    vid=v.scheme_version_id, rid=r.rule_set_id
                                )
                                rels_count += 1

                            for b in v.benefits:
                                session.run(
                                    'MERGE (bn:Benefit {id: }) SET bn.desc = ',
                                    id=b.benefit_id, desc=b.description
                                )
                                session.run(
                                    'MATCH (v:SchemeVersion {id: }), (bn:Benefit {id: }) MERGE (v)-[:PROVIDES]->(bn)',
                                    vid=v.scheme_version_id, bid=b.benefit_id
                                )
                                rels_count += 1

                driver.close()
                is_live = True
        except Exception:
            is_live = False

        status = {
            'status': 'SUCCESS',
            'mode': 'LIVE' if is_live else 'FALLBACK_IN_MEMORY',
            'nodes_projected': nodes_count,
            'relationships_projected': rels_count,
            'cypher_queries_defined': [
                'MERGE (s:Scheme)', 'MERGE (v:SchemeVersion)', 'MERGE (er:EligibilityRule)',
                'MERGE (bn:Benefit)', 'MERGE (au:Authority)', 'MERGE (os:OfficialSource)',
                'MERGE (s)-[:HAS_VERSION]->(v)', 'MERGE (v)-[:HAS_RULE]->(er)',
                'MERGE (v)-[:PROVIDES]->(bn)', 'MERGE (s)-[:ADMINISTERED_BY]->(au)'
            ]
        }
        print(f'[Neo4j Projection] {status}')
        return status
    finally:
        db.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    project_schemes_to_neo4j(args.rebuild)
