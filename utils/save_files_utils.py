import os
import subprocess
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger("file_saver")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [FileSaver] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


import re

def format_for_markdown(content: str) -> str:
    """
    Format content for better markdown rendering by:
    - Converting custom bullets (• 1., • 2., etc.) to Markdown numbered list format
    - Adding proper spacing
    """
    lines = content.split('\n')
    formatted_lines = []
    for line in lines:
        # Convert lines starting with "• <number>." to markdown-style numbered list
        match = re.match(r"•\s*(\d+)\.\s*(.*)", line)
        if match:
            number, text = match.groups()
            formatted_lines.append(f"{number}. {text}")
        else:
            formatted_lines.append(line)
    
    # Join with double newlines to ensure bullet spacing
    return "\n\n".join(formatted_lines)

def save_as_md(content: str, filename: str, dir_path: Path) -> Path:
    if filename.endswith('.txt'):
        filename = filename.replace('.txt', '.md')
    path = dir_path / filename

    formatted_content = format_for_markdown(content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(formatted_content)

    logger.info(f"Saved MD file at {path}")
    return path


def save_as_txt(content: str, filename: str, dir_path: Path) -> Path:
    path = dir_path / filename
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"Saved TXT file at {path}")
    return path

# def save_as_md(content: str, filename: str, dir_path: Path) -> Path:
#     if filename.endswith('.txt'):
#         filename = filename.replace('.txt', '.md')
#     path = dir_path / filename
#     with open(path, 'w', encoding='utf-8') as f:
#         f.write(content)
#     logger.info(f"Saved MD file at {path}")
#     return path

def render_pdf_with_quarto(md_path: Path, pdf_path: Path):
    try:
        md_dir = md_path.parent
        md_filename = md_path.name
        pdf_filename = pdf_path.name

        # Quarto render command with PDF output and TOC
        cmd = [
            "quarto",
            "render",
            md_filename,
            "--to", "pdf",
            "--output", pdf_filename,
            "--toc"
        ]

        subprocess.run(cmd, check=True, cwd=str(md_dir))
        logger.info(f"Rendered PDF using Quarto at {pdf_path}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Quarto rendering failed: {e}")

def save_document_all_formats(content: str, filename: str, subdir: str, base_dir: Path) -> Dict[str, Path]:
    dir_path = base_dir / subdir
    os.makedirs(dir_path, exist_ok=True)
    logger.info(f"Saving documents in directory: {dir_path}")

    paths = {}
    paths['txt'] = save_as_txt(content, filename, dir_path)
    paths['md'] = save_as_md(content, filename, dir_path)
    
    # Render PDF using Quarto from MD
    pdf_filename = filename.replace('.txt', '.pdf')
    pdf_path = dir_path / pdf_filename
    render_pdf_with_quarto(paths['md'], pdf_path)
    paths['pdf'] = pdf_path

    logger.info(f"All files saved: {paths}\n\n")
    return paths
