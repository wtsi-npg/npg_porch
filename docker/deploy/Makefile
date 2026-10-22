IMAGE_NAME ?= npg_porch
TAG        ?= $(shell git describe --always --tags --dirty)
BASE_IMAGE ?= python:3.14-slim
LATEST_TAG ?= latest

APP_UID    ?= 1000
APP_GID    ?= $(APP_UID)
PORT       ?= 8081

ifeq ($(GITHUB_ACTIONS),true)
 DOCKER_REGISTRY ?= ghcr.io
 DOCKER_USER     ?= $(GITHUB_REPOSITORY_OWNER)
else
 DOCKER_REGISTRY ?= docker.io
 DOCKER_USER     ?= wsinpg
endif

DOCKER_PREFIX ?= $(DOCKER_REGISTRY)/$(DOCKER_USER)
DOCKER_ARGS   ?= --progress=plain --rm

now=$(shell date --utc --iso-8601=seconds)

git_url=$(shell git remote get-url origin)
git_commit=$(shell git log --pretty=format:'%H' -n 1)

images := $(addsuffix .$(TAG), $(IMAGE_NAME))
remote := $(addsuffix .$(TAG).pushed, $(IMAGE_NAME))

.PHONY: all push remote-clean clean

all: $(images)

push: $(remote)

npg_porch.$(TAG): Dockerfile
	docker buildx build $(DOCKER_ARGS) \
	--load \
	--build-arg BASE_IMAGE=$(BASE_IMAGE) \
	--build-arg APP_UID=$(APP_UID) \
	--build-arg APP_GID=$(APP_GID) \
	--build-arg PORT=$(PORT) \
	--label org.opencontainers.image.title=$(IMAGE_NAME) \
	--label org.opencontainers.image.source=$(git_url) \
	--label org.opencontainers.image.revision=$(git_commit) \
	--label org.opencontainers.image.version=$(TAG) \
	--label org.opencontainers.image.created=$(now) \
	--label org.opencontainers.image.vendor=npg.sanger.ac.uk \
	--tag $(DOCKER_PREFIX)/$(IMAGE_NAME):$(LATEST_TAG) \
	--tag $(DOCKER_PREFIX)/$(IMAGE_NAME):$(TAG) \
	--file $< ../..
	touch $@

%.$(TAG).pushed: %.$(TAG)
	docker push $(DOCKER_PREFIX)/$*:$(TAG)
	docker push $(DOCKER_PREFIX)/$*:$(LATEST_TAG)
	touch $@

remote-clean:
	rm -f $(remote)

clean:
	rm -f $(foreach image_name,$(IMAGE_NAME), $(image_name)*)
