import os
from anthropic import Anthropic

# Initialize the Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_relevance_score(story):
    """Calculate a relevance score for how well a HN story matches user interests.
    
    Args:
        story (dict): Story details from the Hacker News API
        
    Returns:
        int: Relevance score from 0-100, where higher values indicate more relevant content
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
    system_prompt = """Evaluate how strongly this Hacker News story would match the following interest categories:

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

Rate the story's relevance to these interests on a scale from 0-100, where:
- 0-25: Not relevant to these interests
- 26-50: Slightly relevant to these interests
- 51-75: Moderately relevant to these interests
- 76-100: Highly relevant to these interests

ONLY respond with a single integer between 0 and 100, and nothing else."""
    
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
        
        # Parse the response - this assumes Claude follows instructions and returns a number
        response = message.content[0].text.strip()
        try:
            score = int(response)
            # Ensure the score is within the valid range
            return max(0, min(100, score))
        except ValueError:
            # If we couldn't parse an integer, make a best effort to continue
            if "not relevant" in response.lower():
                return 0
            elif "highly relevant" in response.lower():
                return 90
            elif "moderately relevant" in response.lower():
                return 60
            elif "slightly relevant" in response.lower():
                return 30
            else:
                return 0
        
    except Exception as e:
        # Log error and default to 0 if API call fails
        print(f"Error calculating relevance score: {e}")
        return 0

# Keep the old function for backward compatibility, but use the new one internally
def is_interesting(story, threshold=75):
    """Classify if a HN story matches user interests using a relevance score.
    
    Args:
        story (dict): Story details from the Hacker News API
        threshold (int): Minimum relevance score to be considered interesting (0-100)
        
    Returns:
        bool: True if the story's relevance score exceeds the threshold
    """
    # If we already have a stored relevance score, use it
    if 'relevance_score' in story and story['relevance_score'] is not None:
        return story['relevance_score'] >= threshold
    
    # Otherwise, calculate a new score
    score = get_relevance_score(story)
    
    # Store the score in the story dictionary for potential later use
    story['relevance_score'] = score
    
    return score >= threshold