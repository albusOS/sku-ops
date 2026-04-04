"""Shared auth helpers for tests."""
import time
import jwt
from shared.infrastructure.config import JWT_ALGORITHM, JWT_SECRET
from shared.kernel.constants import DEFAULT_ORG_ID
ADMIN_USER_ID = '0195f2c0-89ab-7a10-8a01-000000000001'
CONTRACTOR_USER_ID = '0195f2c0-89ab-7a10-8a01-000000000003'
BCRYPT_USER_ID = '0195f2c0-89ab-7a10-8a01-000000000004'
SEEDED_DEPT_ID = '0195f2c0-89ac-7f42-8b11-000000000001'
SEEDED_JOB_ID = '019d44b8-a763-757a-9d68-a576ca2044c3'
SEEDED_VENDOR_ID = '019d44b8-a75b-70ec-908b-56d412a7f883'

def make_token(user_id: str=ADMIN_USER_ID, org_id: str=DEFAULT_ORG_ID, role: str='admin', name: str='Test User', email: str='', expired: bool=False) -> str:
    payload = {'sub': user_id, 'email': email or f'{user_id}@test.com', 'role': 'authenticated', 'app_metadata': {'role': role}, 'user_metadata': {'name': name}, 'exp': int(time.time()) + (-3600 if expired else 3600)}
    if org_id:
        payload['app_metadata']['organization_id'] = org_id
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def admin_headers() -> dict[str, str]:
    token = make_token(ADMIN_USER_ID, role='admin', email='admin@supplyyard.com')
    return {'Authorization': f'Bearer {token}'}

def contractor_headers() -> dict[str, str]:
    token = make_token(CONTRACTOR_USER_ID, role='contractor', name='Sarah Okafor', email='sarah@summitpm.com')
    return {'Authorization': f'Bearer {token}'}

def admin_token() -> str:
    return make_token(ADMIN_USER_ID, role='admin', email='admin@supplyyard.com')

def contractor_token() -> str:
    return make_token(CONTRACTOR_USER_ID, role='contractor', email='sarah@summitpm.com')

def expired_token() -> str:
    return make_token(expired=True)
