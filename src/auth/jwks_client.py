
from __future__ import annotations

import asyncio
import time

import httpx
import jwt


class JWKSClientError(Exception):
    """Base exception for JWKS client failures."""


class JWKSUnavailableError(JWKSClientError):
    """Raised when the JWKS endpoint cannot be reached."""


class JWKSInvalidResponseError(JWKSClientError):
    """Raised when the JWKS endpoint returns an invalid response."""


class SigningKeyNotFoundError(JWKSClientError):
    """Raised when the requested signing key is not available."""


class JWKSClient:
    """
    Retrieves and caches trusted RS256 signing keys from a JWKS endpoint.

    The HTTP client is injected and its lifecycle is managed by the caller.
    """

    def __init__(
        self,
        jwks_url: str,
        http_client: httpx.AsyncClient,
        cache_ttl_seconds: int = 300,
        unknown_kid_refresh_interval_seconds: int = 5,
    ) -> None:
        if cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds must be greater than zero")

        if unknown_kid_refresh_interval_seconds < 0:
            raise ValueError(
                "unknown_kid_refresh_interval_seconds cannot be negative"
            )

        self._jwks_url = jwks_url
        self._http_client = http_client
        self._cache_ttl_seconds = cache_ttl_seconds
        self._unknown_kid_refresh_interval_seconds = (
            unknown_kid_refresh_interval_seconds
        )

        self._signing_keys: dict[str, jwt.PyJWK] = {}
        self._cache_expires_at = 0.0
        self._last_unknown_kid_refresh_at = 0.0

        self._refresh_lock = asyncio.Lock()

    async def get_signing_key(self, kid: str) -> jwt.PyJWK:
        """
        Return the trusted signing key matching the supplied key ID.

        Refreshes expired caches and performs a controlled refresh when
        an unknown key ID is encountered.
        """
        if not isinstance(kid, str) or not kid.strip():
            raise SigningKeyNotFoundError("A valid key ID is required")

        async with self._refresh_lock:
            now = time.monotonic()
            cache_is_fresh = now < self._cache_expires_at

            if cache_is_fresh and kid in self._signing_keys:
                return self._signing_keys[kid]

            if cache_is_fresh:
                refresh_cooldown_active = (
                    now - self._last_unknown_kid_refresh_at
                    < self._unknown_kid_refresh_interval_seconds
                )

                if refresh_cooldown_active:
                    raise SigningKeyNotFoundError(
                        f"No trusted signing key found for kid: {kid}"
                    )

                await self._refresh()
                self._last_unknown_kid_refresh_at = time.monotonic()

            else:
                await self._refresh()

            signing_key = self._signing_keys.get(kid)

            if signing_key is None:
                raise SigningKeyNotFoundError(
                    f"No trusted signing key found for kid: {kid}"
                )

            return signing_key

    async def _refresh(self) -> None:
        """Fetch and replace the cached signing keys from JWKS."""
        try:
            response = await self._http_client.get(self._jwks_url)
            response.raise_for_status()
            jwks_document = response.json()

        except (httpx.HTTPError, ValueError) as exc:
            raise JWKSUnavailableError(
                "Unable to retrieve JWKS from the configured endpoint"
            ) from exc

        if not isinstance(jwks_document, dict):
            raise JWKSInvalidResponseError(
                "JWKS response must be a JSON object"
            )

        jwks_keys = jwks_document.get("keys")

        if not isinstance(jwks_keys, list):
            raise JWKSInvalidResponseError(
                "JWKS response does not contain a valid keys array"
            )

        signing_keys: dict[str, jwt.PyJWK] = {}

        for key_data in jwks_keys:
            if not isinstance(key_data, dict):
                continue

            kid = key_data.get("kid")

            if not isinstance(kid, str) or not kid.strip():
                continue

            # RAG01 currently trusts RSA signing keys using RS256 only.
            if key_data.get("kty") != "RSA":
                continue

            if key_data.get("use") not in (None, "sig"):
                continue

            key_ops = key_data.get("key_ops")

            if key_ops is not None and (
                not isinstance(key_ops, list) or "verify" not in key_ops
            ):
                continue

            if key_data.get("alg") not in (None, "RS256"):
                continue

            try:
                signing_keys[kid] = jwt.PyJWK.from_dict(
                    key_data,
                    algorithm="RS256",
                )
            except (jwt.PyJWTError, TypeError, ValueError):
                continue

        if not signing_keys:
            raise JWKSInvalidResponseError(
                "JWKS response contains no usable RS256 signing keys"
            )

        self._signing_keys = signing_keys
        self._cache_expires_at = (
            time.monotonic() + self._cache_ttl_seconds
        )
