"""
Project controller module for managing project-specific directories and paths.
"""

from .BaseController import BaseController
import os


class ProjectController(BaseController):
    """
    Controller for handling project-level filesystem operations.
    """

    def __init__(self):
        """
        Initializes the project controller.
        """
        super().__init__()

    def get_project_path(self, project_id: str) -> str:
        """
        Retrieves the absolute path to a project's data directory, creating it if necessary.
        
        Args:
            project_id (str): The unique identifier of the project.
            
        Returns:
            str: The absolute path to the project directory.
        """
        project_dir = os.path.join(self.files_dir, str(project_id))

        if not os.path.exists(project_dir):
            os.makedirs(project_dir, exist_ok=True)

        return project_dir

