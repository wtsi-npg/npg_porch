import pytest
from starlette import status

from npg_porch.models import Pipeline, Version

headers = {
    "Authorization": "Bearer cac0533d5599489d9a3d998028a79fe8",
    "accept": "application/json",
}
headers4power_user = {
    "Authorization": "Bearer 4bab73544c834c6f86f9662e5de26d0d",
    "accept": "application/json",
}


def test_create_version(async_minimum, fastapi_testclient):
    pipeline = Pipeline(name="new_pipeline", uri="test.pipeline")
    version_one = Version(version="1.0", pipeline=pipeline)
    version_two = Version(version="2.0", pipeline=pipeline)
    response = fastapi_testclient.post(
        "/versions", json=version_one.model_dump(), follow_redirects=True
    )
    assert (
        response.status_code == status.HTTP_403_FORBIDDEN
    ), "Fails to create version with no authentication"

    response = fastapi_testclient.post(
        "/versions",
        json=version_one.model_dump(),
        follow_redirects=True,
        headers=headers4power_user,
    )
    assert (
        response.status_code == status.HTTP_403_FORBIDDEN
    ), "Fails to create version with admin authentication"

    p_response = fastapi_testclient.post(
        "/pipelines",
        json=version_one.model_dump(),
        follow_redirects=True,
        headers=headers4power_user,
    )

    response = fastapi_testclient.post(
        "/versions",
        json=version_two.model_dump(),
        follow_redirects=True,
        headers=headers,
    )
    assert (
        response.status_code == status.HTTP_403_FORBIDDEN
    ), "Authentication for wrong pipeline"

    response = fastapi_testclient.post(
        "/pipelines/new_pipeline/token/new_token",
        follow_redirects=True,
        headers=headers4power_user,
    )
    token_headers = {
        "Authorization": f"Bearer {response.json()['token']}",
        "accept": "application/json",
    }

    response = fastapi_testclient.post(
        "/versions",
        json=version_one.model_dump(),
        follow_redirects=True,
        headers=token_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT, "Version already exists"

    response = fastapi_testclient.post(
        "/versions",
        json=version_two.model_dump(),
        follow_redirects=True,
        headers=token_headers,
    )
    assert (
        response.status_code == status.HTTP_201_CREATED
    ), "Version created successfully"


def test_get_versions(async_minimum, fastapi_testclient):
    versions = [
        {
            "pipeline": {"name": "ptest one", "uri": "pipeline-test.com"},
            "version": "0.3.14",
        },
        {
            "pipeline": {"name": "ptest one", "uri": "pipeline-test.com"},
            "version": "1.0.0",
        },
    ]

    response = fastapi_testclient.get("/versions/fake pipeline")
    assert response.json() == []
    response = fastapi_testclient.get("/versions/ptest one")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [versions[0]]
    fastapi_testclient.post(
        "/versions", json=versions[1], follow_redirects=True, headers=headers
    )
    response = fastapi_testclient.get("/versions/ptest one")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == versions
