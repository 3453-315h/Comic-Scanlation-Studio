## 2024-08-02 - Optimize color space conversion in style analysis
**Learning:** Converting the entire high-resolution comic page to grayscale (e.g. `cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)`) before analyzing small bubble regions is a significant bottleneck.
**Action:** Extract the Region of Interest (ROI) from the color image first, and only apply color space conversion on the tiny ROI array. This greatly reduces processing time.
