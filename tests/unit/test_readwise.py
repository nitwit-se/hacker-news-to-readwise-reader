"""
Tests for the Readwise Reader integration.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from src.readwise import (
    get_api_key, get_headers, url_exists_in_readwise,
    add_to_readwise, batch_add_to_readwise, ReadwiseError
)

class TestReadwiseIntegration:
    """Test cases for Readwise Reader integration."""

    def test_get_api_key_exists(self, monkeypatch):
        """Test that get_api_key returns the API key when it exists."""
        # Set up the environment variable
        monkeypatch.setenv("READWISE_API_KEY", "test_api_key")
        
        # Call the function
        api_key = get_api_key()
        
        # Check the result
        assert api_key == "test_api_key"

    def test_get_api_key_missing(self, monkeypatch):
        """Test that get_api_key raises an error when API key is missing."""
        # Clear the environment variable
        monkeypatch.delenv("READWISE_API_KEY", raising=False)
        
        # Call the function and check for exception
        with pytest.raises(ReadwiseError, match="READWISE_API_KEY environment variable not set"):
            get_api_key()

    def test_get_headers(self, monkeypatch):
        """Test that get_headers returns the correct headers."""
        # Set up the environment variable
        monkeypatch.setenv("READWISE_API_KEY", "test_api_key")
        
        # Call the function
        headers = get_headers()
        
        # Check the result
        assert headers == {
            "Authorization": "Token test_api_key",
            "Content-Type": "application/json",
        }

    @patch("src.readwise.get_all_readwise_urls")
    def test_url_exists_in_readwise_true(self, mock_get_all_urls):
        """Test url_exists_in_readwise when URL exists."""
        # Set up the mock to return a set of URLs including our test URL
        mock_get_all_urls.return_value = {
            "https://example.com/test",
            "https://another-site.com/article"
        }
        
        # Call the function
        result = url_exists_in_readwise("https://example.com/test")
        
        # Check the result
        assert result is True
        
        # Verify the mock was called once
        mock_get_all_urls.assert_called_once()

    @patch("src.readwise.get_all_readwise_urls")
    def test_url_exists_in_readwise_false(self, mock_get_all_urls):
        """Test url_exists_in_readwise when URL doesn't exist."""
        # Set up the mock to return a set of URLs NOT including our test URL
        mock_get_all_urls.return_value = {
            "https://different-url.com/test",
            "https://another-site.com/article"
        }
        
        # Call the function
        result = url_exists_in_readwise("https://example.com/test")
        
        # Check the result
        assert result is False
        
        # Verify the mock was called once
        mock_get_all_urls.assert_called_once()

    @patch("src.readwise.get_all_readwise_urls")
    def test_url_exists_in_readwise_error(self, mock_get_all_urls):
        """Test url_exists_in_readwise when API call fails."""
        # Set up the mock to raise an exception
        mock_get_all_urls.side_effect = ReadwiseError("API error")
        
        # Call the function and check for exception
        with pytest.raises(ReadwiseError, match="API error"):
            url_exists_in_readwise("https://example.com/test")

    @patch("src.readwise.get_api_key")
    @patch("src.readwise.requests.post")
    def test_add_to_readwise_success(self, mock_post, mock_get_api_key):
        """Test add_to_readwise when successful."""
        # Mock the API key
        mock_get_api_key.return_value = "test_api_key"
        
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Call the function
        result = add_to_readwise("https://example.com/test", "Test Title")
        
        # Check the result
        assert result == {"id": "123", "status": "success"}
        
        # Verify that the correct API call was made
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["url"] == "https://example.com/test"
        assert kwargs["json"]["title"] == "Test Title"
        assert kwargs["json"]["author"] == "hn-poll"
        assert kwargs["json"]["tags"] == ["hackernews"]
        assert kwargs["json"]["should_clean_html"] is True

    @patch("src.readwise.get_api_key")
    @patch("src.readwise.requests.post")
    def test_add_to_readwise_error(self, mock_post, mock_get_api_key):
        """Test add_to_readwise when API call fails."""
        # Mock the API key
        mock_get_api_key.return_value = "test_api_key"
        
        # Set up the mock to raise a RequestException
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("API error")
        
        # Call the function and check for exception
        with pytest.raises(ReadwiseError, match="Failed to add URL to Readwise: API error"):
            add_to_readwise("https://example.com/test", "Test Title")

    @patch("src.readwise.add_to_readwise")
    @patch("src.readwise.url_exists_in_readwise")
    @patch("src.readwise.get_story")
    def test_batch_add_to_readwise(self, mock_get_story, mock_url_exists, mock_add):
        """Test batch_add_to_readwise with mixed results."""
        # Set up the mocks
        # All stories exist in HN API
        mock_get_story.return_value = {"id": 123, "title": "Test Title", "url": "https://example.com/test"}
        
        # First and fourth URLs exist in Readwise, others don't
        mock_url_exists.side_effect = [True, False, False, True]
        
        # Second URL successfully added, third URL errors
        mock_add.side_effect = [
            {"id": "123", "status": "success"},
            ReadwiseError("API error")
        ]
        
        # Test data
        stories = [
            {"id": 1, "url": "https://example.com/1", "title": "Test 1"},  # Already exists
            {"id": 2, "url": "https://example.com/2", "title": "Test 2"},  # Added successfully
            {"id": 3, "url": "https://example.com/3", "title": "Test 3"},  # API error
            {"id": 4, "url": "https://example.com/4", "title": "Test 4"},  # Already exists
        ]
        
        # Call the function
        # Provide existing_urls set to prevent API calls and set verify_story_exists=False
        # to bypass the need for real Hacker News API calls
        added_ids, failed_ids = batch_add_to_readwise(
            stories,
            existing_urls={
                "https://example.com/1",
                "https://example.com/4"
            },
            verify_story_exists=False
        )
        
        # Check the results
        assert added_ids == [1, 2, 4]  # 1 and 4 already existed, 2 added successfully
        assert len(failed_ids) == 1
        assert failed_ids[0][0] == 3  # Story 3 failed
        
        # Verify that add_to_readwise was called exactly for the right stories
        assert mock_add.call_count == 2  # Called for stories 2 and 3 (not 1 and 4 since they already exist)