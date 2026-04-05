from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a DOCX file to PDF for local review and sharing."
    )
    parser.add_argument(
        "--input",
        default="build/docx/paper.docx",
        help="Path to the DOCX input file. Defaults to build/docx/paper.docx.",
    )
    parser.add_argument(
        "--output",
        default="build/pdf/paper.pdf",
        help="Path to the PDF output file. Defaults to build/pdf/paper.pdf.",
    )
    return parser.parse_args()


def convert_with_word(input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    input_abs = input_path.resolve()
    target_pdf = output_path.resolve()

    script = f"""
$ErrorActionPreference = 'Stop'
$inputPath = '{str(input_abs).replace("'", "''")}'
$targetPdf = '{str(target_pdf).replace("'", "''")}'
$word = $null
$document = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $document = $word.Documents.Open($inputPath)
    $document.SaveAs([ref] $targetPdf, [ref] 17)
}}
finally {{
    if ($document -ne $null) {{
        $document.Close()
    }}
    if ($word -ne $null) {{
        $word.Quit()
    }}
}}
"""
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )


def convert_with_libreoffice(input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    soffice = shutil.which("soffice")
    if not soffice:
        raise FileNotFoundError("LibreOffice executable `soffice` was not found on PATH.")

    output_dir = output_path.parent.resolve()
    result = subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(input_path.resolve()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    generated = output_dir / f"{input_path.stem}.pdf"
    if result.returncode == 0 and generated != output_path.resolve() and generated.exists():
        generated.replace(output_path)
    return result


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(
            f"Error: DOCX input not found: {input_path}. "
            "Run `python manuscript.py docx` first.",
            file=sys.stderr,
        )
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    conversion_errors: list[str] = []

    if sys.platform.startswith("win"):
        word_result = convert_with_word(input_path, output_path)
        if word_result.returncode == 0 and output_path.exists():
            print(f"Wrote PDF output to {output_path} using Microsoft Word.")
            return 0
        conversion_errors.append(
            word_result.stderr.strip() or word_result.stdout.strip() or "Word conversion failed."
        )

    try:
        libreoffice_result = convert_with_libreoffice(input_path, output_path)
    except FileNotFoundError as exc:
        conversion_errors.append(str(exc))
    else:
        if libreoffice_result.returncode == 0 and output_path.exists():
            print(f"Wrote PDF output to {output_path} using LibreOffice.")
            return 0
        conversion_errors.append(
            libreoffice_result.stderr.strip()
            or libreoffice_result.stdout.strip()
            or "LibreOffice conversion failed."
        )

    print("Error: unable to convert DOCX to PDF.", file=sys.stderr)
    for message in conversion_errors:
        if message:
            print(f"- {message}", file=sys.stderr)
    print(
        "Install Microsoft Word on Windows or LibreOffice with `soffice` on PATH, "
        "then rerun this script.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
