import os
import numpy as np
from PIL import Image
from scipy.fftpack import dct

class DoubleJPEGAnalyzer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_ext = os.path.splitext(file_path)[1].lower()

    def analyze(self):
        report = {"red_flags": []}
        if self.file_ext not in [".jpg", ".jpeg"]:
            return report

        try:
            img = Image.open(self.file_path).convert('L')
            arr = np.array(img, dtype=float)
            
            h, w = arr.shape
            
            # Subsample to speed up (take center 500x500)
            ch, cw = h // 2, w // 2
            sh, sw = min(250, ch), min(250, cw)
            arr = arr[ch-sh:ch+sh, cw-sw:cw+sw]
            h, w = arr.shape
            
            if h < 8 or w < 8:
                return report

            # Compute DCT of 8x8 blocks
            coefs = []
            for i in range(0, h - 8, 8):
                for j in range(0, w - 8, 8):
                    block = arr[i:i+8, j:j+8]
                    # 2D DCT
                    block_dct = dct(dct(block.T, norm='ortho').T, norm='ortho')
                    # Look at a specific AC coefficient, e.g. (1,1)
                    coefs.append(block_dct[1, 1])

            # Histogram analysis of AC coefficients for Double Quantization (periodic artifacts)
            if coefs:
                hist, bins = np.histogram(coefs, bins=50, range=(-20, 20))
                # In double quantized images, histogram has periodic valleys (zeros)
                valleys = np.sum(hist == 0)
                if valleys > 15: # Arbitrary threshold for POC
                    report["red_flags"].append({
                        "rule_id": "DOUBLE_JPEG_COMPRESSION",
                        "description": f"Detected {valleys} histogram valleys in DCT coefficients, strongly indicating image was re-saved (Double Quantization).",
                        "severity": "High",
                        "points": 50
                    })
                    
        except Exception as e:
            import sys
            print(f"Error in Double JPEG analysis: {e}", file=sys.stderr)
            return report

        return report
