#!/usr/bin/env python3
import os
import cv2
import numpy as np

class WatermarkDetector:
    """Detects visible AI-generated watermarks (Google Gemini, OpenAI DALL-E) across the full image."""
    def __init__(self, file_path):
        self.file_path = file_path
        
    def detect_gemini_watermark(self, template_path):
        flags = []
        try:
            img = cv2.imread(self.file_path)
            if img is None:
                return flags
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Load template
            template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
            if template_img is None:
                return flags
                
            # Handle alpha channel: create white shape on black background for clean correlation
            if template_img.shape[2] == 4:
                mask = template_img[:, :, 3]
                template_gray = np.zeros(mask.shape, dtype=np.uint8)
                template_gray[mask > 0] = 255
            else:
                template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
                
            best_val = 0.0
            best_size = None
            best_contrast = 0.0
            
            for size in [24, 32, 40, 48, 56, 64]:
                if gray.shape[0] < size or gray.shape[1] < size:
                    continue
                resized = cv2.resize(template_gray, (size, size))
                res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                # Get local patch at match location to evaluate contrast
                x, y = max_loc
                patch = gray[y:y+size, x:x+size]
                contrast = float(np.max(patch) - np.min(patch))
                
                if max_val > best_val:
                    best_val = max_val
                    best_size = size
                    best_contrast = contrast
            
            # Watermark must have high correlation (>= 0.70) and a realistic local contrast range (10.0 <= best_contrast < 60.0)
            # to filter out false positive matches on solid/flat background regions.
            if best_val >= 0.70 and 10.0 <= best_contrast < 60.0:
                flags.append({
                    "rule_id": "AI_WATERMARK_DETECTED",
                    "description": f"Detected visible Google Gemini / AI star watermark in the document (correlation: {best_val:.2f}, local contrast: {best_contrast:.1f}, template size: {best_size}px).",
                    "severity": "High",
                    "points": 50
                })
        except Exception:
            pass
        return flags

    def detect_dalle_watermark(self):
        flags = []
        try:
            img = cv2.imread(self.file_path)
            if img is None:
                return flags
            h, w, c = img.shape
            if c != 3 and c != 4:
                return flags
                
            # Convert full image to HSV
            hsv = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2HSV)
            
            # Define HSV ranges for the 5 DALL-E colors (Yellow, Teal, Blue, Orange/Red, Green)
            color_ranges = [
                ((20, 100, 100), (32, 255, 255)),   # Yellow
                ((85, 100, 100), (105, 255, 255)),  # Teal
                ((105, 100, 100), (130, 255, 255)), # Blue
                ((5, 100, 100), (18, 255, 255)),    # Orange/Red
                ((38, 100, 100), (80, 255, 255))    # Green
            ]
            
            # Find centroids for each color contour
            centroids = []
            for idx, (low, high) in enumerate(color_ranges):
                mask = cv2.inRange(hsv, low, high)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    # DALL-E blocks are small (typically 3x3 to 15x15 pixels)
                    if 4 <= area <= 300:
                        M = cv2.moments(cnt)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            centroids.append({"color_idx": idx, "cx": cx, "cy": cy})
            
            # Check if we have adjacent centroids matching the spatial sequence
            # Sort centroids by cx
            centroids = sorted(centroids, key=lambda p: p["cx"])
            
            # Search for a sequence of 4 or 5 adjacent colored blocks aligned horizontally
            # cy must be very close, cx must increase sequentially
            for i in range(len(centroids)):
                seq = [centroids[i]]
                for j in range(i + 1, len(centroids)):
                    last = seq[-1]
                    curr = centroids[j]
                    
                    dx = curr["cx"] - last["cx"]
                    dy = abs(curr["cy"] - last["cy"])
                    
                    if 1 <= dx <= 25 and dy <= 6:
                        # Make sure color indices are different (sequential progression)
                        if curr["color_idx"] != last["color_idx"]:
                            seq.append(curr)
                            
                # If we found at least 4 unique colors aligned horizontally in sequence
                unique_colors = len(set(p["color_idx"] for p in seq))
                if unique_colors >= 4 and len(seq) >= 4:
                    flags.append({
                        "rule_id": "AI_WATERMARK_DETECTED",
                        "description": "Detected visible DALL-E colored squares signature in the document.",
                        "severity": "High",
                        "points": 50
                    })
                    break
        except Exception:
            pass
        return flags

    def analyze(self, template_path):
        flags = []
        # Run Gemini detector
        if template_path and os.path.exists(template_path):
            flags.extend(self.detect_gemini_watermark(template_path))
        # Run DALL-E detector
        flags.extend(self.detect_dalle_watermark())
        return flags
