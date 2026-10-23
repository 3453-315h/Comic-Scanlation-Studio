"""
Inpainting Module - Comic Translation Studio

Implements text removal/inpainting using:
- LaMa (AI) - High quality results, requires model download (~200MB)
- OpenCV algorithms - Fast, no download required

Available Methods:
- lama: LaMa AI inpainting (best quality)
- telea: OpenCV Fast Marching Method - Fast, good for small regions
- ns: OpenCV Navier-Stokes - Slower, better for larger regions
- hybrid: Auto-select telea/ns based on region size
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class Inpainter:
    """Unified inpainting interface supporting multiple backends
    
    Features:
    - Multiple backends: LaMa (AI), OpenCV (Telea/NS)
    - Intelligent text mask detection
    - Guided inpainting with text-color-aware mask expansion
    - Mask edge blurring to reduce ghosting artifacts
    """
    
    METHODS = ["lama", "telea", "ns", "hybrid"]
    
    def __init__(self, 
                 method: str = "lama", 
                 mask_dilation: int = 5, 
                 protect_borders: bool = True,
                 guided_mode: bool = True,
                 mask_blur: int = 5,
                 whiten_mode: bool = False):
        """Initialize inpainter with specified method
        
        Args:
            method: "lama", "telea", "ns", or "hybrid"
            mask_dilation: Pixels to expand mask by
            protect_borders: Whether to avoid erasing detected bubble borders
            guided_mode: Use text-color-aware mask expansion to reduce ghosting
            mask_blur: Gaussian blur kernel size for mask edges (0 to disable)
            whiten_mode: If True, fills the inpaint region with pure white instead of using the model.
        """
        self.method = method.lower()
        self.lama_model = None
        
        # Parameters
        self.inpaint_radius = 5
        self.mask_dilation = mask_dilation
        self.protect_borders = protect_borders
        self.guided_mode = guided_mode
        self.mask_blur = mask_blur if mask_blur % 2 == 1 else mask_blur + 1  # Must be odd for GaussianBlur
        self.whiten_mode = whiten_mode
        self.telea_max_area = 10000
        
        # Try to load LaMa if requested
        if self.method == "lama":
            self._load_lama()
        
        logger.info(f"Initialized inpainter (method={self.method}, dilation={self.mask_dilation}, guided={self.guided_mode})")
    
    def _load_lama(self):
        """Load LaMa model"""
        try:
            # Lazy import SimpleLama to avoid startup conflicts
            from simple_lama_inpainting import SimpleLama
            # The following imports are already at the top level and are needed globally.
            # Moving them here would cause NameErrors in other parts of the class.
            # import cv2
            # import numpy as np
            # import logging
            # from PIL import Image
            # from pathlib import Path
            self.lama_model = SimpleLama()
            logger.info("LaMa AI inpainting model loaded successfully")
        except ImportError:
            logger.warning(
                "simple-lama-inpainting not installed. "
                "Install with: pip install simple-lama-inpainting"
            )
            self.method = "hybrid"
        except Exception as e:
            logger.warning(f"Failed to load LaMa model: {e}. Falling back to OpenCV.")
            self.method = "hybrid"
    
    def inpaint(self, image: np.ndarray, bbox: list) -> np.ndarray:
        """Inpaint the region defined by bbox
        
        Args:
            image: Input image (BGR)
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            Inpainted image
        """
        self._validate_bbox(bbox)
        
        if self.method == "lama" and self.lama_model is not None:
            return self._inpaint_lama(image, bbox)
        else:
            return self._inpaint_opencv(image, bbox)
    
    def inpaint_multiple(self, image: np.ndarray, bboxes: list) -> np.ndarray:
        """Inpaint multiple regions efficiently
        
        Args:
            image: Input image
            bboxes: List of bounding boxes
            
        Returns:
            Inpainted image with all regions removed
        """
        if self.method == "lama" and self.lama_model is not None:
            return self._inpaint_lama_multiple(image, bboxes)
        else:
            return self._inpaint_opencv_multiple(image, bboxes)
    
    def _validate_bbox(self, bbox: list) -> None:
        """Validate bounding box format"""
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"Invalid bbox format: expected [x1, y1, x2, y2], got {bbox}")
        x1, y1, x2, y2 = bbox
        if x1 >= x2 or y1 >= y2:
            raise ValueError(f"Invalid bbox dimensions: {bbox}")
    
    # ─────────────────────────────────────────────────────────────
    # LaMa AI Inpainting
    # ─────────────────────────────────────────────────────────────
    
    def _inpaint_lama(self, image: np.ndarray, bbox: list) -> np.ndarray:
        """Use LaMa AI for single region inpainting"""
        from PIL import Image
        
        x1, y1, x2, y2 = bbox
        h, w = image.shape[:2]
        
        # Ensure bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        # Create mask (white = inpaint region) using text detection
        mask = self._create_text_mask(image, bbox)
        
        # (Optional additional dilation if needed, but _create_text_mask handles it)
        
        # Convert to PIL
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        pil_mask = Image.fromarray(mask)
        
        # Run LaMa
        # Run LaMa
        if self.whiten_mode:
            # Simple white fill
            result_bgr = image.copy()
            # Where mask is white (text), make image white
            result_bgr[mask > 0] = [255, 255, 255]
            logger.debug(f"Whiten-mode inpaint for bbox {bbox}")
        else:
            result = self.lama_model(pil_image, pil_mask)
            # Convert back to BGR numpy
            result_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
        
        # Ensure output matches input dimensions exactly
        # LaMa often pads to nearest multiple of 8, causing shape mismatch
        if result_bgr.shape[:2] != (h, w):
            result_bgr = result_bgr[:h, :w]
            
        return result_bgr
    
    def _inpaint_lama_multiple(self, image: np.ndarray, bboxes: list) -> np.ndarray:
        """Use LaMa AI for multiple region inpainting"""
        from PIL import Image
        
        h, w = image.shape[:2]
        
        # Create combined mask representing ONLY the text pixels
        mask = np.zeros((h, w), dtype=np.uint8)
        for bbox in bboxes:
            # Use intelligent text masking to keep the bubble background
            text_mask = self._create_text_mask(image, bbox)
            mask = cv2.bitwise_or(mask, text_mask)
        
        # Dilate slightly more for LaMa to ensure clean removal
        # (Already dilated in _create_text_mask, but LaMa likes a bit more context)
        # kernel = cv2.getStructuringElement(
        #     cv2.MORPH_ELLIPSE, 
        #     (3, 3)
        # )
        # mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Convert to PIL
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        pil_mask = Image.fromarray(mask)
        
        # Run LaMa
        # Run LaMa
        # Run LaMa
        if self.whiten_mode:
             # Simple white fill
            result_bgr = image.copy()
            result_bgr[mask > 0] = [255, 255, 255]
            logger.info(f"Whiten-mode inpainted {len(bboxes)} regions")
        else:
            result = self.lama_model(pil_image, pil_mask)
            # Convert back
            result_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
            logger.info(f"LaMa inpainted {len(bboxes)} regions")
            
        return result_bgr
    
    # ─────────────────────────────────────────────────────────────
    # OpenCV Inpainting
    # ─────────────────────────────────────────────────────────────
    
    def _inpaint_opencv(self, image: np.ndarray, bbox: list) -> np.ndarray:
        """Use OpenCV algorithms for inpainting"""
        x1, y1, x2, y2 = bbox
        
        # Create mask
        mask = self._create_text_mask(image, bbox)
        
        # Choose method based on region size
        method = self.method
        if method == "hybrid":
            area = (x2 - x1) * (y2 - y1)
            method = "telea" if area < self.telea_max_area else "ns"
        
        # Inpaint
        # Inpaint
        # Inpaint
        if self.whiten_mode:
            # Smart Fill: Sample background color from the bubble
            roi = image[y1:y2, x1:x2]
            roi_mask = mask[y1:y2, x1:x2]
            
            # Get background pixels within ROI
            bg_pixels = roi[roi_mask == 0]
            
            if bg_pixels.size > 0:
                bg_pixels = bg_pixels.reshape(-1, 3)
                median_color = np.median(bg_pixels, axis=0).astype(np.uint8)
                fill_color = median_color.tolist()
            else:
                fill_color = [255, 255, 255]

            result = image.copy()
            result[mask > 0] = fill_color
            logger.debug(f"Smart-Fill (OpenCV) inpainted {bbox} with {fill_color}")
        elif method == "telea":
            result = cv2.inpaint(image, mask, self.inpaint_radius, cv2.INPAINT_TELEA)
            logger.debug(f"OpenCV ({method}) inpainted {bbox}")
        else:  # ns
            result = cv2.inpaint(image, mask, self.inpaint_radius, cv2.INPAINT_NS)
            logger.debug(f"OpenCV ({method}) inpainted {bbox}")
        
        return result
    
    def _inpaint_opencv_multiple(self, image: np.ndarray, bboxes: list) -> np.ndarray:
        """Use OpenCV for multiple regions at once"""
        h, w = image.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        
        valid_regions = 0
        for bbox in bboxes:
            # Safety check
            if not bbox or not isinstance(bbox, list) or len(bbox) != 4:
                continue
                
            x1, y1, x2, y2 = bbox
            # Strict bounds check
            if x1 < 0 or y1 < 0 or x2 > w or y2 > h or x1 >= x2 or y1 >= y2:
                logger.warning(f"Skipping out-of-bounds bbox: {bbox} in image {w}x{h}")
                continue

            try:
                mask = self._create_text_mask(image, bbox)
                combined_mask = cv2.bitwise_or(combined_mask, mask)
                valid_regions += 1
            except Exception as e:
                logger.error(f"Failed to create mask for bbox {bbox}: {e}")
                continue
        
        if valid_regions == 0:
            return image
            
        try:
            # Dilate combined mask slightly
            kernel = np.ones((self.mask_dilation, self.mask_dilation), np.uint8)
            combined_mask = cv2.dilate(combined_mask, kernel, iterations=1)
            
            if self.whiten_mode:
                # Smart Fill: Per-bubble background sampling
                result = image.copy()
                
                # We need to iterate again because we need per-bbox masks and ROIs
                for bbox in bboxes:
                    if not bbox or len(bbox) != 4: continue
                    x1, y1, x2, y2 = bbox
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    
                    try:
                        roi_text_mask = self._create_text_mask(image, bbox)[y1:y2, x1:x2]
                    except Exception:
                        continue
                    
                    if roi_text_mask.sum() == 0: continue
                    
                    roi = result[y1:y2, x1:x2]
                    bg_pixels = roi[roi_text_mask == 0]
                    
                    if bg_pixels.size > 0:
                        bg_pixels = bg_pixels.reshape(-1, 3)
                        median_color = np.median(bg_pixels, axis=0).astype(np.uint8)
                        fill_color = median_color.tolist()
                    else:
                        fill_color = [255, 255, 255]
                    
                    roi[roi_text_mask > 0] = fill_color
                    result[y1:y2, x1:x2] = roi

                logger.info(f"Smart-Fill (OpenCV) inpainted {valid_regions} regions")
            else:
                result = cv2.inpaint(image, combined_mask, self.inpaint_radius, cv2.INPAINT_TELEA)
                logger.info(f"OpenCV (Telea) inpainted {valid_regions} regions")
            
            return result
        except cv2.error as e:
            logger.error(f"OpenCV Inpaint CRASH prevention: {e}")
            return image
    
    def _expand_mask_by_color(self, 
                               image: np.ndarray, 
                               mask: np.ndarray, 
                               bbox: list, 
                               is_dark_text: bool) -> np.ndarray:
        """
        Expand mask toward pixels matching the text color for cleaner inpainting.
        
        This guided approach helps catch text anti-aliasing and partial pixels
        that the threshold-based mask might miss, reducing ghosting artifacts.
        
        Args:
            image: Full image (BGR)
            mask: Current binary mask (255 = inpaint)
            bbox: Bounding box [x1, y1, x2, y2]
            is_dark_text: True if text is dark on light background
            
        Returns:
            Enhanced mask with color-guided expansion
        """
        x1, y1, x2, y2 = bbox
        h, w = image.shape[:2]
        
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        region = image[y1:y2, x1:x2]
        region_mask = mask[y1:y2, x1:x2]
        
        if region.size == 0:
            return mask
        
        # Convert to grayscale
        if len(region.shape) == 3:
            region_gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        else:
            region_gray = region.copy()
        
        # Create a "fringe" mask - pixels near the current mask boundary
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        dilated = cv2.dilate(region_mask, kernel_dilate, iterations=1)
        fringe = cv2.bitwise_and(dilated, cv2.bitwise_not(region_mask))
        
        # In the fringe area, look for pixels that match text color intensity
        # Dark text: pixels below threshold
        # Light text: pixels above threshold
        if is_dark_text:
            # Text is dark, find dark pixels in fringe
            _, fringe_text = cv2.threshold(region_gray, 0, 255, 
                                            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            # Text is light, find light pixels in fringe  
            _, fringe_text = cv2.threshold(region_gray, 0, 255,
                                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Only keep the text-colored pixels that are in the fringe zone
        expansion = cv2.bitwise_and(fringe, fringe_text)
        
        # Add expansion to original mask
        enhanced_mask = cv2.bitwise_or(region_mask, expansion)
        
        # Write back to the full mask
        result = mask.copy()
        result[y1:y2, x1:x2] = enhanced_mask
        
        return result
    
    def _create_text_mask(self, image: np.ndarray, bbox: list) -> np.ndarray:
        """Create intelligent mask for text region with multi-method thresholding.
        
        Uses a combined approach:
        1. Otsu global thresholding for high-contrast text
        2. Adaptive thresholding for varying backgrounds
        3. Smart border protection (only removes thin border lines, not text)
        4. Guided expansion for anti-aliased edges
        """
        x1, y1, x2, y2 = bbox
        h, w = image.shape[:2]
        
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        mask = np.zeros((h, w), dtype=np.uint8)
        region = image[y1:y2, x1:x2]
        
        if region.size == 0:
            return mask
        
        roi_h, roi_w = region.shape[:2]
        if roi_h < 2 or roi_w < 2:
            return mask
        
        # Convert to grayscale
        if len(region.shape) == 3:
            region_gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        else:
            region_gray = region.copy()
        
        # Determine polarity robustly using percentiles to handle mid-tone colored bubbles
        # By default assume dark text unless there's overwhelming evidence of a black background.
        p5 = np.percentile(region_gray, 5)
        p50 = np.median(region_gray)
        p95 = np.percentile(region_gray, 95)
        
        if p50 > 127:
            # If median is bright, it's almost certainly dark text on a light background
            is_dark_text = True
        else:
            # If median is dark, check if it's just a medium-color bubble or an actual black bubble
            distance_to_dark = p50 - p5
            distance_to_bright = p95 - p50
            # If the bright extreme is much further from the median, the foreground stroke is white text.
            # We bias towards dark text, requiring distance_to_bright to be significantly larger.
            is_dark_text = distance_to_dark >= (distance_to_bright * 0.5)
            
        if is_dark_text:
            thresh_type = cv2.THRESH_BINARY_INV
        else:
            thresh_type = cv2.THRESH_BINARY
            
        # 1. Otsu Threshold
        _, otsu_mask = cv2.threshold(region_gray, 0, 255, thresh_type + cv2.THRESH_OTSU)
        
        # 2. Adaptive Threshold (REMOVED)
        # We exclusively use otsu_mask. adaptive_mask introduces massive fragmented noise on 
        # faded borders that geometrically mimics text and breaks topological filtering.
        text_mask = otsu_mask
        
        # 3. Fill hollow contours FIRST & Eliminate Speech Bubble Borders robustly
        # By identifying massive holes (>1.5% of ROI), we can confidently isolate the speech 
        # bubble border (which is the parent contour of the massive hole) and erase it!
        max_hole_area = roi_h * roi_w * 0.015
        
        # Topological Trick: Draw a 1-pixel frame around the mask. This forces any cut-off
        # speech bubble borders that touch the edge to connect and form a closed loop!
        cv2.rectangle(text_mask, (0, 0), (roi_w - 1, roi_h - 1), 255, 1)
        
        border_mask = np.zeros_like(text_mask)
        
        # Find contours to identify the massive holes inside speech bubbles
        contours, hierarchy = cv2.findContours(text_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is not None:
            parents_to_draw = set()
            massive_holes = []
            
            for i, cnt in enumerate(contours):
                if hierarchy[0][i][3] != -1: # has a parent (it's a hole)
                    if cv2.contourArea(cnt) < max_hole_area:
                        # Small hole (e.g. inside an 'O'), fill it directly in text_mask
                        cv2.drawContours(text_mask, [cnt], 0, 255, -1)
                    else:
                        # Massive hole! Mark the parent and the hole for border isolation
                        parents_to_draw.add(hierarchy[0][i][3])
                        massive_holes.append(cnt)
            
            # First, draw ALL parents filled (this creates a solid blob for every bubble)
            for p_idx in parents_to_draw:
                cv2.drawContours(border_mask, [contours[p_idx]], 0, 255, thickness=cv2.FILLED)
                
            # Then, subtract ALL massive holes (this carves out the text areas, leaving ONLY the borders)
            for hole_cnt in massive_holes:
                cv2.drawContours(border_mask, [hole_cnt], 0, 0, thickness=cv2.FILLED)
                        
        # Perfectly erase all identified speech bubble borders from the text mask
        text_mask = cv2.bitwise_and(text_mask, cv2.bitwise_not(border_mask))
        
        # Erase the 1-pixel topological frame we added
        cv2.rectangle(text_mask, (0, 0), (roi_w - 1, roi_h - 1), 0, 1)
                    
        # 4. Clean up through connected components (Filters bubble border lines safely)
        # First, apply a blind Edge Wipe. The YOLO detection box is tightly drawn around the bubble.
        # This means the speech bubble borders ALWAYS live on the extreme 0-4% edge of the ROI.
        # Faded/broken borders are geometrically identical to text, so we simply zero out the edges.
        if self.protect_borders:
            margin_x = max(3, int(roi_w * 0.04))
            margin_y = max(3, int(roi_h * 0.04))
            cv2.rectangle(text_mask, (0, 0), (roi_w, margin_y), 0, -1) # Top
            cv2.rectangle(text_mask, (0, roi_h - margin_y), (roi_w, roi_h), 0, -1) # Bottom
            cv2.rectangle(text_mask, (0, 0), (margin_x, roi_h), 0, -1) # Left
            cv2.rectangle(text_mask, (roi_w - margin_x, 0), (roi_w, roi_h), 0, -1) # Right

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(text_mask, connectivity=8)
        final_mask = np.zeros_like(text_mask)
        
        for i in range(1, num_labels):
            cx, cy, cw, ch, area = stats[i]
            keep = True
            
            if self.protect_borders:
                bb_area = cw * ch
                roi_area = roi_h * roi_w
                extent = area / float(max(bb_area, 1))
                aspect = cw / float(max(ch, 1))
                
                # 1. Straight lines (Panel borders that slipped past the edge wipe)
                if aspect > 8.0 or aspect < 0.12:
                    keep = False
                    
                # 2. Massive structures (Intact bubble borders penetrating deep into the ROI)
                # Text characters are never larger than 10% of the entire speech bubble area.
                elif bb_area > roi_area * 0.10:
                    keep = False
                    
                # 3. Large hollow structures (Thick C-shapes or long curves)
                elif bb_area > roi_area * 0.05 and extent < 0.45:
                    keep = False
            
            # Drop pure speckle noise (dust)
            if keep and area <= 5:
                keep = False
                
            if keep:
                final_mask[labels == i] = 255
                
        text_mask = final_mask
        
        # 4. Dilate aggressively to catch ALL anti-aliasing / ghosting
        # But FIRST, restrict the mask bounds so we don't accidentally dilate *into* the speech bubble border
        # Find the bounding box of ALL text components, and only dilate *within* that bounding box + a small margin.
        text_y, text_x = np.nonzero(text_mask)
        if len(text_y) > 0:
            min_y, max_y = np.min(text_y), np.max(text_y)
            min_x, max_x = np.min(text_x), np.max(text_x)
            # Use an extremely aggressive dilation to catch ALL faint anti-aliasing and smudges
            # A 13x13 or larger kernel expands the mask by ~6 pixels to guarantee clean backgrounds
            custom_dilation = max(13, self.mask_dilation * 3 + 1)
            kernel_expand = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (custom_dilation, custom_dilation))
            
            # Dilate the text mask to encompass the blurry edges
            text_mask = cv2.dilate(text_mask, kernel_expand, iterations=1)
        else:
            # Empty mask
            pass
        
        # 5. Fill internal holes (e.g., inside O, P, D)
        contours, hierarchy = cv2.findContours(text_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is not None:
            for i, cnt in enumerate(contours):
                if hierarchy[0][i][3] != -1: # has a parent (it's a hole)
                    if cv2.contourArea(cnt) < max_hole_area:
                        cv2.drawContours(text_mask, [cnt], 0, 255, -1)
        
        # Fallback if somehow mask is completely empty (e.g. blank bubble, or detection failed)
        bbox_area = roi_h * roi_w
        mask_coverage = np.count_nonzero(text_mask) / max(bbox_area, 1)
        if mask_coverage < 0.005:
            logger.debug(f"Text mask empty ({mask_coverage:.1%}). No text found to inpaint.")
            # Do NOT erase the whole box, just return the empty mask to prevent destroying the bubble.
            pass
            
        mask[y1:y2, x1:x2] = text_mask
        
        # ── Refinement for White Fill Mode ──
        if self.whiten_mode:
            try:
                # Ensure the entire mask is super solid if we are just going to paint it white
                roi_mask = mask[y1:y2, x1:x2]
                if roi_mask.shape[0] >= 3 and roi_mask.shape[1] >= 3:
                    k_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                    mask[y1:y2, x1:x2] = cv2.dilate(roi_mask, k_dilate, iterations=1)
            except Exception as e:
                logger.warning(f"Mask refinement failed for bbox {bbox}: {e}")

        # ── Smooth mask edges (Optimized for ROI only) ──
        if self.mask_blur > 0:
            roi_mask = mask[y1:y2, x1:x2]
            if roi_mask.size > 0:
                blurred = cv2.GaussianBlur(roi_mask, (self.mask_blur, self.mask_blur), 0)
                _, roi_mask = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
                mask[y1:y2, x1:x2] = roi_mask
        
        return mask


# Legacy alias for backward compatibility
class LamaInpainter(Inpainter):
    """Alias for backward compatibility"""
    def __init__(self, model_name: str = "lama", mask_dilation: int = 5, protect_borders: bool = True,
                 guided_mode: bool = True, mask_blur: int = 5, whiten_mode: bool = False):
        # Map old model names to new methods
        method = "lama"
        if "opencv" in model_name.lower() or "hybrid" in model_name.lower():
            method = "hybrid"
        elif "telea" in model_name.lower():
            method = "telea"
        elif "ns" in model_name.lower():
            method = "ns"
        
        super().__init__(method=method, mask_dilation=mask_dilation, protect_borders=protect_borders,
                         guided_mode=guided_mode, mask_blur=mask_blur, whiten_mode=whiten_mode)