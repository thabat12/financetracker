"""
    The API only updates user data as soon as a user links to their Plaid account, but after that
    link, there is no other way to update the Plaid account other than running batch scripts / cron
    jobs on the user data. So that is why you have to do these cron jobs to update data and yeah it
    kinda sucks but there are also benefits like async updating.
"""
import json

from api.api_utils.data_util import db_update_all_data_asynchronously
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


def update_all_user_data_lambda_handler(event, context):
    print("event:", json.dumps(event, indent=4))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello from lambda!",
            "input": event
        })
    }