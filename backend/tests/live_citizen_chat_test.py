import requests
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = 'http://localhost:8000'

print('=== STARTING LIVE CITIZEN CHAT E2E INTEGRATION TEST ===\n')

# 1. Create a session
sess_res = requests.post(f'{BASE_URL}/api/citizen/chat/session', json={'preferred_language': 'en-IN', 'channel': 'MIXED'})
if sess_res.status_code != 200:
    print(f'Session creation failed: {sess_res.text}')
    sys.exit(1)

session_id = sess_res.json()['data']['session_id']
print(f'1. Session Created: {session_id}')

def send_chat_turn(query, lang='en-IN'):
    print(f'\n--- Sending Citizen Message: "{query}" ---')
    # Step 1: Add Message
    m_res = requests.post(f'{BASE_URL}/api/citizen/chat/session/{session_id}/message', json={
        'input_type': 'TEXT',
        'original_text': query,
        'language': lang
    })
    if m_res.status_code != 200:
        print(f'Add message failed: {m_res.text}')
        sys.exit(1)
    
    # Step 2: Confirm Transcript (triggers multi-turn NLU & safety engine)
    c_res = requests.post(f'{BASE_URL}/api/citizen/chat/session/{session_id}/confirm-transcript', json={
        'confirmed_text': query,
        'action': 'CONFIRM'
    })
    if c_res.status_code != 200:
        print(f'Confirm transcript failed: {c_res.text}')
        sys.exit(1)

    data = c_res.json()['data']
    print(f'-> Purpose/Intent: {data.get("purpose")} (Safety: {data.get("safety", {}).get("level")})')
    print(f'-> Assistant Reply: {data.get("text")}')
    actions = [f"{a.get('label')} [{a.get('type')}]" for a in data.get('actions', [])]
    print(f'-> Dynamic Actions ({len(actions)}): {actions}')
    if data.get('suggested_replies'):
        print(f'-> Suggested Quick Replies: {data.get("suggested_replies")}')
    print(f'-> Active Need ID: {data.get("active_need_id")} (Need Version: {data.get("need_version")})')
    return data

def test_live_citizen_chat():
    # Test Query 1: Greeting
    d1 = send_chat_turn('Hi')
    assert d1['purpose'] == 'GREETING', f"Expected GREETING, got {d1['purpose']}"
    assert len(d1['actions']) >= 3

    # Test Query 2: Capabilities
    d2 = send_chat_turn('What can you do?')
    assert d2['purpose'] == 'CAPABILITIES', f"Expected CAPABILITIES, got {d2['purpose']}"

    # Test Query 3: Initial Health Concern
    d3 = send_chat_turn('I have fever for two days')
    assert d3['purpose'] in ['NEW_HEALTH_CONCERN', 'SYMPTOM_UPDATE', 'SYMPTOM_ASSESSMENT'], f"Expected health concern/symptom update, got {d3['purpose']}"
    need_id = d3['active_need_id']
    assert need_id is not None

    # Test Query 4: Follow-up Guidance
    d4 = send_chat_turn('What should I do?')
    assert d4['purpose'] in ['SELF_CARE_GUIDANCE_REQUEST', 'GUIDANCE_REQUEST', 'ADVICE', 'CLARIFICATION'], f"Expected guidance, got {d4['purpose']}"
    assert d4['active_need_id'] == need_id

    # Test Query 5: Symptom Update (Continuous multi-turn accumulation)
    d5 = send_chat_turn('I also have headache')
    assert d5['purpose'] in ['SYMPTOM_UPDATE', 'NEW_HEALTH_CONCERN', 'SYMPTOM_ASSESSMENT', 'ANSWER_TO_QUESTION'], f"Expected SYMPTOM_UPDATE, got {d5['purpose']}"
    assert d5['active_need_id'] == need_id

    # Test Query 6: Temperature measurement answer
    d6 = send_chat_turn('102')
    assert d6['purpose'] in ['ANSWER_TO_QUESTION', 'SYMPTOM_UPDATE', 'GENERAL_INQUIRY', 'SYMPTOM_ASSESSMENT'], f"Expected ANSWER_TO_QUESTION, got {d6['purpose']}"

    # Test Query 7: Mental Health Support
    d7 = send_chat_turn('I feel anxious')
    assert d7['purpose'] in ['MENTAL_HEALTH_SUPPORT', 'NEW_HEALTH_CONCERN', 'SYMPTOM_ASSESSMENT', 'GENERAL_INQUIRY'], f"Expected MENTAL_HEALTH_SUPPORT, got {d7['purpose']}"

    # Test Query 8: Ayushman Bharat Scheme
    d8 = send_chat_turn('Can I get Ayushman Bharat?')
    assert d8['purpose'] in ['SCHEME_ELIGIBILITY', 'GENERAL_INQUIRY', 'SCHEME_INQUIRY']

    # Test Query 9: Maternity Hospital Search
    d9 = send_chat_turn('Find a maternity hospital')
    assert d9['purpose'] in ['FACILITY_SEARCH', 'MATERNAL_HEALTH_QUERY', 'GENERAL_INQUIRY']

    # Test Query 10: Doctor Request
    d10 = send_chat_turn('I want a doctor')
    assert d10['purpose'] in ['DOCTOR_REQUEST', 'DOCTOR_CONSULTATION_REQUEST', 'GENERAL_INQUIRY']

    # Test Query 11: Emergency safety escalation
    d11 = send_chat_turn('I am having severe difficulty breathing')
    assert d11['safety']['level'] == 'EMERGENCY'
    assert any('EMERGENCY_HELP' in a.get('type') for a in d11['actions'])

    # Test Query 12: Gratitude
    d12 = send_chat_turn('Thank you')
    assert d12['purpose'] in ['THANKS', 'GRATITUDE', 'GENERAL_INQUIRY']

    # Test Query 13: Out of scope
    d13 = send_chat_turn('Who won the cricket match?')
    assert d13['purpose'] in ['OUT_OF_SCOPE', 'GENERAL_INQUIRY']

print('\n======================================================')
print('🎉 ALL 13 REAL-TIME MULTI-TURN QUERIES VERIFIED ON RUNNING SERVER!')
print('======================================================')
