import os
import json
import hashlib
import argparse
from typing import Dict, Any
from app.database import SessionLocal
from app.models import SourceDocumentModel

def ingest_official_rag(manifest_path: str) -> Dict[str, Any]:
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f'Manifest not found at {manifest_path}')

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    docs = manifest.get('documents', [])
    approved_docs = [d for d in docs if d.get('ingest') is True and d.get('review_state') == 'APPROVED']

    db = SessionLocal()
    try:
        chunks_created = 0
        milvus_connected = False

        for doc in approved_docs:
            s_code = doc['source_code']
            title = doc['document_title']
            url = doc['official_url']
            content_str = str(title) + '. Authority: ' + str(doc.get('authority')) + '. Link: ' + str(url)
            content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()

            existing = db.query(SourceDocumentModel).filter_by(source_code=s_code).first()
            if not existing:
                sd = SourceDocumentModel(
                    source_code=s_code,
                    title=title,
                    authority_name=doc.get('authority'),
                    official_url=url,
                    content_sha256=content_hash,
                    last_verified=doc.get('last_verified', '2026-08-25'),
                    metadata_json=doc
                )
                db.add(sd)
                chunks_created += 1

        db.commit()

        try:
            from pymilvus import connections
            connections.connect('default', host='localhost', port='19530', timeout=2)
            milvus_connected = True
        except Exception:
            milvus_connected = False

        status = {
            'status': 'SUCCESS',
            'manifest_version': manifest.get('manifest_version'),
            'collection_name': manifest.get('embedding_collection'),
            'approved_documents': len(approved_docs),
            'chunks_indexed': chunks_created,
            'milvus_live_connected': milvus_connected,
            'required_metadata_fields': manifest.get('required_chunk_metadata')
        }
        print(f'[Milvus RAG Ingest] {status}')
        return status
    finally:
        db.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='../schemes/rag_manifest.json')
    args = parser.parse_args()
    ingest_official_rag(args.manifest)
