"""
Base controller module providing shared functionality for all controllers.
"""

from helpers.config import get_settings, Settings
import os
import random
import string


class BaseController:
    """
    Base controller class that initializes shared settings and directory paths.
    """

    def __init__(self):
        """
        Initializes the base controller with application settings and common directories.
        """
        self.app_settings = get_settings()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.files_dir = os.path.normpath(os.path.join(self.base_dir, "../assets/files"))
        self.database_dir = os.path.normpath(os.path.join(self.base_dir, "assets/database"))

    def generate_random_string(self, length: int = 12) -> str:
        """
        Generates a random string of lowercase letters and digits.
        
        Args:
            length (int): The length of the string to generate. Defaults to 12.
            
        Returns:
            str: The generated random string.
        """
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def get_database_path(self, db_name: str) -> str:
        """
        Retrieves the path for a specific database, creating it if it doesn't exist.
        
        Args:
            db_name (str): The name of the database.
            
        Returns:
            str: The absolute path to the database directory.
        """
        database_path = os.path.join(self.database_dir, db_name)

        if not os.path.exists(database_path):
            os.makedirs(database_path, exist_ok=True)

        return database_path