import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from PRGracePeriod import get_api_score, get_last_payroll, grace_period_decision, get_grace_period

@patch('PRGracePeriod.get_score')
def test_get_api_score(mock_get_score):
    mock_get_score.return_value = {'score': 0.5}
    result = get_api_score(123, 'test-context')
    assert result == 0.5
    mock_get_score.assert_called_once_with(123, 'test-context', 'restore')

@patch('PRGracePeriod.ah_db.open_db_connection')
@patch('PRGracePeriod.get_sql_data')
def test_get_last_payroll(mock_get_sql_data, mock_db_connection):
    mock_df = pd.DataFrame({'PayrollActiveStatusId': [2]})
    mock_get_sql_data.return_value = mock_df
    
    result = get_last_payroll(123)
    assert result == 2
    
    mock_get_sql_data.return_value = pd.DataFrame()
    result = get_last_payroll(123)
    assert result == 3

def test_grace_period_decision():
    # Test case 1: Score below cutoff, payroll active
    assert grace_period_decision(123, 0.01, 2) == 1
    
    # Test case 2: Score below cutoff, payroll inactive
    assert grace_period_decision(123, 0.01, 1) == 0
    
    # Test case 3: Score above cutoff, payroll active
    assert grace_period_decision(123, 0.02, 2) == 0
    
    # Test case 4: Score above cutoff, payroll inactive
    assert grace_period_decision(123, 0.02, 1) == 0

@patch('PRGracePeriod.get_last_payroll')
@patch('PRGracePeriod.get_api_score')
@patch('PRGracePeriod.UserExperiment')
def test_get_grace_period(mock_user_experiment, mock_get_api_score, mock_get_last_payroll):
    mock_user_experiment.return_value.get_user_group.return_value = 1
    mock_get_api_score.return_value = 0.01
    mock_get_last_payroll.return_value = 2
    
    result = get_grace_period(123, 'test-context')
    expected = {
        'score': 0.01,
        'gracePeriod': 1,
        'userId': 123
    }
    assert result == expected
    
    # Test for group 2
    mock_user_experiment.return_value.get_user_group.return_value = 2
    result = get_grace_period(123, 'test-context')
    expected['gracePeriod'] = 0
    assert result == expected
    
    # Test for group 3
    mock_user_experiment.return_value.get_user_group.return_value = 3
    result = get_grace_period(123, 'test-context')
    expected['gracePeriod'] = 1
    assert result == expected

@patch('PRGracePeriod.get_last_payroll')
@patch('PRGracePeriod.get_api_score')
@patch('PRGracePeriod.UserExperiment')
def test_get_grace_period_edge_cases(mock_user_experiment, mock_get_api_score, mock_get_last_payroll):
    mock_user_experiment.return_value.get_user_group.return_value = 1
    
    # Test with very low score
    mock_get_api_score.return_value = 0.00001
    mock_get_last_payroll.return_value = 2
    result = get_grace_period(123, 'test-context')
    assert result['gracePeriod'] == 1
    
    # Test with score at cutoff
    mock_get_api_score.return_value = 0.01114
    result = get_grace_period(123, 'test-context')
    assert result['gracePeriod'] == 1
    
    # Test with score just above cutoff
    mock_get_api_score.return_value = 0.01115
    result = get_grace_period(123, 'test-context')
    assert result['gracePeriod'] == 0

@patch('PRGracePeriod.get_last_payroll', side_effect=Exception("Database error"))
@patch('PRGracePeriod.get_api_score')
@patch('PRGracePeriod.UserExperiment')
def test_get_grace_period_error_handling(mock_user_experiment, mock_get_api_score, mock_get_last_payroll):
    mock_user_experiment.return_value.get_user_group.return_value = 1
    mock_get_api_score.return_value = 0.01
    
    with pytest.raises(Exception) as exc_info:
        get_grace_period(123, 'test-context')
    assert str(exc_info.value) == "Database error"

if __name__ == '__main__':
    pytest.main([__file__])