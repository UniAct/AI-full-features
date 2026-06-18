"""
Project model module for managing project records in the database.
"""

from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Tuple, Optional


class ProjectModel(BaseDataModel):
    """
    Model for performing database operations on Project records.
    """

    def __init__(self, db_client: object):
        """
        Initializes the project model with a database client.
        """
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: object) -> "ProjectModel":
        """
        Factory method to create a new instance of ProjectModel.
        """
        return cls(db_client)

    async def create_project(self, project: Project) -> Project:
        """
        Creates a new project record in the database.
        
        Args:
            project (Project): The project object to persist.
            
        Returns:
            Project: The persisted project object.
        """
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)
        
        return project

    async def get_project_or_create_one(self, project_id: str) -> Project:
        """
        Retrieves an existing project by ID or creates a new one if it doesn't exist.
        """
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                
                if project is None:
                    project_rec = Project(project_id=project_id)
                    project = await self.create_project(project=project_rec)
                
                return project

    async def get_all_projects(self, page: int = 1, page_size: int = 10) -> Tuple[List[Project], int]:
        """
        Retrieves a paginated list of all projects and the total number of pages.
        
        Args:
            page (int): The page number to retrieve.
            page_size (int): Number of projects per page.
            
        Returns:
            Tuple[List[Project], int]: A list of projects and the total page count.
        """
        async with self.db_client() as session:
            async with session.begin():
                # Count total projects
                count_query = select(func.count(Project.project_id))
                total_documents_result = await session.execute(count_query)
                total_documents = total_documents_result.scalar_one()

                # Calculate total pages
                total_pages = (total_documents + page_size - 1) // page_size

                # Retrieve paginated projects
                query = (
                    select(Project)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
                result = await session.execute(query)
                projects = result.scalars().all()

                return projects, total_pages

