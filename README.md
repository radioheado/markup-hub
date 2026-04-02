# markup-hub

`markup-hub` is a lightweight collaboration layer for long-form Markdown projects. It renders manifest-driven chapter files into a single local HTML review surface, lets reviewers leave inline comments or edit suggestions, and writes those review
traces back into the source files when you are ready to process them.

No server. No login. No database setup. Just Markdown, a browser, and a folder layout your team already understands.

## Why it exists

Many writing workflows eventually hit the same problem:

- source files live comfortably in Markdown
- export to Word or PDF works, but is fragile and time-consuming to maintain
- reviewers want one readable place to comment without losing traceability

`markup-hub` keeps Markdown as the source of truth while giving collaborators a stable browser-based review surface.

## Features

- renders multi-file Markdown projects from a `main.md` manifest
- resolves heading, table, figure, and section numbering across included files
- provides a local HTML viewer with navigation and inline annotation support
- saves reviewer comments to `reviews.json`
- applies saved reviews back into source Markdown as review blocks

## Project model

`markup-hub` is the engine, not the content store. Your actual papers, proposals, notes, or chapter folders should live beside it or anywhere else on disk, as long as the config can point to them.

Each document project only needs a simple contract:

1. a `main.md` manifest
2. chapter or source files, commonly under `src/`
3. one `<!-- INCLUDE ... -->` line per source file in the manifest

Example manifest:

```md
<!-- INCLUDE src/intro.md -->
<!-- INCLUDE src/related_work.md -->
<!-- INCLUDE src/results.md -->
```

## Repository layout

```text
markup-hub/
├── build_viewer.py
├── apply_review.py
├── collab_config.toml
├── collab_viewer_template.html
├── lib/
│   ├── manifests.py
│   └── numbering.py
├── examples/
│   └── sample-paper/
└── README.md
```

A typical workspace might look like this:

```text
workspace/
├── collab_viewer.html
├── markup-hub/
├── paper-a/
│   ├── main.md
│   └── src/
└── proposal-b/
    ├── main.md
    └── src/
```

This is the recommended setup for most users:

- keep `markup-hub/` as the tool repo
- keep each paper or document in its own sibling folder
- generate `collab_viewer.html` into the workspace root so collaborators can find it quickly

Your document folders do not need to live inside `markup-hub/`.
They can live anywhere your machine can reach. The only requirement is that
`collab_config.toml` points each group at a valid `main.md` manifest.

## Configuration

All viewer inputs are defined in `collab_config.toml`.
Start by copying `collab_config.example.toml` to `collab_config.toml`.

Minimal example:

```toml
project = "Research Workspace"
subtitle = "Spring 2026"
reviewers = ["Reviewer One", "Reviewer Two"]

[groups."Paper A"]
main = "../paper-a/main.md"

[groups."Proposal B"]
main = "../proposal-b/main.md"
```

Those `main = ...` paths are where you tell the hub where your own paper folders live.
In the common sibling-folder layout above, `../paper-a/main.md` means:

- start in `markup-hub/`
- go up one level to the workspace root
- enter `paper-a/`
- load `main.md`

### Reviewers

The `reviewers` list controls the identity picker shown in the viewer.
Set this to your own collaborators, for example:

```toml
reviewers = ["Alice Smith", "Bob Lee", "Advisor Name"]
```

## Setup

1. Clone or copy `markup-hub`
2. Copy `collab_config.example.toml` to `collab_config.toml`
3. Set `reviewers = [...]` to your own reviewer names
4. Point each group at a `main.md` manifest in one of your document folders
5. Run:

```bash
python build_viewer.py
```

By default this writes `../collab_viewer.html`, but you can choose any output path:

```bash
python build_viewer.py --out ./collab_viewer.html
```

Then open the generated HTML file in Chrome or Edge.

## Review workflow

### For authors

1. Update Markdown files in your document project
2. Rebuild the viewer:

```bash
python build_viewer.py
```

3. Share the generated `collab_viewer.html`
4. After reviewers save annotations, apply them:

```bash
python apply_review.py
```

### For reviewers

1. Open `collab_viewer.html`
2. Pick your identity
3. Select text and add comments or edit suggestions
4. Click `Save`

## Reusable library modules

Generic manuscript logic is being moved into `lib/` so the hub can evolve into a reusable toolkit instead of depending on one paper repo's private scripts.

- `lib/manifests.py`: manifest parsing, file loading, path normalization, labels
- `lib/numbering.py`: heading numbering and table/figure/section reference resolution

## Example project

The repo includes `examples/sample-paper/` as a tiny self-contained example for testing, demos, and GitHub presentation without bundling real research material.

## Scope

`markup-hub` is intentionally narrow:

- it does not replace your manuscript repo
- it does not require a web server
- it does not prescribe how you export to Word or PDF
- it focuses on reading, reviewing, and traceable annotation over Markdown source
