# Aarogya Sahayak — Scheme & Grounded RAG Integration Architecture

## 1. GraphRAG Knowledge Representation (Neo4j & Milvus)
Aarogya Sahayak integrates structured medical knowledge graphs (Neo4j) with dense semantic vector search (Milvus) to provide deterministic, policy-grounded clinical protocols and government scheme recommendations.

```
       [ Clinical Guidelines / Schemes ]
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
  [ Neo4j Graph ]              [ Milvus Vectors ]
  • Eligibility Rules          • Semantic Clinical Text
  • Protocol Workflows         • MoHFW Protocol Chunks
  • Dependency Trees           • ICMR Treatment Manuals
         │                             │
         └──────────────┬──────────────┘
                        ▼
           [ Grounded RAG Aggregator ]
                        │
                        ▼
          • Policy ID & Citation
          • Verified Confidence Score (e.g. 96%)
          • Structured Eligibility Criteria
```

---

## 2. Integrated Government Schemes

### 2.1 Janani Suraksha Yojana (JSY)
* **Objective**: Reducing maternal and neonatal mortality by promoting institutional delivery.
* **Cash Benefit**: ₹1,400 DBT assistance for rural mothers delivering in public health facilities + free 102 transport.
* **Target Beneficiary**: All pregnant women in rural areas delivering in government PHC/CHC/DH.
* **Required Documents**: Aadhaar Card, Mother and Child Protection (MCP) card, Bank Account Passbook.

### 2.2 Pradhan Mantri Matru Vandana Yojana (PMMVY)
* **Objective**: Providing compensation for wage loss during pregnancy and ensuring nutritional support for mother and infant.
* **Cash Benefit**: ₹5,000 in direct bank transfers for first living child.
* **Target Beneficiary**: Pregnant women and lactating mothers.
* **Required Documents**: Joint Aadhaar card of husband and wife, MCP card, Bank Account details.

### 2.3 Ayushman Bharat — PM-JAY
* **Objective**: Providing financial protection against catastrophic health expenditures.
* **Benefit**: Cashless treatment up to ₹5,00,000 per family per year for secondary and tertiary care.
* **Target Beneficiary**: Deprived rural households identified under SECC database.
* **Required Documents**: Ration Card, Aadhaar Card, ABHA Health Account ID.

### 2.4 Mukhyamantri Vayoshri Yojana (Maharashtra)
* **Objective**: Assisting senior citizens suffering from age-related physical disabilities.
* **Benefit**: ₹3,000 direct benefit transfer for purchasing assistive devices (glasses, hearing aids, walking sticks).
* **Target Beneficiary**: Senior citizens aged 60+ residing in Maharashtra.
* **Required Documents**: Age proof (Aadhaar/Voter ID), Domicile certificate, Bank account passbook.

---

## 3. Grounded Retrieval Metadata Contract
Every RAG recommendation payload contains strict provenance metadata:
```json
{
  "source_policy": "MoHFW Antenatal Care Guidelines 2026",
  "policy_id": "ICMR-OBS-01",
  "confidence_score": 0.96,
  "guidelines": [
    "Patient presents with elevated blood pressure and visual disturbance in pregnancy.",
    "Immediate referral to Primary Health Center for Medical Officer evaluation.",
    "Advise resting in left lateral position and avoid physical exertion."
  ],
  "disclaimer": "AI-assisted summary — human clinical review required."
}
```
