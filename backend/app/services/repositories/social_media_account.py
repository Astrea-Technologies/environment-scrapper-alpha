import uuid
from typing import List, Optional

from sqlmodel import Session, select

from app.db.models.social_media_account import SocialMediaAccount, Platform


class SocialMediaAccountRepository:
    """
    Repository for SocialMediaAccount operations.
    
    This repository implements CRUD operations for the SocialMediaAccount model
    using SQLModel with async/await pattern.
    """
    
    async def create(self, session: Session, *, account_data: dict) -> SocialMediaAccount:
        """
        Create a new social media account.
        
        Args:
            session: Database session
            account_data: Dictionary with account data
            
        Returns:
            Created SocialMediaAccount instance
        """
        account = SocialMediaAccount(**account_data)
        session.add(account)
        session.commit()
        session.refresh(account)
        return account
    
    async def get(self, session: Session, *, account_id: uuid.UUID) -> Optional[SocialMediaAccount]:
        """
        Get a social media account by ID.
        
        Args:
            session: Database session
            account_id: UUID of the account
            
        Returns:
            SocialMediaAccount if found, None otherwise
        """
        return session.get(SocialMediaAccount, account_id)
    
    async def get_by_platform_and_handle(
        self,
        session: Session,
        *,
        platform: Platform,
        handle: str
    ) -> Optional[SocialMediaAccount]:
        """
        Get a social media account by platform and handle.
        
        Args:
            session: Database session
            platform: Social media platform
            handle: User handle on the platform
            
        Returns:
            SocialMediaAccount if found, None otherwise
        """
        statement = select(SocialMediaAccount).where(
            SocialMediaAccount.platform == platform,
            SocialMediaAccount.handle == handle
        )
        return session.exec(statement).first()
    
    async def list(
        self,
        session: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[SocialMediaAccount]:
        """
        Get a list of social media accounts with pagination.
        
        Args:
            session: Database session
            skip: Number of accounts to skip
            limit: Maximum number of accounts to return
            
        Returns:
            List of SocialMediaAccount instances
        """
        statement = select(SocialMediaAccount).offset(skip).limit(limit)
        return session.exec(statement).all()
    
    async def filter_by_platform(
        self,
        session: Session,
        *,
        platform: Platform,
        skip: int = 0,
        limit: int = 100
    ) -> List[SocialMediaAccount]:
        """
        Filter social media accounts by platform.
        
        Args:
            session: Database session
            platform: Social media platform
            skip: Number of accounts to skip
            limit: Maximum number of accounts to return
            
        Returns:
            List of SocialMediaAccount instances
        """
        statement = (
            select(SocialMediaAccount)
            .where(SocialMediaAccount.platform == platform)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    async def get_accounts_for_entity(
        self,
        session: Session,
        *,
        entity_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[SocialMediaAccount]:
        """
        Get all social media accounts for a political entity.
        
        Args:
            session: Database session
            entity_id: UUID of the political entity
            skip: Number of accounts to skip
            limit: Maximum number of accounts to return
            
        Returns:
            List of SocialMediaAccount instances
        """
        statement = (
            select(SocialMediaAccount)
            .where(SocialMediaAccount.political_entity_id == entity_id)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    async def update(
        self,
        session: Session,
        *,
        account: SocialMediaAccount,
        update_data: dict
    ) -> SocialMediaAccount:
        """
        Update a social media account.
        
        Args:
            session: Database session
            account: SocialMediaAccount instance to update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated SocialMediaAccount instance
        """
        for key, value in update_data.items():
            setattr(account, key, value)
        
        session.add(account)
        session.commit()
        session.refresh(account)
        return account
    
    async def delete(self, session: Session, *, account_id: uuid.UUID) -> Optional[SocialMediaAccount]:
        """
        Delete a social media account.
        
        Args:
            session: Database session
            account_id: UUID of the account
            
        Returns:
            Deleted SocialMediaAccount if found, None otherwise
        """
        account = await self.get(session=session, account_id=account_id)
        if account:
            session.delete(account)
            session.commit()
        return account 