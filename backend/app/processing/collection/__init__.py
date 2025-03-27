"""
Social Media Collection Package

This package provides classes for collecting data from social media platforms
using APIFY actors.
"""

from app.processing.collection.base import BaseCollector
from app.processing.collection.twitter import TwitterCollector
from app.processing.collection.facebook import FacebookCollector
from app.processing.collection.instagram import InstagramCollector
from app.processing.collection.factory import CollectorFactory

__all__ = [
    "BaseCollector",
    "TwitterCollector", 
    "FacebookCollector",
    "InstagramCollector",
    "CollectorFactory"
] 