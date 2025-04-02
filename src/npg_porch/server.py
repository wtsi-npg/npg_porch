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

from importlib import metadata
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, PackageLoader

from npg_porch.db.connection import get_DbAccessor
from npg_porch.endpoints import pipelines, tasks, ui

# https://fastapi.tiangolo.com/tutorial/bigger-applications/
# https://fastapi.tiangolo.com/tutorial/metadata

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
async def root(request: Request, db_accessor=Depends(get_DbAccessor)) -> HTMLResponse:
    pipeline_list = await db_accessor.get_all_pipelines()
    return templates.TemplateResponse(
        "listing.j2",
        {
            "endpoint": "/ui/tasks",
            "pipeline_name": None,
            "pipelines": pipeline_list,
            "request": request,
            "version": version,
        },
    )


@app.get(
    "/form_redirect",
    response_class=RedirectResponse,
    summary="Redirect to deal with form input",
)
async def form_redirect(pipeline_name: str) -> RedirectResponse:
    return RedirectResponse(f"/pipeline/{pipeline_name}")


@app.get(
    # Needs intermediate path to prevent interference with other paths
    "/pipeline/{pipeline_name}",
    response_class=HTMLResponse,
    tags=["ui"],
    summary="Web page with listing of porch tasks for specified pipeline.",
)
async def pipeline(
    request: Request, pipeline_name: str, db_accessor=Depends(get_DbAccessor)
) -> HTMLResponse:
    pipeline_list = await db_accessor.get_all_pipelines()
    return templates.TemplateResponse(
        "listing.j2",
        {
            "endpoint": f"/ui/tasks/{ pipeline_name }",
            "pipeline_name": pipeline_name,
            "pipelines": pipeline_list,
            "request": request,
            "version": version,
        },
    )


# Redirect intermediate path
@app.get("/pipeline", response_class=RedirectResponse)
async def pipeline_redirect() -> RedirectResponse:
    return RedirectResponse("/")


@app.get(
    "/about",
    response_class=HTMLResponse,
    tags=["about"],
    summary="Web page with links to pipeline OpenAPI documentation.",
)
async def about(request: Request, db_accessor=Depends(get_DbAccessor)) -> HTMLResponse:
    pipeline_list = await db_accessor.get_all_pipelines()
    return templates.TemplateResponse(
        "about.j2", {"pipelines": pipeline_list, "request": request, "version": version}
    )
