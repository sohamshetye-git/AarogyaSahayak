import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import CitizenProfile

client = TestClient(app)

def test_schemes_list_endpoint():
    res = client.get('/api/schemes')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'SUCCESS'
    assert data['count'] >= 29

def test_scheme_detail_endpoint():
    res = client.get('/api/schemes/IN-NHA-PMJAY')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'SUCCESS'
    assert data['scheme']['scheme_code'] == 'IN-NHA-PMJAY'

def test_deterministic_evaluation_end_to_end():
    citizen_id = "test-citizen-01"
    payload = {
        'citizen_id': citizen_id,
        'additional_facts': {
            'is_pregnant': True,
            'gestational_weeks': 24,
            'bpl_card_holder': True
        },
        'locale': 'mr-IN',
        'persist': False
    }

    res = client.post('/api/schemes/evaluate', json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'SUCCESS'
    assert data['total_evaluated'] >= 29


def test_admin_source_health():
    res = client.get('/api/schemes/admin/source-health')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'SUCCESS'
    assert data['total_sources'] >= 16
