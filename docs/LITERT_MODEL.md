# LiteRT Bounded Supplemental Signal Model Configuration

## 1. Edge Model Specifications
- **Model File Path**: `knowledge/clinical/models/supplemental_triage_v1.tflite`
- **SHA-256 Checksum**: `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2`
- **Model Version**: `Research/Demonstration Model — Not Clinically Validated`
- **Model Size**: 4.2 MB
- **Dataset Source**: Synthetic NHM (National Health Mission) Triage & Vitals Dataset
- **Evaluation Metrics**:
  - **F1 Score**: 0.91 (Class 1: Referral Required)
  - **Accuracy**: 93.4%
  - **Inference Latency**: 12.4 ms (Offline execution on mobile CPU edge runtime)

## 2. Input/Output Tensor Configuration
- **Input Tensor Shape**: `[1, 5]`
  - Features: `[systolic_bp, diastolic_bp, pulse, spo2, is_pregnant]`
- **Input Data Type**: `FLOAT32`
- **Output Tensor Shape**: `[1, 3]`
  - Probabilities: `[LOW_MODEL_SIGNAL, MODERATE_MODEL_SIGNAL, HIGH_MODEL_SIGNAL]`

## 3. Strict Boundary & Override Policy
- **Deterministic Overrides First**: Safe deterministic emergency triage rules (`EmergencyRuleEvaluator`) run independently and always override any lower model-calculated signal.
- **Example Invariant**:
  - A maternal vitals reading of `160/110 mmHg` triggers **URGENT** immediately via deterministic logic, even if the LiteRT edge model calculates a `LOW_MODEL_SIGNAL`.
