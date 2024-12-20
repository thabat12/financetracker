include .env
PG_PASSWORD = $(POSTGRES_PASSWORD)

MODELS_TARGET = models.py

# python environments
download_dependencies: ./api/requirements.txt ./db/requirements.txt
	@cat ./api/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip uninstall -y
	@cat ./api/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip install


# LOCAL TESTING:

# running stuff
run_api:
	@uvicorn api.api:api_app --reload --host $(API_HOST) --port $(API_PORT) --log-level debug

run_test_api:
	@uvicorn api.api:test_app --reload --host $(TEST_API_HOST) --port $(TEST_API_PORT)  --log-level debug

# database migration solution
migrate_db: ./db/models.py
	@alembic -c ./alembic/alembic.ini revision --autogenerate -m "revision"
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

# dockerfile specifics
docker_up:
	@docker-compose -f .\docker\docker-compose.yml --env-file ./.env up