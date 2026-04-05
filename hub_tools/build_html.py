from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a simple HTML preview from numbered Markdown."
    )
    parser.add_argument(
        "--input",
        default="build/merged/paper_numbered.md",
        help="Path to the numbered Markdown input file. Defaults to build/merged/paper_numbered.md.",
    )
    parser.add_argument(
        "--output",
        default="build/html/paper.html",
        help="Path to the HTML output file. Defaults to build/html/paper.html.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import markdown
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: markdown. Install requirements with "
            "`python -m pip install -r markup-hub/requirements.txt`."
        ) from exc

    input_path = Path(args.input)
    output_path = Path(args.output)
    source = input_path.read_text(encoding="utf-8")
    body = markdown.markdown(source, extensions=["tables"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Paper preview</title>
  <style>
    body {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: 12pt;
      line-height: 1.6;
      color: #222222;
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
      background: #ffffff;
    }}
    h1, h2, h3, h4 {{
      color: #2E4057;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1.5rem 0;
    }}
    th, td {{
      border: 1px solid #999999;
      padding: 0.5rem 0.75rem;
      text-align: left;
    }}
    tbody tr:nth-child(even) {{
      background: #F2F2F2;
    }}
  </style>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']]
      }}
    }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
{body}
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Wrote HTML preview to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
