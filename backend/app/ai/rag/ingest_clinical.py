import os
import sys
import argparse
from app.ai.rag.clinical_rag import ingest_manifest

def main():
    parser = argparse.ArgumentParser(description="Ingest authoritative clinical guidelines into Milvus RAG")
    parser.add_argument(
        "--manifest",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "../../../../../knowledge/clinical/manifest.yaml"),
        help="Path to manifest.yaml"
    )
    args = parser.parse_args()

    manifest_path = os.path.abspath(args.manifest)
    print(f"Ingesting clinical guidelines from manifest: {manifest_path}")

    res = ingest_manifest(manifest_path)
    print(f"Ingestion Complete: {res}")

if __name__ == "__main__":
    main()
