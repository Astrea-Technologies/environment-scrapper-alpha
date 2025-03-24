import uuid
from typing import List, Optional, Dict, Any

from sqlmodel import Session

from app.db.models.entity_relationship import EntityRelationship, RelationshipType
from app.services.repositories.entity_relationship import EntityRelationshipRepository


# Create a singleton instance of the repository
entity_relationship_repository = EntityRelationshipRepository()


async def create_entity_relationship(*, session: Session, relationship_data: Dict[str, Any]) -> EntityRelationship:
    """
    Create a new entity relationship.
    
    Args:
        session: Database session
        relationship_data: Dictionary with relationship data
        
    Returns:
        Created entity relationship
    """
    return await entity_relationship_repository.create(session=session, relationship_data=relationship_data)


async def get_entity_relationship(*, session: Session, relationship_id: uuid.UUID) -> Optional[EntityRelationship]:
    """
    Get an entity relationship by ID.
    
    Args:
        session: Database session
        relationship_id: UUID of the relationship
        
    Returns:
        Entity relationship if found, None otherwise
    """
    return await entity_relationship_repository.get(session=session, relationship_id=relationship_id)


async def get_entity_relationships(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100
) -> List[EntityRelationship]:
    """
    Get a list of entity relationships with pagination.
    
    Args:
        session: Database session
        skip: Number of relationships to skip
        limit: Maximum number of relationships to return
        
    Returns:
        List of entity relationships
    """
    return await entity_relationship_repository.list(session=session, skip=skip, limit=limit)


async def get_relationships_for_entity(
    *,
    session: Session,
    entity_id: uuid.UUID,
    as_source: bool = True,
    as_target: bool = True,
    skip: int = 0,
    limit: int = 100
) -> List[EntityRelationship]:
    """
    Get all relationships for a political entity.
    
    Args:
        session: Database session
        entity_id: UUID of the entity
        as_source: Include relationships where entity is source
        as_target: Include relationships where entity is target
        skip: Number of relationships to skip
        limit: Maximum number of relationships to return
        
    Returns:
        List of entity relationships
    """
    return await entity_relationship_repository.get_relationships_for_entity(
        session=session,
        entity_id=entity_id,
        as_source=as_source,
        as_target=as_target,
        skip=skip,
        limit=limit
    )


async def get_relationships_by_type(
    *,
    session: Session,
    relationship_type: RelationshipType,
    skip: int = 0,
    limit: int = 100
) -> List[EntityRelationship]:
    """
    Get all relationships of a specific type.
    
    Args:
        session: Database session
        relationship_type: Type of relationship
        skip: Number of relationships to skip
        limit: Maximum number of relationships to return
        
    Returns:
        List of entity relationships
    """
    return await entity_relationship_repository.get_entities_with_relationship_type(
        session=session,
        relationship_type=relationship_type,
        skip=skip,
        limit=limit
    )


async def update_relationship_strength(
    *,
    session: Session,
    relationship_id: uuid.UUID,
    strength: float
) -> Optional[EntityRelationship]:
    """
    Update the strength of a relationship.
    
    Args:
        session: Database session
        relationship_id: UUID of the relationship
        strength: New strength value (0.0 to 1.0)
        
    Returns:
        Updated entity relationship if found, None otherwise
    """
    return await entity_relationship_repository.update_relationship_strength(
        session=session,
        relationship_id=relationship_id,
        strength=strength
    )


async def update_entity_relationship(
    *,
    session: Session,
    relationship: EntityRelationship,
    update_data: Dict[str, Any]
) -> EntityRelationship:
    """
    Update an entity relationship.
    
    Args:
        session: Database session
        relationship: Existing entity relationship
        update_data: Dictionary with fields to update
        
    Returns:
        Updated entity relationship
    """
    return await entity_relationship_repository.update(
        session=session,
        relationship=relationship,
        update_data=update_data
    )


async def delete_entity_relationship(*, session: Session, relationship_id: uuid.UUID) -> Optional[EntityRelationship]:
    """
    Delete an entity relationship.
    
    Args:
        session: Database session
        relationship_id: UUID of the relationship
        
    Returns:
        Deleted entity relationship if found, None otherwise
    """
    return await entity_relationship_repository.delete(session=session, relationship_id=relationship_id) 