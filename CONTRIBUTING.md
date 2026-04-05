# Contributing

Thanks for your interest in improving `markup-hub`.

## Project shape

- `markup-hub` is the collaboration and review engine
- document folders live outside this repo in normal use
- `examples/` contains small demo content for testing and GitHub presentation

## Local setup

1. Copy `collab_config.example.toml` to `collab_config.toml`
2. Adjust the reviewer names and document paths for your workspace
3. Install dependencies with `python -m pip install -r requirements.txt`
4. Run `python build_viewer.py`
5. Open the generated viewer in Chrome or Edge

## Development guidelines

- Keep the repo generic: avoid hardcoding one person's folder structure or reviewer names
- Prefer reusable logic in `core/` and `export/` over one-off scripts
- Keep the viewer self-contained: inline CSS and JS, no framework, no server
- Treat document folders as external clients of the hub rather than bundled project content
- Keep root scripts thin and push durable logic into `core/` or `export/`

## Before opening a PR

- Rebuild the viewer locally if you changed rendering or data preparation logic
- Test against at least one real manifest and the sample project when possible
- If you changed manuscript pipeline behavior, run the relevant `python manuscript.py ...` command as well
- Update `README.md` if the setup or config story changes

## Scope

Good contributions include:

- manifest and numbering improvements
- viewer usability and review workflow improvements
- manuscript pipeline and export improvements
- portability and browser-compatibility fixes
- documentation and onboarding polish

Please avoid committing:

- local `collab_config.toml`
- generated viewer outputs
- private manuscript content unless it belongs in `examples/`
