"""
APIFY API Client

This module provides a client for interacting with APIFY API to scrape social media platforms.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApifyClient:
    """
    Client for interacting with the APIFY API.
    
    This class provides methods for starting, monitoring, and retrieving results
    from APIFY actors. It includes error handling, retries, and rate limiting.
    """
    
    def __init__(self):
        """Initialize the APIFY client with API key from settings."""
        self.api_key = settings.APIFY_API_KEY
        self.base_url = "https://api.apify.com/v2"
        self.default_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.last_request_time = 0
        self.min_request_interval = settings.SCRAPING_MIN_REQUEST_INTERVAL
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        
        self.last_request_time = time.time()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
        retry_delay: int = 2
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the APIFY API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint (relative to base URL)
            data: Request data for POST requests
            params: Query parameters
            retries: Number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Parsed JSON response
            
        Raises:
            HTTPException: If the request fails after all retries
        """
        url = f"{self.base_url}{endpoint}"
        
        # Enforce rate limiting
        await self._enforce_rate_limit()
        
        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=self.default_headers,
                        json=data if data else None,
                        params=params if params else None
                    ) as response:
                        if response.status >= 400:
                            response_text = await response.text()
                            logger.error(
                                f"APIFY API error: {response.status}, {response_text}, "
                                f"Endpoint: {endpoint}, Attempt: {attempt + 1}/{retries}"
                            )
                            
                            # Raise error on last attempt or for 4xx client errors (except 429)
                            if attempt == retries - 1 or (400 <= response.status < 500 and response.status != 429):
                                raise HTTPException(
                                    status_code=response.status,
                                    detail=f"APIFY API error: {response_text}"
                                )
                            
                            # Exponential backoff delay
                            delay = retry_delay * (2 ** attempt)
                            await asyncio.sleep(delay)
                            continue
                        
                        return await response.json()
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"APIFY API connection error: {str(e)}, Attempt: {attempt + 1}/{retries}")
                
                if attempt == retries - 1:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Failed to connect to APIFY API after {retries} attempts: {str(e)}"
                    )
                
                # Exponential backoff delay
                delay = retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        # This code should never be reached, but return an empty dict to satisfy type checking
        return {}
    
    async def start_actor_run(
        self,
        actor_id: str,
        run_input: Dict[str, Any]
    ) -> str:
        """
        Start an APIFY actor run.
        
        Args:
            actor_id: ID of the APIFY actor to run
            run_input: Actor input parameters
            
        Returns:
            Run ID of the actor run
        """
        endpoint = f"/acts/{actor_id}/runs"
        
        logger.info(f"Starting APIFY actor run: {actor_id}")
        response = await self._make_request("POST", endpoint, data={"run": run_input})
        
        run_id = response.get("data", {}).get("id")
        if not run_id:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start APIFY actor run: {json.dumps(response)}"
            )
        
        logger.info(f"APIFY actor run started: {run_id}")
        return run_id
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get the status of an APIFY actor run.
        
        Args:
            run_id: ID of the actor run
            
        Returns:
            Run status details
        """
        endpoint = f"/actor-runs/{run_id}"
        return await self._make_request("GET", endpoint)
    
    async def is_run_finished(self, run_id: str) -> bool:
        """
        Check if an APIFY actor run is finished.
        
        Args:
            run_id: ID of the actor run
            
        Returns:
            True if the run is finished, False otherwise
        """
        run_info = await self.get_run_status(run_id)
        status = run_info.get("data", {}).get("status")
        return status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]
    
    async def wait_for_run_to_finish(
        self,
        run_id: str,
        check_interval: int = 5,
        max_wait_time: int = 600
    ) -> Dict[str, Any]:
        """
        Wait for an APIFY actor run to finish.
        
        Args:
            run_id: ID of the actor run
            check_interval: Interval between status checks in seconds
            max_wait_time: Maximum wait time in seconds
            
        Returns:
            Run details after completion
            
        Raises:
            HTTPException: If the run fails or times out
        """
        logger.info(f"Waiting for APIFY actor run to finish: {run_id}")
        
        start_time = time.time()
        
        while True:
            run_info = await self.get_run_status(run_id)
            status = run_info.get("data", {}).get("status")
            
            if status == "SUCCEEDED":
                logger.info(f"APIFY actor run completed successfully: {run_id}")
                return run_info
            
            if status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                logger.error(f"APIFY actor run failed: {run_id}, status: {status}")
                raise HTTPException(
                    status_code=500,
                    detail=f"APIFY actor run failed with status: {status}"
                )
            
            # Check for timeout
            if time.time() - start_time > max_wait_time:
                logger.error(f"Timed out waiting for APIFY actor run: {run_id}")
                raise HTTPException(
                    status_code=504,
                    detail=f"Timed out waiting for APIFY actor run after {max_wait_time} seconds"
                )
            
            await asyncio.sleep(check_interval)
    
    async def get_run_results(
        self,
        run_id: str,
        clean: bool = True,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the results of an APIFY actor run.
        
        Args:
            run_id: ID of the actor run
            clean: Whether to clean the run after retrieving results
            limit: Maximum number of results to retrieve
            
        Returns:
            List of results from the actor run
        """
        endpoint = f"/actor-runs/{run_id}/dataset/items"
        params = {}
        
        if limit:
            params["limit"] = limit
        
        logger.info(f"Getting results for APIFY actor run: {run_id}")
        response = await self._make_request("GET", endpoint, params=params)
        
        # Clean up the run if requested
        if clean:
            await self.delete_run(run_id)
        
        return response.get("data", [])
    
    async def delete_run(self, run_id: str) -> bool:
        """
        Delete an APIFY actor run.
        
        Args:
            run_id: ID of the actor run
            
        Returns:
            True if the run was deleted successfully
        """
        endpoint = f"/actor-runs/{run_id}"
        
        logger.info(f"Deleting APIFY actor run: {run_id}")
        await self._make_request("DELETE", endpoint)
        
        return True
    
    async def start_and_wait_for_results(
        self,
        actor_id: str,
        run_input: Dict[str, Any],
        limit: Optional[int] = None,
        check_interval: int = 5,
        max_wait_time: int = 600
    ) -> List[Dict[str, Any]]:
        """
        Helper method to start an actor run, wait for it to finish, and get results.
        
        Args:
            actor_id: ID of the APIFY actor to run
            run_input: Actor input parameters
            limit: Maximum number of results to retrieve
            check_interval: Interval between status checks in seconds
            max_wait_time: Maximum wait time in seconds
            
        Returns:
            List of results from the actor run
        """
        run_id = await self.start_actor_run(actor_id, run_input)
        await self.wait_for_run_to_finish(run_id, check_interval, max_wait_time)
        return await self.get_run_results(run_id, clean=True, limit=limit) 