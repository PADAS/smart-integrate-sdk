import os
from environs import Env

cdip_sdk_envfile = os.environ.get("CDIP_SDK_ENVFILE", None)

env = Env()

if cdip_sdk_envfile:
    env.read_env(cdip_sdk_envfile)
else:
    # Default behavior
    env.read_env()

KEYCLOAK_ISSUER = env.str("KEYCLOAK_ISSUER", None)
KEYCLOAK_CLIENT_ID = env.str("KEYCLOAK_CLIENT_ID", None)
KEYCLOAK_CLIENT_SECRET = env.str("KEYCLOAK_CLIENT_SECRET", None)
KEYCLOAK_AUDIENCE = env.str("KEYCLOAK_AUDIENCE", None)

CDIP_API_ENDPOINT = env.str("CDIP_API_ENDPOINT", None)
CDIP_ADMIN_ENDPOINT = env.str("CDIP_ADMIN_ENDPOINT", None)

CDIP_API_SSL_VERIFY = env.bool("CDIP_API_SSL_VERIFY", True)
CDIP_ADMIN_SSL_VERIFY = env.bool("CDIP_ADMIN_SSL_VERIFY", True)

LOG_LEVEL = env.log_level("LOG_LEVEL", "INFO")
DEFAULT_LOOKBACK_DAYS = env.int("DEFAULT_LOOKBACK_DAYS", 30)

RUNNING_IN_K8S = bool("KUBERNETES_PORT" in os.environ)

OAUTH_TOKEN_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
PORTAL_API_ENDPOINT = f"{CDIP_ADMIN_ENDPOINT}/api/v1.0"

# Enables the pub sub flow for processing observations
PUBSUB_ENABLED = env.bool("PUBSUB_ENABLED", False)

# Google Cloud Settings
GOOGLE_PUB_SUB_PROJECT_ID = env.str("GOOGLE_PUB_SUB_PROJECT_ID", "project_id not set")
GOOGLE_APPLICATION_CREDENTIALS = env.str(
    "GOOGLE_APPLICATION_CREDENTIALS", "google credentials file not set"
)
CLOUD_STORAGE_TYPE = env.str("CLOUD_STORAGE_TYPE", "google")
BUCKET_NAME = env.str("BUCKET_NAME", "cdip-dev-cameratrap")

# Kafka Settings
KAFKA_BROKER = env.str("KAFKA_BROKER", "localhost:9092")
CONFLUENT_CLOUD_ENABLED = env.bool("CONFLUENT_CLOUD_ENABLED", False)
KEY_ORDERING_ENABLED = env.bool("KEY_ORDERING_ENABLED", False)

CONFLUENT_CLOUD_USERNAME = env.str("CONFLUENT_CLOUD_USERNAME", "username not set")
CONFLUENT_CLOUD_PASSWORD = env.str("CONFLUENT_CLOUD_PASSWORD", "password not set")
