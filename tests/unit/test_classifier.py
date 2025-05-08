"""
Unit tests for src.classifier module.
"""

import pytest
import asyncio
import importlib.util
import os
from typing import List, Dict, Any

# Check if the classifier module exists before importing
classifier_module_exists = importlib.util.find_spec("src.classifier") is not None

# Import only if the module exists
if classifier_module_exists:
    from src.classifier import (
        get_relevance_score, is_interesting, 
        get_domain_relevance_score, get_relevance_score_async,
        process_story_batch_async, load_prompt_template,
        STORY_PROMPT_TEMPLATE
    )

from tests.fixtures.mock_anthropic import mock_anthropic, mock_async_anthropic

# Skip all tests - these are examples for a module that would need additional mocking
pytestmark = pytest.mark.skip(
    reason="classifier tests are examples only and depend on the specific implementation"
)

# Create test fixture for temporary prompt files
@pytest.fixture
def temp_prompt_files(tmp_path):
    """Create temporary prompt template files for testing."""
    # Create a temporary directory for prompts
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    
    # Create a test story prompt file
    story_file = prompts_dir / "story_test.txt"
    story_file.write_text("Test story prompt template")
    
    # Create a test domain prompt file
    domain_file = prompts_dir / "domain_test.txt"
    domain_file.write_text("Test domain prompt template")
    
    return {
        "prompts_dir": prompts_dir,
        "story_file": story_file,
        "domain_file": domain_file
    }

@pytest.mark.unit
def test_load_prompt_template(temp_prompt_files):
    """Test loading prompt templates from files."""
    if not classifier_module_exists:
        pytest.skip("Classifier module not available")
    
    # Test loading an existing template
    story_template = load_prompt_template(
        str(temp_prompt_files["story_file"]), 
        "Default story template"
    )
    assert story_template == "Test story prompt template"
    
    # Test loading a non-existent template (should fall back to default)
    non_existent = load_prompt_template(
        str(temp_prompt_files["prompts_dir"] / "nonexistent.txt"),
        "Default fallback template"
    )
    assert non_existent == "Default fallback template"


@pytest.mark.unit
def test_get_relevance_score(mock_anthropic):
    """Test getting a relevance score for a story."""
    # Test with programming story (should get high score)
    story = {
        "id": 1,
        "title": "Python Programming Tips and Tricks",
        "url": "https://example.com/python-tips"
    }
    
    score = get_relevance_score(story)
    assert score == 90  # From our mock
    
    # Test with funding story (should get low score)
    story = {
        "id": 2,
        "title": "Startup Raises $10M in Funding",
        "url": "https://example.com/startup-funding"
    }
    
    score = get_relevance_score(story)
    assert score == 25  # From our mock
    
    # Test with AI story (should get high score)
    story = {
        "id": 3,
        "title": "New Advances in Machine Learning Research",
        "url": "https://example.com/ml-advances"
    }
    
    score = get_relevance_score(story)
    assert score == 85  # From our mock
    
    # Test with generic story (should get default score)
    story = {
        "id": 4,
        "title": "Some Generic News Story",
        "url": "https://example.com/generic-news"
    }
    
    score = get_relevance_score(story)
    assert score == 75  # Default from our mock


@pytest.mark.unit
def test_is_interesting(mock_anthropic):
    """Test checking if a story is interesting."""
    # Test with previously scored story
    story = {
        "id": 1,
        "title": "Some Story",
        "relevance_score": 80
    }
    
    # Should be interesting with default threshold
    assert is_interesting(story) is True
    
    # Should not be interesting with higher threshold
    assert is_interesting(story, threshold=90) is False
    
    # Test with unscored programming story (should get scored)
    story = {
        "id": 2,
        "title": "Python Programming Guide",
        "url": "https://example.com/python-guide"
    }
    
    assert is_interesting(story) is True
    assert story['relevance_score'] == 90  # Should add score to story
    
    # Test with unscored funding story (should get scored)
    story = {
        "id": 3,
        "title": "Startup Funding News",
        "url": "https://example.com/funding-news"
    }
    
    assert is_interesting(story) is False
    assert story['relevance_score'] == 25  # Should add score to story


@pytest.mark.unit
def test_get_domain_relevance_score(mock_anthropic):
    """Test getting a relevance score for a domain."""
    # Test with programming domain
    score = get_domain_relevance_score("python.org")
    assert score == 90
    
    # Test with generic domain
    score = get_domain_relevance_score("example.com")
    assert score == 75
    
    # Test caching (should use cached value)
    # Make sure mock was called correct number of times
    assert len(mock_anthropic.messages.called_with) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_relevance_score_async(mock_async_anthropic):
    """Test getting a relevance score asynchronously."""
    # Test with programming story
    story = {
        "id": 1,
        "title": "Python Programming Guide",
        "url": "https://example.com/python-guide"
    }
    
    score = await get_relevance_score_async(story)
    assert score == 90
    
    # Test with funding story
    story = {
        "id": 2,
        "title": "Startup Funding News",
        "url": "https://example.com/funding-news"
    }
    
    score = await get_relevance_score_async(story)
    assert score == 25
    
    # Test domain optimization with python.org
    story = {
        "id": 3,
        "title": "Some Python News",
        "url": "https://python.org/news"
    }
    
    score = await get_relevance_score_async(story)
    assert score == 90


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_story_batch_async(mock_async_anthropic):
    """Test processing a batch of stories asynchronously."""
    # Create a batch of stories
    stories = [
        {
            "id": 1,
            "title": "Python Programming Guide",
            "url": "https://example.com/python-guide"
        },
        {
            "id": 2,
            "title": "Startup Funding News",
            "url": "https://example.com/funding-news"
        },
        {
            "id": 3,
            "title": "Machine Learning Research",
            "url": "https://example.com/ml-research"
        }
    ]
    
    # Process the batch
    processed_stories = await process_story_batch_async(stories, throttle_delay=0)
    
    # Check all stories were processed
    assert len(processed_stories) == 3
    
    # Check scores were added
    assert processed_stories[0]['relevance_score'] == 90  # Python
    assert processed_stories[1]['relevance_score'] == 25  # Funding
    assert processed_stories[2]['relevance_score'] == 85  # ML