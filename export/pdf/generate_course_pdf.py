"""Generate a professional PDF from the rendered course site."""

from __future__ import annotations

import html
import re
import subprocess
import tempfile
from pathlib import Path

from weasyprint import CSS, HTML


ROOT_DIR = Path(__file__).resolve().parents[2]
SITE_HTML = ROOT_DIR / "export/site/index.html"
PRINT_CSS = ROOT_DIR / "export/pdf/course-print.css"
OUTPUT_PDF = ROOT_DIR / "export/pdf/course-site.pdf"


def render_mermaid_blocks(site_html: str, work_dir: Path) -> str:
    mermaid_dir = work_dir / "mermaid"
    mermaid_dir.mkdir(parents=True, exist_ok=True)
    puppeteer_cfg = work_dir / "puppeteer-config.json"
    puppeteer_cfg.write_text('{"args":["--no-sandbox"]}', encoding="utf-8")

    pattern = re.compile(r"<pre class=\"mermaid\">(.*?)</pre>", re.DOTALL)
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        mermaid_source = html.unescape(match.group(1)).strip()
        src_path = mermaid_dir / f"diagram-{counter:02d}.mmd"
        out_path = mermaid_dir / f"diagram-{counter:02d}.svg"
        src_path.write_text(mermaid_source, encoding="utf-8")

        subprocess.run(
            [
                "mmdc",
                "-i",
                str(src_path),
                "-o",
                str(out_path),
                "-b",
                "transparent",
                "-p",
                str(puppeteer_cfg),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        rel_path = out_path.relative_to(work_dir).as_posix()
        return (
            '<div class="pdf-mermaid-wrap">'
            f'<img class="pdf-mermaid" src="{rel_path}" alt="Diagramme Mermaid {counter}" />'
            '</div>'
        )

    return pattern.sub(repl, site_html)


def strip_runtime_assets(site_html: str) -> str:
    site_html = re.sub(r"<script[^>]*>.*?</script>", "", site_html, flags=re.DOTALL)
    site_html = re.sub(
        r'<script[^>]+src="[^"]+"[^>]*></script>',
        "",
        site_html,
        flags=re.DOTALL,
    )
    site_html = re.sub(
        r'<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js[^"]+">',
        "",
        site_html,
    )
    site_html = re.sub(
        r'<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>',
        "",
        site_html,
    )
    return site_html


def main() -> None:
    if not SITE_HTML.exists():
        raise FileNotFoundError(f"Site HTML not found: {SITE_HTML}")

    source_html = SITE_HTML.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="course_pdf_") as tmp:
        work_dir = Path(tmp)
        html_with_svgs = render_mermaid_blocks(source_html, work_dir)
        final_html = strip_runtime_assets(html_with_svgs)
        temp_html = work_dir / "course-print.html"
        temp_html.write_text(final_html, encoding="utf-8")

        print("Génération du PDF du cours depuis le site...")
        HTML(filename=str(temp_html), base_url=str(ROOT_DIR / "export/site")).write_pdf(
            str(OUTPUT_PDF),
            stylesheets=[CSS(filename=str(PRINT_CSS))],
        )
        print(f"  PDF généré : {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
