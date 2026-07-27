#!/usr/bin/env python3
import io
import os
from PIL import Image, ImageChops, ImageStat

class ELAAnalyzer:
    """Performs Error Level Analysis and Grid-based statistical analysis."""
    def __init__(self, file_path, quality=90, threshold_stddev=3.5, min_anomaly_mean=0.8, grid_size=30):
        self.file_path = file_path
        self.quality = quality
        self.threshold_stddev = threshold_stddev
        self.min_anomaly_mean = min_anomaly_mean
        self.grid_size = grid_size
        
    def analyze(self, output_ela_path=None):
        report = {
            "ela_statistics": {},
            "grid_analysis": {
                "rows": self.grid_size,
                "cols": self.grid_size,
                "anomalous_blocks": []
            },
            "tampering_score": 0,
            "tampering_risk": "Low",
            "ela_image_saved": None
        }
        
        try:
            with Image.open(self.file_path) as original:
                original = original.convert("RGB")
                width, height = original.size
                
                # Resave in memory
                tmp_buffer = io.BytesIO()
                original.save(tmp_buffer, format="JPEG", quality=self.quality)
                tmp_buffer.seek(0)
                resaved = Image.open(tmp_buffer)
                
                # Calculate difference
                diff = ImageChops.difference(original, resaved)
                diff_gray = diff.convert("L")
                
                # Global stats
                global_stat = ImageStat.Stat(diff_gray)
                extrema = diff_gray.getextrema()
                
                global_mean = global_stat.mean[0]
                global_stddev = global_stat.stddev[0]
                global_max = extrema[1]
                
                report["ela_statistics"] = {
                    "global_mean_error": round(global_mean, 4),
                    "global_stddev_error": round(global_stddev, 4),
                    "global_max_error": int(global_max)
                }
                
                # Grid segmentation
                grid_rows = self.grid_size
                grid_cols = self.grid_size
                block_width = max(1, width // grid_cols)
                block_height = max(1, height // grid_rows)
                
                block_means = []
                blocks_data = []
                
                for r in range(grid_rows):
                    for c in range(grid_cols):
                        x0 = c * block_width
                        y0 = r * block_height
                        x1 = width if c == grid_cols - 1 else (c + 1) * block_width
                        y1 = height if r == grid_rows - 1 else (r + 1) * block_height
                        
                        block = diff_gray.crop((x0, y0, x1, y1))
                        block_mean = ImageStat.Stat(block).mean[0]
                        
                        block_means.append(block_mean)
                        blocks_data.append({
                            "row": r,
                            "col": c,
                            "bbox": [x0, y0, x1, y1],
                            "mean_error": block_mean
                        })
                        
                all_blocks_mean = sum(block_means) / len(block_means)
                all_blocks_variance = sum((m - all_blocks_mean) ** 2 for m in block_means) / len(block_means)
                all_blocks_stddev = all_blocks_variance ** 0.5
                
                report["grid_analysis"]["average_block_mean"] = round(all_blocks_mean, 4)
                report["grid_analysis"]["stddev_block_means"] = round(all_blocks_stddev, 4)
                
                # Flag anomalies
                anomalies = []
                for b in blocks_data:
                    deviation = b["mean_error"] - all_blocks_mean
                    stddev_multiplier = deviation / all_blocks_stddev if all_blocks_stddev > 0 else 0
                    
                    if stddev_multiplier > self.threshold_stddev and b["mean_error"] > self.min_anomaly_mean:
                        anomalies.append({
                            "row": b["row"],
                            "col": b["col"],
                            "bbox": b["bbox"],
                            "mean_error": round(b["mean_error"], 4),
                            "std_dev_deviations": round(stddev_multiplier, 2)
                        })
                        
                report["grid_analysis"]["anomalous_blocks"] = anomalies
                
                # Scoring
                score = 0
                score += min(45, len(anomalies) * 15)
                
                if global_mean > 0:
                    ratio = global_max / global_mean
                    if ratio > 15:
                        score += 25
                    elif ratio > 8:
                        score += 15
                        
                if all_blocks_stddev > 3.0:
                    score += 30
                elif all_blocks_stddev > 1.5:
                    score += 15
                    
                max_block_mean = max([b["mean_error"] for b in anomalies]) if anomalies else 0
                if max_block_mean > 20:
                    score += 30
                elif max_block_mean > 12:
                    score += 15
                    
                report["tampering_score"] = min(100, score)
                
                if report["tampering_score"] >= 55:
                    report["tampering_risk"] = "High"
                elif report["tampering_score"] >= 25:
                    report["tampering_risk"] = "Medium"
                else:
                    report["tampering_risk"] = "Low"
                    
                # Save ELA visualization
                if output_ela_path:
                    max_err = max(1, global_max)
                    # Normalize to [0, 255] and scale contrast
                    scale = 255.0 / max_err
                    enhanced = diff_gray.point(lambda p: min(255, int(p * scale)))
                    enhanced.save(output_ela_path)
                    report["ela_image_saved"] = output_ela_path
                    
        except Exception as e:
            report["error"] = f"ELA Analysis failed: {e}"
            
        return report
