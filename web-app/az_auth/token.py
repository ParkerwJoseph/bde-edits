from dataclasses import dataclass
from jose import jwt, JWTError
from fastapi import HTTPException, status


JWT_DECODE_OPTIONS = {
    "verify_signature": False,
    "verify_aud": False,
    "verify_iat": False,
    "verify_exp": False,
    "verify_nbf": False,
    "verify_iss": False,
    "verify_sub": False,
    "verify_jti": False,
    "verify_at_hash": False,
}


@dataclass
class TokenClaims:
    azure_id: str
    tenant_id: str
    email: str | None
    name: str | None
    preferred_username: str | None


def decode_token(token: str) -> dict:
    """Decode JWT token without verification."""
    try:
        return jwt.decode(token, key="", options=JWT_DECODE_OPTIONS)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


def extract_claims(token: str) -> TokenClaims:
    """Extract user claims from ID token.

    Microsoft Azure AD token claims:
    - oid: Object ID (unique user identifier)
    - tid: Tenant ID
    - email: Email (may not always be present)
    - preferred_username: Usually the UPN (user@domain.com) - most reliable for email
    - name: Display name
    - upn: User Principal Name (alternative to preferred_username)
    """
    try:
        payload = jwt.decode(token, key="", options=JWT_DECODE_OPTIONS)

        azure_id = payload.get("oid") or payload.get("sub")
        tenant_id = payload.get("tid")

        if not azure_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user or tenant identifier",
            )

        # Get email - try multiple claims as Microsoft isn't consistent
        # Priority: email > preferred_username > upn
        email = (
            payload.get("email") or
            payload.get("preferred_username") or
            payload.get("upn")
        )

        return TokenClaims(
            azure_id=azure_id,
            tenant_id=tenant_id,
            email=email,
            name=payload.get("name"),
            preferred_username=payload.get("preferred_username") or payload.get("upn"),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to decode token",
        )
