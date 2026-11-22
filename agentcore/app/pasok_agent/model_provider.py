"""
Pasok — local model provider for the AgentCore runtime
======================================================

The runtime's default model is Bedrock Claude, which is account-gated on this box. This
module gives the runtime a second, working brain on the same account, so the agent's
answers can be demonstrated locally instead of only described.

Set the environment to pick one:

    PASOK_MODEL=bedrock   (default) Bedrock Claude via bedrock-runtime
    PASOK_MODEL=mantle             Bedrock Mantle (OpenAI-compatible), models that work
                                   on this account: kimi-k2.5, deepseek, qwen, glm

The Mantle key is a short-term Bedrock API key, minted from the caller's credentials by
SigV4-presigning Action=CallWithBearerToken. No secret is stored: it is minted on demand
and cached for ~11 hours per process.

The model is chosen by the same env switch that the Lambda lane uses, so local and AWS
run the same brain.
"""

from __future__ import annotations

import base64
import os
import time

_MANTLE_REGION = os.environ.get("AWS_REGION", "us-west-2")
_TOKEN_TTL = 11 * 3600
_cache: dict[str, float | str] = {"token": "", "exp": 0.0}


def _credentials():
    """Resolve AWS credentials from the environment or the default chain."""
    ak = os.environ.get("AWS_ACCESS_KEY_ID")
    sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
    st = os.environ.get("AWS_SESSION_TOKEN")
    if ak and sk:
        return ak, sk, st
    import boto3
    profile = os.environ.get("AWS_PROFILE", "pasok")
    c = boto3.Session(profile_name=profile).get_credentials().get_frozen_credentials()
    return c.access_key, c.secret_key, c.token


def bedrock_token(region: str = _MANTLE_REGION, expires: int = 43200) -> str:
    """Short-term Bedrock bearer token (cached)."""
    now = time.time()
    if _cache["token"] and now < float(_cache["exp"]):
        return str(_cache["token"])

    from botocore.auth import SigV4QueryAuth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials

    ak, sk, st = _credentials()
    creds = Credentials(access_key=ak, secret_key=sk, token=st) if st \
        else Credentials(access_key=ak, secret_key=sk)
    req = AWSRequest(method="POST", url="https://bedrock.amazonaws.com/",
                     headers={"host": "bedrock.amazonaws.com"},
                     params={"Action": "CallWithBearerToken"})
    SigV4QueryAuth(creds, "bedrock", region, expires=expires).add_auth(req)
    url = req.url or ""
    presigned = url.replace("https://", "") + "&Version=1"
    token = "bedrock-api-key-" + base64.b64encode(presigned.encode()).decode()

    _cache["token"], _cache["exp"] = token, now + _TOKEN_TTL
    return token


DEFAULT_MANTLE_MODEL = "moonshotai.kimi-k2.5"


def build_model():
    """Return the Strands model the runtime should use, per PASOK_MODEL."""
    kind = os.environ.get("PASOK_MODEL", "bedrock").strip().lower()

    if kind == "mantle":
        from strands.models.openai import OpenAIModel
        model_id = os.environ.get("PASOK_MANTLE_MODEL", DEFAULT_MANTLE_MODEL)
        base = (f"https://bedrock-mantle.{_MANTLE_REGION}.api.aws/v1")
        return OpenAIModel(
            client_args={"api_key": bedrock_token(), "base_url": base},
            model_id=model_id,
        )

    # default: Bedrock Claude through bedrock-runtime (gated on this account)
    from strands.models import BedrockModel
    return BedrockModel(
        model_id=os.environ.get("PASOK_BEDROCK_MODEL",
                                "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
        region_name=_MANTLE_REGION,
    )


def describe() -> str:
    kind = os.environ.get("PASOK_MODEL", "bedrock").strip().lower()
    if kind == "mantle":
        return f"mantle:{os.environ.get('PASOK_MANTLE_MODEL', DEFAULT_MANTLE_MODEL)}"
    return "bedrock:us.anthropic.claude-sonnet-4-5-20250929-v1:0"
