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

import os
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager, sessionmaker, joinedload
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from typing import Optional, Dict, List

from npg.porchdb.models import Pipeline as DbPipeline, Task as DbTask, Event, Base
from npg.porch.models import Task, Pipeline

config = {
    'DB_URL': os.environ.get('DB_URL'),
    'DB_SCHEMA': os.environ.get('DB_SCHEMA') if os.environ.get('DB_SCHEMA') else 'npg_porch'
}

engine = create_async_engine(
    config['DB_URL'], future=True
)
Base.metadata.schema = config['DB_SCHEMA']
session_factory = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_DbAccessor():
    'Provides a hook for fastapi to Depend on a DB session in each route'
    async with session_factory() as session:
        async with session.begin():
            yield AsyncDbAccessor(session)


class AsyncDbAccessor:
    '''
    A data access class for routine sqlalchemy operations

    Instantiate with a sqlalchemy AsyncSession
    '''

    def __init__(self, session):
        self.session = session

    async def get_pipeline(self, pipeline: Pipeline):
        if pipeline.name:

            pipeline_result = await self.session.execute(
                select(DbPipeline)
                .filter_by(name=pipeline.name)
            )
        else:
            pipeline_result = await self.session.execute(
                select(DbPipeline)
                .filter(repository_uri=pipeline.uri)
            )
        return pipeline_result.scalar_one().convert_to_model()

    async def get_all_pipelines(self, name: Optional[str]=None) -> List[Pipeline]:
        pipelines = []
        if name:
            pipelines = await self.session.execute(
                select(DbPipeline)
                .filter_by(name=name)
            )
        else:
            pipelines = await self.session.execute(
                select(DbPipeline)
            )

        return [pipe.convert_to_model() for pipe in pipelines.scalars().all()]

    async def get_pipeline_tasks(self, state: str) -> List[Task]:
        if (state):
            tasks = await self.session.execute(
                select(DbTask)
                .filter(state=state)
            )
        else:
            tasks = await self.session.execute(
                select(DbTask)
            )

        return [t.convert_to_model() for t in tasks.scalars().all()]

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
        pipeline_result = await session.execute(
            select(DbPipeline)
            .filter_by(repository_uri=task.pipeline.uri)
        )
        db_pipeline = pipeline_result.scalar_one()
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
            .where(DbPipeline.repository_uri == pipeline.uri)
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
        Other fields cannot be changed
        '''

        session = self.session
        # Get the matching task from the DB
        pipeline_result = await self.get_pipeline(task.pipeline)
        db_pipe = pipeline_result.scalar_one()
        task_result = await self.session.execute(
            select(DbTask)
            .filter(pipeline=db_pipe)
            .filter(job_descriptor=task.generate_task_id())
        )
        og_task = task_result.scalar_one()
        # Check that the updated state is a valid change
        if (og_task):
            # TODO - any rollback?
            comparable_task = og_task.convert_to_model()
            if (comparable_task.task_input_id != task.task_input_id):
                raise Exception('Cannot change task definition. Submit a new task instead')
            new_status = task.status
            # Might be the same as the old one, but save and log nevertheless
            # in case we have some heart beat status in future.
            og_task.state(new_status)
            session.add(og_task)
            event = Event(
                    change=f'Task changed, new status {new_status}',
                           token_id=token_id, task=task)
            session.add(event)
            await session.commit()
        else:
            raise Exception('Could not find task to update it')

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
