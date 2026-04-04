"""Tests for shared.helpers.uuid.parse_uuid_str (auth + DB bind boundary)."""
import pytest
from shared.helpers.uuid import parse_uuid_str

def test_parse_uuid_str_accepts_canonical_lowercase():
    u = '0195f2c0-89ab-7a10-8a01-000000000001'
    assert parse_uuid_str('user id', u) == u

def test_parse_uuid_str_rejects_garbage():
    with pytest.raises(ValueError, match='invalid user id'):
        parse_uuid_str('user id', 'not-a-uuid')

def test_parse_uuid_str_strips_whitespace():
    u = '00000000-0000-0000-0000-000000000001'
    assert parse_uuid_str('user id', f'  {u}  ') == u
