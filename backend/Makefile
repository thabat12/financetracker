MODELS_TARGET = models.py

download_dependencies: ./api/requirements.txt ./batch/requirements.txt ./db/requirements.txt
	@cat ./api/requirements.txt ./batch/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip uninstall -y
	@cat ./api/requirements.txt ./batch/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip install

test_models:
	@echo "Testing models creation"
	@python -m db.test_models


# TODO: look into uvicorn and how to use it