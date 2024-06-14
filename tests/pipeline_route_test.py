import json

from starlette import status

from npg_porch.models import Pipeline


headers = {
    'Authorization': 'Bearer cac0533d5599489d9a3d998028a79fe8',
    'accept': 'application/json'
}
headers4power_user = {
    'Authorization': 'Bearer 4bab73544c834c6f86f9662e5de26d0d',
    'accept': 'application/json'
}


def http_create_pipeline(fastapi_testclient, pipeline):

    response = fastapi_testclient.post(
        '/pipelines', json=pipeline.model_dump(), follow_redirects=True
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = fastapi_testclient.post(
        '/pipelines', json=pipeline.model_dump(), follow_redirects=True,
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = fastapi_testclient.post(
        '/pipelines', json=pipeline.model_dump(), follow_redirects=True,
        headers=headers4power_user
    )
    assert response.status_code == status.HTTP_201_CREATED

    return response.json()


def test_pipeline_get(async_minimum, fastapi_testclient):

    response = fastapi_testclient.get('/pipelines')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = fastapi_testclient.get('/pipelines', headers=headers)
    assert response.status_code == status.HTTP_200_OK
    pipeline = Pipeline.model_validate(response.json()[0])
    assert pipeline, 'Response fits into the over-the-wire model'
    assert pipeline.name == 'ptest one'
    assert pipeline.version == '0.3.14'


def test_pipeline_filtered_get(async_minimum, fastapi_testclient):

    second_pipeline = Pipeline(
        name='ptest two',
        uri='http://test.com',
        version='0.3.14'
    )

    third_pipeline = Pipeline(
        name='ptest three',
        uri='http://other-test.com',
        version='0.3.14'
    )

    http_create_pipeline(fastapi_testclient, second_pipeline)
    http_create_pipeline(fastapi_testclient, third_pipeline)

    response = fastapi_testclient.get(
        '/pipelines?version=0.3.14', headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    pipes = response.json()
    assert len(pipes) == 3, 'All three pipelines have the same version'

    response = fastapi_testclient.get(
        '/pipelines?uri=http://test.com', headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    pipes = response.json()
    assert len(pipes) == 1, 'Only one pipeline matches the uri'
    assert pipes[0] == second_pipeline.model_dump()


def test_get_known_pipeline(async_minimum, fastapi_testclient):

    response = fastapi_testclient.get(
        '/pipelines/ptest one', headers=headers
    )
    assert response.status_code == status.HTTP_200_OK

    pipeline = Pipeline.model_validate(response.json())
    assert pipeline, 'Response fits into the over-the-wire model'
    assert pipeline.name == 'ptest one'
    assert pipeline.version == '0.3.14'

    response = fastapi_testclient.get(
        '/pipelines/not here', headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == "Pipeline 'not here' not found"


def test_create_pipeline(async_minimum, fastapi_testclient):
    invalid_pipeline = {
        "name": "ptest one",
        "url": "http://test.com",  # URL, not URI
        "version": "1"
    }
    response = fastapi_testclient.post(
            "/pipelines", json=json.dumps(invalid_pipeline), follow_redirects=True,
            headers=headers4power_user
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Create a pipeline
    desired_pipeline = Pipeline(
        name='ptest two',
        uri='http://test.com',
        version='1'
    )

    response = http_create_pipeline(fastapi_testclient, desired_pipeline)
    pipeline = Pipeline.model_validate(response)
    assert pipeline == desired_pipeline, 'Got back what we put in'

    # Create the same pipeline
    response = fastapi_testclient.post(
        '/pipelines',
        json=desired_pipeline.model_dump(),
        follow_redirects=True,
        headers=headers4power_user
    )
    assert response.status_code == status.HTTP_409_CONFLICT, 'ptest two already in DB'
    assert response.json()['detail'] == 'Pipeline already exists'

    # Create a different pipeline
    second_desired_pipeline = Pipeline(
        name='ptest three',
        uri='http://anothertest.com',
        version='1'
    )

    response = http_create_pipeline(fastapi_testclient, second_desired_pipeline)

    # Retrieve the same pipelines
    response = fastapi_testclient.get(
        '/pipelines', headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[1:] == [desired_pipeline.model_dump(), second_desired_pipeline.model_dump()]

    # Create a very poorly provenanced pipeline
    third_desired_pipeline = Pipeline(
        name='ptest three and a half',
        uri='http://anothertest.com',
        version=None
    )

    response = fastapi_testclient.post(
        '/pipelines',
        json=third_desired_pipeline.model_dump(),
        follow_redirects=True,
        headers=headers4power_user
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
