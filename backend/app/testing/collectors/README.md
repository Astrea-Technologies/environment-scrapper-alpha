# Instagram Test Collector

This directory contains test collectors for verifying that APIFY responses are correctly parsed and transformed into our application's data model.

## InstagramTestCollector

The `InstagramTestCollector` class loads real APIFY Instagram response data from JSON files and tests the transformation process, generating output files that show exactly how the raw APIFY data is transformed into our internal data model.

### Why This Is Useful

1. **Schema Validation**: When APIFY updates their API or response format, this tool helps verify that our transformations still work correctly.
2. **Data Integrity**: Ensures that the transformed data maintains all essential information from the original APIFY response.
3. **Debugging**: Provides sample data and output files that can be used to debug issues with the transformation process.
4. **Documentation**: Acts as living documentation of how APIFY responses are transformed.

### Getting Started

To use the Instagram test collector:

1. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Adding Sample Data**
   First, you need to add sample APIFY response data:
   ```
   python run_instagram_test.py --add-sample path/to/apify_response.json post
   ```

   The last parameter specifies the type of data:
   - `post`: For Instagram post data
   - `comment`: For Instagram comment data
   - `profile`: For Instagram profile data

3. **Running the Test Collector**
   
   To test individual components:
   ```
   python run_instagram_test.py
   ```

   To test the complete Instagram scraping workflow:
   ```
   python run_instagram_test.py --workflow [username] [post_count]
   ```

   This will transform all available sample data and save the output to `output/instagram_test/`.

### Actual Instagram Scraping Workflow

The test collector simulates the actual Instagram scraping sequence:

1. **Profile Retrieval**: First, it obtains profile data using APIFY actor `cL9BqLGM9fymiF8rs` (Instagram Scraper)
2. **Post Extraction**: Then, it extracts the latest 1-n posts from the profile response
3. **Comment Collection**: Finally, it makes separate calls to the APIFY actor `apify/instagram-comment-scraper` to get comments for each post

This sequence mirrors the actual production workflow, allowing you to test the complete data collection pipeline.

### Sample Data Structure

Sample data should be structured as JSON arrays of APIFY response objects. You can obtain this data by:
1. Running a real APIFY actor and saving the response
2. Exporting data from the APIFY console
3. Using the APIFY API to fetch sample responses

### Output Files

The test collector generates the following output files:
- `transformed_posts_[timestamp].json`: Transformed post data
- `transformed_comments_[timestamp].json`: Transformed comment data
- `transformed_profiles_[timestamp].json`: Transformed profile data

When running the workflow test, it generates these additional files:
- `profile_[username]_[timestamp].json`: Transformed profile
- `posts_[username]_[timestamp].json`: Transformed posts
- `comments_post[idx]_[timestamp].json`: Transformed comments for each post
- `workflow_summary_[username]_[timestamp].json`: Summary of the workflow run

These files show exactly how the APIFY response data is transformed into our application's data model.

### Example Usage in Tests

```python
import pytest
from app.testing.collectors.instagram_test import InstagramTestCollector

@pytest.mark.asyncio
async def test_instagram_transformation():
    collector = InstagramTestCollector()
    
    # Test post transformation
    posts = await collector.test_post_transformation("test-account-id")
    assert len(posts) > 0
    assert "platform_id" in posts[0]
    assert "content" in posts[0]
    
    # Verify specific transformations
    first_post = posts[0]
    assert first_post["platform"] == "instagram"
    assert "text" in first_post["content"]
    assert "hashtags" in first_post["content"]
    
    # Test the full workflow
    workflow_results = await collector.test_instagram_scraping_workflow(
        username="testuser",
        post_count=3,
        output_dir="tests/output"
    )
    assert "profile" in workflow_results
    assert "posts" in workflow_results
    assert "comments" in workflow_results 