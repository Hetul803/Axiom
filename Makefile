.PHONY: test competition-notebook competition-validate competition-smoke startup-backend startup-frontend
setup:
	python -c "import sys; print('Python', sys.version.split()[0])"
test:
	python -m pytest
competition-notebook:
	python competition/build_notebook.py
competition-validate: competition-notebook
	python competition/validate_notebook.py
competition-smoke:
	python competition/offline_smoke_test.py
startup-backend:
	uvicorn startup.backend.main:app --reload
startup-frontend:
	npm install --prefix startup/frontend && npm run dev --prefix startup/frontend
competition-release:
	python competition/build_release.py && python competition/validate_release.py
