MODELS_TARGET = models.py

# python environments
download_dependencies: ./api/requirements.txt ./db/requirements.txt
	@cat ./api/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip uninstall -y
	@cat ./api/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip install

# testing
test_models:
	@echo "Testing models creation"
	@python -m db.test_models

# running stuff
run_api:
	@uvicorn api.api:app --reload --log-level debug

# database migration solution
migrate_db: ./db/models.py
	@alembic -c ./alembic/alembic.ini revision --autogenerate -m "$(shell date +'%Y%m%d_%H%M%S')"
	@alembic -c ./alembic/alembic.ini upgrade head

clear_db_cache:
	@echo "Clearing alembic version files..."
	@rm -r ./alembic/versions
	@mkdir ./alembic/versions
	@python -m db.reset_alembic
	@echo "Alembic version directory cleared and version table reset."

# clearing all data in the database
clear_db:
	@python -m db.init_db

test_api:
	@python -m pytest -v -s