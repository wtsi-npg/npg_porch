from npg_porch.models import Task, TaskStateEnum, Pipeline
from starlette import status

# Not testing get-all-tasks as this method will ultimately go

headers4ptest_one = {
    "Authorization": "Bearer cac0533d5599489d9a3d998028a79fe8",
    "accept": "application/json",
}
headers4ptest_some = {
    "Authorization": "Bearer ba53eaf7073d4c2b95ca47aeed41086c",
    "accept": "application/json",
}


def test_task_creation(async_minimum, fastapi_testclient):
    # Create a task with a sparse pipeline definition
    task_one = Task(
        pipeline={"name": "ptest one", "version": "0.3.14"},
        task_input={"number": 1},
        status=TaskStateEnum.PENDING,
    )

    response = fastapi_testclient.post(
        "tasks",
        json=task_one.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one,
    )
    assert response.status_code == status.HTTP_201_CREATED
    response_obj = response.json()
    assert task_one == response_obj

    # Try again and expect to succeed with a different status code and the
    # same task returned.
    response = fastapi_testclient.post(
        "tasks",
        json=task_one.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == response_obj

    task_two = Task(
        pipeline={"name": "ptest none", "version": "0.3.14"},
        task_input={"number": 1},
        status=TaskStateEnum.PENDING,
    )
    # The token is valid, but for a different pipeline. It is impossible
    # to have a valid token for a pipeline that does not exist.
    response = fastapi_testclient.post(
        "tasks",
        json=task_two.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_task_update(async_minimum, fastapi_testclient):
    task = fastapi_testclient.get("/tasks", headers=headers4ptest_one).json()[0]
    assert task["status"] == TaskStateEnum.PENDING.value

    unauthenticated = fastapi_testclient.put(
        "/tasks", json=task, follow_redirects=True
    )
    assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED

    task["status"] = TaskStateEnum.RUNNING
    response = fastapi_testclient.put(
        "/tasks", json=task, follow_redirects=True, headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK

    modified_task = Task.model_validate(response.json())
    assert modified_task == task

    # Now invalidate the task by changing the signature
    modified_task.task_input = {"something": "different"}
    response = fastapi_testclient.put(
        "/tasks",
        json=modified_task.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task to be modified could not be found"}

    # And change the reference pipeline to something wrong.
    # This token is valid, but for a different pipeline. It is impossible
    # to have a valid token for a pipeline that does not exist.
    modified_task.pipeline = Pipeline.model_validate(
        {"name": "ptest one thousand", "version": "1.0"}
    )
    response = fastapi_testclient.put(
        "/tasks",
        json=modified_task.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_task_update_mixed_outcomes(async_minimum, fastapi_testclient):
    # Confirms task updates are independent in a mixed-outcome workflow: a valid
    # update must be persisted even if a later update in the same user action
    # fails validation, and the failed update must leave its target task
    # unchanged.
    #
    # This is important because the web UI allows a user to update several tasks in one
    # batch-like workflow (although we haven't gone to the length of creating a new
    # batch-like endpoint and are just using the existing endpoint repeatedly).
    tasks = fastapi_testclient.get(
        "/tasks?pipeline_name=ptest one", headers=headers4ptest_one
    ).json()
    assert len(tasks) == 2, (
        "The fixture should provide two tasks in ptest one for the mixed-outcome update scenario"
    )

    to_update = tasks[0]
    to_fail = tasks[1]

    to_update["status"] = TaskStateEnum.RUNNING
    success_response = fastapi_testclient.put(
        "/tasks", json=to_update, follow_redirects=True, headers=headers4ptest_one
    )
    assert success_response.status_code == status.HTTP_200_OK, (
        "Updating the first task with a valid payload should succeed"
    )

    # Change the identifying task_input as well as the status so the server can
    # no longer match this request to an existing task to update.
    invalid_signature_payload = dict(to_fail)
    invalid_signature_payload["status"] = TaskStateEnum.RUNNING
    invalid_signature_payload["task_input"] = {"this": "does not match existing task"}
    failed_response = fastapi_testclient.put(
        "/tasks",
        json=invalid_signature_payload,
        follow_redirects=True,
        headers=headers4ptest_one,
    )
    assert failed_response.status_code == status.HTTP_404_NOT_FOUND, (
        "Updating the second task with a mismatched signature should fail"
    )
    assert failed_response.json() == {"detail": "Task to be modified could not be found"}, (
        "A failed update should report that the original task could not be located"
    )

    # Re-query by status to prove the first update stuck and the second task was
    # not moved despite the failed request.
    running_tasks = fastapi_testclient.get(
        "/tasks?pipeline_name=ptest one&status=RUNNING", headers=headers4ptest_one
    ).json()
    assert len(running_tasks) == 1, (
        "Only the successfully updated task should be moved into RUNNING"
    )
    assert running_tasks[0]["task_input"] == to_update["task_input"], (
        "The RUNNING task should be the one that was updated successfully"
    )

    pending_tasks = fastapi_testclient.get(
        "/tasks?pipeline_name=ptest one&status=PENDING", headers=headers4ptest_one
    ).json()
    assert len(pending_tasks) == 1, (
        "The failed update should leave the other task in PENDING"
    )
    assert pending_tasks[0]["task_input"] == to_fail["task_input"], (
        "The still-pending task should be the one whose update failed"
    )


def test_task_claim(async_minimum, async_tasks, fastapi_testclient):
    response = fastapi_testclient.get("/versions/ptest some", headers=headers4ptest_one)
    assert response.status_code == status.HTTP_200_OK

    version_1 = Pipeline(version=response.json()[0], name="ptest some")
    version_2 = Pipeline(version=response.json()[1], name="ptest some")
    tasks_seen = []

    # Cannot claim with a token issued for a different pipeline.
    response = fastapi_testclient.post(
        "/tasks/claim", json=version_1.model_dump(), headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = fastapi_testclient.post(
        "/tasks/claim", json=version_1.model_dump(), headers=headers4ptest_some
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 1, "Defaults to one task claimed"
    t = tasks[0]
    assert t["task_input"] == {"input": 1}
    assert t["status"] == TaskStateEnum.CLAIMED
    tasks_seen.append(t["task_input_id"])

    response = fastapi_testclient.post(
        "/tasks/claim?num_tasks=0",
        json=version_1.model_dump(),
        headers=headers4ptest_some,
    )
    assert (
        response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    ), "Not allowed to use invalid numbers of tasks"  # noqa: E501

    response = fastapi_testclient.post(
        "/tasks/claim?num_tasks=2",
        json=version_1.model_dump(),
        headers=headers4ptest_some,
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 2, "Asked for two, got two"
    tasks_seen.extend([t["task_input_id"] for t in tasks])

    # Cannot test race conditions, because sqlite only pretends to support full async
    # Claim the rest
    response = fastapi_testclient.post(
        "/tasks/claim?num_tasks=8",
        json=version_1.model_dump(),
        headers=headers4ptest_some,
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 2, "Asked for eight, got two"
    tasks_seen.extend([t["task_input_id"] for t in tasks])

    # Claim tasks from the other pipeline version
    response = fastapi_testclient.post(
        "/tasks/claim?num_tasks=10",
        json=version_2.model_dump(),
        headers=headers4ptest_some,
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 5, "Asked for ten, got five"
    tasks_seen.extend([t["task_input_id"] for t in tasks])
    assert len(set(tasks_seen)) == 10, "Ten unique tasks were claimed"

    response = fastapi_testclient.post(
        "/tasks/claim", json=version_2.model_dump(), headers=headers4ptest_some
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 0, "Tried to claim, did not get any tasks"


def test_get_tasks(async_minimum, async_tasks, fastapi_testclient):
    response = fastapi_testclient.get("/tasks")
    assert (
        response.status_code == status.HTTP_200_OK
    ), "Authorisation not required for GET requests"
    response = fastapi_testclient.get("/tasks", headers=headers4ptest_one)
    assert (
        response.status_code == status.HTTP_200_OK
    ), "Authorised GET requests also work"
    tasks = response.json()

    unique_pipelines = {t["pipeline"]["name"] for t in tasks}

    assert (
        "ptest one" in unique_pipelines
    ), "Tasks for pipeline present with relevant token"
    assert (
        "ptest some" in unique_pipelines
    ), "Tasks for other pipelines also present with token"

    response = fastapi_testclient.get(
        "/tasks?pipeline_name=ptest one", headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK, "One optional argument works"
    tasks = response.json()
    assert len(tasks) == 2, "Most tasks now filtered"
    assert {t["pipeline"]["name"] for t in tasks} == {
        "ptest one"
    }, "All tasks belong to pipeline"

    response = fastapi_testclient.get(
        "/tasks?status=PENDING", headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK, "Other optional argument works"
    tasks = response.json()
    # async_minimum provides 2 tasks, async_tasks provides 10
    assert len(tasks) == 12, "Twelve pending tasks selected"

    response = fastapi_testclient.get(
        "/tasks?status=RUNNING", headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK, "Other optional argument works"
    tasks = response.json()
    assert len(tasks) == 0, "No running tasks selected"

    response = fastapi_testclient.get(
        '/tasks?pipeline_name="ptest one"&status=PENDING', headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK, "Both arguments together work"
    print(response.text)
    tasks = response.json()
    assert len(tasks) == 0, "but no tasks are returned that match status and pipeline"

    response = fastapi_testclient.get(
        '/tasks?pipeline_version="0.3.14"', headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
