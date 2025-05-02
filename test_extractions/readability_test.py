#\!/usr/bin/env python3

import requests
from readability import Document
import html2text

def extract_main_content(url):
    """
    Extract main content from a URL using readability-lxml and html2text
    
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
    
    # Extract main content with Readability
    doc = Document(response.text)
    title = doc.title()
    main_content_html = doc.summary()
    
    # Convert to markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # No wrapping
    markdown = h.handle(main_content_html)
    
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
        with open("readability_output.md", "w") as f:
            f.write(f"# {title}\n\n")
            f.write(content)
            
        print(f"\nFull content saved to readability_output.md")
    except Exception as e:
        print(f"Error: {e}")
EOT < /dev/null