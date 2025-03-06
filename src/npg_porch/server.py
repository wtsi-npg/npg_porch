# Copyright (C) 2021, 2022, 2025 Genome Research Ltd.
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

import math
from fastapi import FastAPI, Request, Depends
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, PackageLoader
from pydantic import PositiveInt

from npg_porch.db.connection import get_DbAccessor
from npg_porch.endpoints import pipelines, tasks
from npg_porch.models import TaskExpanded, Pipeline

# https://fastapi.tiangolo.com/tutorial/bigger-applications/
# https://fastapi.tiangolo.com/tutorial/metadata

tags_metadata = [
    {
        "name": "pipelines",
        "description": "Manage pipelines.",
    },
    {
        "name": "index",
        "description": "Links to documentation.",
    },
]


app = FastAPI(
    title="Pipeline Orchestration (POrch)",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=tags_metadata,
)
app.include_router(pipelines.router)
app.include_router(tasks.router)

env = Environment(loader=PackageLoader("npg_porch", "templates"))
templates = Jinja2Templates(env=env)

version = metadata.version("npg_porch")


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["index"],
    summary="Web page with listing of Porch tasks.",
)
async def root(
    request: Request,
    page: PositiveInt = 1,
    results_per_page: PositiveInt = 20,
    pipeline_name: str = "",
    db_accessor=Depends(get_DbAccessor),
) -> Response:
    url = redirect_default_arg(request.url, "pipeline_name", pipeline_name, "")
    url = redirect_default_arg(url, "page", page, 1)
    if url != request.url:
        return RedirectResponse(url=url)
    max_page_number = math.ceil(
        await db_accessor.count_tasks(pipeline_name) / results_per_page
    )
    if page > max_page_number > 0:
        return RedirectResponse(
            url=request.url.include_query_params(page=max_page_number)
        )
    task_list: list[TaskExpanded] = await db_accessor.get_expanded_tasks(
        page=page, limit=results_per_page, pipeline_name=pipeline_name
    )
    pipeline_list: list[Pipeline] = await db_accessor.get_all_pipelines()

    return templates.TemplateResponse(
        "index.j2",
        {
            "request": request,
            "pipelines": pipeline_list,
            "tasks": task_list,
            "max_page_number": max_page_number,
            "current_page": page,
            "version": version,
        },
    )


@app.get(
    "/about",
    response_class=HTMLResponse,
    tags=["about"],
    summary="Web page with links to OpenAPI documentation.",
)
async def about(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "about.j2", {"request": request, "version": version}
    )


def redirect_default_arg(
    url, argument_name, argument_value, argument_default: any = None
) -> str:
    if argument_value == argument_default:
        return url.remove_query_params(argument_name)
    else:
        return url
