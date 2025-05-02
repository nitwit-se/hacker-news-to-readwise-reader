# Content Extraction Libraries Research

## Current Dependencies
- requests>=2.31.0
- beautifulsoup4>=4.12.2
- html2text>=2020.1.16

## Library Options

### 1. Newspaper3k
- **Overview**: Full-featured news article extraction library
- **Features**: Article extraction, natural language processing, multi-language support
- **Approach**: Uses a combination of heuristics and machine learning to identify main content
- **Advantages**: 
  - Very well-suited for news articles
  - Can extract additional metadata (authors, publish date, etc.)
  - Mature and well-documented
- **Disadvantages**:
  - Heavy dependency with many requirements
  - May be overkill for simple content extraction
  - Might struggle with non-news websites
- **Maintenance**: Actively maintained with regular updates

### 2. Readability (Mozilla's Readability.js port)
- **Overview**: Python port of Mozilla's Readability.js (used in Firefox Reader View)
- **Features**: Extracts main article content, removes clutter
- **Approach**: Uses heuristic rules to identify content, scores elements by characteristics
- **Advantages**:
  - Well-tested algorithm used in Firefox
  - Lightweight compared to newspaper3k
  - Works well for a variety of websites, not just news
- **Disadvantages**:
  - Some Python ports may not be well-maintained
  - May require additional processing for optimal results
- **Maintenance**: Varies by port, most are relatively stable

### 3. Trafilatura
- **Overview**: Web scraping tool designed for text extraction
- **Features**: Extracts main content, comments, metadata from web pages
- **Approach**: Uses rule-based processing and structural analysis
- **Advantages**:
  - Specifically designed for text extraction
  - High accuracy in benchmarks
  - Good handling of a wide variety of websites
- **Disadvantages**:
  - May have more dependencies than needed
- **Maintenance**: Actively maintained, good community support

### 4. Goose3
- **Overview**: Article extraction library
- **Features**: Extracts articles and metadata from web pages
- **Approach**: Uses DOM analysis and heuristics to identify content
- **Advantages**:
  - Good balance between features and simplicity
  - Specifically designed for article extraction
- **Disadvantages**:
  - Fork of an older library (Goose)
  - May not handle all site layouts well
- **Maintenance**: Maintained, but less active than some alternatives

### 5. BoilerPy3
- **Overview**: Python port of the Boilerpipe Java library
- **Features**: Removes boilerplate content for cleaner text extraction
- **Approach**: Uses statistical and structural features to classify text blocks
- **Advantages**:
  - Fast and lightweight
  - Good at removing boilerplate content
- **Disadvantages**:
  - Not as actively maintained
  - May not extract images and other media
- **Maintenance**: Limited recent activity

### 6. BeautifulSoup Custom Solution
- **Overview**: Enhance our current BeautifulSoup implementation
- **Features**: Customized to our needs, building on existing code
- **Approach**: Identify and implement heuristics specifically for our use case
- **Advantages**:
  - Already a dependency in the project
  - No additional dependencies needed
  - Complete control over implementation
- **Disadvantages**:
  - Requires more custom development
  - May need ongoing refinement as websites change
- **Maintenance**: Maintained by us

## Recommendation

The best options appear to be:

1. **Trafilatura** - High accuracy, active maintenance, designed for text extraction
2. **ReadabilityParser** (Python port of Mozilla's Readability.js) - Proven algorithm, widely used
3. **Enhanced BeautifulSoup Solution** - Build on existing dependencies, custom implementation

For our Hacker News poller project, the best approach might be to start with a lightweight solution that builds on our existing dependencies, then add a specialized library if needed.
EOT < /dev/null