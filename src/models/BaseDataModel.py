"""
Base data model module providing shared functionality for all database models.
"""

from helpers.config import get_settings, Settings


class BaseDataModel:
    """
    Base class for data models, providing access to database clients and application settings.
    """

    def __init__(self, db_client: object):
        """
        Initializes the base data model.

        Args:
            db_client (object): The database client/session maker.
        """
        self.db_client = db_client
        self.app_settings = get_settings()

    async def init(self):
        """
        Optional async initialization hook for subclasses.
        Called by create_instance() after construction.
        """
        pass
