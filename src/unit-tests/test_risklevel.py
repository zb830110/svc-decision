import pytest
from unittest.mock import patch, MagicMock
from risklevel import get_activation_risk_score, activation_risk_level, get_activation_risk_level

@patch('risklevel.get_score')
def test_get_activation_risk_score(mock_get_score):
    mock_get_score.return_value = {'score': 0.5}
    result = get_activation_risk_score(123, 'test-context')
    assert result == {'score': 0.5}
    mock_get_score.assert_called_once_with(123, 'test-context', 'activation')

def test_activation_risk_level():
    # Test low risk cases
    assert activation_risk_level(0) == 'low'
    assert activation_risk_level(0.5) == 'low'
    assert activation_risk_level(1) == 'low'
    
    # Test high risk case
    assert activation_risk_level(1.5) == 'high'
    
    # Test unknown risk case
    assert activation_risk_level(-1) == 'unknown'
    
    # Test edge cases
    assert activation_risk_level(1.0001) == 'high'
    assert activation_risk_level(0.9999) == 'low'

@patch('risklevel.get_score')
def test_get_activation_risk_level(mock_get_score):
    mock_get_score.return_value = {'score': 0.5}
    
    level, group = get_activation_risk_level(123, 0.5)
    assert level == 'low'
    assert group == 2
    
    level, group = get_activation_risk_level(123, 1.5)
    assert level == 'high'
    assert group == 2
    
    level, group = get_activation_risk_level(123, -1)
    assert level == 'unknown'
    assert group == 2

@patch('risklevel.get_score')
def test_get_activation_risk_level_edge_cases(mock_get_score):
    test_cases = [
        (0, 'low'),
        (1, 'low'),
        (1.0001, 'high'),
        (0.9999, 'low'),
        (-0.0001, 'unknown'),
        (float('inf'), 'high'),
        (float('-inf'), 'unknown'),
    ]
    
    for score, expected_level in test_cases:
        mock_get_score.return_value = {'score': score}
        level, group = get_activation_risk_level(123, score)
        assert level == expected_level
        assert group == 2

@patch('risklevel.get_score')
def test_get_activation_risk_level_error_handling(mock_get_score):
    mock_get_score.side_effect = Exception("API Error")
    
    with pytest.raises(Exception) as exc_info:
        get_activation_risk_level(123, 0.5)
    assert str(exc_info.value) == "API Error"

@patch('risklevel.get_score')
def test_get_activation_risk_score_invalid_input(mock_get_score):
    # Test with invalid user_id
    with pytest.raises(ValueError):
        get_activation_risk_score("invalid_user", 'test-context')
    
    # Test with invalid context_id
    with pytest.raises(ValueError):
        get_activation_risk_score(123, None)

def test_activation_risk_level_invalid_input():
    with pytest.raises(TypeError):
        activation_risk_level("not a number")

@patch('risklevel.get_score')
def test_get_activation_risk_level_missing_score(mock_get_score):
    mock_get_score.return_value = {}  # Missing 'score' key
    
    with pytest.raises(KeyError):
        get_activation_risk_level(123, 0.5)

if __name__ == '__main__':
    pytest.main([__file__])