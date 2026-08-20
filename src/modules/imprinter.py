"""
Text Imprinting Module - Comic Translation Studio

Renders translated text onto inpainted comic pages using Qt's native text rendering.
Uses QPainter and QFont for stable, crash-free text rendering.

Based on analysis of BallonsTranslator's rendering approach.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging
import re

# Text processing
try:
    import pyphen
    HYPHENATION_AVAILABLE = True
except ImportError:
    HYPHENATION_AVAILABLE = False

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QImage, QPainter, QFont, QFontMetrics, QColor, QPen, QFontDatabase,
    QTextDocument, QTextOption, QAbstractTextDocumentLayout, QTextLayout
)

logger = logging.getLogger(__name__)


def numpy_to_qimage(img: np.ndarray) -> QImage:
    """Convert a BGR numpy array to QImage."""
    if img is None or img.size == 0:
        return QImage()
    
    # Ensure contiguous memory
    if not img.flags['C_CONTIGUOUS']:
        img = np.ascontiguousarray(img)
    
    height, width = img.shape[:2]
    
    if len(img.shape) == 2:
        # Grayscale
        bytes_per_line = width
        return QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8).copy()
    elif img.shape[2] == 3:
        # BGR -> RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * width
        return QImage(img_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).copy()
    elif img.shape[2] == 4:
        # BGRA -> RGBA
        img_rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        bytes_per_line = 4 * width
        return QImage(img_rgba.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888).copy()
    
    return QImage()


def qimage_to_numpy(qimg: QImage) -> np.ndarray:
    """Convert a QImage to a BGR numpy array."""
    if qimg.isNull():
        return np.array([])
    
    # Convert to RGB888 format
    qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
    
    width = qimg.width()
    height = qimg.height()
    bytes_per_line = qimg.bytesPerLine()
    
    # Get the raw data
    ptr = qimg.constBits()
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, bytes_per_line)
    arr = arr[:, :width*3].reshape(height, width, 3).copy()
    
    # Convert RGB to BGR for OpenCV
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


@dataclass
class FontStyle:
    """Typography settings for text imprinting"""
    font_family: str = "Arial"
    font_size: int = 24
    font_weight: str = "normal"  # normal, bold
    color: Tuple[int, int, int] = (0, 0, 0)  # BGR
    background_color: Optional[Tuple[int, int, int, int]] = None  # BGRA, None = transparent
    alignment: str = "center"  # left, center, right
    line_height: float = 1.2
    letter_spacing: int = 0
    casing: str = "preserve"  # preserve, upper, lower
    padding: int = 15  # minimum pixels from bubble edge
    padding_percent: float = 0.12  # dynamic padding as % of bubble size (for curved bubbles)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "color": self.color,
            "background_color": self.background_color,
            "alignment": self.alignment,
            "line_height": self.line_height,
            "letter_spacing": self.letter_spacing,
            "casing": self.casing,
            "padding": self.padding
        }


class TextImprinter:
    """
    Renders translated text onto inpainted comic images using Qt.
    
    Features:
    - Auto-fit font size to bubble bounds
    - Multi-line text wrapping via QTextDocument (Standard + HTML Support)
    - Configurable alignment and styling
    - Crash-free rendering via Qt's native text engine
    """
    
    # Common comic fonts (fallback order)
    COMIC_FONTS = [
        "CC Wild Words",
        "Comic Sans MS", 
        "Anime Ace",
        "Badaboom",
        "Bangers",
        "Arial",
        "DejaVu Sans"
    ]
    
    def __init__(self, default_style: Optional[FontStyle] = None, hyphenation_lang: str = 'en_US'):
        """
        Initialize the text imprinter.
        
        Args:
            default_style: Default font style for text rendering
            hyphenation_lang: Language code for hyphenation (e.g., 'en_US', 'de_DE')
        """
        self.default_style = default_style or FontStyle()
        self._font_cache: Dict[str, QFont] = {}
        
        # Initialize hyphenator for shape-aware wrapping
        self._hyphenator = None
        if HYPHENATION_AVAILABLE:
            try:
                self._hyphenator = pyphen.Pyphen(lang=hyphenation_lang)
                logger.debug(f"Hyphenation enabled for language: {hyphenation_lang}")
            except Exception as e:
                logger.warning(f"Failed to initialize hyphenation: {e}")
        
    def _get_font(self, family: str, size: int, weight: str = "normal") -> QFont:
        """Get or create a QFont."""
        cache_key = f"{family}_{size}_{weight}"
        
        if cache_key not in self._font_cache:
            font = QFont(family, size)
            if weight == "bold":
                font.setBold(True)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            self._font_cache[cache_key] = font
                
        return self._font_cache[cache_key]
        
    def _is_comic_style(self, contours) -> bool:
        """Heuristic to guess if text is hand-written/comic style based on irregularity"""
        return True
    
    def load_custom_fonts(self, font_dir: Path):
        """
        Load custom fonts from a directory using QFontDatabase.
        """
        if not font_dir.exists():
            return
            
        count = 0
        for font_file in font_dir.glob("*.[ot]tf"): # .otf or .ttf
            try:
                id = QFontDatabase.addApplicationFont(str(font_file))
                if id != -1:
                    families = QFontDatabase.applicationFontFamilies(id)
                    logger.info(f"Loaded custom font: {families}")
                    count += 1
            except Exception as e:
                logger.error(f"Failed to load font {font_file}: {e}")
                
        if count > 0:
            logger.info(f"Loaded {count} custom fonts from {font_dir}")

    def _calculate_auto_font_size(self,
                                   text: str,
                                   font_family: str,
                                   font_weight: str,
                                   max_width: int,
                                   max_height: int,
                                   line_height: float,
                                   min_size: int = 8,
                                   max_size: int = 72) -> int:
        """
        Find the largest font size that fits text in bounds using QTextDocument.
        """
        best_size = min_size
        
        # Binary search for optimal size
        low, high = min_size, max_size
        
        doc = QTextDocument()
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere) # Similar to CSS break-word
        doc.setDefaultTextOption(option)
        
        while low <= high:
            mid = (low + high) // 2
            
            # Setup standard font for measurement
            font = self._get_font(font_family, mid, font_weight)
            doc.setDefaultFont(font)
            doc.setTextWidth(max_width)
            
            # Set text (check if html or plain)
            if '<' in text and '>' in text:
                doc.setHtml(text)
            else:
                doc.setPlainText(text)
            
            # Check height
            total_height = doc.size().height()
            
            # Also check if any word is wider than max_width (optional, but handled by wrap mode)
            # Actually wrap mode handles it.
            
            if total_height <= max_height:
                best_size = mid
                low = mid + 1
            else:
                high = mid - 1
                
        return best_size

    def _calculate_auto_font_size_elliptical(self, text: str, font_family: str, font_weight: str, max_width: int, max_height: int, line_height: float, min_size: int = 8, max_size: int = 72) -> int:
        best_size = min_size
        low, high = min_size, max_size
        while low <= high:
            mid = (low + high) // 2
            font = self._get_font(font_family, mid, font_weight)
            used_height = self._render_text_elliptical(painter=None, text=text, font=font, rect_w=max_width, rect_h=max_height, color=(0,0,0), alignment='center', line_height_mult=line_height)
            if used_height <= max_height:
                best_size = mid
                low = mid + 1
            else:
                high = mid - 1
        return best_size

    def imprint(self, 
                image: np.ndarray, 
                bubbles: List[Any], 
                style: Optional[FontStyle] = None,
                auto_fit: bool = True,
                original_image: Optional[np.ndarray] = None,
                use_detected_style: bool = False,
                use_elliptical_wrapping: bool = False) -> np.ndarray:
        """
        Imprint text into the image bubbles.
        """
        if not bubbles:
            return image
            
        # Convert to QImage for painting
        q_img = numpy_to_qimage(image)
        if q_img.isNull():
            logger.error("Failed to convert image for imprinting")
            return image
            
        painter = QPainter(q_img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Use default style if none provided
        base_style = style or self.default_style
        
        img_height, img_width = image.shape[:2]
        
        for bubble in bubbles:
            if not bubble.text_translated:
                continue
                
            # Get bubble bounds
            if not bubble.bbox or len(bubble.bbox) != 4:
                continue
                
            x1, y1, x2, y2 = map(int, bubble.bbox)
            
            # Clamp to image
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_width, x2), min(img_height, y2)
            
            w = x2 - x1
            h = y2 - y1
            
            if w <= 0 or h <= 0:
                continue

            # Apply padding
            padding = base_style.padding
            if base_style.padding_percent > 0:
                padding = max(padding, int(min(w, h) * base_style.padding_percent))
                
            text_rect_w = w - 2*padding
            text_rect_h = h - 2*padding
            
            if text_rect_w <= 0 or text_rect_h <= 0:
                continue
                
            # Determine font size & Setup Document
            font_size = base_style.font_size
            
            # If bubble has its own font size preference (from manual editing), respect it?
            # Imprinting usually overrides manual size in favor of batch settings unless specified.
            # But here we want to support manual edit results. 
            # If bubble.font_size exists and is valid, user might have set it.
            # However, auto_fit argument usually dictates behavior.
            
            if auto_fit:
                if use_elliptical_wrapping:
                    font_size = self._calculate_auto_font_size_elliptical(bubble.text_translated, base_style.font_family, base_style.font_weight, text_rect_w, text_rect_h, base_style.line_height)
                else:
                    font_size = self._calculate_auto_font_size(bubble.text_translated, base_style.font_family, base_style.font_weight, text_rect_w, text_rect_h, base_style.line_height)
            
            # Prepare Document
            doc = QTextDocument()
            font = self._get_font(base_style.font_family, font_size, base_style.font_weight)
            doc.setDefaultFont(font)
            doc.setTextWidth(text_rect_w)
            
            # Text Color
            # CSS styling for color if using setHtml
            c = base_style.color
            color_css = f"rgb({c[2]}, {c[1]}, {c[0]})" # BGR -> RGB
            
            # Alignment
            # Note: For HTML, we might need a wrapper div for alignment
            align_css = "center"
            if base_style.alignment == "left": align_css = "left"
            if base_style.alignment == "right": align_css = "right"
            
            # Set Content
            # Wrap in color/alignment div
            # Check if likely HTML already
            is_html = '<' in bubble.text_translated and '>' in bubble.text_translated
            
            if is_html:
                # Inject color/alignment into a wrapper if not present?
                # Just wrap standardly
                html_content = f"""
                <div style='color: {color_css}; text-align: {align_css}; font-family: "{base_style.font_family}"; font-size: {font_size}pt;'>
                    {bubble.text_translated}
                </div>
                """
                doc.setHtml(html_content)
            else:
                # Plain text, use document properties for alignment/color
                # Actually, QTextDocument default color is tricky. Better use CSS wrapper too.
                # Escape special chars? setHtml does it if we don't.
                # But setPlainText doesn't support color/alignment easily on doc level without options.
                # Converting to HTML wrapper is safest.
                import html
                escaped_text = html.escape(bubble.text_translated).replace('\n', '<br>')
                html_content = f"""
                <div style='color: {color_css}; text-align: {align_css}; font-family: "{base_style.font_family}"; font-size: {font_size}pt;'>
                    {escaped_text}
                </div>
                """
                doc.setHtml(html_content)

            # Center Vertically
            doc_height = doc.size().height()
            y_offset = (text_rect_h - doc_height) / 2
            
            # Save painter state
            painter.save()
            
            if use_elliptical_wrapping:
                # Use new elliptical renderer
                # Translate to top-left of rect (padding handled inside or we pass rect dimensions)
                # _render_text_elliptical expects rect_w, rect_h and translates to center itself from (0,0)?
                # No, it translates painter by (w/2, h/2). 
                # So we should translate painter to (x1+padding, y1+padding) first?
                # Let's check _render_text_elliptical logic:
                # "painter.translate(rect_w/2, rect_h/2)" - implies it starts at 0,0 of the rect.
                
                painter.translate(x1 + padding, y1 + padding)
                
                self._render_text_elliptical(
                    painter,
                    bubble.text_translated,
                    font,
                    text_rect_w,
                    text_rect_h,
                    base_style.color,
                    base_style.alignment
                )
            else:
                # Standard Rectangular Rendering
                painter.translate(x1 + padding, y1 + padding + y_offset)
                doc.drawContents(painter)
            
            painter.restore()
                
        painter.end()
        return qimage_to_numpy(q_img)
    
    def detect_bubble_style(self, image: np.ndarray, bubble: Any) -> FontStyle:
        """Detect font style for a single bubble."""
        return self.default_style
    
    def analyze_style(self, image: np.ndarray, bubbles: List[Any]) -> FontStyle:
        """
        Analyze overall text style from the original image.
        """
        # 1. Choose Font
        chosen_font = self.default_style.font_family
        available_families = QFontDatabase.families()
        for font in self.COMIC_FONTS:
            if font in available_families:
                chosen_font = font
                break
        
        # 2. Detect Color (Black or White text?)
        text_color = (0, 0, 0) # Default Black
        if bubbles:
            samples = 0
            dark_bubbles = 0
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            for b in bubbles[:5]: 
                x1, y1, x2, y2 = map(int, b.bbox)
                w, h = x2-x1, y2-y1
                cx1, cy1 = x1 + w//4, y1 + h//4
                cx2, cy2 = cx1 + w//2, cy1 + h//2
                if cx1 >= cx2 or cy1 >= cy2: continue
                
                roi = gray[cy1:cy2, cx1:cx2]
                if roi.size == 0: continue
                bright = np.mean(roi)
                if bright < 80:
                    dark_bubbles += 1
                samples += 1
            
            if samples > 0 and (dark_bubbles / samples) > 0.5:
                text_color = (255, 255, 255)
                logger.info("Detected dark bubbles: Using WHITE text")
            else:
                logger.info("Detected bright bubbles: Using BLACK text")

        return FontStyle(
            font_family=chosen_font,
            font_size=self.default_style.font_size,
            color=text_color,
            padding=self.default_style.padding,
            line_height=self.default_style.line_height
        )

    def _hyphenate_word(self, word: str, max_width: float, font: QFont) -> List[str]:
        """
        Break a word using hyphenation if it exceeds max_width.
        
        Args:
            word: Word to potentially hyphenate
            max_width: Maximum allowed width in pixels
            font: Font for measuring text width
            
        Returns:
            List of word fragments (may be single item if no hyphenation needed)
        """
        if not self._hyphenator:
            return [word]
            
        metrics = QFontMetrics(font)
        word_width = metrics.horizontalAdvance(word)
        
        # If word fits, no need to hyphenate
        if word_width <= max_width:
            return [word]
        
        # Get hyphenation points
        pairs = self._hyphenator.pairs(word)
        if not pairs:
            return [word]
        
        # Find the longest prefix that fits with hyphen
        for left, right in pairs:
            left_with_hyphen = left + "-"
            if metrics.horizontalAdvance(left_with_hyphen) <= max_width:
                # Recursively check if remaining part needs hyphenation too
                remaining = self._hyphenate_word(right, max_width, font)
                return [left_with_hyphen] + remaining
        
        # No hyphenation point fits, return original
        return [word]

    def _render_text_elliptical(self, 
                                painter, 
                                text: str, 
                                font: QFont, 
                                rect_w: int, 
                                rect_h: int, 
                                color: Tuple[int, int, int], 
                                alignment: str,
                                line_height_mult: float = 1.2) -> float:
        """
        Render text fitting into an ellipse defined by rect_w/rect_h.
        
        Features:
        - Uses word hyphenation for better text flow (via pyphen)
        - Variable line widths based on ellipse geometry
        - Preserves italic/bold HTML tags where possible
        
        Returns total height used.
        """
        # Ellipse equation: (x/a)^2 + (y/b)^2 = 1
        # width at y: x = a * sqrt(1 - (y/b)^2)
        # total width = 2*x
        
        a = rect_w / 2
        b = rect_h / 2
        
        # Extract and preserve simple formatting tags, store positions
        # For now, strip HTML for layout calculation
        clean_text = re.sub(r'<[^<]+?>', '', text)
        
        metrics = QFontMetrics(font)
        line_height = metrics.height() * line_height_mult
        
        # Word-wrap with hyphenation support
        words = clean_text.split()
        
        # First pass: estimate total height to find starting Y
        lines_content: List[str] = []
        current_line = ""
        
        # Use center width for estimation
        est_width = rect_w * 0.8
        
        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            if metrics.horizontalAdvance(test_line) <= est_width:
                current_line = test_line
            else:
                if current_line:
                    lines_content.append(current_line)
                current_line = word
        if current_line:
            lines_content.append(current_line)
        
        estimated_height = len(lines_content) * line_height
        start_y = -estimated_height / 2
        
        # Second pass: actual layout with elliptical widths and hyphenation
        final_lines: List[Tuple[str, float, float]] = []  # (text, x, y)
        word_index = 0
        y = start_y
        pending_fragment = ""  # For hyphenated word fragments
        
        while word_index < len(words) or pending_fragment:
            # Check if y is within ellipse bounds
            if abs(y) >= b:
                break
            
            # Calculate available width at this y
            try:
                val = 1 - (y / b) ** 2
                if val < 0:
                    val = 0
                width_at_y = 2 * a * np.sqrt(val) * 0.9  # 10% padding
            except:
                width_at_y = 10
            
            available_width = max(10, width_at_y)
            
            # Build line with words that fit
            current_line = ""
            line_complete = False
            
            while not line_complete:
                # Get next word (or pending fragment from hyphenation)
                if pending_fragment:
                    word = pending_fragment
                    pending_fragment = ""
                    from_pending = True
                elif word_index < len(words):
                    word = words[word_index]
                    from_pending = False
                else:
                    line_complete = True
                    break
                
                # Try to add word to current line
                test_line = f"{current_line} {word}".strip() if current_line else word
                test_width = metrics.horizontalAdvance(test_line)
                
                if test_width <= available_width:
                    current_line = test_line
                    if not from_pending:
                        word_index += 1
                else:
                    # Word doesn't fit
                    if current_line:
                        # Line has content, finalize it
                        if from_pending:
                            pending_fragment = word
                        line_complete = True
                    else:
                        # Empty line but word still doesn't fit - try hyphenation
                        fragments = self._hyphenate_word(word, available_width, font)
                        
                        if len(fragments) > 1 and metrics.horizontalAdvance(fragments[0]) <= available_width:
                            current_line = fragments[0]
                            pending_fragment = "".join(fragments[1:]).lstrip("-")
                            if not from_pending:
                                word_index += 1
                            line_complete = True
                        else:
                            # Can't hyphenate, force the word and move on
                            current_line = word
                            if not from_pending:
                                word_index += 1
                            line_complete = True
            
            if current_line:
                # Center the line horizontally
                line_width = metrics.horizontalAdvance(current_line)
                if line_width > available_width:
                    return float('inf')
                x = -line_width / 2
                final_lines.append((current_line, x, y))
                y += line_height
        
        if word_index < len(words) or pending_fragment:
            return float('inf')

        if painter is not None:
            painter.save()
            painter.translate(rect_w / 2, rect_h / 2)
            text_pen = QPen(QColor(*color))
            painter.setPen(text_pen)
            painter.setFont(font)
            for line_text, x, line_y in final_lines:
                painter.drawText(QPointF(x, line_y + metrics.ascent()), line_text)
            painter.restore()

        return y - start_y

def imprint_text(image: np.ndarray, 
                 bubbles: List[Any],
                 font_family: str = "Arial",
                 font_size: int = 24,
                 color: Tuple[int, int, int] = (0, 0, 0),
                 auto_fit: bool = True) -> np.ndarray:
    """Conventional convenience function."""
    style = FontStyle(
        font_family=font_family,
        font_size=font_size,
        color=color
    )
    imprinter = TextImprinter(default_style=style)
    return imprinter.imprint(image, bubbles, style, auto_fit)
