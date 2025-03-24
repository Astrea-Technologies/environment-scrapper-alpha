import uuid
from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from app.db.models.entity_relationship import EntityRelationship, RelationshipType


class EntityRelationshipRepository:
    """
    Repository for EntityRelationship operations.
    
    This repository implements CRUD operations for the EntityRelationship model
    using SQLModel with async/await pattern.
    """
    
    async def create(self, session: Session, *, relationship_data: dict) -> EntityRelationship:
        """
        Create a new entity relationship.
        
        Args:
            session: Database session
            relationship_data: Dictionary with relationship data
            
        Returns:
            Created EntityRelationship instance
        """
        relationship = EntityRelationship(**relationship_data)
        session.add(relationship)
        session.commit()
        session.refresh(relationship)
        return relationship
    
    async def get(self, session: Session, *, relationship_id: uuid.UUID) -> Optional[EntityRelationship]:
        """
        Get an entity relationship by ID.
        
        Args:
            session: Database session
            relationship_id: UUID of the relationship
            
        Returns:
            EntityRelationship if found, None otherwise
        """
        return session.get(EntityRelationship, relationship_id)
    
    async def list(
        self,
        session: Session,
        *,
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
            List of EntityRelationship instances
        """
        statement = select(EntityRelationship).offset(skip).limit(limit)
        return session.exec(statement).all()
    
    async def get_relationships_for_entity(
        self,
        session: Session,
        *,
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
            List of EntityRelationship instances
        """
        if as_source and as_target:
            statement = (
                select(EntityRelationship).where(
                    (EntityRelationship.source_entity_id == entity_id) | 
                    (EntityRelationship.target_entity_id == entity_id)
                ).offset(skip).limit(limit)
            )
        elif as_source:
            statement = (
                select(EntityRelationship)
                .where(EntityRelationship.source_entity_id == entity_id)
                .offset(skip).limit(limit)
            )
        elif as_target:
            statement = (
                select(EntityRelationship)
                .where(EntityRelationship.target_entity_id == entity_id)
                .offset(skip).limit(limit)
            )
        else:
            return []
            
        return session.exec(statement).all()
    
    async def get_entities_with_relationship_type(
        self,
        session: Session,
        *,
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
            List of EntityRelationship instances
        """
        statement = (
            select(EntityRelationship)
            .where(EntityRelationship.relationship_type == relationship_type)
            .offset(skip).limit(limit)
        )
        return session.exec(statement).all()
    
    async def update_relationship_strength(
        self,
        session: Session,
        *,
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
            Updated EntityRelationship if found, None otherwise
        """
        relationship = await self.get(session=session, relationship_id=relationship_id)
        if relationship:
            # Ensure strength is within valid range
            clamped_strength = max(0.0, min(1.0, strength))
            relationship.strength = clamped_strength
            relationship.last_updated = datetime.utcnow()
            
            session.add(relationship)
            session.commit()
            session.refresh(relationship)
        return relationship
    
    async def update(
        self,
        session: Session,
        *,
        relationship: EntityRelationship,
        update_data: dict
    ) -> EntityRelationship:
        """
        Update an entity relationship.
        
        Args:
            session: Database session
            relationship: EntityRelationship instance to update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated EntityRelationship instance
        """
        for key, value in update_data.items():
            setattr(relationship, key, value)
        
        # Always update the last_updated timestamp
        relationship.last_updated = datetime.utcnow()
        
        session.add(relationship)
        session.commit()
        session.refresh(relationship)
        return relationship
    
    async def delete(self, session: Session, *, relationship_id: uuid.UUID) -> Optional[EntityRelationship]:
        """
        Delete an entity relationship.
        
        Args:
            session: Database session
            relationship_id: UUID of the relationship
            
        Returns:
            Deleted EntityRelationship if found, None otherwise
        """
        relationship = await self.get(session=session, relationship_id=relationship_id)
        if relationship:
            session.delete(relationship)
            session.commit()
        return relationship 