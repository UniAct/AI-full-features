"""
Asset model module for managing project assets in the database.
"""

from .BaseDataModel import BaseDataModel
from .db_schemes import Asset
from sqlalchemy.future import select
from typing import List, Optional


class AssetModel(BaseDataModel):
    """
    Model for performing database operations on Asset records.
    """

    def __init__(self, db_client: object):
        """
        Initializes the asset model with a database client.
        """
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: object) -> "AssetModel":
        """
        Factory method to create a new instance of AssetModel.
        """
        return cls(db_client)

    async def create_asset(self, asset: Asset) -> Asset:
        """
        Creates a new asset record in the database.
        
        Args:
            asset (Asset): The asset object to persist.
            
        Returns:
            Asset: The persisted asset object with updated ID.
        """
        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()
            await session.refresh(asset)
        return asset

    async def get_all_project_assets(self, asset_project_id: str, asset_type: str) -> List[Asset]:
        """
        Retrieves all assets for a specific project and type.
        """
        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_type == asset_type
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records

    async def get_asset_record(self, asset_project_id: str, asset_name: str) -> Optional[Asset]:
        """
        Retrieves a single asset record by project ID and name.
        """
        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
        return record

