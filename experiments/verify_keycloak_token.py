import sys

import jwt
from jwt import InvalidTokenError
from jwt.exceptions import PyJWKClientError

ISSUER = "http://localhost:8080/realms/rag01"
AUDIENCE = "rag01-api"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"
ALGORITHM = "RS256"


def verify_access_token(token: str) -> dict:
    """
    Verify a Keycloak access token using the realm's public JWKS key.
    """

    jwks_client = jwt.PyJWKClient(JWKS_URL)

    # Select the signing key matching the token's kid header.
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    # Verify signature and standard token claims.
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={
            "require": ["exp", "iat", "sub", "iss", "aud"],
        },
    )

    return claims


def main():
    print("\nRAG01 - Keycloak JWT Verification")
    print("----------------------------------")
    print(f"Issuer:   {ISSUER}")
    print(f"Audience: {AUDIENCE}")
    print(f"JWKS:     {JWKS_URL}")

    token = input("\nPaste your ACCESS TOKEN: ").strip()

    if not token:
        print("\nFAIL: No token provided.")
        sys.exit(1)

    try:
        claims = verify_access_token(token)

        print("\nPASS: Token signature and claims verified.")
        print("\nVerified claims:")
        print(f"Issuer:   {claims['iss']}")
        print(f"Audience: {claims['aud']}")
        print(f"Expires:  {claims['exp']}")
        print(f"Issued:   {claims['iat']}")
        print("Subject:  Present (user identifier not displayed)")

    except PyJWKClientError as exc:
        print(f"\nFAIL: Could not retrieve or select the JWKS signing key: {exc}")
        sys.exit(1)

    except InvalidTokenError as exc:
        print(f"\nFAIL: Token verification failed: {exc}")
        sys.exit(1)

    except Exception as exc:  # noqa: BLE001
        print(f"\nFAIL: Unexpected error: {type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
