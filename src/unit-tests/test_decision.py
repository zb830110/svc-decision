import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from decision import app
import risk.maxAdjustment.futureMaxAdjust as fma


client = TestClient(app)

@pytest.fixture
def mock_get_new_max():
    with patch('decision.ma.get_new_max') as mock:
        yield mock

@pytest.fixture
def mock_get_old_max():
    with patch('decision.ma.get_old_max') as mock:
        yield mock

@pytest.fixture
def mock_get_temp_max():
    with patch('decision.ma.get_temp_max') as mock:
        yield mock

def test_get_max_adjustment_success(mock_get_new_max):
    mock_get_new_max.return_value = {
        'newmax': 1000,
        'score': 0.8,
        'tipPercent': 10,
        'reasonCode': 'GOOD_HISTORY',
        'maxcap': 1500
    }
    
    response = client.get("/max-adjustment/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {
        'newmax': 1000,
        'score': 0.8,
        'tipPercent': 10,
        'reasonCode': 'GOOD_HISTORY',
        'maxcap': 1500,
        'userId': 123
    }

def test_get_max_adjustment_fallback(mock_get_new_max, mock_get_old_max, mock_get_temp_max):
    mock_get_new_max.return_value = {'reasonCode': 'NO_NEW_MAX'}
    mock_get_old_max.return_value = 500
    mock_get_temp_max.return_value = 50
    
    response = client.get("/max-adjustment/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {
        'score': -1,
        'tipPercent': -1,
        'oldmax': 500,
        'newmax': 500,
        'reasonCode': 'NO_NEW_MAX',
        'boostAmount': 50,
        'totalAmount': -1,
        'reasonCategory': None,
        'maxcap': -1,
        'userId': 123
    }

@patch('decision.fma.get_express_future_max')
def test_get_express_future_max(mock_get_express_future_max):
    mock_get_express_future_max.return_value = {'futuremax': 1200}
    
    response = client.get("/express-future-max/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {'futuremax': 1200}

@patch('decision.rgp.get_grace_period')
def test_get_restore_grace_period(mock_get_grace_period):
    mock_get_grace_period.return_value = {'gracePeriod': 7, 'userId': 123}
    
    response = client.get("/restore-grace-period/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {'gracePeriod': 7, 'userId': 123}

@patch('decision.UserExperiment')
@patch('decision.drr.get_days')
def test_get_savings_deposit_request_risk(mock_get_days, mock_user_experiment):
    mock_user_experiment.return_value.get_user_group.return_value = 2
    mock_get_days.return_value = {'score': 0.7, 'days': 30}
    
    response = client.get("/savings-deposit-request-risk/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {'score': 0.7, 'days': 30, 'userId': 123}

@patch('decision.nu.get_max')
def test_get_new_user_max(mock_get_max):
    mock_get_max.return_value = {'newmax': 500, 'score': 0.6}
    
    response = client.get("/new-user-max/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {'newmax': 500, 'score': 0.6, 'userId': 123}

@patch('decision.pgp.get_grace_period')
def test_get_payroll_grace_period(mock_get_grace_period):
    mock_get_grace_period.return_value = {'gracePeriod': 5, 'score': 0.8, 'userId': 123}
    
    response = client.get("/payroll-grace-period/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {'gracePeriod': 5, 'score': 0.8, 'userId': 123}

@patch('decision.mac.get_decision')
def test_get_competitor_max_decision(mock_get_decision):
    mock_get_decision.return_value = {'decision': 'APPROVE', 'score': 0.9}
    
    response = client.get("/competitor-max-decision?userid=123&max=1000", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {'userId': 123, 'decision': 'APPROVE', 'score': 0.9}

@patch('decision.eu.existing_user_unemployment_check')
def test_get_unemployment_existing_user_check(mock_unemployment_check):
    mock_unemployment_check.return_value = {'eligible': True, 'reason': 'GOOD_HISTORY'}
    
    response = client.get("/unemployment-existing-user-check/123", headers={"X-call-context-id": "test-context"})
    
    assert response.status_code == 200
    assert response.json() == {'eligible': True, 'reason': 'GOOD_HISTORY'}

# Add more tests for error cases, edge cases, and other scenarios
