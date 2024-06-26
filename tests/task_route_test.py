from npg_porch.models import Pipeline, Task, TaskStateEnum
from starlette import status

# Not testing get-all-tasks as this method will ultimately go

headers4ptest_one = {
    'Authorization': 'Bearer cac0533d5599489d9a3d998028a79fe8',
    'accept': 'application/json'
}
headers4ptest_some = {
    'Authorization': 'Bearer ba53eaf7073d4c2b95ca47aeed41086c',
    'accept': 'application/json'
}

def test_task_creation(async_minimum, fastapi_testclient):

    # Create a task with a sparse pipeline definition
    task_one = Task(
        pipeline = {
            'name': 'ptest one'
        },
        task_input = {
            'number': 1
        }
    )

    response = fastapi_testclient.post(
        'tasks',
        json=task_one.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_201_CREATED
    response_obj = response.json()
    assert task_one == response_obj

    # Try again and expect to succeed with a different status code and the
    # same task returned.
    response = fastapi_testclient.post(
        'tasks',
        json=task_one.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == response_obj

    task_two = Task(
        pipeline = {
            'name': 'ptest none'
        },
        task_input = {
            'number': 1
        }
    )
    # The token is valid, but for a different pipeline. It is impossible
    # to have a valid token for a pipeline that does not exist.
    response = fastapi_testclient.post(
        'tasks',
        json=task_two.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_task_update(async_minimum, fastapi_testclient):

    task = fastapi_testclient.get('/tasks', headers=headers4ptest_one).json()[0]
    assert task['status'] is None

    task['status'] = TaskStateEnum.PENDING
    response = fastapi_testclient.put(
        '/tasks',
        json=task,
        follow_redirects=True,
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK

    modified_task = Task.model_validate(response.json())
    assert modified_task == task

    # Now invalidate the task by changing the signature
    modified_task.task_input = {
        'something': 'different'
    }
    response = fastapi_testclient.put(
        '/tasks',
        json=modified_task.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Task to be modified could not be found'}

    # And change the reference pipeline to something wrong.
    # This token is valid, but for a different pipeline. It is impossible
    # to have a valid token for a pipeline that does not exist.
    modified_task.pipeline = Pipeline.model_validate({
        'name': 'ptest one thousand'
    })
    response = fastapi_testclient.put(
        '/tasks',
        json=modified_task.model_dump(),
        follow_redirects=True,
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_task_claim(async_minimum, async_tasks, fastapi_testclient):

    response = fastapi_testclient.get(
        '/pipelines/ptest some', headers=headers4ptest_one)
    assert response.status_code == status.HTTP_200_OK

    pipeline = response.json()
    tasks_seen = []

    # Cannot claim with a token issued for a different pipeline.
    response = fastapi_testclient.post(
        '/tasks/claim',
        json=pipeline,
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = fastapi_testclient.post(
        '/tasks/claim',
        json=pipeline,
        headers=headers4ptest_some
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 1, 'Defaults to one task claimed'
    t = tasks[0]
    assert t['task_input'] == {'input': 1}
    assert t['status'] == TaskStateEnum.CLAIMED
    tasks_seen.append(t['task_input_id'])

    response = fastapi_testclient.post(
        '/tasks/claim?num_tasks=0',
        json=pipeline,
        headers=headers4ptest_some
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, 'Not allowed to use invalid numbers of tasks' # noqa: E501

    response = fastapi_testclient.post(
        '/tasks/claim?num_tasks=2',
        json=pipeline,
        headers=headers4ptest_some
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 2, 'Asked for two, got two'
    tasks_seen.extend([t['task_input_id'] for t in tasks])

    # Cannot test race conditions, because sqlite only pretends to support full async
    # Claim the rest
    response = fastapi_testclient.post(
        '/tasks/claim?num_tasks=8',
        json=pipeline,
        headers=headers4ptest_some
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 7, 'Asked for eight, got seven'
    tasks_seen.extend([t['task_input_id'] for t in tasks])
    assert len(set(tasks_seen)) == 10, 'Ten unique tasks were claimed'

    response = fastapi_testclient.post(
        '/tasks/claim',
        json=pipeline,
        headers=headers4ptest_some
    )
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 0, 'Tried to claim, did not get any tasks'

def test_get_tasks(async_minimum, async_tasks, fastapi_testclient):
    response = fastapi_testclient.get('/tasks')
    assert response.status_code == status.HTTP_403_FORBIDDEN, 'Need a token to see any tasks'

    response = fastapi_testclient.get('/tasks', headers=headers4ptest_one)
    assert response.status_code == status.HTTP_200_OK, 'Authorised task fetching'
    tasks = response.json()

    unique_pipelines = {t['pipeline']['name'] for t in tasks}

    assert 'ptest one' in unique_pipelines, 'Tasks for pipeline present with relevant token'
    assert 'ptest some' in unique_pipelines, 'Tasks for other pipelines also present with token'

    response = fastapi_testclient.get(
        '/tasks?pipeline_name=ptest one',
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK, 'One optional argument works'
    tasks = response.json()
    assert len(tasks) == 2, 'Most tasks now filtered'
    assert {t['pipeline']['name'] for t in tasks} == {'ptest one'}, 'All tasks belong to pipeline'

    response = fastapi_testclient.get(
        '/tasks?status=PENDING',
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK, 'Other optional argument works'
    tasks = response.json()
    assert len(tasks) == 10, 'Ten pending tasks selected'

    response = fastapi_testclient.get(
        '/tasks?pipeline_name="ptest one"&status=PENDING',
        headers=headers4ptest_one
    )
    assert response.status_code == status.HTTP_200_OK, 'Both arguments together work'
    print(response.text)
    tasks = response.json()
    assert len(tasks) == 0, 'but no tasks are returned that match status and pipeline'
