# Copyright (C) 2021, 2022, 2024 Genome Research Ltd.
#
# Author: Kieron Taylor kt19@sanger.ac.uk
# Author: Marina Gourtovaia mg8@sanger.ac.uk
#
# This file is part of npg_porch
#
# npg_porch is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.orm.exc import NoResultFound

from npg_porch.db.models import Event
from npg_porch.db.models import Pipeline as DbPipeline
from npg_porch.db.models import Task as DbTask, TaskExpanded as DbTaskExp
from npg_porch.db.models import Token as DbToken
from npg_porch.models import Pipeline, Task, TaskStateEnum
from npg_porch.models.token import Token


class AsyncDbAccessor:
    """
    A data access class for routine sqlalchemy operations

    Instantiate with a sqlalchemy AsyncSession
    """

    def __init__(self, session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    async def get_pipeline_by_name(self, name: str) -> Pipeline:
        pipeline = await self._get_pipeline_db_object(name)
        return pipeline.convert_to_model()

    async def _get_pipeline_db_object(self, name: str) -> Pipeline:
        pipeline_result = await self.session.execute(
            select(DbPipeline).filter_by(name=name)
        )
        return pipeline_result.scalar_one()  # errors if no rows

    async def _get_pipeline_db_objects(
        self,
        name: str | None = None,
        version: str | None = None,
        uri: str | None = None,
    ) -> list[Pipeline]:
        query = select(DbPipeline)
        if name:
            query = query.filter_by(name=name)
        if version:
            query = query.filter_by(version=version)
        if uri:
            query = query.filter_by(repository_uri=uri)

        pipeline_result = await self.session.execute(query)
        return pipeline_result.scalars().all()

    async def get_all_pipelines(
        self, uri: str | None = None, version: str | None = None
    ) -> list[Pipeline]:
        pipelines = await self._get_pipeline_db_objects(uri=uri, version=version)
        return [pipe.convert_to_model() for pipe in pipelines]

    async def create_pipeline(self, pipeline: Pipeline) -> Pipeline:
        session = self.session
        assert isinstance(pipeline, Pipeline)

        pipe = DbPipeline(
            name=pipeline.name, version=pipeline.version, repository_uri=pipeline.uri
        )

        session.add(pipe)
        await session.commit()
        return pipe.convert_to_model()

    async def create_pipeline_token(self, name: str, desc: str) -> Token:
        session = self.session
        db_pipeline = await self._get_pipeline_db_object(name)

        db_token = DbToken(pipeline=db_pipeline, description=desc)
        session.add(db_token)
        await session.commit()

        return Token(name=db_pipeline.name, token=db_token.token, description=desc)

    async def create_task(self, token_id: int, task: Task) -> tuple[Task, bool]:
        """Given a task definition creates a task.

        If the task does not exist, a tuple consisting of Task object for a
        newly created database record and a boolean True object is returned.

        If the task already exists, a tuple consisting of Task object for an
        existing database record and a boolean True object is returned.
        """
        self.logger.debug("CREATE TASK: " + str(task))
        session = self.session
        db_pipeline = await self._get_pipeline_db_object(task.pipeline.name)

        task.status = TaskStateEnum.PENDING
        t = self.convert_task_to_db(task, db_pipeline)
        created = True
        try:
            nested = await session.begin_nested()
            session.add(t)
            event = Event(task=t, token_id=token_id, change="Created")
            t.events.append(event)
            await session.commit()
        except IntegrityError:
            await nested.rollback()
            # Task already exists, query the database to get the up-to-date
            # representation of the task.
            t = await self.get_db_task(
                pipeline_name=task.pipeline.name, job_descriptor=t.job_descriptor
            )
            created = False

        return (t.convert_to_model(), created)

    async def claim_tasks(
        self, token_id: int, pipeline: Pipeline, claim_limit: int | None = 1
    ) -> list[Task]:
        session = self.session

        try:
            pipeline_result = await session.execute(
                select(DbPipeline).filter_by(name=pipeline.name)
            )
            pipeline = pipeline_result.scalar_one()
        except NoResultFound:
            raise NoResultFound("Pipeline not found")

        potential_tasks = await session.execute(
            select(DbTask)
            .join(DbTask.pipeline)
            .where(DbPipeline.name == pipeline.name)
            .where(DbTask.state == TaskStateEnum.PENDING)
            .order_by(DbTask.created)
            .options(contains_eager(DbTask.pipeline))
            .with_for_update()
            .limit(claim_limit)
            .execution_options(populate_existing=True)
        )

        claimed_tasks = potential_tasks.scalars().all()
        try:
            for task in claimed_tasks:
                task.state = TaskStateEnum.CLAIMED
                event = Event(change="Task claimed", token_id=token_id, task=task)
                session.add(event)
            await session.commit()
        except IntegrityError as e:
            self.logger.info(e)
            await session.rollback()
            return []

        work = []
        for task in claimed_tasks:
            work.append(task.convert_to_model())
        return work

    async def update_task(self, token_id: int, task: Task) -> Task:
        """
        Allows the modification of state of a task.
        Other fields cannot be changed.
        """
        session = self.session
        # Get the matching task from the DB
        try:
            db_pipe = await self._get_pipeline_db_object(task.pipeline.name)
        except NoResultFound:
            raise NoResultFound("Pipeline not found")

        try:
            task_result = await session.execute(
                select(DbTask)
                .filter_by(pipeline=db_pipe)
                .filter_by(job_descriptor=task.generate_task_id())
            )
            og_task = task_result.scalar_one()  # Doesn't raise exception if no rows?!
        except NoResultFound:
            raise NoResultFound("Task to be modified could not be found")

        new_status = task.status
        # Might be the same as the old one, but save and log nevertheless
        # in case we have some heart beat status in future.
        og_task.state = new_status
        event = Event(
            change=f"Task changed, new status {new_status}",
            token_id=token_id,
            task=og_task,
        )
        session.add(event)
        await session.commit()

        return og_task.convert_to_model()

    async def get_tasks(
        self, pipeline_name: str | None = None, task_status: TaskStateEnum | None = None
    ) -> list[Task]:
        """
        Gets all the tasks.

        Can filter tasks by pipeline name and task status in order to be more useful.
        """
        query = (
            select(DbTask).join(DbTask.pipeline).options(joinedload(DbTask.pipeline))
        )

        if pipeline_name:
            query = query.where(DbPipeline.name == pipeline_name)

        if task_status:
            query = query.filter(DbTask.state == task_status)

        task_result = await self.session.execute(query)
        tasks = task_result.scalars().all()
        return [t.convert_to_model() for t in tasks]

    async def get_ordered_tasks(self, limit: int = 100):
        query = (
            select(DbTaskExp)
            .join(DbTaskExp.pipeline)
            .options(joinedload(DbTaskExp.pipeline))
            .order_by(DbTaskExp.created.desc())
            .limit(limit)
        )

        task_result = await self.session.execute(query)
        tasks = task_result.scalars().all()
        return [t.convert_to_model() for t in tasks]

    async def get_db_task(
        self,
        pipeline_name: str,
        job_descriptor: str,
    ) -> DbTask:
        """Get the task."""
        query = (
            select(DbTask)
            .join(DbTask.pipeline)
            .options(joinedload(DbTask.pipeline))
            .where(DbPipeline.name == pipeline_name)
            .where(DbTask.job_descriptor == job_descriptor)
        )
        task_result = await self.session.execute(query)

        return task_result.scalars().one()

    @staticmethod
    def convert_task_to_db(task: Task, pipeline: DbPipeline) -> DbTask:
        assert task.status in TaskStateEnum

        return DbTask(
            pipeline=pipeline,
            job_descriptor=task.generate_task_id(),
            definition=task.task_input,
            state=task.status,
        )

    async def get_events_for_task(self, task: Task) -> list[Event]:
        events = await self.session.execute(
            select(Event)
            .join(Event.task)
            .where(DbTask.job_descriptor == task.task_input_id)
        )
        return events.scalars().all()
