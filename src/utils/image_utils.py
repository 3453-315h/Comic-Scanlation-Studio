"""
Image processing utilities bridging OpenCV, PIL, and PyQt6.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Union
from PIL import Image

from PySide6.QtGui import QPixmap, QImage


def load_image(path: Union[str, Path]) -> np.ndarray:
    """
    Load image from file path using OpenCV.
    Returns: BGR numpy array
    """
    # Use cv2.imdecode to handle unicode paths better on Windows if needed, 
    # but standard imread is usually fine if path is str
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    image = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    
    if image is None:
        raise ValueError(f"Failed to load image: {path}")
        
    # Handle alpha channel if present (convert to BGR)
    if len(image.shape) == 3 and image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        
    return image


def save_image(image: np.ndarray, path: Union[str, Path]) -> None:
    """
    Save image to file path using Pillow (safer than cv2.imwrite for segfaults).
    Input: BGR numpy array
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert BGR to RGB for Pillow
        if len(image.shape) == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image
            
        # Use Pillow to save
        pil_img = Image.fromarray(rgb_image)
        pil_img.save(str(path))
        print(f"DEBUG: Saved image successfully with Pillow: {path}")
        
    except Exception as e:
        print(f"DEBUG: save_image (Pillow) failed: {e}")
        raise


def to_qpixmap(image: np.ndarray) -> QPixmap:
    """
    Convert OpenCV BGR numpy array to QPixmap.
    FIX: Creates copy to prevent data lifetime issues & missing cv2 import
    """
    # Create a copy to ensure data buffer persists after numpy array is garbage collected
    image_copy = image.copy()
    
    height, width = image_copy.shape[:2]
    
    if len(image_copy.shape) == 2:  # Grayscale
        bytes_per_line = width
        qimage = QImage(
            image_copy.data, width, height, bytes_per_line, 
            QImage.Format.Format_Grayscale8
        )
    else:  # BGR
        channels = image_copy.shape[2]
        bytes_per_line = channels * width
        qimage = QImage(
            image_copy.data, width, height, bytes_per_line, 
            QImage.Format.Format_BGR888
        )
    
    return QPixmap.fromImage(qimage)


def extract_roi(image: np.ndarray, bbox: list) -> np.ndarray:
    """
    Extract region of interest from image using bounding box.
    bbox: [x1, y1, x2, y2]
    Returns: Copied ROI to prevent modifying original
    """
    x1, y1, x2, y2 = bbox
    # Ensure coordinates are within bounds
    h, w = image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    # Return a copy to avoid reference issues
    return image[y1:y2, x1:x2].copy()


def resize_maintaining_aspect(image: np.ndarray, max_size: int) -> np.ndarray:
    """
    Resize image so its longest side is max_size, preserving aspect ratio.
    """
    h, w = image.shape[:2]
    if max(h, w) <= max_size:
        return image
    
    scale = max_size / max(h, w)
    new_size = (int(w * scale), int(h * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def extract_archive(archive_path: Path, output_dir: Path) -> list[Path]:
    """
    Extract images from an archive (zip/cbz or rar/cbr).
    Tries to open as ZIP first (handles .cbz and misnamed .cbr).
    Falls back to patool for true RAR/CBR files.
    Returns list of extracted image paths.
    """
    import zipfile
    import shutil
    
    archive_path = Path(archive_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    extracted_files = []
    
    # helper to check if file is a valid zip (regardless of extension)
    def _is_within(base: Path, target: Path) -> bool:
        """Return True if target is inside base (after resolving)."""
        try:
            target.resolve().relative_to(base.resolve())
            return True
        except Exception:
            return False

    def try_extract_zip(path, out):
        """Safely extract a zip/cbz into out, preventing path traversal."""
        try:
            if not zipfile.is_zipfile(path):
                return False

            with zipfile.ZipFile(path, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    # Skip directories explicitly
                    if member.is_dir():
                        continue

                    member_path = Path(member.filename)

                    # Reject absolute or parent-traversing paths
                    dest_path = (out / member_path).resolve()
                    if not _is_within(out, dest_path):
                        raise ValueError(f"Unsafe archive entry blocked: {member.filename}")

                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(member, 'r') as src, open(dest_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
            return True
        except Exception as e:
            print(f"ERROR: zip extraction failed: {e}")
            return False

    try:
        # 1. Try as ZIP first (fastest, handles CBZ and misnamed CBR)
        if try_extract_zip(archive_path, output_dir):
            pass # Success
            
        # 2. If not a ZIP, try patool (handles generic formats like RAR/CBR)
        else:
            try:
                import patoolib
                # patool output is noisy, maybe suppress?
                patoolib.extract_archive(str(archive_path), outdir=str(output_dir), verbosity=-1)
            except ImportError:
                print("ERROR: patool not installed. Cannot extract non-ZIP archive.")
                return []
            except Exception as e:
                print(f"ERROR: patool extraction failed: {e}")
                return []

        # 3. Collect valid images (recursively)
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        for file_path in output_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in valid_exts:
                # Ignore MacOS metadata
                if '__MACOSX' in file_path.parts or file_path.name.startswith('._'):
                    continue
                extracted_files.append(file_path)
                
        # Sort by filename naturally to keep page order
        extracted_files.sort(key=lambda x: str(x))
        return extracted_files

    except Exception as e:
        print(f"Archive extraction failed: {e}")
        return []


def create_cbz(image_paths: list[Path], output_path: Path) -> bool:
    """
    Create a .cbz archive from a list of images.
    """
    import zipfile
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, img_path in enumerate(image_paths):
                # Use sequential numbering to ensure reader order (001.jpg, 002.jpg)
                arcname = f"{i+1:03d}{img_path.suffix}"
                zf.write(img_path, arcname=arcname)
        return True
    except Exception as e:
        print(f"Failed to create CBZ: {e}")
        return False


def create_pdf(image_paths: list[Path], output_path: Path) -> bool:
    """
    Create a PDF from a list of images using img2pdf.
    """
    import img2pdf
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # img2pdf writes directly to file handle
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in image_paths]))
        return True
    except Exception as e:
        print(f"Failed to create PDF: {e}")
        return False
