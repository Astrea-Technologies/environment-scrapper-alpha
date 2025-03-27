"""
Instagram Test Collector

A test collector that uses real APIFY response data to verify schema transformations.
This is separate from the main Instagram collector and is used for testing purposes.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.processing.collection.instagram import InstagramCollector

logger = logging.getLogger(__name__)

class InstagramTestCollector:
    """
    Test collector for Instagram data that uses real APIFY response samples.
    
    This collector loads real APIFY responses from JSON files and transforms them
    using the same logic as the production collector. It's used to verify that
    response schemas are correctly parsed and transformed.
    """
    
    def __init__(self, sample_data_path: str = "backend/app/testing/data/instagram/"):
        """Initialize the Instagram test collector with path to sample data."""
        self.sample_data_path = Path(sample_data_path)
        self.instagram_collector = InstagramCollector()
        self.post_samples = []
        self.comment_samples = []
        self.profile_samples = []
        self.load_sample_responses()
        
    def load_sample_responses(self):
        """Load sample APIFY responses from JSON files."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.sample_data_path, exist_ok=True)
            
            # Load post samples
            post_path = self.sample_data_path / "post_samples.json"
            if post_path.exists():
                with open(post_path, "r") as f:
                    self.post_samples = json.load(f)
                logger.info(f"Loaded {len(self.post_samples)} Instagram post samples")
            
            # Load comment samples
            comment_path = self.sample_data_path / "comment_samples.json"
            if comment_path.exists():
                with open(comment_path, "r") as f:
                    self.comment_samples = json.load(f)
                logger.info(f"Loaded {len(self.comment_samples)} Instagram comment samples")
            
            # Load profile samples
            profile_path = self.sample_data_path / "profile_samples.json"
            if profile_path.exists():
                with open(profile_path, "r") as f:
                    self.profile_samples = json.load(f)
                logger.info(f"Loaded {len(self.profile_samples)} Instagram profile samples")
                
        except Exception as e:
            logger.error(f"Error loading sample files: {str(e)}")
            # Initialize empty if files don't exist
            if not self.post_samples:
                self.post_samples = []
            if not self.comment_samples:
                self.comment_samples = []
            if not self.profile_samples:
                self.profile_samples = []
    
    def save_sample_response(self, data: List[Dict[str, Any]], sample_type: str):
        """Save a new sample response to the appropriate file."""
        file_path = self.sample_data_path / f"{sample_type}_samples.json"
        
        # Load existing samples if file exists
        existing_samples = []
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    existing_samples = json.load(f)
            except Exception as e:
                logger.error(f"Error reading existing samples: {str(e)}")
        
        # Add new samples
        existing_samples.extend(data)
        
        # Save combined samples
        with open(file_path, "w") as f:
            json.dump(existing_samples, f, indent=2)
        
        logger.info(f"Saved {len(data)} new {sample_type} samples to {file_path}")
        
        # Update in-memory samples
        if sample_type == "post":
            self.post_samples = existing_samples
        elif sample_type == "comment":
            self.comment_samples = existing_samples
        elif sample_type == "profile":
            self.profile_samples = existing_samples
    
    async def test_post_transformation(self, account_id: str, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Test transformation of Instagram posts using real APIFY samples.
        
        Args:
            account_id: Account ID to associate with the posts
            output_file: Optional path to save the transformed posts
            
        Returns:
            List of transformed posts
        """
        if not self.post_samples:
            raise ValueError("No Instagram post samples available. Please add sample data first.")
        
        logger.info(f"Testing transformation of {len(self.post_samples)} Instagram posts")
        
        transformed_posts = []
        for raw_post in self.post_samples:
            transformed = self.instagram_collector.transform_post(raw_post, account_id)
            transformed_posts.append(transformed)
        
        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(transformed_posts, f, indent=2)
            logger.info(f"Saved {len(transformed_posts)} transformed posts to {output_file}")
        
        return transformed_posts
    
    async def test_comment_transformation(self, post_id: str, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Test transformation of Instagram comments using real APIFY samples.
        
        Args:
            post_id: Post ID to associate with the comments
            output_file: Optional path to save the transformed comments
            
        Returns:
            List of transformed comments
        """
        if not self.comment_samples:
            raise ValueError("No Instagram comment samples available. Please add sample data first.")
        
        logger.info(f"Testing transformation of {len(self.comment_samples)} Instagram comments")
        
        transformed_comments = []
        for raw_comment in self.comment_samples:
            transformed = self.instagram_collector.transform_comment(raw_comment, post_id)
            transformed_comments.append(transformed)
        
        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(transformed_comments, f, indent=2)
            logger.info(f"Saved {len(transformed_comments)} transformed comments to {output_file}")
        
        return transformed_comments
    
    async def test_profile_transformation(self, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Test transformation of Instagram profiles using real APIFY samples.
        
        Args:
            output_file: Optional path to save the transformed profiles
            
        Returns:
            List of transformed profiles
        """
        if not self.profile_samples:
            raise ValueError("No Instagram profile samples available. Please add sample data first.")
        
        logger.info(f"Testing transformation of {len(self.profile_samples)} Instagram profiles")
        
        transformed_profiles = []
        for raw_profile in self.profile_samples:
            transformed = self.instagram_collector.transform_profile(raw_profile)
            transformed_profiles.append(transformed)
        
        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(transformed_profiles, f, indent=2)
            logger.info(f"Saved {len(transformed_profiles)} transformed profiles to {output_file}")
        
        return transformed_profiles
    
    def add_apify_response(self, response_data: List[Dict[str, Any]], response_type: str):
        """
        Add a new APIFY response as a sample.
        
        Args:
            response_data: Raw APIFY response data
            response_type: Type of response ("post", "comment", or "profile")
        """
        if response_type not in ["post", "comment", "profile"]:
            raise ValueError(f"Invalid response type: {response_type}. Must be 'post', 'comment', or 'profile'.")
        
        self.save_sample_response(response_data, response_type)
        
    async def test_instagram_scraping_workflow(
        self, 
        username: str, 
        post_count: int = 3, 
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test the full Instagram scraping workflow using real APIFY response samples.
        
        This simulates the actual sequence of:
        1. Obtaining profile data from actor cL9BqLGM9fymiF8rs
        2. Extracting latest posts from the profile response
        3. Making calls to apify/instagram-comment-scraper for each post
        
        Args:
            username: Instagram username to simulate scraping for
            post_count: Number of posts to include in the simulation
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing the results of each step
        """
        if not self.profile_samples:
            raise ValueError("No Instagram profile samples available. Please add sample data first.")
            
        if not self.post_samples:
            raise ValueError("No Instagram post samples available. Please add sample data first.")
            
        if not self.comment_samples:
            raise ValueError("No Instagram comment samples available. Please add sample data first.")
        
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        account_id = f"test-account-{username}"
        
        logger.info(f"Testing full Instagram scraping workflow for user: {username}")
        
        # Step 1: Get profile data (simulate cL9BqLGM9fymiF8rs actor call)
        logger.info(f"Step 1: Simulating profile data retrieval with actor cL9BqLGM9fymiF8rs")
        profile_data = self.profile_samples[0] if self.profile_samples else {}
        
        # Transform profile data
        transformed_profile = self.instagram_collector.transform_profile(profile_data)
        
        if output_dir:
            with open(f"{output_dir}/profile_{username}_{timestamp}.json", "w") as f:
                json.dump(transformed_profile, f, indent=2)
                
        # Step 2: Extract posts from profile response
        logger.info(f"Step 2: Extracting latest {post_count} posts from profile response")
        
        # In real APIFY responses, posts are often nested in the profile response
        # For our test, we'll just use the available post samples
        available_posts = min(post_count, len(self.post_samples))
        posts = self.post_samples[:available_posts]
        
        transformed_posts = []
        for post in posts:
            transformed_post = self.instagram_collector.transform_post(post, account_id)
            transformed_posts.append(transformed_post)
            
        if output_dir:
            with open(f"{output_dir}/posts_{username}_{timestamp}.json", "w") as f:
                json.dump(transformed_posts, f, indent=2)
                
        # Step 3: Get comments for each post (simulate apify/instagram-comment-scraper calls)
        logger.info(f"Step 3: Simulating comment scraping for {len(transformed_posts)} posts")
        
        all_comments = {}
        for idx, post in enumerate(transformed_posts):
            post_id = post.get("platform_id", f"test-post-{idx}")
            
            # Simulate comment scraping call
            logger.info(f"Simulating comment scraping for post: {post_id}")
            
            # Take a subset of comment samples for this post (with different counts for realism)
            comment_count = min(len(self.comment_samples), (idx + 1) * 5)
            post_comments = self.comment_samples[:comment_count]
            
            # Transform comments
            transformed_comments = []
            for comment in post_comments:
                transformed_comment = self.instagram_collector.transform_comment(comment, post_id)
                transformed_comments.append(transformed_comment)
                
            all_comments[post_id] = transformed_comments
            
            if output_dir:
                with open(f"{output_dir}/comments_post{idx}_{timestamp}.json", "w") as f:
                    json.dump(transformed_comments, f, indent=2)
        
        # Create workflow summary
        workflow_results = {
            "profile": transformed_profile,
            "posts": transformed_posts,
            "comments": all_comments,
            "metadata": {
                "username": username,
                "timestamp": timestamp,
                "post_count": len(transformed_posts),
                "total_comments": sum(len(comments) for comments in all_comments.values())
            }
        }
        
        if output_dir:
            with open(f"{output_dir}/workflow_summary_{username}_{timestamp}.json", "w") as f:
                json.dump(workflow_results["metadata"], f, indent=2)
                
        logger.info(f"Instagram scraping workflow test completed for user: {username}")
        logger.info(f"Processed {len(transformed_posts)} posts and {workflow_results['metadata']['total_comments']} comments")
        
        return workflow_results 