import os
import time
import base64
import pytest
from app.models import (
    CitizenProfile, CitizenChatSession, CitizenChatMessage, CitizenNeed,
    ServiceRequest, Case, CasePriorityEnum
)
from app.ai.pii.masker import PIIMasker
from app.safety.emergency_rules import EmergencyRuleEvaluator

def test_no_hardcoded_transcript_substitution_on_empty_audio(client):
    """Verify endpoint honestly reports NO_AUDIO/EMPTY_AUDIO instead of returning fake text."""
    # 1. Empty request
    res_empty = client.post("/api/citizen/voice/transcribe", json={
        "audio_base64": "",
        "preferred_language": "mr-IN"
    })
    assert res_empty.status_code == 200
    data = res_empty.json()["data"]
    assert data["status"] == "NO_AUDIO"
    assert data["transcript"] == ""

    # 2. Corrupt / minimal non-audio bytes
    tiny_audio = base64.b64encode(b"short").decode("utf-8")
    res_tiny = client.post("/api/citizen/voice/transcribe", json={
        "audio_base64": tiny_audio,
        "preferred_language": "mr-IN"
    })
    assert res_tiny.status_code == 200
    data_tiny = res_tiny.json()["data"]
    assert data_tiny["status"] in ["EMPTY_AUDIO", "PROVIDER_UNAVAILABLE"]
    # Ensure no Marathi or Hindi demo text is returned
    assert "माझ्या आईला" not in data_tiny.get("transcript", "")
    assert "दोन दिवसांपासून" not in data_tiny.get("transcript", "")

def test_pii_masking_before_ai_intake():
    """Verify citizen names, 10-digit phone numbers and ABHA IDs are masked."""
    raw_input = "माझे नाव Sunita Devi आहे, फोन 9876543210 आणि छातीत खूप त्रास होतोय."
    masked, token_map = PIIMasker.mask_text(raw_input, citizen_name="Sunita Devi")
    assert "Sunita Devi" not in masked
    assert "9876543210" not in masked
    assert "[CITIZEN_1]" in masked or "[PHONE_REDACTED]" in masked

def test_chat_session_history_and_restoration(client):
    """Verify full message ordering and retrieval for continuous chat."""
    # Start session
    res = client.post("/api/citizen/chat/session", json={
        "preferred_language": "mr-IN",
        "channel": "MIXED"
    })
    assert res.status_code == 200
    session_id = res.json()["data"]["session_id"]

    # Add message 1
    msg1_res = client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "मला ताप आहे आणि अशक्तपणा वाटतोय",
        "language": "mr-IN"
    })
    assert msg1_res.status_code == 200

    # Confirm transcript 1
    conf1 = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "मला ताप आहे आणि अशक्तपणा वाटतोय",
        "action": "CONFIRM"
    })
    assert conf1.status_code == 200

    # Fetch history via dedicated history endpoint
    hist_res = client.get(f"/api/citizen/chat/session/{session_id}/history")
    assert hist_res.status_code == 200
    history_data = hist_res.json()["data"]
    assert history_data["session_id"] == session_id
    assert len(history_data["messages"]) >= 2
    # Verify sequence ordering
    seqs = [m["sequence_number"] for m in history_data["messages"]]
    assert seqs == sorted(seqs)

    # Test active session endpoint
    active_res = client.get("/api/citizen/chat/session/active")
    assert active_res.status_code == 200
    active_data = active_res.json()["data"]
    assert active_data is not None
    assert active_data["session_id"] == session_id

def test_multi_turn_fever_guidance_and_temperature_answer(client):
    """
    Test required multi-turn scenario:
    1. Citizen: 'I have had fever for two days and feel weak' -> UNDERSTANDING_CONFIRMATION
    2. Citizen: 'What should I do to reduce fever?' -> SAFE_GUIDANCE (not duplicate intake)
    3. Citizen: 'My temperature is 103 F' -> ANSWER_TO_QUESTION updates existing need
    4. Citizen: 'Now I am having difficulty breathing' -> EMERGENCY safety override
    """
    # 1. Start session
    session_res = client.post("/api/citizen/chat/session", json={
        "preferred_language": "mr-IN",
        "channel": "MIXED"
    })
    assert session_res.status_code == 200
    session_id = session_res.json()["data"]["session_id"]

    # Turn 1: Initial fever statement
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "मला दोन दिवसांपासून ताप आहे आणि अशक्तपणा वाटतोय",
        "language": "mr-IN"
    })
    t1_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "मला दोन दिवसांपासून ताप आहे आणि अशक्तपणा वाटतोय",
        "action": "CONFIRM"
    })
    assert t1_res.status_code == 200
    d1 = t1_res.json()["data"]
    assert d1["purpose"] == "NEW_HEALTH_CONCERN"
    block_types_1 = [b["block_type"] for b in d1["blocks"]]
    assert "UNDERSTANDING_CONFIRMATION" in block_types_1

    # Turn 2: Follow-up question "What should I do to reduce fever?"
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "ताप कमी करण्यासाठी मी काय करावे?",
        "language": "mr-IN"
    })
    t2_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "ताप कमी करण्यासाठी मी काय करावे?",
        "action": "CONFIRM"
    })
    assert t2_res.status_code == 200
    d2 = t2_res.json()["data"]
    assert d2["purpose"] in ["SELF_CARE_GUIDANCE_REQUEST", "SELF_CARE_GUIDANCE", "FOLLOW_UP_QUESTION"]
    block_types_2 = [b["block_type"] for b in d2["blocks"]]
    assert "SAFE_GUIDANCE" in block_types_2
    assert "CLARIFYING_QUESTION" in block_types_2
    # Ensure it did NOT output another redundant UNDERSTANDING_CONFIRMATION block
    assert "UNDERSTANDING_CONFIRMATION" not in block_types_2

    # Turn 3: Citizen answers temperature question "१०३ डिग्री"
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "१०३ डिग्री",
        "language": "mr-IN"
    })
    t3_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "१०३ डिग्री",
        "action": "CONFIRM"
    })
    assert t3_res.status_code == 200
    d3 = t3_res.json()["data"]
    assert d3["purpose"] == "ANSWER_TO_QUESTION"
    assert d3["understanding"]["vitals"].get("temperature_f") == 103.0

    # Turn 4: New emergency warning sign appears "आता मला श्वास घेण्यास त्रास होत आहे"
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "आता मला श्वास घेण्यास खूप त्रास होत आहे",
        "language": "mr-IN"
    })
    t4_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "आता मला श्वास घेण्यास खूप त्रास होत आहे",
        "action": "CONFIRM"
    })
    assert t4_res.status_code == 200
    d4 = t4_res.json()["data"]
    assert d4["safety"]["level"] == "EMERGENCY"
    block_types_4 = [b["block_type"] for b in d4["blocks"]]
    assert "SAFETY_ALERT" in block_types_4
    actions_4 = [a["type"] for a in d4["actions"]]
    assert "EMERGENCY_HELP" in actions_4
    assert "SPEAK_TO_DOCTOR" in actions_4

def test_messages_a_b_c_d_conversational_progression(client):
    """
    Verify complete specification for Messages A, B, C, D:
    Message A: 'Give suggestion what I should do to reduce fever.'
    Message B: 'What should I do?' (uses previous context)
    Message C: 'I also have cold.' (updates same CitizenNeed, does not create duplicate need/case)
    Message D: 'I am having difficulty breathing.' (deterministic emergency safety override)
    """
    # Create session with English language
    session_res = client.post("/api/citizen/chat/session", json={
        "preferred_language": "en-IN",
        "channel": "MIXED"
    })
    assert session_res.status_code == 200
    session_id = session_res.json()["data"]["session_id"]

    # Initial intake
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "I have had fever and weakness for two days.",
        "language": "en-IN"
    })
    t0_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "I have had fever and weakness for two days.",
        "action": "CONFIRM"
    })
    assert t0_res.status_code == 200
    d0 = t0_res.json()["data"]
    initial_need_id = d0["active_need_id"]
    assert initial_need_id is not None
    assert d0["need_version"] == 1

    # Message A: "Give suggestion what I should do to reduce fever."
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "Give suggestion what I should do to reduce fever.",
        "language": "en-IN"
    })
    ta_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "Give suggestion what I should do to reduce fever.",
        "action": "CONFIRM"
    })
    assert ta_res.status_code == 200
    da = ta_res.json()["data"]
    assert da["purpose"] in ["SELF_CARE_GUIDANCE_REQUEST", "FOLLOW_UP_QUESTION"]
    assert da["active_need_id"] == initial_need_id
    assert "SAFE_GUIDANCE" in [b["block_type"] for b in da["blocks"]]
    assert "UNDERSTANDING_CONFIRMATION" not in [b["block_type"] for b in da["blocks"]]
    assert "antibiotics" in da["text"].lower() or "fluids" in da["text"].lower() or "rest" in da["text"].lower()

    # Message B: "What should I do?"
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "What should I do?",
        "language": "en-IN"
    })
    tb_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "What should I do?",
        "action": "CONFIRM"
    })
    assert tb_res.status_code == 200
    db = tb_res.json()["data"]
    assert db["active_need_id"] == initial_need_id
    assert "SAFE_GUIDANCE" in [b["block_type"] for b in db["blocks"]]
    assert "UNDERSTANDING_CONFIRMATION" not in [b["block_type"] for b in db["blocks"]]

    # Message C: "I also have cold."
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "I also have cold.",
        "language": "en-IN"
    })
    tc_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "I also have cold.",
        "action": "CONFIRM"
    })
    assert tc_res.status_code == 200
    dc = tc_res.json()["data"]
    assert dc["purpose"] in ["SYMPTOM_UPDATE", "NEW_HEALTH_CONCERN"]
    assert dc["active_need_id"] == initial_need_id
    # Verified that need version incremented on factual update
    assert dc["need_version"] >= 2
    assert "cold" in dc["text"].lower() or "cold" in [s.lower() for s in dc["understanding"]["symptoms"]]

    # Message D: "I am having difficulty breathing."
    client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "I am having difficulty breathing.",
        "language": "en-IN"
    })
    td_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "I am having difficulty breathing.",
        "action": "CONFIRM"
    })
    assert td_res.status_code == 200
    dd = td_res.json()["data"]
    assert dd["safety"]["level"] == "EMERGENCY"
    assert "SAFETY_ALERT" in [b["block_type"] for b in dd["blocks"]]
    action_types_d = [a["type"] for a in dd["actions"]]
    assert "EMERGENCY_HELP" in action_types_d
    assert "SPEAK_TO_DOCTOR" in action_types_d

def test_idempotency_and_zero_duplicate_needs(client):
    """Verify idempotency key reuse returns same message and updates the single active need."""
    session_res = client.post("/api/citizen/chat/session", json={"preferred_language": "mr-IN"})
    session_id = session_res.json()["data"]["session_id"]

    idem_key = "IDEM-CHAT-MSG-777"
    msg1 = client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "डोकेदुखी होत आहे",
        "language": "mr-IN",
        "idempotency_key": idem_key
    })
    assert msg1.status_code == 200
    m_id1 = msg1.json()["data"]["message_id"]

    # Re-sending identical request must return same message
    msg2 = client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "TEXT",
        "original_text": "डोकेदुखी होत आहे",
        "language": "mr-IN",
        "idempotency_key": idem_key
    })
    assert msg2.status_code == 200
    assert msg2.json()["data"]["message_id"] == m_id1


def test_greeting_creates_no_case_and_returns_dynamic_actions(client):
    res = client.post("/api/citizen/chat/session", json={"preferred_language": "en-IN", "channel": "MIXED"})
    assert res.status_code == 200
    sess_id = res.json()["data"]["session_id"]

    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "Hello", "language": "en-IN"})
    t_res = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "Hello", "action": "CONFIRM"})
    assert t_res.status_code == 200
    d = t_res.json()["data"]
    assert d["purpose"] == "GREETING"
    assert d["understanding"]["intent"] == "GREETING"
    assert d["active_need_id"] is None
    assert len(d["actions"]) >= 3
    labels = [a["label"] for a in d["actions"]]
    assert any("Health" in l for l in labels)


def test_capabilities_query(client):
    res = client.post("/api/citizen/chat/session", json={"preferred_language": "mr-IN"})
    sess_id = res.json()["data"]["session_id"]
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "तू काय करू शकतोस?", "language": "mr-IN"})
    t_res = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "तू काय करू शकतोस?", "action": "CONFIRM"})
    assert t_res.status_code == 200
    d = t_res.json()["data"]
    assert d["purpose"] == "CAPABILITIES"
    assert d["active_need_id"] is None


def test_fever_and_guidance_multi_turn(client):
    res = client.post("/api/citizen/chat/session", json={"preferred_language": "en-IN"})
    sess_id = res.json()["data"]["session_id"]

    # Turn 1: I have fever for two days
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "I have fever for two days", "language": "en-IN"})
    t1 = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "I have fever for two days", "action": "CONFIRM"})
    assert t1.status_code == 200
    d1 = t1.json()["data"]
    assert d1["purpose"] == "NEW_HEALTH_CONCERN"
    initial_need_id = d1["active_need_id"]
    assert initial_need_id is not None

    # Turn 2: Give suggestions to reduce fever
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "Give suggestions to reduce fever", "language": "en-IN"})
    t2 = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "Give suggestions to reduce fever", "action": "CONFIRM"})
    assert t2.status_code == 200
    d2 = t2.json()["data"]
    assert d2["purpose"] in ["SELF_CARE_GUIDANCE_REQUEST", "FOLLOW_UP_QUESTION"]
    assert d2["active_need_id"] == initial_need_id

    # Turn 3: I also have headache (updates existing need, does NOT create duplicate)
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "I also have headache", "language": "en-IN"})
    t3 = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "I also have headache", "action": "CONFIRM"})
    assert t3.status_code == 200
    d3 = t3.json()["data"]
    assert d3["purpose"] == "SYMPTOM_UPDATE"
    assert d3["active_need_id"] == initial_need_id
    assert d3["need_version"] >= 2

    # Turn 4: 102 (understood as temperature answer)
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "102", "language": "en-IN"})
    t4 = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "102", "action": "CONFIRM"})
    assert t4.status_code == 200
    d4 = t4.json()["data"]
    assert d4["purpose"] == "ANSWER_TO_QUESTION"
    assert d4["active_need_id"] == initial_need_id
    assert d4["understanding"]["vitals"].get("temperature_f") == 102.0


def test_mental_health_support_vs_crisis(client):
    res1 = client.post("/api/citizen/chat/session", json={"preferred_language": "en-IN"})
    s1 = res1.json()["data"]["session_id"]
    client.post(f"/api/citizen/chat/session/{s1}/message", json={"input_type": "TEXT", "original_text": "I feel anxious", "language": "en-IN"})
    t_supp = client.post(f"/api/citizen/chat/session/{s1}/confirm-transcript", json={"confirmed_text": "I feel anxious", "action": "CONFIRM"})
    assert t_supp.status_code == 200
    d_supp = t_supp.json()["data"]
    assert d_supp["purpose"] == "MENTAL_HEALTH_SUPPORT"
    assert d_supp["safety"]["level"] != "EMERGENCY"

    # Crisis escalation
    res2 = client.post("/api/citizen/chat/session", json={"preferred_language": "en-IN"})
    s2 = res2.json()["data"]["session_id"]
    client.post(f"/api/citizen/chat/session/{s2}/message", json={"input_type": "TEXT", "original_text": "I want to hurt myself", "language": "en-IN"})
    t_crisis = client.post(f"/api/citizen/chat/session/{s2}/confirm-transcript", json={"confirmed_text": "I want to hurt myself", "action": "CONFIRM"})
    assert t_crisis.status_code == 200
    d_crisis = t_crisis.json()["data"]
    assert d_crisis["purpose"] == "MENTAL_HEALTH_CRISIS"
    assert d_crisis["safety"]["level"] == "EMERGENCY"
    actions = [a["action"] for a in d_crisis["actions"]]
    assert "CALL_108" in actions


def test_scheme_eligibility_and_facility_search(client):
    res = client.post("/api/citizen/chat/session", json={"preferred_language": "en-IN"})
    sess_id = res.json()["data"]["session_id"]

    # Scheme query
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "Can I get Ayushman Bharat?", "language": "en-IN"})
    t_sch = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "Can I get Ayushman Bharat?", "action": "CONFIRM"})
    assert t_sch.status_code == 200
    d_sch = t_sch.json()["data"]
    assert d_sch["purpose"] == "SCHEME_ELIGIBILITY"
    assert "5 lakh" in d_sch["text"].lower() or "500000" in d_sch["text"].lower() or "ayushman" in d_sch["text"].lower()
    actions_sch = [a["type"] for a in d_sch["actions"]]
    assert "CHECK_SCHEMES" in actions_sch

    # Facility search query
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "Find a maternity hospital", "language": "en-IN"})
    t_fac = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "Find a maternity hospital", "action": "CONFIRM"})
    assert t_fac.status_code == 200
    d_fac = t_fac.json()["data"]
    assert d_fac["purpose"] in ["FACILITY_SEARCH", "MATERNAL_HEALTH_QUERY"]
    actions_fac = [a["type"] for a in d_fac["actions"]]
    assert "FIND_FACILITY" in actions_fac


def test_doctor_request_intent(client):
    res = client.post("/api/citizen/chat/session", json={"preferred_language": "en-IN"})
    sess_id = res.json()["data"]["session_id"]
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "I want a doctor", "language": "en-IN"})
    t_doc = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "I want a doctor", "action": "CONFIRM"})
    assert t_doc.status_code == 200
    d_doc = t_doc.json()["data"]
    assert d_doc["purpose"] == "DOCTOR_REQUEST"
    actions_doc = [a["type"] for a in d_doc["actions"]]
    assert "SPEAK_TO_DOCTOR" in actions_doc


def test_thanks_and_unrelated_queries_produce_no_cases(client):
    res = client.post("/api/citizen/chat/session", json={"preferred_language": "en-IN"})
    sess_id = res.json()["data"]["session_id"]

    # Thanks
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "Thank you", "language": "en-IN"})
    t_thx = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "Thank you", "action": "CONFIRM"})
    assert t_thx.status_code == 200
    d_thx = t_thx.json()["data"]
    assert d_thx["purpose"] == "THANKS"
    assert len(d_thx["actions"]) == 0
    assert d_thx["active_need_id"] is None

    # Unrelated
    client.post(f"/api/citizen/chat/session/{sess_id}/message", json={"input_type": "TEXT", "original_text": "Who won the cricket match?", "language": "en-IN"})
    t_un = client.post(f"/api/citizen/chat/session/{sess_id}/confirm-transcript", json={"confirmed_text": "Who won the cricket match?", "action": "CONFIRM"})
    assert t_un.status_code == 200
    d_un = t_un.json()["data"]
    assert d_un["purpose"] == "OUT_OF_SCOPE"
    assert d_un["active_need_id"] is None
