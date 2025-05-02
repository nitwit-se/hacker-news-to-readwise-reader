import os
from anthropic import Anthropic

# Initialize the Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def is_interesting(story):
    """Classify if a HN story matches user interests.
    
    Args:
        story (dict): Story details from the Hacker News API
        
    Returns:
        bool: True if the story matches user interests, False otherwise
    """
    title = story.get('title', '')
    url = story.get('url', '')
    
    # Extract domain if URL is available
    domain = ""
    if url and '://' in url:
        domain = url.split('://')[1].split('/')[0]
    
    # Construct prompt with all available information
    prompt = f"Title: {title}\nDomain: {domain}\nURL: {url}"
    
    # Interest categories defined in the system prompt
    system_prompt = """Classify if this Hacker News story would interest someone with these interests:

1. Technology & Tools:
   - Emacs, Linux, NixOS, MacOS, Apple hardware
   - E-book readers and related technology

2. Programming & Computer Science:
   - Python, Julia, Lisp
   - Functional programming, logic programming
   - Any interesting programming language concepts

3. Security & Hacking:
   - Infosec, cybersecurity, penetration testing
   - Ethical hacking, cracking (in educational context)
   - Security research, vulnerabilities

4. Projects & Creativity:
   - DIY/home projects with technology
   - Creative coding, generative art
   - Hardware hacking, electronics

5. Science & Research:
   - AI, machine learning, LLMs
   - Climate change, environmental tech
   - Scientific computing

6. Books & Reading:
   - Technical books, programming books
   - E-book technology, digital reading

ONLY respond with YES or NO and nothing else."""
    
    # Call Claude API to classify
    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",  # Using Haiku for speed and cost
            max_tokens=100,                   # Tokens for response
            temperature=0,                    # No randomness for consistent results
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the response - this assumes Claude follows instructions and returns YES/NO
        response = message.content[0].text.strip().upper()
        return "YES" in response
        
    except Exception as e:
        # Log error and default to not interesting if API call fails
        print(f"Error classifying story: {e}")
        return False