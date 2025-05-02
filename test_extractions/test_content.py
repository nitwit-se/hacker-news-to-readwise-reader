#!/usr/bin/env python3

"""
Test script for the improved content extraction and cleaning.
"""

import sys
import os
import argparse
import time

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.content import fetch_url_content, html_to_markdown, clean_markdown_content, get_content_summary

def test_content_extraction(url):
    """Test the content extraction process for a URL."""
    print(f"\nTesting content extraction for: {url}")
    
    # Step 1: Fetch HTML content
    print("\n1. Fetching HTML content...")
    try:
        html_content = fetch_url_content(url)
        print(f"HTML content fetched: {len(html_content)} characters")
        
        # Save raw HTML for inspection
        with open("test_raw_html.html", "w") as f:
            f.write(html_content)
        print("Raw HTML saved to test_raw_html.html")
    except Exception as e:
        print(f"Error fetching HTML: {e}")
        return
    
    # Step 2: Extract main content with BeautifulSoup
    print("\n2. Extracting main content with BeautifulSoup...")
    try:
        markdown = html_to_markdown(html_content)
        print(f"Markdown content extracted: {len(markdown)} characters")
        
        # Save raw markdown for inspection
        with open("test_raw_markdown.md", "w") as f:
            f.write(markdown)
        print("Raw markdown saved to test_raw_markdown.md")
    except Exception as e:
        print(f"Error extracting main content: {e}")
        return
    
    # Step 3: Clean the markdown
    print("\n3. Cleaning and filtering markdown content...")
    try:
        cleaned_markdown = clean_markdown_content(markdown)
        print(f"Cleaned markdown: {len(cleaned_markdown)} characters")
        print(f"Removed {len(markdown) - len(cleaned_markdown)} characters of noise")
        
        # Save cleaned markdown for inspection
        with open("test_cleaned_markdown.md", "w") as f:
            f.write(cleaned_markdown)
        print("Cleaned markdown saved to test_cleaned_markdown.md")
    except Exception as e:
        print(f"Error cleaning markdown: {e}")
        return
    
    # Step 4: Generate a summary
    print("\n4. Generating content summary...")
    try:
        summary = get_content_summary(cleaned_markdown)
        print(f"Summary: {len(summary)} characters")
        print(f"\nSummary preview: {summary[:200]}...")
        
        # Save summary for inspection
        with open("test_summary.txt", "w") as f:
            f.write(summary)
        print("Summary saved to test_summary.txt")
    except Exception as e:
        print(f"Error generating summary: {e}")
        return
    
    print("\nContent extraction test completed successfully!")

def main():
    parser = argparse.ArgumentParser(description='Test content extraction')
    parser.add_argument('--url', type=str, 
                        default='https://hbr.org/2023/12/research-how-ai-tools-like-chatgpt-are-changing-the-way-we-brainstorm', 
                        help='URL to test content extraction with')
    args = parser.parse_args()
    
    print("Content Extraction Test")
    print("======================")
    print(f"Testing URL: {args.url}")
    
    test_content_extraction(args.url)

if __name__ == "__main__":
    main()