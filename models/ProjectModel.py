from pymongo.errors import DuplicateKeyError

from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from .enums.DataBaseEnum import DataBaseEnum


class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

        # Always initialize collection
        self.collection = self.db_client[
            DataBaseEnum.COLLECTION_PROJECT_NAME.value
        ]

    @classmethod
    async def create_instance(cls, db_client: object):
        """
        Factory method to create instance
        and initialize indexes.
        """
        instance = cls(db_client)
        await instance.init_collection()
        return instance

    async def init_collection(self):
        """
        Initialize collection indexes.

        MongoDB create_index() is idempotent:
        - Existing index -> ignored
        - Missing index -> created

        This is production-safe because
        new indexes will automatically be
        added on deployment.
        """

        indexes = Project.get_indexes()

        for index in indexes:
            await self.collection.create_index(
                index["key"],
                name=index["name"],
                unique=index.get("unique", False),
            )

    async def create_project(self, project: Project):
        """
        Create a new project.

        Handles race condition where
        multiple requests try to create
        same project_id simultaneously.
        """

        try:
            result = await self.collection.insert_one(
                project.model_dump(
                    by_alias=True,
                    exclude_unset=True
                )
            )

            project.id = result.inserted_id
            return project

        except DuplicateKeyError:
            # Another request already created it
            record = await self.collection.find_one(
                {"project_id": project.project_id}
            )

            return Project(**record)

    async def get_project_or_create_one(
        self,
        project_id: str
    ):
        """
        Get existing project.

        If not exists -> create one.

        Safe for concurrent requests.
        """

        record = await self.collection.find_one(
            {"project_id": project_id}
        )

        # Return existing project
        if record:
            return Project(**record)

        # Create new project
        project = Project(project_id=project_id)

        return await self.create_project(project)

    async def get_all_project(
        self,
        page: int = 1,
        page_size: int = 10
    ):
        """
        Get paginated projects list.
        """

        # Prevent invalid input
        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 10

        total_documents = await self.collection.count_documents({})

        # Calculate total pages
        total_pages = (
            total_documents + page_size - 1
        ) // page_size

        cursor = (
            self.collection.find()
            .skip((page - 1) * page_size)
            .limit(page_size)
        )

        projects = []

        async for document in cursor:
            projects.append(Project(**document))

        return projects, total_pages

