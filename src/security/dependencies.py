
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.auth.token_verifier import (
    InvalidAccessTokenError,
    TokenVerificationUnavailableError,
)
from src.security.identity_resolver import (
    IdentityResolver,
    InternalUserNotFoundError,
    NoActiveAccessError,
)
from src.security.principal import AuthenticatedPrincipal

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_principal(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> AuthenticatedPrincipal:
    """
    Authenticate the request and resolve its internal application identity.

    JWT verification is delegated to TokenVerifier.
    Internal identity resolution is delegated to IdentityResolver.
    The database session is supplied by the request-scoped dependency.
    """

    # 1. Require a Bearer token.
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Retrieve the shared verifier initialized during application startup.
    token_verifier = request.app.state.token_verifier

    # 3. Verify the access token.
    try:
        verified_claims = await token_verifier.verify_access_token(
            credentials.credentials
        )

    except InvalidAccessTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    except TokenVerificationUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        ) from exc

    # 4. Obtain the subject from the verified claims.
    keycloak_sub = verified_claims["sub"]

    # 5. Retrieve the shared identity resolver.
    identity_resolver: IdentityResolver = (
        request.app.state.identity_resolver
    )

    # 6. Resolve the internal user and active application access.
    try:
        principal = await identity_resolver.resolve_principal(
            keycloak_sub=keycloak_sub,
            session=session,
        )

    except InternalUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated identity is not registered.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    except NoActiveAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have active application access.",
        ) from exc

    # 7. Return the trusted application identity.
    return principal
