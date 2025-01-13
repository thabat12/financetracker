from db.models import *
from api.api_utils.auth_util import GoogleAuthUserInfo
import random

NUMBERS, LETTERS = [str(i) for i in range(10)], [chr(i) for i in range(ord('a'), ord('z') + 1)]
EMAIL_DOMAINS = ["gmail.com", "googlemail.com"]
PLAID_SANDBOX_INSTITUTION_IDS = [
    "ins_49",  # Chase
    "ins_10",  # Bank of America
    "ins_11",  # Wells Fargo
    "ins_5",   # Citi
    "ins_4",   # PNC
    "ins_12",  # US Bank
    "ins_25",  # Capital One
    "ins_23",  # Chase (Test)
    "ins_24"   # Bank of America (Test)
]

# credit: gpt (we are all going to be replaced by ai, no doubt about it)
def generate_random_mock_google_user():
    # Generate a realistic email (local part up to 64 characters, domain after '@')
    local_part = ''.join(random.choice(LETTERS + NUMBERS) for _ in range(random.randint(5, 64)))
    domain_part = random.choice(EMAIL_DOMAINS)
    generated_email = f"{local_part}@{domain_part}"

    # Generate user info
    new_user = GoogleAuthUserInfo(
        id=''.join(random.choice(NUMBERS) for _ in range(21)),  # Google user IDs are usually 21 digits
        email=generated_email,
        verified_email=random.choice([True, False]),  # Email verification status
        name=' '.join([''.join(random.choice(LETTERS) for _ in range(random.randint(3, 10))) for _ in range(2)]),
        given_name=''.join(random.choice(LETTERS) for _ in range(random.randint(3, 10))),
        family_name=''.join(random.choice(LETTERS) for _ in range(random.randint(3, 10))),
        picture=f"https://randomuser.me/api/portraits/{random.choice(['men', 'women'])}/{random.randint(1, 99)}.jpg",  # Mock profile picture URL
        error=None,  # Leave error fields as None
        error_description=None
    )
    
    return new_user