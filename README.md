# FastAPI Server for Pipeline Orchestration Project

## What is it?

npg_porch is an OpenAPI web service and database schema that can be used for managing invocations of pipelines. The user of the pipeline provides definitions for how the pipeline will be invoked, a pipeline wrapper that can interpret the definitions, and whatever mechanism needed to initiate the pipeline with a job scheduler such as LSF or WR. npg_porch provides tracking for pipeline invocations in the same way that a workflow engine might track jobs

npg_porch's singular purpose is to ensure that pipelines are run once and only once for each definition of work. The requirements and software used by the Institute's faculty are so diverse that no single product can provide for tracking, scheduling and execution of pipelines. npg_porch handles the tracking element without restricting any other aspect of workflow use.

[User documentation](./docs/user_guide.md)

## Principles to consider

npg_porch does not:

- understand the pipelines
- store any pipeline data beyond that necessary to ensure idempotency of pipeline runs
- run your jobs for you
- provide deep insight into how each pipeline is running

npg_porch does:

- provide a central system to register new work
- enforce uniqueness of work to prevent replication of effort
- allow for re-running of pipelines
- store messages from pipeline wrappers that may help in failure diagnosis

## Requirements

Python >= 3.7
sqlite3 >= 3.9

## Installation & Usage

To run the server, please execute the following from the root directory:

```bash
bash
pip3 install -e .
cd server
mkdir -p logs
export DB_URL=postgresql+asyncpg://npg_rw:$PASS@npg_porch_db:$PORT/$DATABASE
export DB_SCHEMA='non_default'
uvicorn main:app --host 0.0.0.0 --port 8080 --reload --log-config logging.json
```

and open your browser at `http://localhost:8080` to see links to the docs.

The server will not start without `DB_URL` in the environment

## Testing

```bash
export NPG_PORCH_MODE=TEST
# Only do this as needed
pip install -e .[test]
pytest
```

Individual tests are run in the form `pytest server/tests/init_test.py`

### Fixtures

Fixtures reside under `server/tests/fixtures` and are registered in `server/tests/conftest.py`
They can also be listed by invoking `pytest --fixtures`

Any fixtures that are not imported in `conftest.py` will not be detected.

## Deployment of schema from ORM

Create a schema on a postgres server:

```bash
psql --host=npg_porch_db --port=$PORT --username=npg_admin --password -d postgres

CREATE SCHEMA npg_porch
```

Then run a script that deploys the ORM to this schema

```bash
DB=npg_porch
export DB_URL=postgresql+psycopg2://npg_admin:$PASS@npg_porch_db:$PORT/$DB
# note that the script requires a regular PG driver, not the async version showed above
server/deploy_schema.py

psql --host=npg_porch_db --port=$PORT --username=npg_admin --password -d $DB
```

Permissions must be granted to the npg_rw and npg_ro users to the newly created schema

```sql
GRANT USAGE ON SCHEMA npg_porch TO npgtest_ro, npgtest_rw;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA npg_porch TO npgtest_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA npg_porch TO npgtest_ro;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA npg_porch TO npgtest_rw;
```

Note that granting usage on sequences is required to allow autoincrement columns to work during an insert. This is a trick of newer Postgres versions.

It may prove necessary to `GRANT` to specific named tables and sequences. Under specific circumstances the `ALL TABLES` qualifier doesn't work.

Until token support is implemented, a row will need to be inserted manually into the token table. Otherwise none of the event logging works.
