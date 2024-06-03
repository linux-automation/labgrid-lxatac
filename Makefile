PYTHON=python3

PYTHON_ENV_ROOT=envs
PYTHON_QA_ENV=$(PYTHON_ENV_ROOT)/$(PYTHON)-qa-env

# helper ######################################################################
.PHONY: clean envs

clean:
	rm -rf $(PYTHON_ENV_ROOT)

envs: qa-env

# testing #####################################################################
.PHONY: qa qa-env qa-ruff

$(PYTHON_QA_ENV)/.created:
	rm -rf $(PYTHON_QA_ENV) && \
	$(PYTHON) -m venv $(PYTHON_QA_ENV) && \
	. $(PYTHON_QA_ENV)/bin/activate && \
	$(PYTHON) -m pip install pip --upgrade && \
	$(PYTHON) -m pip install ruff && \
	date > $(PYTHON_QA_ENV)/.created

qa-env: $(PYTHON_QA_ENV)/.created

qa: qa-ruff

qa-ruff: qa-env
	. $(PYTHON_QA_ENV)/bin/activate && \
	ruff format --check --diff && ruff check

qa-ruff-fix: qa-env
	. $(PYTHON_QA_ENV)/bin/activate && \
	ruff format && ruff check --fix
