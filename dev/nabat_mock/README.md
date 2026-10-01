# Mocking the NABat Integration

The integration with the NABat platform requires some trickier auth and API calls to test
fully. This directory contains helpful tools for local development testing, covering both
halves of the integration:

- **Keycloak** stands in for NABat's OIDC login, so the "open in batai" redirect and code
  exchange can be exercised for real.
- **nabat-mock** stands in for NABat's GraphQL API (`BATAI_NABAT_API_URL`), so recording
  fetches can run end to end against real infrastructure (the existing `minio` service)
  instead of hitting `sciencebase.gov`.

## Running the mock stack

In the top-level directory of the repository there is a docker compose file that can be used
in conjunction with whichever docker compose files you already use for development. This means
you only need to spin up these services when required. To chain docker compose files, simply
use the `-f` flag multiple times. For example, with local development:

```bash
docker compose -f docker-compose.yml -f docker-compose-nabat-mock.yml up
```

## Keycloak Configuration

Keycloak configuration is defined in [NABAT-realm.json](./NABAT-realm.json). It sets up 2
clients: a proxy "NABat" and a client for the locally running BatAI application. It also sets
up a test user (this would be the analog to your account with NABat). The username and
password for this user are both `testuser`.

This realm issues lightweight access tokens, so any claim batai needs has to be re-added by
an explicit protocol mapper - including `sub` (the user's Keycloak ID), which Keycloak
otherwise strips from lightweight tokens by default even though it's normally unconditional
per the OIDC spec. `create_recording_annotation` reads `sub` directly, so the `profile` scope
carries an `oidc-sub-mapper` for it. Keep that in mind if this realm export ever gets
regenerated from Keycloak's admin UI - it's easy to lose.

## nabat-mock

[mock_server.py](./mock_server.py) stands in for NABat's GraphQL API. BatAI never uses a real
GraphQL client - every query is a plain string with literal IDs, POSTed as `{"query": "..."}`
- so rather than running an actual GraphQL server, the mock just pattern-matches on substrings
in the query text and returns canned JSON shaped like NABat's real responses.

It's currently scoped to the single-recording fetch flow only (not NABat's "file list"
feature). Any `recording_id` resolves successfully except `0`, which is reserved to simulate
"not found / access denied" and exercise the existing 403 handling.

Every recording fetched this way also gets one already-vetted species seeded onto it, so
`create_nabat_recording_from_response()` picks it up and creates a matching
`NABatRecordingAnnotation` automatically on first fetch - there's something to see in the
annotations list immediately rather than an empty one. The seeded annotation's email matches
the Keycloak test user (`testuser@example.com`), so it's visible when browsing as them.
Pushing an annotation back to NABat (`.../push-to-nabat`) is mocked too and always succeeds.

This seeding requires a local `Species` row with a matching pk to already exist - species
sync itself isn't mocked. Defaults to pk `1`; override `SEED_ANNOTATION_SPECIES_ID` /
`SEED_ANNOTATION_EMAIL` if your database doesn't have that row or you want a different one.
Most dev databases already have Species data from prior real NABat usage, before this mock
existed.

Presigned URLs are generated for real against the `minio` service already in
`docker-compose.yml`, so the download and spectrogram-generation steps run against real
infrastructure. nabat-mock itself never connects to minio - presigning is pure local
signing - it only needs to know the *bucket name*, not to reach it. Until an object
actually exists at `recordings/example.wav`, the presigned URL it returns will 404 when
downloaded.

Seed that object (and create the bucket) with [upload_recording.py](./upload_recording.py),
once minio is up:

```bash
docker compose -f docker-compose.yml -f docker-compose-nabat-mock.yml up -d minio
uv run dev/nabat_mock/upload_recording.py
```

With no path given, it uploads the repo's own [assets/example.wav](../../assets/example.wav).
Pass a different path to use your own file instead - it must actually be a `.wav` (checked
both by extension and by parsing it with Python's `wave` module). The project's own
virtualenv already has the `minio` package (a transitive dependency via
django-minio-storage), so `uv run` needs no extra install.

### Running celery natively (not in Docker)

Whoever downloads the presigned URL (the celery worker) must be able to resolve the host
baked into it. nabat-mock signs against `MINIO_ENDPOINT`, defaulting to the compose-network
name `minio:9000` - fine if celery is also containerized. If you run celery natively (see
[native-development.md](../native-development.md)), it can't resolve `minio`; only the
published port on `localhost` is reachable from the host.

If you run celery locally for your development, make sure to set `MINIO_ENDPOINT=localhost:9000` in your environment.

```bash
MINIO_ENDPOINT=localhost:9000 docker compose -f docker-compose.yml -f docker-compose-nabat-mock.yml up
```

## Testing the full flow

Once the mock stack is running alongside BatAI, run [./print-nabat-auth-url.sh](./print-nabat-auth-url.sh)
to generate a URL.

Paste the URL into your browser, and if this is the first time you're going through the
workflow or KC doesn't have an active token for `testuser` you'll need to log in as
`testuser`. This redirects to your local BatAI application, exchanges the code with
Keycloak, and then kicks off a real fetch of the recording (backed by nabat-mock and minio)
and real spectrogram generation - the same pipeline production runs, driven entirely by
local infrastructure.
