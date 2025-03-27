"""
Collector Factory

This module provides a factory for creating platform-specific collectors.
"""

import logging
from typing import Dict, Optional, Type, Union

from app.processing.collection.base import BaseCollector
from app.processing.collection.twitter import TwitterCollector
from app.processing.collection.facebook import FacebookCollector
from app.processing.collection.instagram import InstagramCollector

logger = logging.getLogger(__name__)


class CollectorFactory:
    """
    Factory for creating platform-specific social media collectors.
    
    This class manages the registry of available collectors and
    provides methods to get the appropriate collector for a given platform.
    """
    
    _registry: Dict[str, Type[BaseCollector]] = {
        "twitter": TwitterCollector,
        "facebook": FacebookCollector,
        "instagram": InstagramCollector
    }
    
    @classmethod
    def register_collector(cls, platform: str, collector_class: Type[BaseCollector]) -> None:
        """
        Register a new collector for a platform.
        
        Args:
            platform: Name of the platform (e.g., "twitter", "facebook")
            collector_class: Collector class to register
            
        Raises:
            ValueError: If the collector class is not a subclass of BaseCollector
        """
        if not issubclass(collector_class, BaseCollector):
            raise ValueError(f"Collector class must be a subclass of BaseCollector, got {collector_class}")
        
        cls._registry[platform.lower()] = collector_class
        logger.info(f"Registered collector for platform: {platform}")
    
    @classmethod
    def get_collector(cls, platform: str) -> BaseCollector:
        """
        Get a collector instance for the specified platform.
        
        Args:
            platform: Name of the platform (e.g., "twitter", "facebook")
            
        Returns:
            An instance of the appropriate collector
            
        Raises:
            ValueError: If no collector is registered for the platform
        """
        platform = platform.lower()
        
        if platform not in cls._registry:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(f"No collector registered for platform: {platform}. Supported platforms: {supported}")
        
        collector_class = cls._registry[platform]
        return collector_class()
    
    @classmethod
    def list_supported_platforms(cls) -> list[str]:
        """
        Get a list of all supported platforms.
        
        Returns:
            List of platform names
        """
        return list(cls._registry.keys())
    
    @classmethod
    def is_platform_supported(cls, platform: str) -> bool:
        """
        Check if a platform is supported.
        
        Args:
            platform: Name of the platform to check
            
        Returns:
            True if the platform is supported, False otherwise
        """
        return platform.lower() in cls._registry 