# bats-ai

## Setup
1. Install [VS Code with dev container support](https://code.visualstudio.com/docs/devcontainers/containers#_installation).
1. Open the project in VS Code, then run `Dev Containers: Reopen in Container`
   from the Command Palette (`Ctrl+Shift+P`).
1. Once the container is ready, open a terminal and run:
   ```sh
   ./manage.py migrate
   ./manage.py createsuperuser
   ./manage.py loaddata species
   ```

## Run
Open the **Run and Debug** panel (`Ctrl+Shift+D`) and select a launch configuration:

* **Django: Server** — Starts the development server at <http://localhost:8000/>
* **Django: Server (eager Celery)** — Same, but Celery tasks run synchronously
  in the web process (useful for debugging task code without a worker)
* **Celery: Worker** — Starts only the Celery worker
* **Django + Celery** — Starts both the server and a Celery worker
* **Django: Management Command** — Pick and run any management command
* **Vite: Dev Server** - Starts the frontend development server at <http://localhost:8080/>
* **Django + Celery + Vite** - Starts the server, a Celery worker, and the frontend.

## Test
Run the full test suite from a terminal: `tox`

Auto-format code: `tox -e format`

Run and debug individual tests from the **Testing** panel (`Ctrl+Shift+;`).

## Rebuild
After changes to the Dockerfile, Docker Compose files, or `devcontainer.json`,
run `Dev Containers: Rebuild Container` from the Command Palette (`Ctrl+Shift+P`).

For dependency changes in `pyproject.toml`, just run `uv sync --all-extras --all-groups`.

## Dev Tool Endpoints

1. Main Site Interface <http://localhost:8080/>
2. Site Administration <http://localhost:8000/admin/>
3. Swagger API (These are default swagger endpoints using Django-REST) <http://localhost:8000/api/docs/swagger/>
4. Django Ninja API <http://localhost:8000/api/v1/docs#/>
5. MinIO (S3 local management) <http://localhost:9001/browser>
   Username: 'minioAccessKey'
   Password: 'minioSecretKey'

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

```sh
./manage.py importRecordings /data
```

**With options:**

```bash
./manage.py importRecordings /data \
  --owner username \
  --public \
  --limit 10
```

**Options:**

- `directory` (required): Path to directory containing WAV files
- `--owner USERNAME`: Username of the owner for the recordings (defaults to first superuser)
- `--public`: Make imported recordings public
- `--limit N`: Limit the number of WAV files to import (useful for testing)

## Code Formatting

It's recommended that you use `pre-commit` to provide additional
linting on any commit you make. See the
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
on all pipelines for new MRs. The automated checks in GitLab are optional, but
it is highly recommended to perform these checks locally prior to pushing new
commits.

### Spectrogram contours

Spectrogram processing tasks honor `DJANGO_BATAI_SAVE_SPECTROGRAM_CONTOURS` environment variable.
Set to `False` by default so workers skip contour extraction (less DB storage space); set to `True` if you need
contours in the UI (UI for contours currently disabled due to performance)

### Species Suggestions by Range

The suggested species for a given location are determined by spatial data stored in `/bats_ai/core/data/species-range.geojson`.
As part of the default migrations this data is ingested into the SpeciesRange database and used for determining suggested
species based on  a Recording (internal GRTS_Cell_ID and sample_frame_id).
The if the same species is found multiple times in the geojson the last geometry will be used.
In the future if species-ranges change the managment command of `./manage.py load_species_geojson [optional Geojson Path]`
can be used to reload the default species-range.geojson
if no path is provided or a new one and will update/replace any previous data.
