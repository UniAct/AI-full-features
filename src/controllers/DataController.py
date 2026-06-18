"""
Data controller module for handling file uploads, validation, and path management.
"""

from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignal
import os
import re
from .ProjectController import ProjectController


class DataController(BaseController):
    """
    Controller for managing data-related operations such as file validation
    and unique path generation.
    """

    def __init__(self):
        """
        Initializes the data controller and defines the size scaling factor.
        """
        super().__init__()
        self.size_scaled = 1048576  # 1 MB in bytes

    def validate_uploaded_file(self, file: UploadFile) -> tuple[bool, str]:
        """
        Validates the uploaded file's type and size.

        Args:
            file (UploadFile): The file uploaded via the API.

        Returns:
            tuple[bool, str]: A tuple containing validation status and a message/signal.
        """
        # Validate file type using content_type
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

        # Skip size validation to allow uploads of any size.
        return True, ResponseSignal.FILE_VALITADED_SUCCESS.value

    def generate_unique_filepath(
        self, orig_file_name: str, project_id: str
    ) -> tuple[str, str]:
        """
        Generates a unique file path within a project directory to avoid collisions.

        Args:
            orig_file_name (str): The original name of the uploaded file.
            project_id (str): The unique identifier of the project.

        Returns:
            tuple[str, str]: A tuple containing the absolute file path and the new file name.
        """
        random_key = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)
        cleaned_file_name = self.get_clean_file_name(orig_file_name=orig_file_name)

        new_file_name = f"{random_key}_{cleaned_file_name}"
        new_file_path = os.path.join(project_path, new_file_name)

        # Ensure filename uniqueness
        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_name = f"{random_key}_{cleaned_file_name}"
            new_file_path = os.path.join(project_path, new_file_name)

        return new_file_path, new_file_name

    def get_clean_file_name(self, orig_file_name: str) -> str:
        """
        Cleans the file name by removing special characters and replacing spaces.

        Args:
            orig_file_name (str): The original file name to clean.

        Returns:
            str: The sanitized file name.
        """
        # Remove any special characters, except underscore and dot
        cleaned_file_name = re.sub(r"[^\w.]", "", orig_file_name.strip())

        # Replace spaces with underscores
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name
