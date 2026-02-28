# CODEx Guide - JAAQL-middleware-python

## What This Repo Is
Python middleware package for JAAQL, with Docker-based local setup guidance and a Postgres extension area.

## Key Files
- `README.md` - high-level description and local dev warning about database changes
- `BUILD.md` - build/setup instructions
- `requirements.txt` - Python dependencies
- `setup.py` - package build metadata
- `wsgi.py` - WSGI entry point
- `version.py` - version info
- `docker/` - docker setup and local environment docs/scripts
- `jaaql/` - main application package code
- `pgextension/` - Postgres extension-related assets

## Important Local Dev Warning
The README notes JAAQL can make non-reversible database changes. Use isolated local databases/containers for development and testing.

## Common Tasks (likely)
- Install deps: `pip install -r requirements.txt`
- Build/package: review `BUILD.md` and `setup.py`
- Run app: inspect `wsgi.py` / project docs / docker docs for the intended entrypoint

## Working Rules
- Prefer docker/local Postgres workflows over pointing at shared databases.
- Be careful with DB migrations or schema-changing code.
- If changing SQL/query behavior, note backward-compatibility and migration implications.
- Check `docker/docker.md` before inventing local setup steps.

## First Read For Any Task
1. `README.md`
2. `BUILD.md`
3. `docker/docker.md` (for local setup)
4. The target module in `jaaql/`