"""
Pasok — short-term Bedrock bearer token

Bedrock Mantle (bedrock-mantle.<region>.api.aws) accepts a short-term Bedrock API key
as a bearer token. The token is a SigV4-presigned Bedrock request, base64-encoded.

This mirrors AWS's aws_bedrock_token_generator, using botocore (bundled with the AWS
Lambda Python runtime).
"""
from __future__ import annotations

import base64
import os

SERVICE = "bedrock"
HOST = "bedrock.amazonaws.com"
AUTH_PREFIX = "bedrock-api-key-"
TOKEN_VERSION = "&Version=1"
DEFAULT_EXPIRES = 43200  # 12 hours


def generate_bedrock_token(access_key: str, secret_key: str, region: str,
                           session_token: str | None = None,
                           expires: int = DEFAULT_EXPIRES) -> str:
    from botocore.auth import SigV4QueryAuth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials

    creds = Credentials(access_key=access_key, secret_key=secret_key,
                        token=session_token) if session_token else \
        Credentials(access_key=access_key, secret_key=secret_key)

    request = AWSRequest(method="POST", url=f"https://{HOST}/",
                         headers={"host": HOST}, params={"Action": "CallWithBearerToken"})
    SigV4QueryAuth(creds, SERVICE, region, expires=expires).add_auth(request)
    presigned = request.url.replace("https://", "") + TOKEN_VERSION
    return AUTH_PREFIX + base64.b64encode(presigned.encode()).decode()


def token_from_env(region: str | None = None) -> str | None:
    """Return a token minted from the Lambda role credentials (BEDROCK_AK/BEDROCK_SK),
    or from the default botocore credential chain if unset."""
    region = region or os.environ.get("BEDROCK_REGION", "us-west-2")
    ak, sk = os.environ.get("BEDROCK_AK"), os.environ.get("BEDROCK_SK")
    if ak and sk:
        return generate_bedrock_token(ak, sk, region, os.environ.get("BEDROCK_ST"))
    try:
        from botocore.session import Session
        c = Session().get_credentials()
        if c is None:
            return None
        fc = c.get_frozen_credentials()
        return generate_bedrock_token(fc.access_key, fc.secret_key, region, fc.token)
    except Exception:
        return None
