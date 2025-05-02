#\!/usr/bin/env python3

import requests
import trafilatura
import html2text

def extract_main_content(url):
    """
    Extract main content from a URL using trafilatura
    
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
    
    # Extract with trafilatura
    extracted = trafilatura.extract(
        response.text,
        url=url,
        include_comments=False,
        include_tables=True,
        output_format="html"
    )
    
    # Use trafilatura's metadata to get title
    metadata = trafilatura.extract_metadata(response.text, url=url)
    title = metadata.title if metadata and metadata.title else "No title found"
    
    # Convert to markdown if extraction successful
    if extracted:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # No wrapping
        markdown = h.handle(extracted)
    else:
        markdown = "Content extraction failed"
    
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
        with open("trafilatura_output.md", "w") as f:
            f.write(f"# {title}\n\n")
            f.write(content)
            
        print(f"\nFull content saved to trafilatura_output.md")
    except Exception as e:
        print(f"Error: {e}")
EOT < /dev/null