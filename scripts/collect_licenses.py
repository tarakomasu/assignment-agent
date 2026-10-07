"""Copy Python dependency license notices into the release."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

target = Path(sys.argv[1]) / "python"
for package in ("python-docx", "lxml", "playwright", "pypdf", "greenlet", "pyee", "typing_extensions", "pyinstaller"):
    dist = importlib.metadata.distribution(package)
    folder = target / package
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "METADATA.txt").write_text(str(dist.metadata), encoding="utf-8")
    for file in dist.files or []:
        if "license" in str(file).lower() or "copying" in str(file).lower():
            source = Path(dist.locate_file(file))
            if source.is_file():
                shutil.copy2(source, folder / source.name)
