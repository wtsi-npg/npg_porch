from starlette import status

from .fixtures.deploy_db import async_minimum, fastapi_testclient
from npg.porch.models import Pipeline

def test_pipeline_get(async_minimum, fastapi_testclient):
    response = fastapi_testclient.get('/pipelines')
    assert response.status_code == status.HTTP_200_OK
    pipeline = Pipeline.parse_obj(response.json()[0])
    assert pipeline, 'Response fits into the over-the-wire model'
    assert pipeline.name == 'ptest one'
    assert pipeline.version == '0.3.14'

def test_get_known_pipeline(async_minimum, fastapi_testclient):
    response = fastapi_testclient.get('/pipelines/ptest one')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1, 'All one pipelines returned'

    pipeline = Pipeline.parse_obj(response.json()[0])
    assert pipeline, 'Response fits into the over-the-wire model'
    assert pipeline.name == 'ptest one'
    assert pipeline.version == '0.3.14'

    response = fastapi_testclient.get('/pipelines/not here')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == "Pipeline 'not here' not found"

    # Get a versioned pipeline
    response = fastapi_testclient.get('/pipelines/ptest one?pipeline_version=0.3.14')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1, 'All one pipelines returned'

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

    assert response.status_code == status.HTTP_201_CREATED
    pipeline = Pipeline.parse_obj(response.json())
    assert pipeline == desired_pipeline, 'Got back what we put in'

    # Create the same pipeline
    response = fastapi_testclient.post(
        '/pipelines',
        json=desired_pipeline.dict(),
        allow_redirects=True
    )

    assert response.status_code == status.HTTP_409_CONFLICT, 'ptest two already in DB, must be unique'
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

    assert response.status_code == status.HTTP_201_CREATED

    # Retrieve the same pipelines

    response = fastapi_testclient.get(
        '/pipelines'
    )
    assert response.status_code == status.HTTP_200_OK
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

    assert response.status_code == status.HTTP_400_BAD_REQUEST
