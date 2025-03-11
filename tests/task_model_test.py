from datetime import datetime

from npg_porch.models.task import TaskExpanded, TaskStateEnum
from npg_porch.models import Pipeline


def test_expanded_task_date_format():
    pipeline = Pipeline(
        name="pipeline", version="1.0", uri="file:///team117/test_pipeline"
    )
    task = TaskExpanded(
        pipeline=pipeline,
        created=datetime(2025, 1, 1, 0, 0, 0),
        status=TaskStateEnum.PENDING,
    )
    assert str(task.created) == "2025-01-01 00:00:00"
