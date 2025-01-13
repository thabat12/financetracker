"""
This file is used to run the tests in the tests folder. Test are +

"""
import argparse
import pytest

from settings import set_global_settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Financetracker Test Client",
        description="Run the Financetracker Test Client",
    )

    parser.add_argument("-v", action="store_true", help="Run the tests in verbose mode")
    parser.add_argument("--rootdir", type=str, default="./tests", help="The root directory to run the tests from")
    parser.add_argument("--env-file", type=str, help="The .env file to use for deployment")
    args = parser.parse_args()
    set_global_settings(args.env_file)

    pytest_args = []
    if args.v:
        pytest_args.append("-v")
    pytest_args.append(f"--rootdir={args.rootdir}")

    result = pytest.main(pytest_args)