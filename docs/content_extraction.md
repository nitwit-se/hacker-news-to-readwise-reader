# Content Extraction Strategy

This document details the approach used for extracting meaningful content from web pages in the Hacker News Poller project.

## Overview

The project uses a sophisticated multi-stage approach to extract meaningful content from web pages while excluding navigation elements, advertisements, and other non-content elements. This strategy balances effectiveness with simplicity by leveraging existing dependencies (BeautifulSoup and html2text) without requiring additional libraries.

## Extraction Process

### 1. Main Content Container Identification

The system first attempts to locate the main content container using these strategies:

- Searches for common content container elements using CSS selectors:
  - `article`, `main`, `.content`, `#content`, `.post`, `.entry`, etc.
- Falls back to finding the `<div>` with the most text content if no identifiable container exists
- Requires a minimum text length (200 characters) to qualify as main content
- Prioritizes elements with higher text-to-HTML ratios

### 2. Non-Content Element Removal

Once the main container is identified, the system removes elements unlikely to be part of the actual content:

- Removes script, style, nav, header, footer, and aside elements
- Filters out elements with class names matching navigation patterns (e.g., "nav", "menu", "sidebar")
- Removes social media buttons, sharing widgets, and copyright notices
- Filters advertisements based on common ad container class names and IDs
- Removes comment sections unless specifically requested

### 3. Content Cleaning

After extraction, the raw content is processed to improve readability:

- Removes reference-style links that often appear at the end of articles
- Filters out consecutive short lines that are likely menu items
- Preserves headings and meaningful paragraph text
- Cleans up excessive blank lines
- Normalizes whitespace and removes redundant formatting
- Preserves images with appropriate alt text

### 4. Summary Generation

For display purposes, the system generates concise summaries:

- Extracts first few paragraphs to create a meaningful summary
- Removes markdown formatting from the summary for clean display
- Truncates to desired length while preserving sentence structure
- Ensures the summary ends with a complete sentence
- Adds an ellipsis (...) when the content is truncated

## Error Handling

The content extraction process includes robust error handling:

- Timeouts for slow-loading pages
- Special handling for sites that block content fetching (e.g., Twitter)
- Fallback extraction methods when primary methods fail
- Categorization of errors for better debugging and reporting
- Retry mechanism with exponential backoff for transient errors

## Benefits of This Approach

- **Progressive Enhancement**: Builds on existing functionality rather than replacing it
- **Minimal Dependencies**: Leverages already-required libraries
- **Targeted Extraction**: Focuses specifically on article content
- **Maintainable Code**: Clear separation of concerns with distinct processing stages
- **Adaptable**: Works with a wide variety of web page structures

## Implementation

The content extraction is implemented in `src/content.py` with the core functionality divided into:

- URL fetching with proper headers and error handling
- HTML parsing and main content identification
- Content cleaning and formatting
- Summary generation for display
- Error categorization and reporting

## Testing

The `test_extractions/` directory contains test scripts and examples for evaluating and comparing different content extraction approaches:

- `bs4_custom_test.py`: Tests the custom BeautifulSoup-based extraction
- `readability_test.py`: Compares with the Mozilla Readability algorithm
- `trafilatura_test.py`: Benchmarks against the Trafilatura library
- `test_content.py`: Unit tests for the content extraction functionality