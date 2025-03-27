#!/usr/bin/env python
"""
Instagram Test Collector Runner

This script demonstrates how to use the InstagramTestCollector to
verify that Instagram APIFY responses are correctly transformed.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import our module
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.testing.collectors.instagram_test import InstagramTestCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Run the Instagram test collector."""
    # Create output directory
    output_dir = Path("backend/app/testing/output/instagram_test")
    os.makedirs(output_dir, exist_ok=True)
    
    test_collector = InstagramTestCollector()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        # Add sample data
        if cmd == "--add-sample":
            if len(sys.argv) < 4:
                print("Usage: python run_instagram_test.py --add-sample <sample_file> <type>")
                print("Where type is one of: post, comment, profile")
                return
                
            sample_file = sys.argv[2]
            sample_type = sys.argv[3]
            
            # Load and add the sample data
            logger.info(f"Loading sample data from {sample_file}")
            with open(sample_file, "r") as f:
                sample_data = json.load(f)
            
            test_collector.add_apify_response(sample_data, sample_type)
            logger.info(f"Added {len(sample_data)} {sample_type} samples")
            return
            
        # Run workflow test
        elif cmd == "--workflow":
            username = sys.argv[2] if len(sys.argv) > 2 else "testuser"
            post_count = int(sys.argv[3]) if len(sys.argv) > 3 else 3
            
            try:
                logger.info(f"Running Instagram workflow test for user '{username}' with {post_count} posts")
                workflow_results = await test_collector.test_instagram_scraping_workflow(
                    username=username,
                    post_count=post_count,
                    output_dir=output_dir
                )
                logger.info("Workflow test completed successfully")
                logger.info(f"Results saved to {output_dir}")
                return
            except ValueError as e:
                logger.error(f"Workflow test failed: {str(e)}")
                logger.info("Make sure you have added sample data for profiles, posts, and comments.")
                return
                
        # Show help
        elif cmd in ["-h", "--help"]:
            print("Instagram Test Collector Runner")
            print("")
            print("Usage:")
            print("  python run_instagram_test.py                 - Run individual component tests")
            print("  python run_instagram_test.py --workflow [username] [post_count] - Test full workflow")
            print("  python run_instagram_test.py --add-sample <sample_file> <type>  - Add sample data")
            print("")
            print("Sample types:")
            print("  - post: Instagram post data")
            print("  - comment: Instagram comment data") 
            print("  - profile: Instagram profile data")
            return

    # Get current timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Test post transformation
    try:
        transformed_posts = await test_collector.test_post_transformation(
            account_id="test-account-123",
            output_file=output_dir / f"transformed_posts_{timestamp}.json"
        )
        logger.info(f"Successfully transformed {len(transformed_posts)} posts")
    except ValueError as e:
        logger.warning(f"Post transformation test skipped: {str(e)}")
    
    # Test comment transformation
    try:
        transformed_comments = await test_collector.test_comment_transformation(
            post_id="test-post-123",
            output_file=output_dir / f"transformed_comments_{timestamp}.json"
        )
        logger.info(f"Successfully transformed {len(transformed_comments)} comments")
    except ValueError as e:
        logger.warning(f"Comment transformation test skipped: {str(e)}")
    
    # Test profile transformation
    try:
        transformed_profiles = await test_collector.test_profile_transformation(
            output_file=output_dir / f"transformed_profiles_{timestamp}.json"
        )
        logger.info(f"Successfully transformed {len(transformed_profiles)} profiles")
    except ValueError as e:
        logger.warning(f"Profile transformation test skipped: {str(e)}")
    
    logger.info("Instagram test collector run completed")

if __name__ == "__main__":
    asyncio.run(main()) 