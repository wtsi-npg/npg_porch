# Copyright (C) 2021, 2022 Genome Research Ltd.
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
from typing import Optional, List

from npg.porchdb.models import Pipeline as DbPipeline, Task as DbTask, Event
from npg.porch.models import Task, Pipeline, TaskStateEnum


class AsyncDbAccessor:
    '''
    A data access class for routine sqlalchemy operations

    Instantiate with a sqlalchemy AsyncSession
    '''

    def __init__(self, session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    async def get_pipeline_by_name(self, name: str) -> Pipeline:

        pipeline = await self._get_pipeline_db_object(name)
        return pipeline.convert_to_model()

    async def _get_pipeline_db_object(self, name: str) -> Pipeline:

        pipeline_result = await self.session.execute(
            select(DbPipeline)
            .filter_by(name=name)
        )
        return pipeline_result.scalar_one() # errors if no rows

    async def _get_pipeline_db_objects(
        self,
        name: Optional[str] = None,
        version: Optional[str] = None,
        uri: Optional[str] = None
    ) -> List[Pipeline]:
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
        self,
        uri: Optional[str] = None,
        version: Optional[str] = None
    ) -> List[Pipeline]:
        pipelines = []
        pipelines = await self._get_pipeline_db_objects(uri=uri, version=version)
        return [pipe.convert_to_model() for pipe in pipelines]

    async def create_pipeline(self, pipeline: Pipeline) -> Pipeline:
        session = self.session
        assert isinstance(pipeline, Pipeline)

        pipe = DbPipeline(
            name=pipeline.name,
            version=pipeline.version,
            repository_uri=pipeline.uri
        )

        session.add(pipe)
        await session.commit()
        return pipe.convert_to_model()

    async def create_task(self, token_id: int, task: Task) -> Task:
        self.logger.debug('CREATE TASK: ' + str(task))
        session = self.session
        db_pipeline = await self._get_pipeline_db_object(
            task.pipeline.name
        )
        # Check they exist and so on
        task.status = TaskStateEnum.PENDING

        t = self.convert_task_to_db(task, db_pipeline)
        session.add(t)

        event = Event(
            task=t,
            token_id = token_id,
            change='Created'
        )
        t.events.append(event)

        await session.commit()
        # Error handling to follow
        return t.convert_to_model()

    async def claim_tasks(
        self, token_id: int, pipeline: Pipeline, claim_limit: Optional[int] = 1
    ) -> List[Task]:
        session = self.session

        try:
            pipeline_result = await session.execute(
                select(DbPipeline)
                .filter_by(name=pipeline.name)
            )
            pipeline = pipeline_result.scalar_one()
        except NoResultFound:
            raise NoResultFound('Pipeline not found')

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
                event = Event(
                    change='Task claimed', token_id=token_id, task=task
                )
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
        '''
        Allows the modification of state of a task.
        Other fields cannot be changed.
        '''
        session = self.session
        # Get the matching task from the DB
        try:
            db_pipe = await self._get_pipeline_db_object(task.pipeline.name)
        except NoResultFound:
            raise NoResultFound('Pipeline not found')

        try:
            task_result = await session.execute(
                select(DbTask)
                .filter_by(pipeline=db_pipe)
                .filter_by(job_descriptor=task.generate_task_id())
            )
            og_task = task_result.scalar_one() # Doesn't raise exception if no rows?!
        except NoResultFound:
            raise NoResultFound('Task to be modified could not be found')

        new_status = task.status
        # Might be the same as the old one, but save and log nevertheless
        # in case we have some heart beat status in future.
        og_task.state = new_status
        event = Event(change=f'Task changed, new status {new_status}',
                             token_id=token_id, task=og_task)
        session.add(event)
        await session.commit()

        return og_task.convert_to_model()

    async def get_tasks(
        self,
        pipeline_name: Optional[str] = None,
        task_status: Optional[TaskStateEnum] = None
    ) -> List[Task]:
        '''
        Gets all the tasks.

        Can filter tasks by pipeline name and task status in order to be more useful.
        '''
        query = select(DbTask)\
            .join(DbTask.pipeline)\
            .options(joinedload(DbTask.pipeline))

        if pipeline_name:
            query = query.where(DbPipeline.name == pipeline_name)

        if task_status:
            query = query.filter(DbTask.state == task_status)

        task_result = await self.session.execute(query)
        tasks = task_result.scalars().all()
        return [t.convert_to_model() for t in tasks]

    @staticmethod
    def convert_task_to_db(task: Task, pipeline: DbPipeline) -> DbTask:
        assert task.status in TaskStateEnum

        return DbTask(
            pipeline=pipeline,
            job_descriptor=task.generate_task_id(),
            definition=task.task_input,
            state=task.status
        )

    async def get_events_for_task(self, task: Task) -> List[Event]:
        events = await self.session.execute(
            select(Event)
            .join(Event.task)
            .where(DbTask.job_descriptor == task.task_input_id)
        )
        return events.scalars().all()
