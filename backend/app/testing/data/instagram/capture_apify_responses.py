#!/usr/bin/env python
"""
APIFY Response Capture Script

This script helps capture actual APIFY responses for testing purposes.
It demonstrates how to use the APIFY API to fetch real data and save it
in the format expected by the InstagramTestCollector.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from app.core.config import settings
from app.core.apify_client import ApifyClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def capture_instagram_profile(client, username, output_file=None):
    """Capture an Instagram profile using APIFY."""
    logger.info(f"Capturing Instagram profile for user: {username}")
    
    # Configure APIFY input for the Instagram Scraper actor
    run_input = {
        "usernames": [username],
        "resultsType": "details",
        "maxPosts": 0  # Don't need posts for profile info
    }
    
    # Run actor and wait for results
    results = await client.start_and_wait_for_results(
        actor_id=settings.APIFY_INSTAGRAM_ACTOR_ID,
        run_input=run_input,
        limit=1
    )
    
    # Filter for profile objects
    profiles = []
    for item in results:
        if "type" in item and item["type"] == "user":
            profiles.append(item)
    
    logger.info(f"Captured {len(profiles)} profile objects")
    
    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(profiles, f, indent=2)
        logger.info(f"Saved profile data to {output_file}")
    
    return profiles

async def capture_instagram_posts(client, username, count=10, output_file=None):
    """Capture Instagram posts using APIFY."""
    logger.info(f"Capturing {count} Instagram posts for user: {username}")
    
    # Configure APIFY input for the Instagram Scraper actor
    run_input = {
        "usernames": [username],
        "resultsType": "posts",
        "maxPosts": count
    }
    
    # Run actor and wait for results
    results = await client.start_and_wait_for_results(
        actor_id=settings.APIFY_INSTAGRAM_ACTOR_ID,
        run_input=run_input,
        limit=count
    )
    
    # Filter for post objects
    posts = []
    for item in results:
        # Instagram APIFY actor sometimes nests posts inside profile objects
        if "type" in item and item["type"] == "user":
            if "latestPosts" in item:
                posts.extend(item["latestPosts"])
        elif "type" in item and item["type"] == "post":
            # This is a post object directly
            posts.append(item)
        elif "shortCode" in item or "caption" in item:
            # Likely a post without explicit type
            posts.append(item)
    
    logger.info(f"Captured {len(posts)} post objects")
    
    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(posts, f, indent=2)
        logger.info(f"Saved post data to {output_file}")
    
    return posts

async def capture_instagram_comments(client, post_url, count=20, output_file=None):
    """Capture Instagram comments using APIFY."""
    logger.info(f"Capturing {count} Instagram comments for post: {post_url}")
    
    # Configure APIFY input for the Instagram Comment Scraper actor
    run_input = {
        "directUrls": [post_url],
        "resultsType": "comments",
        "maxComments": count
    }
    
    # Run actor and wait for results
    results = await client.start_and_wait_for_results(
        actor_id="apify/instagram-comment-scraper",
        run_input=run_input,
        limit=count
    )
    
    # Extract comments from results
    comments = []
    for item in results:
        if "type" in item and item["type"] == "post":
            if "comments" in item:
                comments.extend(item["comments"])
        elif "id" in item and "ownerUsername" in item:
            # This is likely a comment object directly
            comments.append(item)
    
    logger.info(f"Captured {len(comments)} comment objects")
    
    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(comments, f, indent=2)
        logger.info(f"Saved comment data to {output_file}")
    
    return comments

async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Capture APIFY responses for testing")
    
    # Add subparsers for different capture types
    subparsers = parser.add_subparsers(dest="command", help="Capture command")
    
    # Profile capture command
    profile_parser = subparsers.add_parser("profile", help="Capture Instagram profile")
    profile_parser.add_argument("username", help="Instagram username")
    profile_parser.add_argument("-o", "--output", help="Output file", default="backend/app/testing/data/instagram/profile_samples.json")
    
    # Posts capture command
    posts_parser = subparsers.add_parser("posts", help="Capture Instagram posts")
    posts_parser.add_argument("username", help="Instagram username")
    posts_parser.add_argument("-c", "--count", help="Number of posts to capture", type=int, default=10)
    posts_parser.add_argument("-o", "--output", help="Output file", default="backend/app/testing/data/instagram/post_samples.json")
    
    # Comments capture command
    comments_parser = subparsers.add_parser("comments", help="Capture Instagram comments")
    comments_parser.add_argument("post_url", help="Instagram post URL")
    comments_parser.add_argument("-c", "--count", help="Number of comments to capture", type=int, default=20)
    comments_parser.add_argument("-o", "--output", help="Output file", default="backend/app/testing/data/instagram/comment_samples.json")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create APIFY client
    client = ApifyClient(settings.APIFY_API_KEY)
    
    # Execute the appropriate command
    if args.command == "profile":
        await capture_instagram_profile(client, args.username, args.output)
    elif args.command == "posts":
        await capture_instagram_posts(client, args.username, args.count, args.output)
    elif args.command == "comments":
        await capture_instagram_comments(client, args.post_url, args.count, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 