# Milvus Clinical RAG Architecture & Verification

## 1. Overview & Architecture

The **Milvus Clinical RAG (Retrieval-Augmented Generation)** subsystem provides doctor-facing and ASHA-facing clinical guidance grounded exclusively in verified, authoritative clinical workflows issued by the **Indian Council of Medical Research (ICMR)** and the **Ministry of Health & Family Welfare (MoHFW)**.

```
       +---------------------------------------------+
       |   Authoritative Manifest & Markdown Docs    |
       |  (knowledge/clinical/manifest.yaml + docs)  |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |   Idempotent Chunking & SHA-256 Hashing     |
       |    (backend/app/ai/rag/ingest_clinical.py)   |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       | Multilingual Embedding Layer (Dim = 384)    |
       |      (backend/app/ai/rag/embeddings.py)     |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |       Milvus Vector DB / Memory Store       |
       |     (backend/app/ai/rag/clinical_rag.py)    |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |        Clinical Evidence API Endpoint       |
       |         (POST /api/ai/clinical-evidence)    |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |     Doctor Clinical Evidence Component      |
       | (DoctorConsultationScreen.tsx: Evidence box)|
       +---------------------------------------------+
```

---

## 2. Ingested Guidelines Corpus

1. `DOC-ICMR-MCH-001`: *ICMR Standard Treatment Workflow - Hypertensive Disorders in Pregnancy* (Pre-eclampsia, Gestational Hypertension, Labetalol 100mg first-line therapy).
2. `DOC-MOHFW-ASHA-002`: *MoHFW ASHA Field Manual - Maternal Danger Signs & High Risk Pregnancy Triage* (Visual blurring, pedal edema, urgent referral protocols).
3. `DOC-ICMR-CVD-003`: *ICMR Clinical Management Protocols - Acute Coronary Syndrome & Chest Pain in Primary Care* (Retrosternal chest discomfort, loading dose therapy, urgent transfer).
4. `DOC-MOHFW-RESP-004`: *MoHFW Clinical Guidance - Respiratory Distress and Hypoxemia Management at PHC* (SpO2 < 93%, oxygen therapy, bronchodilators).
5. `DOC-ICMR-PED-005`: *ICMR IMNCI - Pediatric Acute Fever & Dehydration* (Danger signs in under-5s, ORS Plan A/B/C, Paracetamol dosing).

---

## 3. Key Invariants & Safety Guardrails
- **Zero Patient PII in Vector Database**: Milvus stores strictly public medical guidelines with SHA-256 content hashes.
- **Verifiable Citations**: Every passage returned includes issuing authority, document title, section name, and open-source PDF URL.
- **Deterministic Embeddings**: Normalized 384-dimensional multilingual vector representation supporting English, Hindi, and Marathi terminology.
- **Fail-Safe Operation**: If the Milvus server is offline or unreachable, the system transparently falls back to the in-memory cosine similarity store without impacting doctor consultations.
