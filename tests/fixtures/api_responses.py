"""
API response fixtures for testing.
"""

from typing import Dict, Any, List

# Sample response for top stories endpoint
TOP_STORIES_RESPONSE = [
    39428394, 39428395, 39428396, 39428397, 39428398, 
    39428399, 39428400, 39428401, 39428402, 39428403
]

# Sample response for best stories endpoint
BEST_STORIES_RESPONSE = [
    39428404, 39428405, 39428406, 39428407, 39428408, 
    39428409, 39428410, 39428411, 39428412, 39428413
]

# Sample response for new stories endpoint
NEW_STORIES_RESPONSE = [
    39428414, 39428415, 39428416, 39428417, 39428418, 
    39428419, 39428420, 39428421, 39428422, 39428423
]

# Sample response for the maximum item ID
MAX_ITEM_RESPONSE = 39428423

# Sample story responses
STORY_RESPONSES: Dict[int, Dict[str, Any]] = {
    # High-scoring story within timeframe
    39428394: {
        "id": 39428394,
        "title": "Test Story: Programming in Python",
        "url": "https://example.com/python-programming",
        "score": 150,
        "by": "test_user",
        "time": 1683123456,  # Recent timestamp
        "type": "story",
        "kids": [123456, 123457],
        "descendants": 2,
    },
    # Medium-scoring story within timeframe
    39428395: {
        "id": 39428395,
        "title": "Test Story: Machine Learning News",
        "url": "https://example.com/ml-news",
        "score": 42,
        "by": "test_user2",
        "time": 1683123457,
        "type": "story",
    },
    # Low-scoring story within timeframe
    39428396: {
        "id": 39428396,
        "title": "Test Story: Startup Funding",
        "url": "https://example.com/startup-funding",
        "score": 10,
        "by": "test_user3",
        "time": 1683123458,
        "type": "story",
    },
    # Old story with high score
    39428397: {
        "id": 39428397,
        "title": "Test Story: Old Programming Article",
        "url": "https://example.com/old-programming",
        "score": 200,
        "by": "test_user4",
        "time": 1583123459,  # Old timestamp
        "type": "story",
    },
    # Job posting
    39428398: {
        "id": 39428398,
        "title": "Test Job: Software Engineer at Example Inc",
        "url": "https://example.com/job-posting",
        "score": 1,
        "by": "test_user5",
        "time": 1683123460,
        "type": "job",
    },
    # Ask HN
    39428399: {
        "id": 39428399,
        "title": "Ask HN: What programming language should I learn in 2023?",
        "text": "I'm looking to learn a new programming language in 2023. What would you recommend?",
        "score": 50,
        "by": "test_user6",
        "time": 1683123461,
        "type": "story",
    },
    # Invalid story (missing fields)
    39428400: {
        "id": 39428400,
        "title": "Invalid Story",
        "type": "story",
    },
    # Not found case
    39428401: None,
}


def get_mock_story_response(story_id: int) -> Dict[str, Any]:
    """
    Get a mock story response for the given ID, or a default one if not found.
    """
    return STORY_RESPONSES.get(story_id, {
        "id": story_id,
        "title": f"Generic Test Story {story_id}",
        "url": f"https://example.com/story-{story_id}",
        "score": 20,
        "by": "generic_user",
        "time": 1683123456,
        "type": "story",
    })