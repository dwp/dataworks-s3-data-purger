SHELL:=bash

default: help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: bootstrap
bootstrap: ## Bootstrap local environment for first use
	@make git-hooks
	pip install --user pipenv

.PHONY: git-hooks
git-hooks: ## Set up hooks in .githooks
	@git submodule update --init .githooks ; \
	git config core.hooksPath .githooks \

.PHONY: clean
clean:
	rm -rf dist
	rm -rf s3-data-purger.zip

s3-data-purger.zip: clean
	mkdir -p dist
	cp s3_data_purger.py dist
	pipenv install && \
	VENV=$$(pipenv --venv) && \
	cp -rf $${VENV}/lib/python3.7/site-packages/* dist/
	cp -rf docs dist/docs
	cd dist && zip -qr ../$@ .

.PHONY: zip
zip: s3-data-purger.zip
