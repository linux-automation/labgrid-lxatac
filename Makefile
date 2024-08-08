PYTHON=python3

PYTHON_ENV_ROOT=envs
PYTHON_QA_ENV=$(PYTHON_ENV_ROOT)/$(PYTHON)-qa-env

# helper ######################################################################
.PHONY: clean envs

clean:
	rm -rf $(PYTHON_ENV_ROOT)

envs: qa-env

# testing #####################################################################
.PHONY: qa qa-env qa-ruff qa-codespell qa-codespell-fix qa-ruff-fix-codespell qa-codespell-fix qa-ruff-fix

$(PYTHON_QA_ENV)/.created:
	rm -rf $(PYTHON_QA_ENV) && \
	$(PYTHON) -m venv $(PYTHON_QA_ENV) && \
	. $(PYTHON_QA_ENV)/bin/activate && \
	$(PYTHON) -m pip install pip --upgrade && \
	$(PYTHON) -m pip install ruff codespell && \
	date > $(PYTHON_QA_ENV)/.created

qa-env: $(PYTHON_QA_ENV)/.created

qa: qa-ruff qa-codespell

qa-ruff: qa-env
	. $(PYTHON_QA_ENV)/bin/activate && \
	ruff format --check --diff && ruff check

qa-ruff-fix: qa-env
	. $(PYTHON_QA_ENV)/bin/activate && \
	ruff format && ruff check --fix

qa-codespell: qa-env
	. $(PYTHON_QA_ENV)/bin/activate && \
	codespell

qa-codespell-fix: qa-env
	. $(PYTHON_QA_ENV)/bin/activate && \
	codespell -w
