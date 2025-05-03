"""
Mock Anthropic API client for testing.
"""

from typing import Dict, Any, List, Optional
import pytest


class MockAnthropicMessage:
    """Mock message response from Anthropic API."""
    
    def __init__(self, content: str):
        self.content = [
            {
                "type": "text",
                "text": content
            }
        ]


class MockAnthropicResponse:
    """Mock response from Anthropic API."""
    
    def __init__(self, content: str):
        self.content = [
            {
                "type": "text",
                "text": content
            }
        ]


class MockAnthropicMessages:
    """Mock messages interface for Anthropic API."""
    
    def __init__(self, default_response: str = "75"):
        self.default_response = default_response
        self.called_with = []

    def create(self, model: str, max_tokens: int, temperature: float, 
               system: str, messages: List[Dict[str, str]]) -> MockAnthropicResponse:
        """Mock create method."""
        self.called_with.append({
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": messages
        })
        
        # Determine the response based on the content
        content = messages[0]["content"] if messages else ""
        if "Startup Funding" in content or "funding" in content.lower():
            return MockAnthropicResponse("25")  # Low relevance for funding stories
        elif "Python" in content or "programming" in content:
            return MockAnthropicResponse("90")  # High relevance for programming
        elif "Machine Learning" in content or "AI" in content:
            return MockAnthropicResponse("85")  # High relevance for ML/AI
        
        # Default response
        return MockAnthropicResponse(self.default_response)


class MockAsyncAnthropicMessages:
    """Mock async messages interface for Anthropic API."""
    
    def __init__(self, default_response: str = "75"):
        self.default_response = default_response
        self.called_with = []

    async def create(self, model: str, max_tokens: int, temperature: float, 
                     system: str, messages: List[Dict[str, str]]) -> MockAnthropicResponse:
        """Mock async create method."""
        self.called_with.append({
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": messages
        })
        
        # Determine the response based on the content
        content = messages[0]["content"] if messages else ""
        if "Startup Funding" in content or "funding" in content.lower():
            return MockAnthropicResponse("25")  # Low relevance for funding stories
        elif "Python" in content or "programming" in content:
            return MockAnthropicResponse("90")  # High relevance for programming
        elif "Machine Learning" in content or "AI" in content:
            return MockAnthropicResponse("85")  # High relevance for ML/AI
        
        # Default response
        return MockAnthropicResponse(self.default_response)


class MockAnthropic:
    """Mock Anthropic client."""
    
    def __init__(self, api_key: str = "test_key", default_response: str = "75"):
        self.api_key = api_key
        self.messages = MockAnthropicMessages(default_response)


class MockAsyncAnthropic:
    """Mock async Anthropic client."""
    
    def __init__(self, api_key: str = "test_key", default_response: str = "75"):
        self.api_key = api_key
        self.messages = MockAsyncAnthropicMessages(default_response)


@pytest.fixture
def mock_anthropic(monkeypatch):
    """Fixture to mock Anthropic client."""
    mock_client = MockAnthropic()
    
    try:
        # Import here to avoid circular imports
        import src.classifier
        
        # Replace the real client with our mock
        monkeypatch.setattr(src.classifier, "client", mock_client)
    except (ImportError, AttributeError):
        # If classifier module doesn't exist or doesn't have client attribute
        pass
    
    return mock_client


@pytest.fixture
def mock_async_anthropic(monkeypatch):
    """Fixture to mock async Anthropic client."""
    mock_client = MockAsyncAnthropic()
    
    try:
        # Import here to avoid circular imports
        import src.classifier
        
        # Replace the real client with our mock
        monkeypatch.setattr(src.classifier, "async_client", mock_client)
    except (ImportError, AttributeError):
        # If classifier module doesn't exist or doesn't have async_client attribute
        pass
    
    return mock_client