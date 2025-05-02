#\!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import html2text
import re

def extract_main_content(url):
    """
    Extract main content from a URL using custom BeautifulSoup heuristics
    
    Args:
        url (str): The URL to extract content from
        
    Returns:
        tuple: (title, markdown_content)
    """
    # Fetch the page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/91.0.4472.114 Safari/537.36',
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract title
    title = soup.title.text.strip() if soup.title else "No title found"
    
    # Remove non-content elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        element.decompose()
        
    # Remove common ad/nav class patterns
    for element in soup.find_all(class_=re.compile('(nav|menu|header|footer|sidebar|banner|ad|widget|cookie|popup|social|comment)')):
        element.decompose()
        
    # Find the main content
    # Strategies in priority order:
    main_content = None
    
    # 1. Look for common content containers
    for selector in ['article', 'main', '.content', '#content', '.post', '.entry', '.article', '[role="main"]']:
        content_element = soup.select_one(selector)
        if content_element:
            main_content = content_element
            break
    
    # 2. If no content container found, use heuristic to find the div with most text
    if not main_content:
        max_text_length = 0
        for div in soup.find_all('div'):
            text_length = len(div.get_text(strip=True))
            if text_length > max_text_length:
                max_text_length = text_length
                main_content = div
    
    # Get content as HTML
    if main_content:
        content_html = str(main_content)
    else:
        content_html = str(soup.body) if soup.body else str(soup)
    
    # Convert to markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # No wrapping
    markdown = h.handle(content_html)
    
    # Post-process markdown - remove excessive blank lines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    return title, markdown

if __name__ == "__main__":
    # Sample article to test with
    url = "https://hbr.org/2023/12/research-how-ai-tools-like-chatgpt-are-changing-the-way-we-brainstorm"
    
    try:
        title, content = extract_main_content(url)
        print(f"Title: {title}")
        print("\nContent Summary:")
        print(content[:500] + "..." if len(content) > 500 else content)
        
        # Save the output
        with open("bs4_custom_output.md", "w") as f:
            f.write(f"# {title}\n\n")
            f.write(content)
            
        print(f"\nFull content saved to bs4_custom_output.md")
    except Exception as e:
        print(f"Error: {e}")
EOT < /dev/null