"""Root pytest configuration — environment variables only.

All test-level fixtures live in their respective subdirectory conftest files:
  - tests/integration/conftest.py  → db, _db
  - tests/api/conftest.py          → client, auth_headers
"""

import os

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("REDIS_URL", "")
os.environ["JWT_SECRET"] = "test-" + "secret-key-for-pytest-32bytes!"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy-key-not-real")
