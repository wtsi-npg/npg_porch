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

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager, joinedload
from typing import Optional, List

from npg.porchdb.models import Pipeline as DbPipeline, Task as DbTask, Event, Base
from npg.porch.models import Task, Pipeline


class AsyncDbAccessor:
    '''
    A data access class for routine sqlalchemy operations

    Instantiate with a sqlalchemy AsyncSession
    '''

    def __init__(self, session):
        self.session = session

    async def get_pipeline(self, name: str) -> Pipeline:

        pipeline = await self._get_pipeline_db_object(name)
        return pipeline.convert_to_model()

    async def _get_pipeline_db_object(self, name: str):

        pipeline_result = await self.session.execute(
            select(DbPipeline)
            .filter_by(name=name)
        )
        return pipeline_result.one() # errors if no rows

    async def get_all_pipelines(self, uri: Optional[str]=None) -> List[Pipeline]:

        pipelines = []
        if uri:
            pipelines = await self.session.execute(
                select(DbPipeline)
                .filter_by(repository_uri=uri)
            )
        else:
            pipelines = await self.session.execute(
                select(DbPipeline)
            )

        return [pipe.convert_to_model() for pipe in pipelines.scalars().all()]


    async def create_pipeline(self, pipeline) -> Pipeline:
        session = self.session

        pipe = DbPipeline(
            name=pipeline.name,
            version=pipeline.version,
            repository_uri=pipeline.uri
        )

        session.add(pipe)
        await session.commit()
        return pipe.convert_to_model()


    async def create_task(self, token_id: int, task: Task) -> Task:

        session = self.session
        db_pipeline = self._get_pipeline_db_object(task.pipeline.name)
        # Check they exist and so on
        task.status = 'PENDING'

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

        potential_tasks = await session.execute(
            select(DbTask)
            .join(DbTask.pipeline)
            .where(DbPipeline.name == pipeline.name)
            .where(DbTask.state == 'PENDING')
            .order_by(DbTask.created)
            .options(contains_eager(DbTask.pipeline))
            .with_for_update()
            .limit(claim_limit)
            .execution_options(populate_existing=True)
        )

        claimed_tasks = potential_tasks.scalars().all()
        try:
            for task in claimed_tasks:
                task.state = 'CLAIMED'
                event = Event(
                        change='Task claimed', token_id=token_id, task=task)
                session.add(event)
            await session.commit()
        except IntegrityError as e:
            print(e)
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
        db_pipe = await self._get_pipeline_db_object(task.pipeline.name)
        task_result = await self.session.execute(
            select(DbTask)
            .filter(pipeline=db_pipe)
            .filter(job_descriptor=task.generate_task_id())
        )
        og_task = task_result.one() # raises exception if no rows
        # Check that the updated state is a valid change
        comparable_task = og_task.convert_to_model()
        if (comparable_task.task_input_id != task.task_input_id):
            raise Exception(
                    'Cannot change task definition. Submit a new task instead')
        new_status = task.status
        # Might be the same as the old one, but save and log nevertheless
        # in case we have some heart beat status in future.
        og_task.state(new_status)
        event = Event(change=f'Task changed, new status {new_status}',
                             token_id=token_id, task=task)
        session.add(event)
        await session.commit()

        return og_task.convert_to_model()

    async def get_tasks(self) -> List[Task]:
        '''
        Gets all the tasks. Going to be problematic without filtering
        '''
        task_result = await self.session.execute(
            select(DbTask)
            .options(joinedload(DbTask.pipeline))
        )
        tasks = task_result.scalars().all()
        return [t.convert_to_model() for t in tasks]

    @staticmethod
    def convert_task_to_db(task: Task, pipeline: DbPipeline) -> DbTask:
        return DbTask(
            pipeline=pipeline,
            job_descriptor=task.generate_task_id(),
            definition=task.task_input,
            state=task.status
        )
