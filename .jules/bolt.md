# Bolt's Performance Journal

## 2024-05-23 - Avoid full-image mask allocation in iteration
**Learning:** During text detection, OpenCV contour brightness verification was generating a full-image sized mask `np.zeros_like(gray)` inside a loop for every detected contour. For large comic pages (e.g. 2000x1500) and hundreds of contours, this caused massive unnecessary memory allocation and processing overhead, making contour-based OCR/text detection severely CPU/Memory bound.
**Action:** When validating local image features inside a loop, always extract a Region of Interest (ROI) using the object's bounding box and allocate tiny masks relative to the ROI bounds. Shifting contour coordinates using `cnt - [x, y]` allows drawing onto the tiny ROI mask.
