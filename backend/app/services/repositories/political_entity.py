import uuid
from typing import List, Optional, Type

from sqlmodel import Session, select, SQLModel

from app.db.models.political_entity import PoliticalEntity, EntityType


class PoliticalEntityRepository:
    """
    Repository for PoliticalEntity operations.
    
    This repository implements CRUD operations for the PoliticalEntity model
    using SQLModel with async/await pattern.
    """
    
    async def create(self, session: Session, *, entity_data: dict) -> PoliticalEntity:
        """
        Create a new political entity.
        
        Args:
            session: Database session
            entity_data: Dictionary with entity data
            
        Returns:
            Created PoliticalEntity instance
        """
        entity = PoliticalEntity(**entity_data)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity
    
    async def get(self, session: Session, *, entity_id: uuid.UUID) -> Optional[PoliticalEntity]:
        """
        Get a political entity by ID.
        
        Args:
            session: Database session
            entity_id: UUID of the entity
            
        Returns:
            PoliticalEntity if found, None otherwise
        """
        return session.get(PoliticalEntity, entity_id)
    
    async def get_by_name(self, session: Session, *, name: str) -> Optional[PoliticalEntity]:
        """
        Get a political entity by name.
        
        Args:
            session: Database session
            name: Name of the entity
            
        Returns:
            PoliticalEntity if found, None otherwise
        """
        statement = select(PoliticalEntity).where(PoliticalEntity.name == name)
        return session.exec(statement).first()
    
    async def list(
        self,
        session: Session,
        *,
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
            List of PoliticalEntity instances
        """
        statement = select(PoliticalEntity).offset(skip).limit(limit)
        return session.exec(statement).all()
    
    async def filter_by_entity_type(
        self,
        session: Session,
        *,
        entity_type: EntityType,
        skip: int = 0,
        limit: int = 100
    ) -> List[PoliticalEntity]:
        """
        Filter political entities by entity type.
        
        Args:
            session: Database session
            entity_type: Type of the entity
            skip: Number of entities to skip
            limit: Maximum number of entities to return
            
        Returns:
            List of PoliticalEntity instances
        """
        statement = (
            select(PoliticalEntity)
            .where(PoliticalEntity.entity_type == entity_type)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    async def update(
        self,
        session: Session,
        *,
        entity: PoliticalEntity,
        update_data: dict
    ) -> PoliticalEntity:
        """
        Update a political entity.
        
        Args:
            session: Database session
            entity: PoliticalEntity instance to update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated PoliticalEntity instance
        """
        for key, value in update_data.items():
            setattr(entity, key, value)
        
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity
    
    async def delete(self, session: Session, *, entity_id: uuid.UUID) -> Optional[PoliticalEntity]:
        """
        Delete a political entity.
        
        Args:
            session: Database session
            entity_id: UUID of the entity
            
        Returns:
            Deleted PoliticalEntity if found, None otherwise
        """
        entity = await self.get(session=session, entity_id=entity_id)
        if entity:
            session.delete(entity)
            session.commit()
        return entity 