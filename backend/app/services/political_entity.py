import uuid
from typing import List, Optional, Dict, Any

from sqlmodel import Session

from app.db.models.political_entity import PoliticalEntity, EntityType
from app.services.repositories.political_entity import PoliticalEntityRepository


# Create a singleton instance of the repository
political_entity_repository = PoliticalEntityRepository()


async def create_political_entity(*, session: Session, entity_data: Dict[str, Any]) -> PoliticalEntity:
    """
    Create a new political entity.
    
    Args:
        session: Database session
        entity_data: Dictionary with entity data
        
    Returns:
        Created political entity
    """
    return await political_entity_repository.create(session=session, entity_data=entity_data)


async def get_political_entity(*, session: Session, entity_id: uuid.UUID) -> Optional[PoliticalEntity]:
    """
    Get a political entity by ID.
    
    Args:
        session: Database session
        entity_id: UUID of the entity
        
    Returns:
        Political entity if found, None otherwise
    """
    return await political_entity_repository.get(session=session, entity_id=entity_id)


async def get_political_entity_by_name(*, session: Session, name: str) -> Optional[PoliticalEntity]:
    """
    Get a political entity by name.
    
    Args:
        session: Database session
        name: Name of the entity
        
    Returns:
        Political entity if found, None otherwise
    """
    return await political_entity_repository.get_by_name(session=session, name=name)


async def get_political_entities(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100
) -> List[PoliticalEntity]:
    """
    Get a list of political entities with pagination.
    
    Args:
        session: Database session
        skip: Number of entities to skip
        limit: Maximum number of entities to return
        
    Returns:
        List of political entities
    """
    return await political_entity_repository.list(session=session, skip=skip, limit=limit)


async def get_political_entities_by_type(
    *,
    session: Session,
    entity_type: EntityType,
    skip: int = 0,
    limit: int = 100
) -> List[PoliticalEntity]:
    """
    Get a list of political entities filtered by type.
    
    Args:
        session: Database session
        entity_type: Type of the entity
        skip: Number of entities to skip
        limit: Maximum number of entities to return
        
    Returns:
        List of political entities
    """
    return await political_entity_repository.filter_by_entity_type(
        session=session,
        entity_type=entity_type,
        skip=skip,
        limit=limit
    )


async def update_political_entity(
    *,
    session: Session,
    entity: PoliticalEntity,
    update_data: Dict[str, Any]
) -> PoliticalEntity:
    """
    Update a political entity.
    
    Args:
        session: Database session
        entity: Existing political entity
        update_data: Dictionary with fields to update
        
    Returns:
        Updated political entity
    """
    return await political_entity_repository.update(
        session=session,
        entity=entity,
        update_data=update_data
    )


async def delete_political_entity(*, session: Session, entity_id: uuid.UUID) -> Optional[PoliticalEntity]:
    """
    Delete a political entity.
    
    Args:
        session: Database session
        entity_id: UUID of the entity
        
    Returns:
        Deleted political entity if found, None otherwise
    """
    return await political_entity_repository.delete(session=session, entity_id=entity_id) 