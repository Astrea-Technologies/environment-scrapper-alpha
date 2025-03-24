import uuid
from typing import List, Optional, Dict, Any

from sqlmodel import Session

from app.db.models.social_media_account import SocialMediaAccount, Platform
from app.services.repositories.social_media_account import SocialMediaAccountRepository


# Create a singleton instance of the repository
social_media_account_repository = SocialMediaAccountRepository()


async def create_social_media_account(*, session: Session, account_data: Dict[str, Any]) -> SocialMediaAccount:
    """
    Create a new social media account.
    
    Args:
        session: Database session
        account_data: Dictionary with account data
        
    Returns:
        Created social media account
    """
    return await social_media_account_repository.create(session=session, account_data=account_data)


async def get_social_media_account(*, session: Session, account_id: uuid.UUID) -> Optional[SocialMediaAccount]:
    """
    Get a social media account by ID.
    
    Args:
        session: Database session
        account_id: UUID of the account
        
    Returns:
        Social media account if found, None otherwise
    """
    return await social_media_account_repository.get(session=session, account_id=account_id)


async def get_social_media_account_by_platform_and_handle(
    *,
    session: Session,
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
        Social media account if found, None otherwise
    """
    return await social_media_account_repository.get_by_platform_and_handle(
        session=session,
        platform=platform,
        handle=handle
    )


async def get_social_media_accounts(
    *,
    session: Session,
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
        List of social media accounts
    """
    return await social_media_account_repository.list(session=session, skip=skip, limit=limit)


async def get_social_media_accounts_by_platform(
    *,
    session: Session,
    platform: Platform,
    skip: int = 0,
    limit: int = 100
) -> List[SocialMediaAccount]:
    """
    Get a list of social media accounts filtered by platform.
    
    Args:
        session: Database session
        platform: Social media platform
        skip: Number of accounts to skip
        limit: Maximum number of accounts to return
        
    Returns:
        List of social media accounts
    """
    return await social_media_account_repository.filter_by_platform(
        session=session,
        platform=platform,
        skip=skip,
        limit=limit
    )


async def get_social_media_accounts_for_entity(
    *,
    session: Session,
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
        List of social media accounts
    """
    return await social_media_account_repository.get_accounts_for_entity(
        session=session,
        entity_id=entity_id,
        skip=skip,
        limit=limit
    )


async def update_social_media_account(
    *,
    session: Session,
    account: SocialMediaAccount,
    update_data: Dict[str, Any]
) -> SocialMediaAccount:
    """
    Update a social media account.
    
    Args:
        session: Database session
        account: Existing social media account
        update_data: Dictionary with fields to update
        
    Returns:
        Updated social media account
    """
    return await social_media_account_repository.update(
        session=session,
        account=account,
        update_data=update_data
    )


async def delete_social_media_account(*, session: Session, account_id: uuid.UUID) -> Optional[SocialMediaAccount]:
    """
    Delete a social media account.
    
    Args:
        session: Database session
        account_id: UUID of the account
        
    Returns:
        Deleted social media account if found, None otherwise
    """
    return await social_media_account_repository.delete(session=session, account_id=account_id) 