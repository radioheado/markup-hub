# markup-hub

`markup-hub` is a Markdown-first collaboration layer for long-form research writing. It keeps chapter files as the source of truth, assembles them through a `main.md` manifest, and supports two stable review surfaces:

- an HTML reviewer for browser-based reading, comments, and edit suggestions
- a full-manuscript Markdown workflow for in-meeting editing in VS Code

The repository is intentionally small and local-first. No server, no database, and no required cloud platform beyond the shared folder you already use.

## What it does

`markup-hub` currently supports:

- manifest-driven multi-file manuscript assembly
- numbering for chapters, sections, tables, and figures
- a local HTML reviewer with inline annotations saved to `reviews.json`
- applying saved HTML review comments back into source Markdown
- building a reversible `paper.full.md` for direct editing
- syncing edits from `paper.full.md` back into chapter files
- optional Git snapshot prompting after sync

## Source model

The source of truth is always:

1. `main.md`
2. chapter files under `src/` or other included paths
3. your numbering and build rules

Reviewer-facing artifacts are generated from those sources.

Example manifest:

```md
<!-- INCLUDE src/intro.md -->
<!-- INCLUDE src/related_work.md -->
<!-- INCLUDE src/results.md -->
```

## Recommended workspace layout

```text
workspace/
|-- markup-hub/
|-- discussion-a/
|   |-- main.md
|   |-- src/
|   `-- .git/
|-- proposal-b/
|   |-- main.md
|   |-- src/
|   `-- .git/
`-- collab_viewer.html
```

Inside `markup-hub/`:

```text
markup-hub/
|-- apply_review.py
|-- build_full.py
|-- build_viewer.py
|-- manuscript.py
|-- meeting.py
|-- sync_full.py
|-- collab_config.toml
|-- collab_viewer_template.html
|-- core/
|   |-- config.py
|   |-- manifests.py
|   |-- merge_md.py
|   |-- number_md.py
|   |-- numbering.py
|   `-- validate_md.py
|-- export/
|   |-- build_html.py
|   |-- build_word.ps1
|   |-- export_docx.py
|   `-- export_pdf.py
`-- README.md
```

## Configuration

All paper-level paths live in `collab_config.toml`. This is the main way to keep the workflow easy to remember as your manuscript folders grow.

Minimal example:

```toml
project = "Research Workspace"
subtitle = "Spring 2026"
reviewers = ["Reviewer One", "Reviewer Two"]
default_group = "Discussion Topic A"

[groups."Discussion Topic A"]
main = "../discussion-a/main.md"
enabled = true
docx_template = "../discussion-a/src/archive/template.docx"

[groups."Proposal B"]
main = "../proposal-b/main.md"
enabled = true
# docx_template = "../proposal-b/src/archive/template.docx"
```

You do not need to set up a separate command for each chapter or manually pass manuscript paths every time.

- If `collab_config.toml` contains only one enabled paper group, `python meeting.py build` and `python meeting.py sync` will automatically use that paper.
- If you keep multiple paper groups in the config, set `default_group = "..."` to make one of them the default no-argument target.
- If you want to work on a different paper for a specific run, use `--group`, for example `python meeting.py build --group "Proposal B"`.

In other words, `--group` selects a paper, not a chapter.

If you want to temporarily exclude a paper from all config-driven workflows, you have two options:

- set `enabled = false` inside that group's config block
- or comment out that group block in the TOML file

Example:

```toml
[groups."Proposal B"]
main = "../proposal-b/main.md"
enabled = false
```

## Main workflows

### HTML reviewer

Use this when you want a browser-based reading and annotation surface.

Build the viewer:

```powershell
python build_viewer.py
```

Review flow:

1. Open the generated `collab_viewer.html`
2. Add comments or edit suggestions
3. Save annotations to `reviews.json`
4. Apply them back into the chapter files

```powershell
python apply_review.py
```

### Meeting workflow

Use this when you want one integrated manuscript file for live editing in VS Code.

Build the meeting file:

```powershell
python meeting.py build
```

Build `paper.full.md` for all enabled papers in the config:

```powershell
python meeting.py build-all
```

Sync edits back into source files:

```powershell
python meeting.py sync
```

Preview a sync without writing files:

```powershell
python meeting.py sync --dry-run
```

Prompt for a Git snapshot after sync:

```powershell
python meeting.py sync --prompt-commit
```

When multiple groups are configured and you want to target a different paper:

```powershell
python meeting.py build --group "Metrics Paper"
python meeting.py sync --group "Metrics Paper"
```

### Manuscript pipeline

Use this when you want the hub to run the regular manuscript build/export steps for a paper repo.

Examples:

```powershell
python manuscript.py merge
python manuscript.py number
python manuscript.py validate
python manuscript.py html
python manuscript.py docx
python manuscript.py pdf
python manuscript.py all
```

With multiple configured papers:

```powershell
python manuscript.py all --group "Metrics Paper"
```

`manuscript.py all` runs the full pipeline from the hub against the selected paper repo. The paper repo provides content and assets; the hub owns the tooling.

## How the meeting workflow works

`meeting.py build` creates a generated `paper.full.md` beside the target paper's `main.md`. That file includes protected source markers and numbered headings/captions so it is convenient to read during a meeting.

Important:

- `paper.full.md` is generated, not source
- it is safe and recommended to keep `paper.full.md` out of Git
- the files Git should track are `main.md`, chapter files under `src/`, and supporting assets
- after the meeting, run `meeting.py sync` to write accepted edits back into the real source files
- use `{{build_date}}` in source Markdown when you want the generated full manuscript to show the current build date automatically

`meeting.py sync` then:

- reads the edited `paper.full.md`
- maps each block back to its original chapter file
- strips generated heading numbers back to plain Markdown headings
- restores table and figure label placeholders in source files
- refuses to overwrite source files if they changed since the full file was built unless you explicitly force it
- writes `.bak` backups before changing chapter files

The chapter files remain the real manuscript source.
`paper.full.md` is a generated collaboration surface.

## Numbering

Numbering remains part of the build layer, not the source layer.

- source files keep semantic Markdown
- numbered headings and captions are generated for review artifacts
- sync restores source-friendly Markdown before writing back

This preserves compatibility with your existing manuscript tooling.

## Git usage

Each paper folder can live in its own Git repository even when stored inside a shared OneDrive workspace. Git is used for safety and revision control, not for day-to-day syncing between collaborators.

Recommended practice:

- keep chapter Markdown files under Git
- treat `paper.full.md` as a generated meeting artifact
- add `paper.full.md` to the paper repo's `.gitignore`
- create Git snapshots after meaningful sync events, not after every draft edit

## Setup

1. Copy `collab_config.example.toml` to `collab_config.toml`
2. Add your paper folders under `[groups]`
3. Set the `reviewers` list for the HTML viewer
4. Run either the HTML reviewer flow or the meeting flow

## Internal layout

- `core/`: manuscript and configuration logic
- `core/config.py`: config loading and group/path resolution
- `core/manifests.py`: manifest parsing, file loading, labels, and path normalization
- `core/merge_md.py`, `core/number_md.py`, `core/validate_md.py`: manuscript pipeline steps
- `core/numbering.py`: numbering and reference handling
- `export/`: HTML, DOCX, PDF, and Word-export helpers used by `manuscript.py`

## Scope

`markup-hub` does not replace your manuscript repositories. It provides stable review and collaboration tooling around Markdown-first papers.

Its current focus is:

- keeping long-form research writing maintainable
- preserving traceability back to chapter files
- giving collaborators a choice between HTML review and direct manuscript editing
