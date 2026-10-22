# Deployment Dockerfile

The Dockerfile, Makefile and scripts in this directory build the npg_porch server
image for deployment to Kubernetes. The same image is used for both the dev and prod
environments; the `APP_ENV` environment variable selects between them (see
[Dev and prod environments](#dev-and-prod-environments)).

The image runs the server with `uvicorn` as a non-root user (`apprunner`, UID 1000 by
default) under `tini`, logging to STDOUT and STDERR using `docker/logging.json`.

## Building the image

The build context is the root of the repository. The `.git` directory must be present
in the context because `setuptools-scm` uses it to determine the package version (see
the `.dockerignore` file in the repository root).

To build using the Makefile, run the following from this directory:

```bash
make
```

This tags the image as `<registry>/<user>/npg_porch:<tag>` and
`<registry>/<user>/npg_porch:latest`, where `<tag>` is the output of
`git describe --always --tags --dirty`. By default the registry is `docker.io` and the
user is `wsinpg`; when run in GitHub Actions (`GITHUB_ACTIONS=true`) they are `ghcr.io`
and `GITHUB_REPOSITORY_OWNER`. To push the images:

```bash
make push
```

The Makefile uses GNU `date`, so on macOS you may need to install GNU coreutils or
build with `docker` directly. To build without the Makefile, run the following from
the root of the repository:

```bash
docker build --rm -f docker/deploy/Dockerfile -t npg_porch .
```

### Makefile variables

| Variable          | Default                                 | Description                      |
|-------------------|-----------------------------------------|----------------------------------|
| `IMAGE_NAME`      | `npg_porch`                             | Image name                       |
| `TAG`             | `git describe --always --tags --dirty`  | Image version tag                |
| `LATEST_TAG`      | `latest`                                | Additional floating tag          |
| `BASE_IMAGE`      | `python:3.14-slim`                      | Base image                       |
| `APP_UID`         | `1000`                                  | UID of the application user      |
| `APP_GID`         | `$(APP_UID)`                            | GID of the application user      |
| `PORT`            | `8081`                                  | Port the server listens on       |
| `DOCKER_REGISTRY` | `docker.io` (`ghcr.io` in Actions)      | Registry to tag and push to      |
| `DOCKER_USER`     | `wsinpg` (repo owner in Actions)        | Registry namespace               |
| `DOCKER_ARGS`     | `--progress=plain --rm`                 | Extra arguments to `docker build` |

`make clean` removes the local build stamp files and `make remote-clean` removes the
push stamp files, so that the targets can be re-run.

### Build arguments

| Argument     | Default            | Description                                 |
|--------------|--------------------|---------------------------------------------|
| `BASE_IMAGE` | `python:3.14-slim` | Base image for the build and runtime stages |
| `APP_USER`   | `apprunner`        | Name of the application user                |
| `APP_UID`    | `1000`             | UID of the application user                 |
| `APP_GID`    | `$APP_UID`         | GID of the application user                 |
| `APP_ENV`    | `prod`             | Default run mode (`prod` or `dev`)          |
| `PORT`       | `8081`             | Default port the server listens on          |

## Running the image

The server is configured with the following environment variables:

| Variable       | Required | Description                                                                 |
|----------------|----------|-----------------------------------------------------------------------------|
| `DB_URL`       | Yes      | SQLAlchemy database URL, e.g. `postgresql+asyncpg://user:pass@host:5432/db` |
| `DB_SCHEMA`    | No       | Database schema name                                                        |
| `PORT`         | No       | Port to listen on (default `8081`)                                          |
| `APP_ENV`      | No       | `prod` (default) or `dev`                                                   |
| `ENABLE_TLS`   | No       | `true`, `yes`, `y` or `1` (any case) to serve HTTPS (see [TLS](#tls))       |
| `SSL_KEYFILE`  | No       | TLS private key path when TLS is enabled (default `/certs/tls.key`)         |
| `SSL_CERTFILE` | No       | TLS certificate path when TLS is enabled (default `/certs/tls.crt`)         |

For example:

```bash
docker run --rm -p 8081:8081 \
  -e DB_URL='postgresql+asyncpg://porch_user:password@db.example.com:5432/porch_db' \
  -e DB_SCHEMA=porch \
  npg_porch
```

The database schema must already exist; it can be deployed with
`scripts/deploy_schema.py` from the repository.

### TLS

To enable TLS, mount a certificate and key and set `ENABLE_TLS=true` (`yes`, `y` and
`1` also work, in any case; anything else serves HTTP). The entrypoint script then
passes `--ssl-keyfile` and `--ssl-certfile` to `uvicorn`, using
`/certs/tls.key` and `/certs/tls.crt` unless `SSL_KEYFILE` and `SSL_CERTFILE` say
otherwise. The container exits with an error if either file cannot be read.

```bash
docker run --rm -p 8081:8081 \
  -e DB_URL='postgresql+asyncpg://porch_user:password@db.example.com:5432/porch_db' \
  -e ENABLE_TLS=true \
  -v /path/to/certs:/certs:ro \
  npg_porch
```

In Kubernetes, mount the TLS secret (whose keys are `tls.key` and `tls.crt`) as a
volume at `/certs` and set `ENABLE_TLS` to `"true"` in the container's `env`.

Alternatively, any arguments given to the entrypoint script are passed on to
`uvicorn`, so the `--ssl-*` options can be given directly. Because arguments to
`docker run` replace the image's default command, the script path must then be given
explicitly:

```bash
docker run --rm -p 8081:8081 \
  -e DB_URL='postgresql+asyncpg://porch_user:password@db.example.com:5432/porch_db' \
  -v /path/to/certs:/certs:ro \
  npg_porch \
  /app/docker/deploy/scripts/entrypoint.sh \
    --ssl-keyfile /certs/tls.key \
    --ssl-certfile /certs/tls.crt
```

Do not combine this with `ENABLE_TLS`, or the options are passed twice.

The container health check requests `/api/v1/openapi.json` over HTTPS first and falls
back to HTTP, so it works with or without TLS.

### Dev and prod environments

The same image runs in both environments. The deployment sets `APP_ENV` to choose
how the server starts:

| `APP_ENV`        | Code is loaded from                    | Auto-reload | Use                       |
|------------------|----------------------------------------|-------------|---------------------------|
| `prod` (default) | The installed package in `/app`'s venv | No          | Production service        |
| `dev`            | `/app/src`                             | Yes         | Development and testing   |

**Dev:** the server loads the code from `/app/src` and watches it for changes.
Developers can change the code under `/app/src` in the running dev deployment, for
example with `kubectl exec`, `kubectl cp` or a mounted volume. The server reloads
automatically, so changes can be tried and tested without building a new image.

**Prod:** the server runs the package that was installed when the image was built. It
ignores `/app/src` and does not reload, so changes made inside a running prod container
have no effect. Changes reach prod only through a new image built from this repository
and released through the deployment.

Changes made in a dev pod are lost when the pod restarts. Commit them to this
repository so that they are included in the next image.

To run in dev mode locally, mount a checkout over `/app/src`:

```bash
docker run --rm -p 8081:8081 \
  -e APP_ENV=dev \
  -e DB_URL='postgresql+asyncpg://porch_user:password@db.example.com:5432/porch_db' \
  -v "$PWD/src:/app/src" \
  npg_porch
```

## Publishing

The `Create release` GitHub Actions workflow (`.github/workflows/create-release.yml`)
runs `make` and `make push` in this directory to publish the image to `ghcr.io` when a
release is created from `master`.
