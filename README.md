# bats-ai

## Develop with Docker (recommended quickstart)

This is the simplest configuration for developers to start with.

### Initial Setup

1. Run `docker compose run --rm django ./manage.py migrate`
2. Run `docker compose run --rm django ./manage.py createsuperuser`
   and follow the prompts to create your own user
3. Run `docker compose run --rm django ./manage.py loaddata species` to load species
   data into the database

### Run Vue Frontend

1. Run `cd client/`
2. Run `npm install`
3. Run `npm run dev`

### Run Application

1. Run `docker compose up`
2. Access the site, starting at <http://localhost:8000/admin/>
3. When finished, use `Ctrl+C`

### Maintenance

To non-destructively update your development stack at any time:

1. Run `docker compose down`
2. Run `docker compose pull`
3. Run `docker compose build --pull`
4. Run `docker compose run --rm django ./manage.py migrate`

## Dev Tool Endpoints

1. Main Site Interface [http://localhost:8080/](http://localhost:8080/)
2. Site Administration [http://localhost:8000/admin/](http://localhost:8000/admin/)
3. Swagger API (These are default swagger endpoints using Django-REST) [http://localhost:8000/api/docs/swagger/](http://localhost:8000/api/docs/swagger/)
4. Django Ninja API [http://localhost:8000/api/v1/docs#/](http://localhost:8000/api/v1/docs#/)
5. MinIO (S3 local management) [http://localhost:9001/browser](http://localhost:9001/browser)
   Username: 'minioAccessKey'
   Password: 'minioSecretKey'

## Develop Natively (advanced)

This configuration still uses Docker to run attached services in the background,
but allows developers to run Python code on their native system.

### Initial Setup for Native Development

1. Run `docker compose -f ./docker-compose.yml up -d`
2. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
3. Run `export UV_ENV_FILE=./dev/.env.docker-compose-native`
4. Run `./manage.py migrate`
5. Run `./manage.py createsuperuser` and follow the prompts to create your own user

### Run Native Application

1. Ensure `docker compose -f ./docker-compose.yml up -d` is still active
2. Run `export UV_ENV_FILE=./dev/.env.docker-compose-native`
3. Run: `./manage.py runserver_plus`
4. Run in a separate terminal: `uv run celery --app bats_ai.celery worker --loglevel INFO --without-heartbeat`
5. Run in a separate terminal:
   1. `source ./dev/export-env.sh`
   2. `cd ./client`
   3. `npm install`
   4. `npm run dev`
6. When finished, run `docker compose stop`

## Importing Recordings

The `importRecordings` management command allows you to bulk import WAV files from a
directory. It will:

- Recursively search for all `.wav` and `.WAV` files in the specified directory
- Extract GUANO metadata from each file (with filename fallback if metadata is missing)
- Create Recording objects with the extracted metadata
- Generate spectrograms synchronously for each recording
- Log progress to the terminal

### Usage

**Basic usage with Docker Compose (with bind mount):**

```bash
docker compose run --rm -v /path/to/wav/files:/data django ./manage.py importRecordings /data
```

**With options:**

```bash
docker compose run --rm -v /path/to/wav/files:/data django ./manage.py importRecordings /data \
  --owner username \
  --public \
  --limit 10
```

**Options:**

- `directory` (required): Path to directory containing WAV files
- `--owner USERNAME`: Username of the owner for the recordings (defaults to first superuser)
- `--public`: Make imported recordings public
- `--limit N`: Limit the number of WAV files to import (useful for testing)

**Example with bind mount:**

```bash
docker compose run --rm \
  -v /media/bryon.lewis/Elements/BATSAI/training_files:/data \
  django ./manage.py importRecordings /data --limit 5
```

This will:

1. Mount your host directory `/media/bryon.lewis/Elements/BATSAI/training_files` to `/data` in the container
2. Import only the first 5 WAV files found
3. Use the first superuser as the owner
4. Create private recordings (unless `--public` is specified)

## Testing

### Initial Setup for Testing

tox is used to manage the execution of all tests.
[Install `uv`](https://docs.astral.sh/uv/getting-started/installation/) and run tox with
`uv run tox ...`.

When running the "Develop with Docker" configuration, all tox commands must be run as
`docker compose run --rm django uv run tox`; extra arguments may also be appended to this form.

### Running Tests

Run `uv run tox` to launch the full test suite.

Individual test environments may be selectively run.
This also allows additional options to be be added.
Useful sub-commands include:

- `uv run tox -e lint`: Run only the style checks
- `uv run tox -e type`: Run only the type checks
- `uv run tox -e test`: Run only the pytest-driven tests

To automatically reformat all code to comply with
some (but not all) of the style checks, run `uv run tox -e format`.

## Code Formatting

Any contributed code should be compliant with `PEP8`, which is enforced by
`flake8` via `pre-commit`. It's recommended that you use `pre-commit` to ensure
linting procedures are run on any commit you make. See the
[installation instructions](https://pre-commit.com/#install) for your OS/platform
to install.

After you have the software installed, run `pre-commit install` on the command line.
Now every time you commit to this project's code base the linter procedures will
automatically run over the changed files.

To install the linting Python dependencies, run:

```bash
pip install -r pre-commit
```

To run pre-commit on files preemptively from the command line use:

```bash
 git add .
 pre-commit run

 # or

 pre-commit run --all-files
```

See `.pre-commit-config.yaml` for a list of configured linters and fixers.

To add `pre-commit` as a Git hook, run the following:

```bash
pre-commit install
```

This will run the `pre-commit` update prior to finalizing a local commit.  This
is preferred because once the commit is created locally, you will need to rebase
or otherwise rewrite the commit to make adjustments if done after the fact.

Lastly, the GitLab CI/CD infrastructure runs the same `pre-commit` configuration
on all pipelines for new MRs.  The automated checks in GitLab are optional, but
it is highly recommended to perform these checks locally prior to pushing new
commits.
