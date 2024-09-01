import httpx
import asyncio

from db.config import Config

plaid_url = Config.TEST_PLAID_URL


async def get_ins_data():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{plaid_url}/institutions/get',
            json={
                "client_id": Config.TEST_PLAID_CLIENT_ID,
                "secret": Config.PLAID_SECRET,
                "count": 200,
                "offset": 0,
                "country_codes": ["US"],
                "options": {
                    "include_optional_metadata": True
                }
            }
        )

        resp = resp.json()

        print(resp)

asyncio.run(get_ins_data())
    