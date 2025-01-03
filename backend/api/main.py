"""
    Running uvicorn programatically to deal with different development environments.
    Different environments require different configuration files, and at the momment
    we are just going to be using different .env files for that reason.
"""
import argparse
import uvicorn

from settings import set_global_settings

def main():
    parser = argparse.ArgumentParser(
        prog="Financetracker API",
        description="Run the Financetracker API",
    )
    parser.add_argument("api_app", type=str, help="The FastAPI app to run")
    parser.add_argument("--reload", action="store_true", help="Run the server in development mode")
    parser.add_argument("--log-level", type=str, default="debug", help="The log level to run the server on")
    parser.add_argument("--env_file", type=str, help="The .env file to use for deployment")
    args = parser.parse_args()
    set_global_settings(args.env_file)
    
    from settings import settings

    uvicorn_args = {}
    uvicorn_args["app"] = args.api_app
    uvicorn_args["reload"] = args.reload
    uvicorn_args["log_level"] = args.log_level
    uvicorn_args["port"] = settings.api_port
    uvicorn_args["host"] = settings.api_host

    uvicorn.run(**uvicorn_args)


if __name__ == "__main__":
    main()