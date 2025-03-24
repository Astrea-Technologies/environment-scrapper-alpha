"""
Vector embedding service for generating and managing embeddings in Pinecone.

This module provides a service for generating text embeddings using OpenAI's 
embedding models and managing them in the Pinecone vector database for the
Political Social Media Analysis Platform.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import backoff
import numpy as np
from openai import AsyncOpenAI, OpenAIError
# Import exceptions without importing the Pinecone package
# Exceptions will be handled generically to avoid import issues

from app.core.config import settings
from app.db.connections import get_pinecone


logger = logging.getLogger(__name__)


class VectorEmbeddingService:
    """
    Service for generating and managing text embeddings in Pinecone.
    
    This service provides methods for generating embeddings from text content using
    OpenAI's API, storing them in Pinecone, and managing their lifecycle, including
    updates and deletions.
    """
    
    def __init__(
        self,
        pinecone_index=None,
        model_name: Optional[str] = None,
        batch_size: int = 32,
        max_workers: int = 4
    ):
        """
        Initialize the vector embedding service.
        
        Args:
            pinecone_index: Pinecone index instance. If None, gets the default index.
            model_name: Name of the OpenAI embedding model to use. If None,
                        uses the default from settings.
            batch_size: Maximum number of embeddings to process in a batch.
            max_workers: Maximum number of worker threads for parallel processing.
        """
        self._pinecone_index = pinecone_index or get_pinecone()
        self._pinecone_available = self._pinecone_index is not None
        self._model_name = model_name or settings.OPENAI_MODEL
        self._batch_size = batch_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Vector dimension from settings
        self._vector_dimension = settings.OPENAI_EMBEDDING_DIMENSION
        
        # Initialize OpenAI client if API key is available
        self._openai_client = None
        if settings.OPENAI_API_KEY:
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        if not self._pinecone_available:
            logger.warning("Pinecone is not available - vector storage operations will be disabled")
        
        if not self._openai_client:
            logger.warning("OpenAI API key not provided - embedding generation will be disabled")
    
    @backoff.on_exception(
        backoff.expo,
        OpenAIError,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text input using OpenAI.
        
        Args:
            text: The text to generate an embedding for.
            
        Returns:
            The generated embedding vector as a numpy array.
            
        Raises:
            OpenAIError: If there's an error from the OpenAI API.
            ValueError: If OpenAI client is not initialized.
        """
        if not text.strip():
            logger.warning("Attempt to generate embedding for empty text")
            # Return zero vector with correct dimension
            return np.zeros(self._vector_dimension)
        
        if not self._openai_client:
            logger.error("OpenAI client not initialized - cannot generate embeddings")
            raise ValueError("OpenAI client not initialized. Please provide an API key.")
        
        try:
            # Call OpenAI API to get embedding
            response = await self._openai_client.embeddings.create(
                model=self._model_name,
                input=text,
                encoding_format="float"
            )
            
            # Extract the embedding values from the response
            embedding = np.array(response.data[0].embedding)
            return embedding
        except OpenAIError as e:
            logger.error(f"Error generating embedding with OpenAI: {str(e)}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        OpenAIError,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of text inputs using OpenAI.
        
        Args:
            texts: List of texts to generate embeddings for.
            
        Returns:
            List of generated embedding vectors as numpy arrays.
            
        Raises:
            OpenAIError: If there's an error from the OpenAI API.
        """
        if not texts:
            return []
        
        # Process in batches to respect OpenAI API limits
        all_embeddings = []
        
        for i in range(0, len(texts), self._batch_size):
            batch_texts = texts[i:i + self._batch_size]
            
            # Filter out empty texts and create a mapping to track their positions
            non_empty_texts = []
            empty_indices = []
            
            for j, text in enumerate(batch_texts):
                if text.strip():
                    non_empty_texts.append(text)
                else:
                    empty_indices.append(j)
            
            # If all texts in the batch are empty, add zero vectors and continue
            if not non_empty_texts:
                all_embeddings.extend([np.zeros(self._vector_dimension) for _ in batch_texts])
                continue
            
            try:
                # Call OpenAI API to get embeddings for non-empty texts
                response = await self._openai_client.embeddings.create(
                    model=self._model_name,
                    input=non_empty_texts,
                    encoding_format="float"
                )
                
                # Extract embeddings from response
                batch_embeddings = [np.array(data.embedding) for data in response.data]
                
                # Reinsert zero vectors for empty texts
                if empty_indices:
                    full_batch_embeddings = []
                    non_empty_idx = 0
                    
                    for j in range(len(batch_texts)):
                        if j in empty_indices:
                            full_batch_embeddings.append(np.zeros(self._vector_dimension))
                        else:
                            full_batch_embeddings.append(batch_embeddings[non_empty_idx])
                            non_empty_idx += 1
                    
                    all_embeddings.extend(full_batch_embeddings)
                else:
                    all_embeddings.extend(batch_embeddings)
                
            except OpenAIError as e:
                logger.error(f"Error generating batch embeddings with OpenAI: {str(e)}")
                raise
        
        return all_embeddings
    
    @staticmethod
    def _prepare_metadata(
        content_type: str,
        content_id: str,
        account_id: Optional[Union[UUID, str]] = None,
        platform: Optional[str] = None,
        created_at: Optional[datetime] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare metadata for storing with the vector embedding.
        
        Args:
            content_type: Type of content ('post' or 'comment').
            content_id: ID of the content in MongoDB.
            account_id: Optional ID of the social media account.
            platform: Optional social media platform name.
            created_at: Optional timestamp of when the content was created.
            additional_metadata: Optional additional metadata to include.
            
        Returns:
            Dictionary of metadata suitable for storage in Pinecone.
        """
        metadata = {
            "content_type": content_type,
            "content_id": str(content_id),
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        if account_id:
            metadata["account_id"] = str(account_id)
        
        if platform:
            metadata["platform"] = platform
        
        if created_at:
            metadata["created_at"] = created_at.isoformat()
        
        # Add additional metadata
        if additional_metadata:
            # Filter out None values and convert all values to strings
            # since Pinecone metadata only supports string values
            for key, value in additional_metadata.items():
                if value is not None:
                    if isinstance(value, (dict, list)):
                        # Convert complex objects to strings
                        metadata[key] = str(value)
                    else:
                        metadata[key] = str(value)
        
        return metadata
    
    @backoff.on_exception(
        backoff.expo,
        Exception,  # Use generic exception instead of PineconeException
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def store_embedding(
        self,
        vector_id: str,
        embedding: np.ndarray,
        content_type: str,
        content_id: str,
        account_id: Optional[Union[UUID, str]] = None,
        platform: Optional[str] = None,
        created_at: Optional[datetime] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        namespace: str = ""
    ) -> bool:
        """
        Store a single embedding in Pinecone.
        
        Args:
            vector_id: ID to assign to the vector in Pinecone.
            embedding: The embedding vector to store.
            content_type: Type of content ('post' or 'comment').
            content_id: ID of the content in MongoDB.
            account_id: Optional ID of the social media account.
            platform: Optional social media platform name.
            created_at: Optional timestamp of when the content was created.
            additional_metadata: Optional additional metadata to include.
            namespace: Optional namespace to store the vector in.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            Exception: If there's an error from the Pinecone API.
            ConnectionError: If there's a connection error.
            ValueError: If Pinecone is not available.
        """
        if not self._pinecone_available or not self._pinecone_index:
            logger.error("Pinecone not available - cannot store embedding")
            return False
        
        try:
            metadata = self._prepare_metadata(
                content_type=content_type,
                content_id=content_id,
                account_id=account_id,
                platform=platform,
                created_at=created_at,
                additional_metadata=additional_metadata
            )
            
            # Pinecone upsert is synchronous, so run in thread pool
            loop = asyncio.get_event_loop()
            
            # Convert numpy array to list for Pinecone
            vector_values = embedding.tolist()
            
            await loop.run_in_executor(
                self._executor,
                partial(
                    self._pinecone_index.upsert,
                    vectors=[(vector_id, vector_values, metadata)],
                    namespace=namespace
                )
            )
            
            logger.debug(f"Stored embedding for {content_type} {content_id} with vector_id {vector_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing embedding: {str(e)}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        (Exception, ConnectionError),
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def store_embeddings_batch(
        self,
        embedding_data: List[Tuple[
            str,                # vector_id
            np.ndarray,         # embedding
            str,                # content_type
            str,                # content_id
            Optional[Union[UUID, str]],  # account_id
            Optional[str],      # platform
            Optional[datetime], # created_at
            Optional[Dict[str, Any]]  # additional_metadata
        ]],
        namespace: str = ""
    ) -> int:
        """
        Store multiple embeddings in Pinecone in batches.
        
        Args:
            embedding_data: List of tuples containing data for each embedding.
            namespace: Optional namespace to store the vectors in.
            
        Returns:
            Number of successfully stored embeddings.
            
        Raises:
            Exception: If there's an error from the Pinecone API.
            ConnectionError: If there's a connection error.
        """
        if not embedding_data:
            return 0
        
        vectors = []
        
        # Prepare vectors and metadata
        for (
            vector_id,
            embedding,
            content_type,
            content_id,
            account_id,
            platform,
            created_at,
            additional_metadata
        ) in embedding_data:
            metadata = self._prepare_metadata(
                content_type=content_type,
                content_id=content_id,
                account_id=account_id,
                platform=platform,
                created_at=created_at,
                additional_metadata=additional_metadata
            )
            
            # Convert numpy array to list for Pinecone
            vector_values = embedding.tolist()
            
            vectors.append((vector_id, vector_values, metadata))
        
        # Process in batches
        total_stored = 0
        loop = asyncio.get_event_loop()
        
        for i in range(0, len(vectors), self._batch_size):
            batch = vectors[i:i + self._batch_size]
            
            try:
                # Pinecone upsert is synchronous, so run in thread pool
                await loop.run_in_executor(
                    self._executor,
                    partial(
                        self._pinecone_index.upsert,
                        vectors=batch,
                        namespace=namespace
                    )
                )
                
                total_stored += len(batch)
                logger.debug(f"Stored batch of {len(batch)} embeddings")
            except Exception as e:
                logger.error(f"Error storing batch of embeddings: {str(e)}")
                raise
        
        return total_stored
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def update_embedding(
        self,
        vector_id: str,
        embedding: Optional[np.ndarray] = None,
        updated_metadata: Optional[Dict[str, Any]] = None,
        namespace: str = ""
    ) -> bool:
        """
        Update an existing embedding in Pinecone.
        
        Args:
            vector_id: ID of the vector to update.
            embedding: Optional new embedding vector. If None, only updates metadata.
            updated_metadata: Optional metadata to update.
            namespace: Optional namespace to update the vector in.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            Exception: If there's an error from the Pinecone API.
            ConnectionError: If there's a connection error.
        """
        try:
            loop = asyncio.get_event_loop()
            
            # If only updating metadata
            if embedding is None and updated_metadata:
                # First, retrieve the existing vector to get its current values
                fetch_response = await loop.run_in_executor(
                    self._executor,
                    partial(
                        self._pinecone_index.fetch,
                        ids=[vector_id],
                        namespace=namespace
                    )
                )
                
                if vector_id not in fetch_response.vectors:
                    logger.warning(f"Vector {vector_id} not found for metadata update")
                    return False
                
                # Update only the metadata, keeping the existing vector values
                vector_values = fetch_response.vectors[vector_id].values
                current_metadata = fetch_response.vectors[vector_id].metadata or {}
                
                # Merge existing metadata with updates
                updated_metadata = {**current_metadata, **updated_metadata}
                
                # Upsert with updated metadata
                await loop.run_in_executor(
                    self._executor,
                    partial(
                        self._pinecone_index.upsert,
                        vectors=[(vector_id, vector_values, updated_metadata)],
                        namespace=namespace
                    )
                )
            # If updating vector values
            elif embedding is not None:
                vector_values = embedding.tolist()
                
                if updated_metadata:
                    # Get current metadata if needed
                    fetch_response = await loop.run_in_executor(
                        self._executor,
                        partial(
                            self._pinecone_index.fetch,
                            ids=[vector_id],
                            namespace=namespace
                        )
                    )
                    
                    if vector_id in fetch_response.vectors:
                        current_metadata = fetch_response.vectors[vector_id].metadata or {}
                        # Merge existing metadata with updates
                        updated_metadata = {**current_metadata, **updated_metadata}
                
                # Upsert with new vector values and updated metadata
                await loop.run_in_executor(
                    self._executor,
                    partial(
                        self._pinecone_index.upsert,
                        vectors=[(vector_id, vector_values, updated_metadata or {})],
                        namespace=namespace
                    )
                )
            else:
                # Both embedding and updated_metadata are None
                logger.warning("No updates provided for vector")
                return False
            
            logger.debug(f"Updated embedding for vector_id {vector_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating embedding: {str(e)}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def delete_embedding(
        self,
        vector_id: str,
        namespace: str = ""
    ) -> bool:
        """
        Delete an embedding from Pinecone.
        
        Args:
            vector_id: ID of the vector to delete.
            namespace: Optional namespace to delete the vector from.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            Exception: If there's an error from the Pinecone API.
            ConnectionError: If there's a connection error.
        """
        try:
            # Pinecone delete is synchronous, so run in thread pool
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self._executor,
                partial(
                    self._pinecone_index.delete,
                    ids=[vector_id],
                    namespace=namespace
                )
            )
            
            logger.debug(f"Deleted embedding with vector_id {vector_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting embedding: {str(e)}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def delete_embeddings_batch(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> int:
        """
        Delete multiple embeddings from Pinecone in batches.
        
        Args:
            vector_ids: List of vector IDs to delete.
            namespace: Optional namespace to delete the vectors from.
            
        Returns:
            Number of successfully deleted embeddings.
            
        Raises:
            Exception: If there's an error from the Pinecone API.
            ConnectionError: If there's a connection error.
        """
        if not vector_ids:
            return 0
        
        total_deleted = 0
        loop = asyncio.get_event_loop()
        
        # Process in batches
        for i in range(0, len(vector_ids), self._batch_size):
            batch_ids = vector_ids[i:i + self._batch_size]
            
            try:
                # Pinecone delete is synchronous, so run in thread pool
                await loop.run_in_executor(
                    self._executor,
                    partial(
                        self._pinecone_index.delete,
                        ids=batch_ids,
                        namespace=namespace
                    )
                )
                
                total_deleted += len(batch_ids)
                logger.debug(f"Deleted batch of {len(batch_ids)} embeddings")
            except Exception as e:
                logger.error(f"Error deleting batch of embeddings: {str(e)}")
                raise
        
        return total_deleted
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def delete_embeddings_by_filter(
        self,
        filter_condition: Dict[str, Any],
        namespace: str = ""
    ) -> bool:
        """
        Delete embeddings from Pinecone based on metadata filter.
        
        Args:
            filter_condition: Metadata filter condition to match vectors for deletion.
            namespace: Optional namespace to delete the vectors from.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            Exception: If there's an error from the Pinecone API.
            ConnectionError: If there's a connection error.
        """
        try:
            # Pinecone delete is synchronous, so run in thread pool
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self._executor,
                partial(
                    self._pinecone_index.delete,
                    filter=filter_condition,
                    namespace=namespace
                )
            )
            
            logger.debug(f"Deleted embeddings using filter: {filter_condition}")
            return True
        except Exception as e:
            logger.error(f"Error deleting embeddings by filter: {str(e)}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    async def check_vector_exists(
        self,
        vector_id: str,
        namespace: str = ""
    ) -> bool:
        """
        Check if a vector with the given ID exists in Pinecone.
        
        Args:
            vector_id: ID of the vector to check.
            namespace: Optional namespace to check in.
            
        Returns:
            True if the vector exists, False otherwise.
            
        Raises:
            Exception: If there's an error from the Pinecone API.
            ConnectionError: If there's a connection error.
        """
        try:
            # Pinecone fetch is synchronous, so run in thread pool
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                self._executor,
                partial(
                    self._pinecone_index.fetch,
                    ids=[vector_id],
                    namespace=namespace
                )
            )
            
            return vector_id in response.vectors
        except Exception as e:
            logger.error(f"Error checking if vector exists: {str(e)}")
            raise
    
    async def close(self):
        """
        Clean up resources used by the service.
        
        This should be called when the service is no longer needed to ensure
        proper cleanup of thread pool and other resources.
        """
        self._executor.shutdown()
        # Close the OpenAI client
        if self._openai_client:
            await self._openai_client.close() 