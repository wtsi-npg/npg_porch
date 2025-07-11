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
from datetime import datetime, timedelta
from importlib import metadata

from fastapi import FastAPI, Request, Depends
from fastapi.responses import (
    Response,
    HTMLResponse,
    RedirectResponse,
)
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, PackageLoader

from npg_porch.db.connection import get_DbAccessor
from npg_porch.endpoints import pipelines, tasks, ui
from npg_porch.models import TaskStateEnum

# https://fastapi.tiangolo.com/tutorial/bigger-applications/
# https://fastapi.tiangolo.com/tutorial/metadata

DAY_ONE = datetime(1, 1, 1)
RECENT = datetime.now() - timedelta(days=14)

tags_metadata = [
    {
        "name": "pipelines",
        "description": "Manage pipelines.",
    },
    {
        "name": "ui",
        "description": "Fetching and display of tasks for the UI.",
    },
    {
        "name": "about",
        "description": "Links to pipeline listings and documentation.",
    },
]

app = FastAPI(
    title="Pipeline Orchestration (POrch)",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=tags_metadata,
)
app.include_router(pipelines.router)
app.include_router(tasks.router)
app.include_router(ui.router)

env = Environment(loader=PackageLoader("npg_porch", "templates"))
templates = Jinja2Templates(env=env)

version = metadata.version("npg_porch")


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["ui"],
    summary="Web page with listing of all Porch tasks.",
)
async def root(
    request: Request,
    pipeline_name: str = None,
    task_status: ui.UiStateEnum | TaskStateEnum = ui.UiStateEnum.ALL,
    db_accessor=Depends(get_DbAccessor),
) -> Response:
    redirect = False
    url = request.url
    if not pipeline_name and "pipeline_name" in request.query_params.keys():
        url = request.url.remove_query_params("pipeline_name")
        redirect = True
    if (
        task_status == ui.UiStateEnum.ALL
        and "task_status" in request.query_params.keys()
    ):
        url = request.url.remove_query_params("task_status")
        redirect = True
    if redirect:
        return RedirectResponse(url)

    pipeline_list = await db_accessor.get_recent_pipelines()
    if pipeline_name and pipeline_name not in [
        pipeline.name for pipeline in pipeline_list
    ]:
        return HTMLResponse(
            f"""
            <h1> Error 404 </h1>
            <h3> {pipeline_name} not registered in POrch </h3> 
            """
        )

    endpoint = "/ui/tasks"
    endpoint += f"/{pipeline_name}" if pipeline_name else "/All"
    endpoint += f"/{task_status}/{DAY_ONE}"

    return templates.TemplateResponse(
        "listing.j2",
        {
            "endpoint": endpoint,
            "pipeline_name": pipeline_name,
            "task_status": task_status,
            "pipelines": pipeline_list,
            "request": request,
            "states": [state for state in ui.UiStateEnum]
            + [state for state in TaskStateEnum],
            "version": version,
        },
    )


@app.get(
    "/long_running",
    response_class=HTMLResponse,
    tags=["ui"],
    summary="Web page with listing of long running Porch tasks",
)
async def long_running(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "listing.j2",
        {
            "endpoint": "/ui/long_running",
            "pipeline_name": "Long Running",
            "request": request,
            "version": version,
        },
    )


@app.get(
    "/recently_failed",
    response_class=HTMLResponse,
    tags=["ui"],
    summary="Web page with listing of tasks that have failed in the last 2 " "weeks",
)
async def recently_failed(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "listing.j2",
        {
            "endpoint": f"/ui/tasks/All/{TaskStateEnum.FAILED}/{RECENT}",
            "pipeline_name": "Recently Failed",
            "request": request,
            "version": version,
        },
    )


@app.get(
    "/about",
    response_class=HTMLResponse,
    tags=["about"],
    summary="Web page with links to pipeline OpenAPI documentation.",
)
async def about(request: Request, db_accessor=Depends(get_DbAccessor)) -> HTMLResponse:
    pipeline_list = await db_accessor.get_recent_pipelines()
    return templates.TemplateResponse(
        "about.j2", {"pipelines": pipeline_list, "request": request, "version": version}
    )
