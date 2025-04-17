# Change Log for npg_porch Project

The format is based on [Keep a Changelog](http://keepachangelog.com/).
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

## [2.1.3]

### Added

* Pipeline selection dropdown to change listing view.

### Changed

* Improve endpoint tagging for documentation.
* Initially order listing by status date.
* Only show current pipelines.

## [2.1.2] - 2025-03-13

### Added

* Display date of last status change for tasks shown on the ui.

### Changed

* Improve datetime formatting backend.
* Improve display of task_input json to allow line wrapping.

## [2.1.1] - 2025-03-11

### Changed

* Format of Date Created provided to ui.

### Removed

* Unnecessary database access from index page.

## [2.1.0] - 2025-03-07

### Added

* A Simple Webpage displaying a listing of all tasks.

### Changed

* Remove authorisation requirement for get requests.
* Make TaskStateEnum and RolesEnum stringify to their values and use actual 
  enum values rather than expected values in tests.

## [2.0.0] - 2024-07-31

### Added

* A note about installing on macOS
* An endpoint for creating pipeline tokens
* A development Docker file
* A Token model

### Changed

* Moved the project to the standard Python project layout.
* Reorganised and renamed the modules:
    1. `npg.porch` namespace is collapsed into `npg_porch`,
    2. `npg.porchdb` is reorganised into `npg_porch.db`,
    3. the entry point of the application is relocated and
    renamed `npg/porch_server.py` -> `npg_porch/server.py`
* Moved the test configuration file to the `tests` directory.
* Changed the HTTP code for the `pipeline` endpoint from 409 to 422 in case of
  bad input.
* A Token model is returned rather than a bare string by the endpoint which
creates tokens for a pipeline.
* A request to create an already existing task is no longer invalid, does not
raise an error.
* Updated the Task model so that it is impossible to create or update the task
  without explicitly specifying the new task status.
* pysqlite3 is moved from the production to test dependencies.

## [1.0.0] - 2023-10-16

Initial release
