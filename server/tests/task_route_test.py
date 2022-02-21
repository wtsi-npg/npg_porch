from starlette import status

from npg.porch.models import Task, TaskStateEnum

# Not testing get-all-tasks as this method will ultimately go

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
        json=task_one.dict(),
        allow_redirects=True
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert task_one == response.json()

    # Try again and expect to fail
    response = fastapi_testclient.post(
        'tasks',
        json=task_one.dict(),
        allow_redirects=True
    )

    assert response.status_code == status.HTTP_409_CONFLICT

    task_two = Task(
        pipeline = {
            'name': 'ptest none'
        },
        task_input = {
            'number': 1
        }
    )
    response = fastapi_testclient.post(
        'tasks',
        json=task_two.dict(),
        allow_redirects=True
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_task_update(async_minimum, fastapi_testclient):
    task = fastapi_testclient.get('/tasks').json()[0]

    assert task['status'] is None
    task['status'] = TaskStateEnum.PENDING

    response = fastapi_testclient.put(
        '/tasks',
        json=task,
        allow_redirects=True
    )
    assert response.status_code == status.HTTP_200_OK
    modified_task = Task.parse_obj(response.json())

    assert modified_task == task

    # Now invalidate the task by changing the signature
    modified_task.task_input = {
        'something': 'different'
    }

    response = fastapi_testclient.put(
        '/tasks',
        json=modified_task.dict(),
        allow_redirects=True
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Task to be modified could not be found'}

    # And change the reference pipeline to something wrong
    modified_task.pipeline = {
        'name': 'ptest one thousand'
    }

    response = fastapi_testclient.put(
        '/tasks',
        json=modified_task.dict(),
        allow_redirects=True
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Pipeline not found'}

def test_task_claim(async_tasks, fastapi_testclient):
    response = fastapi_testclient.get('/pipelines/ptest one')

    assert response.status_code == status.HTTP_200_OK
    pipeline = response.json()

    tasks_seen = []

    response = fastapi_testclient.post('/tasks/claim', json=pipeline)
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()

    assert len(tasks) == 1, 'Defaults to one task claimed'
    t = tasks[0]
    assert t['task_input'] == {'input': 1}
    assert t['status'] == TaskStateEnum.CLAIMED
    tasks_seen.append(t['task_input_id'])

    response = fastapi_testclient.post('/tasks/claim?num_tasks=0', json=pipeline)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, 'Not allowed to use invalid numbers of tasks'

    response = fastapi_testclient.post('/tasks/claim?num_tasks=2', json=pipeline)
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 2, 'Asked for two, got two'
    tasks_seen.extend([t['task_input_id'] for t in tasks])

    # Cannot test race conditions, because sqlite only pretends to support full async
    # Claim the rest
    response = fastapi_testclient.post('/tasks/claim?num_tasks=8', json=pipeline)
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 7, 'Asked for eight, got seven'
    tasks_seen.extend([t['task_input_id'] for t in tasks])

    assert len(set(tasks_seen)) == 10, 'Ten unique tasks were claimed'

    response = fastapi_testclient.post('/tasks/claim', json=pipeline)
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert len(tasks) == 0, 'Tried to claim, did not get any tasks'
