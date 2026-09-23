# -*- coding: utf-8 -*-
"""Snowflake login for Affinity apps. Uses the service key pair, not a password."""
from pathlib import Path

SERVICE_USER = "SRV_USR_DEV_BI"
DEFAULT_ACCOUNT = "xda11449.east-us-2.azure"
KEY_FILES = (
    Path(r"C:\Users\ScottPhillips\OneDrive\Snowflake_Keys\rsa_key_dev_bi.p8"),
    Path(
        r"C:\Users\ScottPhillips\OneDrive - Affinity Group\Group Documents"
        r"\Snowflake Reporting\Power BI Snowflake Connection\rsa_key_dev_bi.p8"
    ),
)


def load_private_key(pem_text=None):
    """Load the service private key from a PEM string or the shared key file."""
    from cryptography.hazmat.primitives import serialization

    data = None
    if pem_text:
        text = pem_text.decode() if isinstance(pem_text, bytes) else str(pem_text)
        text = text.replace("\\n", "\n").strip()
        data = text.encode()
    else:
        for path in KEY_FILES:
            if path.exists():
                data = path.read_bytes()
                break
    if not data:
        return None
    return serialization.load_pem_private_key(data, password=None)


def connect_snowflake(
    *,
    account=None,
    role=None,
    warehouse=None,
    database=None,
    schema=None,
    private_key_pem=None,
    password=None,
    user=None,
):
    """Open a Snowflake connection. The service key wins over a password."""
    import snowflake.connector

    key = load_private_key(private_key_pem)
    kwargs = {
        "account": account or DEFAULT_ACCOUNT,
        "role": role or "ROLE_FR_PROD_DATA_ENGG",
        "warehouse": warehouse or "DASH_WH_SI",
    }
    if database:
        kwargs["database"] = database
    if schema:
        kwargs["schema"] = schema
    if key is not None:
        kwargs["user"] = SERVICE_USER
        kwargs["private_key"] = key
        kwargs["authenticator"] = "SNOWFLAKE_JWT"
    else:
        kwargs["user"] = user
        kwargs["password"] = password
    return snowflake.connector.connect(**kwargs)
