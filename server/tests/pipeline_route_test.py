from .fixtures.deploy_db import fastapi_testclient
from npg.porch.models import Pipeline

def test_pipeline_get(async_minimum, fastapi_testclient):
    response = fastapi_testclient.get('/pipelines')
    print(response.content)
    assert response.status_code == 200
    pipeline = Pipeline.parse_obj(response.json()[0])
    assert pipeline, 'Response fits into the over-the-wire model'
    assert pipeline.name is None
    assert pipeline.version == '0.3.14'
