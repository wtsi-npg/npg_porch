from datetime import datetime, timedelta
import html
import json
import re

import pytest
from fastapi.testclient import TestClient
from starlette import status

from npg_porch.endpoints import ui
from npg_porch.server import app
from npg_porch.models import Pipeline, Task, TaskStateEnum

client = TestClient(app)
ptest_one_token = "cac0533d5599489d9a3d998028a79fe8"


def _extract_page_json_attr(page: str, attr_name: str):
    match = re.search(rf'{attr_name}="([^"]+)"', page)
    assert match, f"{attr_name} should be rendered into page config"
    return json.loads(html.unescape(match.group(1)))


@pytest.mark.asyncio
async def test_get_ui_tasks(db_accessor, async_past_tasks):
    done_response = client.get(f"/ui/tasks/All/{TaskStateEnum.DONE}/{datetime.min}")
    pending_response = client.get(
        f"/ui/tasks/All/{TaskStateEnum.PENDING}/{datetime.min}"
    )
    not_done_response = client.get(
        f"/ui/tasks/All/{ui.UiStateEnum.NOT_DONE}/{datetime.min}"
    )
    all_response = client.get(f"/ui/tasks/All/{ui.UiStateEnum.ALL}/{datetime.min}")

    # These include async minimum tasks as well
    assert done_response.json()["recordsTotal"] == 3, "Three tasks are done"
    assert pending_response.json()["recordsTotal"] == 5, "Three tasks are pending"
    assert not_done_response.json()["recordsTotal"] == 11, "Nine tasks are not done"
    assert all_response.json()["recordsTotal"] == 14, "Twelve tasks are present"

    recent_fail_response = client.get(
        f"/ui/tasks/All/{TaskStateEnum.FAILED}/{datetime.now() - timedelta(days=14)}"
    )

    assert (
        recent_fail_response.json()["recordsTotal"] == 2
    ), "Two tasks have failed within the last 14 days"

    modelled_pipeline = Pipeline(
        name="new_pipeline", uri="file://test.pipeline", version="1.0"
    )
    pipeline = await db_accessor.create_pipeline(modelled_pipeline)

    response = client.get(f"/ui/tasks/new_pipeline/{ui.UiStateEnum.ALL}/{datetime.min}")
    assert response.json()["recordsTotal"] == 0, "No tasks in new pipeline"

    for i in range(3):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    done_response = client.get(
        f"/ui/tasks/new_pipeline/{TaskStateEnum.DONE}/{datetime.min}"
    )
    pending_response = client.get(
        f"/ui/tasks/new_pipeline/{TaskStateEnum.PENDING}/{datetime.min}"
    )
    assert (
        done_response.json()["recordsTotal"] == 0
    ), "No tasks are done in new pipeline after task creation"
    assert (
        pending_response.json()["recordsTotal"] == 3
    ), "Three tasks are pending in new pipeline after task creation"


@pytest.mark.asyncio
async def test_get_long_running_ui_tasks(db_accessor):
    modelled_pipeline = Pipeline(
        name="test_pipeline", uri="file://test.pipeline", version="1.0"
    )
    pipeline = await db_accessor.create_pipeline(modelled_pipeline)

    for i in range(4):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    for i in range(2):
        await db_accessor.update_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.DONE,
            ),
        )

    response = client.get("/ui/long_running")

    assert response.json()["recordsTotal"] == 2, "Two long running tasks"


def test_listing_page_state_editing_controls(async_minimum, fastapi_testclient):
    # Verifies the listing pages render the edit-state UI shell and boot config needed by the static page script.
    expected_states = [state.value for state in TaskStateEnum]

    for path in ["/", "/long_running", "/recently_failed"]:
        response = fastapi_testclient.get(path, follow_redirects=True)
        assert response.status_code == 200, f"{path} should render successfully"
        page = response.text

        assert "content-security-policy" in response.headers, (
            f"{path} should return a CSP header for the listing page"
        )
        assert "script-src 'self' https://code.jquery.com https://cdn.datatables.net" in (
            response.headers["content-security-policy"]
        ), f"{path} should allow the expected first-party and CDN scripts"
        assert 'name="filter_mode"' in page, f"{path} should render the filter mode control"
        assert 'id="apply_state_changes"' in page, (
            f"{path} should render the task state apply button"
        )
        assert 'id="sign_in_for_updates"' in page, (
            f"{path} should render the sign-in control for update sessions"
        )
        assert 'id="sign_out_of_updates"' in page, (
            f"{path} should render the sign-out control for update sessions"
        )
        assert 'id="ui_session_status"' in page, (
            f"{path} should render the session status text placeholder"
        )
        assert 'id="token_dialog"' in page, f"{path} should render the token dialog"
        assert 'id="token_fallback"' in page, (
            f"{path} should render the non-dialog token fallback form"
        )
        assert 'id="listing_page"' in page, (
            f"{path} should render the root page element for bootstrapping"
        )
        assert 'href="/static/listing.css"' in page, (
            f"{path} should load the first-party listing stylesheet"
        )
        assert 'src="/static/listing.js"' in page, (
            f"{path} should load the first-party listing script"
        )
        assert 'class="text-start status-column">Status<' in page, (
            f"{path} should render the editable status column header"
        )
        assert _extract_page_json_attr(page, "data-task-states-json") == expected_states, (
            f"{path} should expose the task state options to the page script"
        )
        assert _extract_page_json_attr(page, "data-endpoint-json").startswith("/ui/"), (
            f"{path} should expose a UI data endpoint to the page script"
        )
        assert _extract_page_json_attr(page, "data-ui-csrf-token-json") is None, (
            f"{path} should start with no active UI session CSRF token"
        )
        assert _extract_page_json_attr(page, "data-ui-session-pipeline-name-json") is None, (
            f"{path} should start with no active UI session pipeline name"
        )


def test_listing_page_includes_active_ui_session(async_minimum, fastapi_testclient):
    login = fastapi_testclient.post("/ui/session", json={"token": ptest_one_token})
    assert login.status_code == 200, (
        "Creating a UI session with a valid token should succeed"
    )

    response = fastapi_testclient.get("/", follow_redirects=True)
    assert response.status_code == 200, (
        "The listing page should still render after creating a UI session"
    )
    page = response.text

    assert _extract_page_json_attr(page, "data-ui-csrf-token-json"), (
        "An active UI session should expose a CSRF token to the page script"
    )
    assert _extract_page_json_attr(page, "data-ui-session-pipeline-name-json") == "ptest one", (
        "An active UI session should expose the session pipeline name to the page script"
    )


def test_ui_session_rejects_invalid_token(fastapi_testclient):
    login = fastapi_testclient.post("/ui/session", json={"token": "not-a-real-token"})

    assert login.status_code == status.HTTP_403_FORBIDDEN, (
        "Creating a UI session with an invalid token should be rejected"
    )
    assert login.json() == {"detail": "Invalid token"}, (
        "An invalid UI session token should return the expected error payload"
    )
    assert login.cookies.get("npg_porch_ui_session") is None, (
        "Rejecting an invalid token should not create a UI session cookie"
    )


@pytest.mark.asyncio
async def test_listing_page_escapes_pipeline_names(db_accessor):
    pipeline = Pipeline(
        name='evil<script>alert("xss")</script>',
        uri="file://test.pipeline",
        version="1.0",
    )
    await db_accessor.create_pipeline(pipeline)

    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200, (
        "The listing page should render even when a pipeline name contains HTML"
    )
    page = response.text

    assert 'evil<script>alert("xss")</script>' not in page, (
        "Pipeline names should not be rendered as raw HTML in the listing page"
    )
    assert "evil&lt;script&gt;alert" in page, (
        "Pipeline names should be HTML-escaped in the listing page"
    )


def test_ui_session_login_logout_and_task_update(async_minimum, fastapi_testclient):
    task = fastapi_testclient.get("/tasks").json()[0]
    task["status"] = TaskStateEnum.RUNNING

    unauthenticated = fastapi_testclient.put("/ui/tasks", json=task)
    assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED, (
        "Updating tasks through the UI route should require an authenticated UI session"
    )

    login = fastapi_testclient.post("/ui/session", json={"token": ptest_one_token})
    assert login.status_code == status.HTTP_200_OK, (
        "Creating a UI session with a valid token should succeed"
    )
    payload = login.json()
    assert payload["pipeline_name"] == "ptest one", (
        "The UI session response should identify the pipeline tied to the token"
    )
    csrf_token = payload["csrf_token"]
    assert csrf_token, "The UI session response should include a CSRF token"
    session_cookie = login.cookies.get("npg_porch_ui_session")
    assert session_cookie, "Creating a UI session should set the UI session cookie"
    set_cookie_header = login.headers["set-cookie"].lower()
    assert "httponly" in set_cookie_header, (
        "The UI session cookie should be marked HttpOnly"
    )
    assert "samesite=strict" in set_cookie_header, (
        "The UI session cookie should use SameSite=Strict"
    )

    missing_csrf = fastapi_testclient.put("/ui/tasks", json=task)
    assert missing_csrf.status_code == status.HTTP_403_FORBIDDEN, (
        "The UI task update route should reject requests that omit the CSRF token"
    )
    assert missing_csrf.json() == {"detail": "Invalid CSRF token"}, (
        "Requests missing the CSRF token should fail with the expected error message"
    )

    updated = fastapi_testclient.put(
        "/ui/tasks", json=task, headers={"X-CSRF-Token": csrf_token}
    )
    assert updated.status_code == status.HTTP_200_OK, (
        "The UI task update route should accept authenticated requests with a valid CSRF token"
    )
    assert updated.json()["status"] == TaskStateEnum.RUNNING, (
        "The UI task update route should persist the requested task status change"
    )

    logout = fastapi_testclient.delete(
        "/ui/session", headers={"X-CSRF-Token": csrf_token}
    )
    assert logout.status_code == status.HTTP_204_NO_CONTENT, (
        "Deleting the UI session with a valid CSRF token should succeed"
    )

    after_logout = fastapi_testclient.put(
        "/ui/tasks", json=task, headers={"X-CSRF-Token": csrf_token}
    )
    assert after_logout.status_code == status.HTTP_401_UNAUTHORIZED, (
        "Logging out should invalidate the UI session for subsequent task updates"
    )


def test_root_route_escapes_unknown_pipeline_name(fastapi_testclient):
    response = fastapi_testclient.get(
        "/?pipeline_name=%3Cscript%3Ealert(1)%3C%2Fscript%3E",
        follow_redirects=True,
    )
    assert response.status_code == 404, (
        "Requesting an unknown pipeline should still return a 404 response"
    )
    assert "<script>alert(1)</script>" not in response.text, (
        "The unknown-pipeline page should not render the raw pipeline name as HTML"
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text, (
        "The unknown-pipeline page should HTML-escape the requested pipeline name"
    )


def test_root_route_honours_filter_mode_query(async_past_tasks, fastapi_testclient):
    # Verifies filter_mode query parameters select the expected backing UI endpoint and page heading.
    long_running = fastapi_testclient.get(
        "/?filter_mode=long_running", follow_redirects=True
    )
    assert long_running.status_code == 200, (
        "The long_running filter mode should render the listing page"
    )
    assert "/ui/long_running" in long_running.text, (
        "The long_running filter mode should target the long-running UI endpoint"
    )
    assert "Long Running" in long_running.text, (
        "The long_running filter mode should update the page heading"
    )

    recently_failed = fastapi_testclient.get(
        "/?filter_mode=recently_failed", follow_redirects=True
    )
    assert recently_failed.status_code == 200, (
        "The recently_failed filter mode should render the listing page"
    )
    assert "/ui/tasks/All/FAILED/" in recently_failed.text, (
        "The recently_failed filter mode should target the failed-task UI endpoint"
    )
    assert "Recently Failed" in recently_failed.text, (
        "The recently_failed filter mode should update the page heading"
    )
