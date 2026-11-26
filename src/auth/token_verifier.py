
from __future__ import annotations

import jwt

from src.auth.jwks_client import (
    JWKSClient,
    JWKSInvalidResponseError,
    JWKSUnavailableError,
    SigningKeyNotFoundError,
)


class TokenVerificationError(Exception):
    """Base exception for token verification failures."""


class InvalidAccessTokenError(TokenVerificationError):
    """Raised when an access token is invalid or untrusted."""


class TokenVerificationUnavailableError(TokenVerificationError):
    """Raised when token verification cannot be completed."""


class TokenVerifier:
    """
    Verifies Keycloak access tokens using trusted JWKS signing keys.

    This component validates token authenticity and claims.
    It does not resolve users or perform application authorization.
    """

    def __init__(
        self,
        jwks_client: JWKSClient,
        issuer: str,
        audience: str,
    ) -> None:
        if not issuer.strip():
            raise ValueError("issuer cannot be empty")

        if not audience.strip():
            raise ValueError("audience cannot be empty")

        self._jwks_client = jwks_client
        self._issuer = issuer
        self._audience = audience

    async def verify_access_token(
        self,
        token: str,
    ) -> dict:
        """
        Verify the JWT signature and required claims.

        Returns verified claims only after all checks succeed.
        """
        if not isinstance(token, str) or not token.strip():
            raise InvalidAccessTokenError("Access token is required")

        try:
            # Read the untrusted header to identify the signing key.
            # No claims are trusted at this stage.
            unverified_header = jwt.get_unverified_header(token)

            algorithm = unverified_header.get("alg")
            kid = unverified_header.get("kid")

            # RAG01 accepts only RS256-signed tokens.
            if algorithm != "RS256":
                raise InvalidAccessTokenError(
                    "Unsupported token signing algorithm"
                )

            if not isinstance(kid, str) or not kid.strip():
                raise InvalidAccessTokenError(
                    "Token does not contain a valid key ID"
                )

            # Retrieve the trusted public key matching the token's kid.
            signing_key = await self._jwks_client.get_signing_key(kid)

            # Verify the signature and validate registered claims.
            verified_claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "sub",
                        "iss",
                        "aud",
                    ],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )

            # Require a non-empty subject for internal identity resolution.
            subject = verified_claims.get("sub")

            if not isinstance(subject, str) or not subject.strip():
                raise InvalidAccessTokenError(
                    "Token does not contain a valid subject"
                )

            return verified_claims

        except SigningKeyNotFoundError as exc:
            raise InvalidAccessTokenError(
                "Token signing key is not trusted"
            ) from exc

        except (JWKSUnavailableError, JWKSInvalidResponseError) as exc:
            raise TokenVerificationUnavailableError(
                "Trusted signing keys are currently unavailable"
             ) from exc

        except jwt.InvalidTokenError as exc:
            raise InvalidAccessTokenError(
                "Access token is invalid or expired"
            ) from exc


