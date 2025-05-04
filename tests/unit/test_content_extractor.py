import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.content_extractor import ContentExtractor, extract_content_from_url

# Sample HTML for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
</head>
<body>
    <header>
        <h1>Test Article Title</h1>
        <div class="metadata">By Author Name</div>
    </header>
    <main>
        <article>
            <p>This is the main content of the article. It contains important information.</p>
            <p>This is a second paragraph with additional details.</p>
        </article>
    </main>
    <footer>Copyright 2023</footer>
</body>
</html>
"""

# Sample extracted content that Trafilatura would return
SAMPLE_EXTRACTED = """# Test Article Title

This is the main content of the article. It contains important information.

This is a second paragraph with additional details."""


@pytest.mark.asyncio
async def test_extract_content_success():
    """Test successful content extraction."""
    with patch("src.content_extractor.async_playwright") as mock_playwright:
        # Mock the browser, context, and page
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # Set up the chain of mocks
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # Mock the page content method to return sample HTML
        mock_page.content = AsyncMock(return_value=SAMPLE_HTML)
        
        # Mock Trafilatura to return sample extracted content
        with patch("trafilatura.extract", return_value=SAMPLE_EXTRACTED):
            # Create extractor and test
            extractor = ContentExtractor()
            html, text = await extractor.extract_content("https://example.com/article")
            
            # Verify results
            assert html == SAMPLE_HTML
            assert text == SAMPLE_EXTRACTED
            
            # Verify the correct methods were called
            mock_page.goto.assert_called_once_with(
                "https://example.com/article", 
                timeout=30000, 
                wait_until="networkidle"
            )


@pytest.mark.asyncio
async def test_extract_content_timeout():
    """Test content extraction when page load times out."""
    with patch("src.content_extractor.async_playwright") as mock_playwright:
        # Mock the browser, context, and page
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # Set up the chain of mocks
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # Make the goto method raise a timeout error
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout"))
        
        # Create extractor and test
        extractor = ContentExtractor()
        html, text = await extractor.extract_content("https://example.com/slow-page")
        
        # Verify results
        assert html is None
        assert text is None


@pytest.mark.asyncio
async def test_extract_content_invalid_url():
    """Test content extraction with an invalid URL."""
    extractor = ContentExtractor()
    
    # Test with None URL
    html, text = await extractor.extract_content(None)
    assert html is None
    assert text is None
    
    # Test with invalid URL format
    html, text = await extractor.extract_content("not-a-url")
    assert html is None
    assert text is None


@pytest.mark.asyncio
async def test_extract_content_batch():
    """Test batch extraction of content."""
    with patch("src.content_extractor.ContentExtractor.extract_content") as mock_extract:
        # Set up the mock to return different values for different URLs
        async def mock_extract_side_effect(url):
            if url == "https://example.com/1":
                return "html1", "content1"
            elif url == "https://example.com/2":
                return "html2", "content2"
            else:
                return None, None
        
        mock_extract.side_effect = mock_extract_side_effect
        
        # Create extractor and test
        extractor = ContentExtractor()
        results = await extractor.extract_content_batch([
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/invalid"
        ])
        
        # Verify results
        assert results["https://example.com/1"] == ("html1", "content1")
        assert results["https://example.com/2"] == ("html2", "content2")
        assert results["https://example.com/invalid"] == (None, None)


@pytest.mark.asyncio
async def test_extract_content_from_url():
    """Test the helper function for extracting content from URL."""
    with patch("src.content_extractor.ContentExtractor.extract_content") as mock_extract:
        # Set up the mock
        mock_extract.return_value = ("sample html", "sample content")
        
        # Test the helper function
        content = await extract_content_from_url("https://example.com")
        
        # Verify results
        assert content == "sample content"