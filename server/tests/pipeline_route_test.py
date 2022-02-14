from .fixtures.deploy_db import async_minimum, fastapi_testclient
from npg.porch.models import Pipeline

def test_pipeline_get(async_minimum, fastapi_testclient):
    response = fastapi_testclient.get('/pipelines')
    assert response.status_code == 200
    pipeline = Pipeline.parse_obj(response.json()[0])
    assert pipeline, 'Response fits into the over-the-wire model'
    assert pipeline.name == 'ptest one'
    assert pipeline.version == '0.3.14'

def test_get_known_pipeline(async_minimum, fastapi_testclient):
    response = fastapi_testclient.get('/pipelines/ptest one')
    assert response.status_code == 200
    assert len(response.json()) == 1, 'All one pipelines returned'

    pipeline = Pipeline.parse_obj(response.json()[0])
    assert pipeline, 'Response fits into the over-the-wire model'
    assert pipeline.name == 'ptest one'
    assert pipeline.version == '0.3.14'

    response = fastapi_testclient.get('/pipelines/not here')
    assert response.status_code == 404
    assert response.json()['detail'] == "Pipeline 'not here' not found"

def test_create_pipeline(fastapi_testclient):
    # Create a pipeline
    desired_pipeline = Pipeline(
        name='ptest two',
        uri='http://test.com',
        version='1'
    )

    response = fastapi_testclient.post(
        '/pipelines',
        json=desired_pipeline.dict(),
        allow_redirects=True
    )

    assert response.status_code == 201
    pipeline = Pipeline.parse_obj(response.json())
    assert pipeline == desired_pipeline, 'Got back what we put in'

    # Create the same pipeline
    response = fastapi_testclient.post(
        '/pipelines',
        json=desired_pipeline.dict(),
        allow_redirects=True
    )

    assert response.status_code == 409, 'ptest two already in DB, must be unique'
    assert response.json()['detail'] == 'Pipeline already exists'

    # Create a different pipeline
    second_desired_pipeline = Pipeline(
        name='ptest three',
        uri='http://anothertest.com',
        version='1'
    )

    response = fastapi_testclient.post(
        '/pipelines',
        json=second_desired_pipeline.dict(),
        allow_redirects=True
    )

    assert response.status_code == 201

    # Retrieve the same pipelines

    response = fastapi_testclient.get(
        '/pipelines'
    )
    assert response.status_code == 200
    assert response.json() == [desired_pipeline, second_desired_pipeline]

    # Create a very poorly provenanced pipeline
    third_desired_pipeline = Pipeline(
        name='ptest three and a half',
        uri='http://anothertest.com',
        version=None
    )

    response = fastapi_testclient.post(
        '/pipelines',
        json=third_desired_pipeline.dict(),
        allow_redirects=True
    )

    print(response.json())
    assert response.status_code == 400
