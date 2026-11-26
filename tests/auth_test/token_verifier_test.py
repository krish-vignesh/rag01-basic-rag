
from __future__ import annotations

import base64
import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from src.auth.jwks_client import JWKSClient
from src.auth.token_verifier import (
    InvalidAccessTokenError,
    TokenVerificationUnavailableError,
    TokenVerifier,
)

ISSUER = "http://localhost:8080/realms/rag01"
AUDIENCE = "rag01-api"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"
KEY_ID = "test-key-1"


@pytest.fixture
def rsa_key_pair():
    """Generate a real RSA private/public key pair for JWT tests."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    return private_key, private_key.public_key()


@pytest.fixture
def rsa_jwk(rsa_key_pair):
    """Convert the RSA public key into a JWKS-compatible document."""
    _, public_key = rsa_key_pair

    jwk_document = json.loads(
        jwt.algorithms.RSAAlgorithm.to_jwk(public_key)
    )

    jwk_document.update(
        {
            "kid": KEY_ID,
            "use": "sig",
            "alg": "RS256",
        }
    )

    return jwk_document


@pytest.fixture
def mock_http_client(rsa_jwk):
    """Mock the Keycloak JWKS endpoint without making network requests."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == JWKS_URL

        return httpx.Response(
            status_code=200,
            json={"keys": [rsa_jwk]},
        )

    transport = httpx.MockTransport(handler)

    return httpx.AsyncClient(transport=transport)


@pytest.fixture
def jwks_client(mock_http_client):
    """Create the actual JWKS client with mocked HTTP."""

    return JWKSClient(
        jwks_url=JWKS_URL,
        http_client=mock_http_client,
        cache_ttl_seconds=300,
        unknown_kid_refresh_interval_seconds=0,
    )


@pytest.fixture
def token_verifier(jwks_client):
    """Create the actual token verifier."""

    return TokenVerifier(
        jwks_client=jwks_client,
        issuer=ISSUER,
        audience=AUDIENCE,
    )


@pytest.fixture
def valid_token(rsa_key_pair):
    """Create a valid RS256-signed access-token-shaped JWT."""
    private_key, _ = rsa_key_pair
    now = int(time.time())

    payload = {
        "sub": "test-user-123",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
    }

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )


@pytest.mark.asyncio
async def test_verify_valid_token_returns_verified_claims(
    token_verifier,
    valid_token,
):
    claims = await token_verifier.verify_access_token(valid_token)

    assert claims["sub"] == "test-user-123"
    assert claims["iss"] == ISSUER
    assert claims["aud"] == AUDIENCE


@pytest.mark.asyncio
async def test_rejects_token_with_modified_payload(
    token_verifier,
    valid_token,
):
    """Changing the payload without resigning must invalidate the signature."""
    header, payload, signature = valid_token.split(".")

    modified_payload = json.loads(
        base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    )
    modified_payload["sub"] = "attacker-user"

    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(modified_payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()

    tampered_token = f"{header}.{encoded_payload}.{signature}"

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(tampered_token)


@pytest.mark.asyncio
async def test_rejects_token_signed_with_different_private_key(
    token_verifier,
):
    """A token signed by an untrusted private key must fail verification."""
    different_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    now = int(time.time())

    payload = {
        "sub": "test-user-123",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
    }

    token = jwt.encode(
        payload,
        different_private_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_unsupported_algorithm(
    token_verifier,
):
    """The verifier must reject algorithms other than RS256."""
    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        "test-secret-key-for-rag01-testing-32-bytes",
        algorithm="HS256",
        headers={"kid": KEY_ID},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_wrong_issuer(
    token_verifier,
    rsa_key_pair,
):
    private_key, _ = rsa_key_pair
    now = int(time.time())

    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": "http://untrusted-issuer",
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_wrong_audience(
    token_verifier,
    rsa_key_pair,
):
    private_key, _ = rsa_key_pair
    now = int(time.time())

    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": ISSUER,
            "aud": "another-api",
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_expired_token(
    token_verifier,
    rsa_key_pair,
):
    private_key, _ = rsa_key_pair
    now = int(time.time())

    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now - 600,
            "exp": now - 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_token_with_future_not_before(
    token_verifier,
    rsa_key_pair,
):
    private_key, _ = rsa_key_pair
    now = int(time.time())

    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "nbf": now + 300,
            "exp": now + 600,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_token_missing_required_claim(
    token_verifier,
    rsa_key_pair,
):
    private_key, _ = rsa_key_pair
    now = int(time.time())

    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            # exp is intentionally missing.
        },
        private_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_token_without_kid(
    token_verifier,
    rsa_key_pair,
):
    private_key, _ = rsa_key_pair
    now = int(time.time())

    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_rejects_token_with_unknown_kid(
    token_verifier,
    rsa_key_pair,
):
    private_key, _ = rsa_key_pair
    now = int(time.time())

    token = jwt.encode(
        {
            "sub": "test-user-123",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "unknown-key"},
    )

    with pytest.raises(InvalidAccessTokenError):
        await token_verifier.verify_access_token(token)


@pytest.mark.asyncio
async def test_jwks_unavailable_raises_verification_unavailable():
    """A JWKS network failure must not be treated as a valid token."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=503)

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        unavailable_jwks_client = JWKSClient(
            jwks_url=JWKS_URL,
            http_client=http_client,
        )

        verifier = TokenVerifier(
            jwks_client=unavailable_jwks_client,
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        # The token only needs a readable header and kid here.
        # JWKS retrieval fails before signature verification.
        token = jwt.encode(
            {
                "sub": "test-user-123",
                "iss": ISSUER,
                "aud": AUDIENCE,
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            },
            "test-secret",
            algorithm="HS256",
            headers={"kid": KEY_ID},
        )

        # The verifier rejects HS256 before making the JWKS request.
        # Therefore, use a correctly shaped RS256 token with a test key.
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        token = jwt.encode(
            {
                "sub": "test-user-123",
                "iss": ISSUER,
                "aud": AUDIENCE,
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": KEY_ID},
        )

        with pytest.raises(TokenVerificationUnavailableError):
            await verifier.verify_access_token(token)
