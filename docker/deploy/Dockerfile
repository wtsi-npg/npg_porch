ARG BASE_IMAGE=python:3.14-slim
ARG DEBIAN_FRONTEND="noninteractive"

FROM $BASE_IMAGE AS builder

ARG DEBIAN_FRONTEND

RUN apt-get update && \
    apt-get install -q -y --no-install-recommends \
    build-essential \
    git

WORKDIR /app

COPY . .

RUN python -m venv /app && \
    . ./bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

FROM $BASE_IMAGE

ARG DEBIAN_FRONTEND

RUN apt-get update && \
    apt-get install -q -y --no-install-recommends \
    ca-certificates \
    curl \
    locales \
    tini \
    procps \
    unattended-upgrades && \
    unattended-upgrade -v && \
    locale-gen en_GB en_GB.UTF-8 && \
    localedef -i en_GB -c -f UTF-8 -A /usr/share/locale/locale.alias en_GB.UTF-8 && \
    apt-get remove -q -y unattended-upgrades && \
    apt-get autoremove -q -y && \
    apt-get clean -q -y && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=en_GB.UTF-8 \
    LANGUAGE=en_GB \
    LC_ALL=en_GB.UTF-8 \
    TZ="Etc/UTC"

ARG APP_USER=apprunner
ARG APP_UID=1000
ARG APP_GID=$APP_UID

WORKDIR /app

RUN groupadd --gid $APP_GID $APP_USER && \
    useradd --uid $APP_UID --gid $APP_GID --shell /bin/bash --create-home $APP_USER

COPY --from=builder /app /app
RUN chown -R $APP_USER:$APP_GID /app/src

USER $APP_USER

ARG APP_ENV=prod
ENV APP_ENV=${APP_ENV}

ARG PORT=8081
ENV PORT=${PORT}

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -fsk https://localhost:${PORT}/api/v1/openapi.json -o /dev/null || \
        curl -fs http://localhost:${PORT}/api/v1/openapi.json -o /dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["/app/docker/deploy/scripts/entrypoint.sh"]
