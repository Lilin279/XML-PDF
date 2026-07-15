"""Figure path resolution — maps JATS graphic hrefs to local filesystem paths."""

import os
import base64
import mimetypes
import zipfile
from pathlib import Path
from typing import Optional


class FigureResolver:
    """Resolve JATS <graphic xlink:href="..."> references to actual image files.

    Searches for figures in multiple directories, supporting both
    flat and nested directory structures as well as zip archives.
    """

    def __init__(self, search_dirs: Optional[list] = None):
        """Initialize with optional list of search directories.

        Args:
            search_dirs: List of Path or str directories to search for figures.
                         If None, no additional search paths are configured.
        """
        self.search_dirs = [Path(d) for d in (search_dirs or [])]

    def add_search_dir(self, directory):
        """Add a directory to search for figures."""
        self.search_dirs.append(Path(directory))

    def find(self, href: str) -> Optional[Path]:
        """Resolve a graphic href to an actual file path.

        Search strategies (tried in order):
        1. Exact path relative to each search directory
        2. Filename-only match (strip directory prefix from href)
        3. Case-insensitive filename match
        4. Search inside .zip files in search directories

        Args:
            href: The xlink:href value from <graphic> element,
                  e.g., "RCM46777/fig1.jpg"

        Returns:
            Path to the found image file, or None if not found.
        """
        if not href:
            return None

        filename = Path(href).name

        for search_dir in self.search_dirs:
            if not search_dir.exists():
                continue

            # Strategy 1: Exact path relative to search_dir
            candidate = search_dir / href
            if candidate.exists():
                return candidate

            # Strategy 2: Try without the first directory component
            # e.g., "RCM46777/fig1.jpg" -> try just "fig1.jpg"
            candidate = search_dir / filename
            if candidate.exists():
                return candidate

            # Strategy 3: Recursive search by filename
            for found in search_dir.rglob(filename):
                return found

            # Strategy 4: Case-insensitive search
            for found in search_dir.rglob('*'):
                if found.name.lower() == filename.lower():
                    return found

            # Strategy 5: Fuzzy filename match (fig-01.jpg vs fig1.jpg)
            for found in search_dir.rglob('*'):
                if found.is_file() and self._fuzzy_match(
                    found.name.lower(), filename.lower()
                ):
                    return found

            # Strategy 6: Search inside zip files
            for zip_path in search_dir.glob("*.zip"):
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        for name in zf.namelist():
                            if Path(name).name == filename:
                                # Extract to temp location
                                extract_dir = search_dir / "_extracted"
                                extract_dir.mkdir(exist_ok=True)
                                extracted = extract_dir / filename
                                if not extracted.exists():
                                    zf.extract(name, extract_dir)
                                    # If extracted into subdir, move it
                                    actual = extract_dir / name
                                    if actual != extracted and actual.exists():
                                        import shutil
                                        shutil.move(str(actual), str(extracted))
                                return extracted
                except (zipfile.BadZipFile, OSError):
                    continue

        return None

    def resolve_to_uri(self, href: str) -> Optional[str]:
        """Resolve a graphic href to a file:// URI string.

        Args:
            href: The xlink:href value from <graphic> element.

        Returns:
            file:// URI string, or None if not found.
        """
        path = self.find(href)
        if path is None:
            return None
        return path.as_uri()

    def resolve_to_data_uri(self, href: str) -> Optional[str]:
        """Resolve a graphic href to a base64 data URI.

        This produces a self-contained data URI suitable for
        embedding in HTML that WeasyPrint can render without
        external file dependencies.

        Args:
            href: The xlink:href value from <graphic> element.

        Returns:
            data:image/...;base64,... string, or None if not found.
        """
        path = self.find(href)
        if path is None:
            return None
        return self._file_to_data_uri(path)

    @staticmethod
    def _fuzzy_match(actual: str, expected: str) -> bool:
        """Fuzzy filename match: fig-01.jpg matches fig1.jpg."""
        import re
        # Normalize: strip hyphens, zero-padding, underscores
        def norm(s):
            s = re.sub(r'[-_]', '', s)           # fig-01 -> fig01
            s = re.sub(r'0+(\d+)', r'\1', s)      # fig01 -> fig1
            return s
        return norm(actual) == norm(expected)

    @staticmethod
    def _file_to_data_uri(file_path: Path, max_width: int = 1600,
                          jpeg_quality: int = 85) -> str:
        """Convert an image file to a compressed base64 data URI.

        Resizes large images and recompresses to keep PDF size manageable.
        """
        from PIL import Image
        import io

        img = Image.open(file_path)

        # Convert RGBA/P to RGB for JPEG compression
        if img.mode in ('RGBA', 'P', 'LA'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img

        # Resize if wider than max_width
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Compress to JPEG in memory
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
        compressed = buf.getvalue()

        encoded = base64.b64encode(compressed).decode('ascii')
        return f'data:image/jpeg;base64,{encoded}'


def auto_detect_figure_dir(xml_path) -> Optional[Path]:
    """Auto-detect the figure directory based on XML file location.

    Looks for common patterns:
    - ./figure/ or ./figures/ next to the XML
    - ./figure.zip or ./figures.zip next to the XML
    - ./ (same directory as XML)

    Args:
        xml_path: Path to the JATS XML file.

    Returns:
        Detected figure directory path, or None.
    """
    xml_dir = Path(xml_path).parent

    # Check for figure directories
    for name in ['figures', 'figure', 'figs', 'images']:
        candidate = xml_dir / name
        if candidate.is_dir():
            return candidate

    # Check for extracted zip contents
    for name in ['figures', 'figure']:
        candidate = xml_dir / f"{name}_extracted"
        if candidate.is_dir():
            return candidate

    # The XML directory itself might contain the images
    return xml_dir
