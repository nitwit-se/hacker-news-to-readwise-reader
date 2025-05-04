# Prompt Templates

This directory contains prompt templates used by the Claude AI integration for relevance scoring in the Hacker News Poller application.

## Files

- `story_relevance.txt`: Template for classifying stories based on title, URL, and content
- `domain_relevance.txt`: Template for classifying domains (used for optimization)

## Customizing Templates

You can customize these templates to match your own interests. The templates should instruct Claude to return a single integer between 0-100 indicating relevance.

### Guidelines

1. **Keep the format consistent**:
   - Must instruct Claude to return a single integer between 0-100
   - Maintain clear categories/examples for Claude to evaluate against
   - Don't modify the scoring scale or response format

2. **Personalize the interest categories**:
   - Update the "MY INTERESTS" and "NOT MY INTERESTS" sections
   - Add specific technologies, topics, or fields you care about
   - Include examples of what you don't find interesting

3. **Usage**:
   - Edit these files directly, or
   - Create your own templates and specify their paths:
     ```bash
     # Via command-line:
     hn-poll score --story-prompt /path/to/your/template.txt
     
     # Via environment variables:
     export HN_STORY_PROMPT_FILE=/path/to/your/template.txt
     ```

## Example Custom Template

```
You are evaluating news articles to determine if they match my interests.

MY INTERESTS:
- Machine learning and AI applications in healthcare
- Rust programming language and ecosystem
- Privacy-focused technology
- Self-hosted software and services
- Retro computing and game emulation

NOT MY INTERESTS:
- Startup funding announcements
- Blockchain/cryptocurrency speculation
- Social media platform news
- Corporate earnings reports

Rate how relevant this content is to my interests on a scale from 0-100, where:
0 = completely irrelevant
100 = highly relevant

ONLY respond with a single integer between 0 and 100.
```

The application will load these templates when scoring stories. If a template file cannot be found or loaded, the application will use built-in default templates and display a warning.