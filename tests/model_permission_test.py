import pytest

from npg.porch.models.pipeline import Pipeline
from npg.porch.models.permission import Permission, PermissionValidationException
from pydantic import ValidationError


def test_model_create():
    ''''
    Test objects can be created.
    '''

    p = Permission(requestor_id = 3, role = 'power_user')
    assert type(p) is Permission
    p = Permission(
        requestor_id = 1,
        role = 'regular_user',
        pipeline = Pipeline(name='number one')
    )
    assert type(p) is Permission


def test_xvalidation_role_pipeline():
    '''
    Test cross validation for the role and pipeline fields.
    '''

    with pytest.raises(
            ValidationError,
            match = r'Power user cannot be associated with a pipeline'):
        Permission(
            requestor_id = 3,
            role = 'power_user',
            pipeline = Pipeline(name='number one')
        )


def test_error_with_insufficient_args():

    with pytest.raises(ValidationError, match=r'requestor_id\s+Field required'):
        Permission(
            role = 'regular_user',
            pipeline = Pipeline(name='number one')
        )
    with pytest.raises(ValidationError, match=r'role\s+Field required'):
        Permission(
            requestor_id = 1,
            pipeline = Pipeline(name='number one')
        )


def test_pipeline_validation():

    pipeline = Pipeline(name='number one')
    permission = Permission(
        requestor_id = 3,
        role = 'power_user')
    with pytest.raises(PermissionValidationException,
                       match=r'Operation is not valid for role power_user'):
        permission.validate_pipeline(pipeline)

    permission = Permission(
        requestor_id = 3,
        role = 'regular_user')
    with pytest.raises(PermissionValidationException,
                       match=r'No associated pipeline object'):
        permission.validate_pipeline(pipeline)

    permission = Permission(
        requestor_id = 3,
        role = 'regular_user',
        pipeline = Pipeline(name='number two'))
    with pytest.raises(
            PermissionValidationException, match
            =r"Token-request pipeline mismatch: 'number two' and 'number one'"):
        permission.validate_pipeline(pipeline)

    permission = Permission(
        requestor_id = 3,
        role = 'regular_user',
        pipeline = pipeline)
    assert (permission.validate_pipeline(pipeline) is None), 'no error'
