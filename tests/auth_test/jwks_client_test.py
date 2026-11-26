
import json

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from src.auth.jwks_client import (
    JWKSClient,
    JWKSInvalidResponseError,
    JWKSUnavailableError,
    SigningKeyNotFoundError,
)

JWKS_URL = "https://keycloak.test/realms/rag01/protocol/openid-connect/certs"


# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------


@pytest.fixture
def rsa_jwk():
    """Generate a realistic RSA public JWK for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    public_key = private_key.public_key()

    jwk = json.loads(
        jwt.algorithms.RSAAlgorithm.to_jwk(public_key)
    )

    jwk.update(
        {
            "kid": "test-key-1",
            "use": "sig",
            "alg": "RS256",
        }
    )

    return jwk


@pytest.fixture
def mock_jwks(rsa_jwk):
    """Provide a JWKS document containing one valid signing key."""
    return {"keys": [rsa_jwk]}


@pytest.fixture
def jwks_responses(mock_jwks):
    """Allow individual tests to control successive JWKS responses."""
    return [mock_jwks]


@pytest.fixture
def request_count():
    """Track how many HTTP requests reach the mocked endpoint."""
    return {"count": 0}


@pytest.fixture
async def mock_http_client(jwks_responses, request_count):
    """Create an asynchronous HTTP client with a mocked JWKS endpoint."""

    async def handler(request: httpx.Request) -> httpx.Response:
        request_count["count"] += 1

        response_index = min(
            request_count["count"] - 1,
            len(jwks_responses) - 1,
        )

        response_data = jwks_responses[response_index]

        if isinstance(response_data, httpx.Response):
            return response_data

        return httpx.Response(
            status_code=200,
            json=response_data,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
        timeout=5.0,
    ) as client:
        yield client


@pytest.fixture
def jwks_client(mock_http_client):
    """Create the actual JWKSClient using mocked HTTP."""
    return JWKSClient(
        jwks_url=JWKS_URL,
        http_client=mock_http_client,
        cache_ttl_seconds=300,
        unknown_kid_refresh_interval_seconds=0,
    )


# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_valid_signing_key(
    jwks_client,
    request_count,
):
    """A valid JWKS response should provide the requested key."""

    signing_key = await jwks_client.get_signing_key("test-key-1")

    assert isinstance(signing_key, jwt.PyJWK)
    assert signing_key.key_id == "test-key-1"
    assert signing_key.algorithm_name == "RS256"
    assert request_count["count"] == 1


@pytest.mark.asyncio
async def test_reuse_cached_signing_key(
    jwks_client,
    request_count,
):
    """A second request should reuse the cached key."""

    first_key = await jwks_client.get_signing_key("test-key-1")
    second_key = await jwks_client.get_signing_key("test-key-1")

    assert first_key is second_key
    assert request_count["count"] == 1


@pytest.mark.asyncio
async def test_refresh_expired_cache(
    jwks_client,
    request_count,
    monkeypatch,
):
    """An expired cache should trigger a fresh JWKS request."""

    import src.auth.jwks_client as jwks_module

    clock = {"now": 100.0}

    monkeypatch.setattr(
        jwks_module.time,
        "monotonic",
        lambda: clock["now"],
    )

    await jwks_client.get_signing_key("test-key-1")

    assert request_count["count"] == 1

    # Move beyond the 300-second cache lifetime.
    clock["now"] = 401.0

    await jwks_client.get_signing_key("test-key-1")

    assert request_count["count"] == 2


@pytest.mark.asyncio
async def test_refresh_when_unknown_kid_appears(
    jwks_client,
    jwks_responses,
    rsa_jwk,
    request_count,
):
    """An unknown kid should trigger a refresh."""

    await jwks_client.get_signing_key("test-key-1")

    new_jwk = dict(rsa_jwk)
    new_jwk["kid"] = "test-key-2"

    jwks_responses.append(
        {
            "keys": [rsa_jwk, new_jwk],
        }
    )

    new_key = await jwks_client.get_signing_key("test-key-2")

    assert isinstance(new_key, jwt.PyJWK)
    assert new_key.key_id == "test-key-2"
    assert request_count["count"] == 2


@pytest.mark.asyncio
async def test_reject_unknown_kid(
    jwks_client,
    request_count,
):
    """An unavailable key ID must be rejected."""

    with pytest.raises(SigningKeyNotFoundError):
        await jwks_client.get_signing_key("unknown-key")

    assert request_count["count"] == 1



@pytest.mark.asyncio
async def test_jwks_endpoint_returns_http_error():
    """An unsuccessful HTTP response must fail safely."""

    async def handler(request):
        return httpx.Response(503)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:

        client = JWKSClient(
            jwks_url=JWKS_URL,
            http_client=http_client,
        )

        with pytest.raises(JWKSUnavailableError):
            await client.get_signing_key("test-key-1")


@pytest.mark.asyncio
async def test_jwks_endpoint_returns_invalid_json():
    """Invalid JSON must raise JWKSUnavailableError."""

    async def handler(request):
        return httpx.Response(
            200,
            content=b"this-is-not-valid-json",
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:

        client = JWKSClient(
            jwks_url=JWKS_URL,
            http_client=http_client,
        )

        with pytest.raises(JWKSUnavailableError):
            await client.get_signing_key("test-key-1")


@pytest.mark.asyncio
async def test_reject_jwks_without_keys():
    """A JWKS response without a keys array is invalid."""

    async def handler(request):
        return httpx.Response(
            200,
            json={"unexpected": []},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:

        client = JWKSClient(
            jwks_url=JWKS_URL,
            http_client=http_client,
        )

        with pytest.raises(JWKSInvalidResponseError):
            await client.get_signing_key("test-key-1")


@pytest.mark.asyncio
async def test_reject_jwks_without_usable_signing_keys(
    rsa_jwk,
):
    """Non-signing and unsupported algorithm keys must be ignored."""

    unsuitable_key = dict(rsa_jwk)
    unsuitable_key["alg"] = "RS512"

    async def handler(request):
        return httpx.Response(
            200,
            json={"keys": [unsuitable_key]},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:

        client = JWKSClient(
            jwks_url=JWKS_URL,
            http_client=http_client,
        )

        with pytest.raises(JWKSInvalidResponseError):
            await client.get_signing_key("test-key-1")
