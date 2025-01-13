#####################
# LOCAL ENVIRONMENT #
#####################

# python installations
download_dependencies: ./api/requirements.txt ./db/requirements.txt
	@cat ./api/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip uninstall -y
	@cat ./api/requirements.txt ./db/requirements.txt | sort | uniq | xargs pip install

# running the api
run_api:
	@python -m api.main api.api:api_app --log-level debug --env_file $(ENV)

run_test_api:
	@python -m api.main api.api:test_app --log-level debug --env_file $(ENV)

# testing the api with client
test_api:
	@python -m tests.main -v --env-file $(ENV)

# database migration solution
migrate_db: ./db/models.py
	@alembic -c ./alembic/alembic.ini revision --autogenerate -m "revision"
	@alembic -c ./alembic/alembic.ini upgrade head

clear_db_cache:
	@echo "Clearing alembic version files..."
	@chmod 777 ./alembic/versions/*
	@python -m db.reset_alembic
	@echo "Alembic version directory cleared and version table reset."

# clearing all data in the database
setup_db:
	@python -m db.setup_db --env_file $(ENV)

#####################
## DEV ENVIRONMENT ##
#####################

# dockerfile specifics
docker_build_dev:
	@docker-compose -f .\docker\dev\docker-compose.yml --env-file ./envs/dev.env --project-directory . build

docker_up_dev:
	@docker-compose -f .\docker\dev\docker-compose.yml --env-file ./envs/dev.env --project-directory . up