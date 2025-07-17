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
DEFAULT_DATA_TIMEOUT_SECONDS = env.int("DEFAULT_DATA_TIMEOUT_SECONDS", 60)

RUNNING_IN_K8S = bool("KUBERNETES_PORT" in os.environ)

OAUTH_TOKEN_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
PORTAL_API_ENDPOINT = f"{CDIP_ADMIN_ENDPOINT}/api/v1.0"

# Enables the pub sub flow for processing observations
PUBSUB_ENABLED = env.bool("PUBSUB_ENABLED", False)

# Google Cloud Settings
GCP_PROJECT_ID = env.str("GCP_PROJECT_ID", None)
GOOGLE_PUB_SUB_PROJECT_ID = env.str("GOOGLE_PUB_SUB_PROJECT_ID", "project_id not set")
GOOGLE_APPLICATION_CREDENTIALS = env.str(
    "GOOGLE_APPLICATION_CREDENTIALS", None
)
CLOUD_STORAGE_TYPE = env.str("CLOUD_STORAGE_TYPE", "google")
BUCKET_NAME = env.str("BUCKET_NAME", "cdip-dev-cameratrap")

# How many integrations should run at once.
INTEGRATION_CONCURRENCY = env.int("INTEGRATION_CONCURRENCY", 5)

# How many items should be posted to Sensors API in each request.
INTEGRATION_LOAD_BATCH_SIZE = env.int("INTEGRATION_LOAD_BATCH_SIZE", 25)

TRACING_ENABLED = env.bool("TRACING_ENABLED", True)

# Coerce task count and index into common variables (using CronJob variables). 
# This allows them to be provided by a Kubernetes CronJob or by a Cloud Run Job.
# Get them as strings, because we want '0' to be zero and not False here.
_job_completion_index = os.environ.get('JOB_COMPLETION_INDEX', None) or os.environ.get('CLOUD_RUN_TASK_INDEX', None)
JOB_COMPLETION_INDEX = int(_job_completion_index) if _job_completion_index is not None else None

_job_completion_count = os.environ.get('JOB_COMPLETION_COUNT', None) or os.environ.get('CLOUD_RUN_TASK_COUNT', None)
JOB_COMPLETION_COUNT = int(_job_completion_count) if _job_completion_count is not None else None

# Sanitize task count and index.
if JOB_COMPLETION_INDEX is not None \
    and JOB_COMPLETION_COUNT is not None:
    if JOB_COMPLETION_COUNT and JOB_COMPLETION_COUNT > JOB_COMPLETION_INDEX:
        # Partitioned
        JOB_IS_PARTITIONED = True
    else:
        # Values are set but are not valid.
        raise ValueError('JOB_COMPLETION_COUNT must be greater than 1 and greater than JOB_COMPLETION_INDEX')
else:
    # No partitioning
    JOB_IS_PARTITIONED = False
    JOB_COMPLETION_INDEX = 0
    JOB_COMPLETION_COUNT = 1

