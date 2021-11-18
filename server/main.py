from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from npg.porch.endpoints import pipelines, analysis_tasks
#from npg.porch.endpoints import pipelines

#https://fastapi.tiangolo.com/tutorial/bigger-applications/
#https://fastapi.tiangolo.com/tutorial/metadata

tags_metadata = [
    {
        "name": "pipelines",
        "description": "Manage pipelines.",
    },
    {
        "name": "analysis_tasks",
        "description": "Manage analysis tasks.",
    },
    {
        "name": "index",
        "description": "Links to documentation.",
    },
]


app = FastAPI(
    title = "Pipeline Orchestration (POrch)", 
    openapi_url = "/api/v1/openapi.json",
    openapi_tags = tags_metadata,
)
app.include_router(pipelines.router)
app.include_router(analysis_tasks.router)

@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["index"],
    summary="Web page with links to OpenAPI documentation."
)
async def root():
    return """
    <html>
        <head>
            <title>About Pipeline Orchestration</title>
        </head>
        <body>
            <h1>JSON API for Pipeline Orchestration</h1>
            <p><a href="/docs">docs</a></p>
            <p><a href="/redoc">redoc</a></p>
            <p><a href="/api/v1/openapi.json">OpenAPI JSON Schema</a></p>
        </body>
    </html>
    """
