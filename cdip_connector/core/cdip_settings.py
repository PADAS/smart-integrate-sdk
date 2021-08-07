import os
from environs import Env

cdip_sdk_envfile = os.environs.get('CDIP_SDK_ENVFILE', None)

env = Env()

if cdip_sdk_envfile:
    env.read_env(cdip_sdk_envfile)
else:
    # Default behavior
    env.read_env()

KEYCLOAK_ISSUER = env.str('KEYCLOAK_ISSUER', None)
KEYCLOAK_CLIENT_ID = env.str('KEYCLOAK_CLIENT_ID', None)
KEYCLOAK_CLIENT_SECRET = env.str('KEYCLOAK_CLIENT_SECRET', None)
KEYCLOAK_AUDIENCE = env.str('KEYCLOAK_AUDIENCE', None)

CDIP_API_ENDPOINT = env.str('CDIP_API_ENDPOINT', None)
CDIP_ADMIN_ENDPOINT = env.str('CDIP_ADMIN_ENDPOINT', None)

METRICS_PROXY_HOST = env.str('METRICS_PROXY_HOST', None)
METRICS_PROXY_PORT = env.int('METRICS_PROXY_PORT', 8125)
METRICS_PREFIX = KEYCLOAK_CLIENT_ID
LOG_LEVEL = env.log_level('LOG_LEVEL', 'INFO')
DEFAULT_LOOKBACK_DAYS = env.int('DEFAULT_LOOKBACK_DAYS', 30)

RUNNING_IN_K8S = bool('KUBERNETES_PORT' in os.environ)

OAUTH_TOKEN_URL = f'{KEYCLOAK_ISSUER}/protocol/openid-connect/token'
PORTAL_API_ENDPOINT = f'{CDIP_ADMIN_ENDPOINT}/api/v1.0'
