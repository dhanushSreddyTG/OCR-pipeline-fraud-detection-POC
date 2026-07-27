#!/usr/bin/env python3
"""
Unified Document Fraud Detector

Combines:
1. Metadata extraction & signature analysis (EXIF, XMP, PDF revision tags, DOCX core properties)
2. Pixel-level Error Level Analysis (ELA) with grid anomaly detection

Produces a combined risk score and structured JSON/text reports.
"""

import os
import sys
import re
import json
import argparse
import zipfile
import hashlib
import mimetypes
import io
import xml.etree.ElementTree as ET
import re
import os
import sys
from datetime import datetime
from PIL import Image, ImageChops, ImageEnhance, ImageStat
from font_analyzer import FontAnalyzer
from jpeg_analyzer import DoubleJPEGAnalyzer
from ela_analyzer import ELAAnalyzer
from metadata_forensics import MetadataForensics
from watermark_detector import WatermarkDetector
import tempfile
import concurrent.futures


class FraudDetector:
    def __init__(self, file_path, ela_quality=90, ela_stddev=3.5, ela_min_mean=0.8, ela_grid=30, doc_type=None):
        self.file_path = os.path.abspath(file_path)
        self.file_name = os.path.basename(file_path)
        self.file_ext = os.path.splitext(file_path)[1].lower()
        self.mime_type, _ = mimetypes.guess_type(self.file_path)
        if not self.mime_type:
            self.mime_type = "application/octet-stream"
            
        self.ela_quality = ela_quality
        self.ela_stddev = ela_stddev
        self.ela_min_mean = ela_min_mean
        self.ela_grid = ela_grid
        self.doc_type = doc_type
        
        self.report = {
            "file_system": {},
            "metadata_report": {
                "extracted": {},
                "red_flags": [],
                "risk_score": 0,
                "risk_level": "Low"
            },
            "pixel_report": None,
            "overall_risk_score": 0,
            "overall_risk_level": "Low"
        }

        
    def add_red_flag(self, rule_id, description, severity, points):
        self.report["metadata_report"]["red_flags"].append({
            "rule_id": rule_id,
            "description": description,
            "severity": severity,
            "points": points
        })

    def run_analysis(self, output_ela_path=None):
        if not os.path.exists(self.file_path):
            self.report["error"] = "File not found."
            self.report["overall_risk_level"] = "Error"
            return self.report

        # 1. Filesystem analysis (very fast, done in main thread)
        self.analyze_filesystem()

        is_image = self.file_ext in [".jpg", ".jpeg", ".png", ".webp", ".tiff"]

        def run_metadata_task():
            # 2. Metadata analysis
            if is_image:
                self.analyze_image()
            elif self.file_ext == ".pdf":
                self.analyze_pdf()
            elif self.file_ext in [".docx", ".xlsx", ".pptx"]:
                self.analyze_office_document()
            else:
                self.report["metadata_report"]["extracted"]["info"] = "Generic file type. Advanced metadata extraction skipped."

            # Compute metadata risk score
            meta_points = sum(flag["points"] for flag in self.report["metadata_report"]["red_flags"])
            meta_score = min(100, meta_points)
            self.report["metadata_report"]["risk_score"] = meta_score
            
            if meta_score >= 45:
                self.report["metadata_report"]["risk_level"] = "High"
            elif meta_score >= 16:
                self.report["metadata_report"]["risk_level"] = "Medium"
            else:
                self.report["metadata_report"]["risk_level"] = "Low"
            return meta_score

        def run_pixel_task():
            # 3. Pixel level ELA analysis (for images)
            if is_image:
                ela_engine = ELAAnalyzer(
                    self.file_path, 
                    quality=self.ela_quality, 
                    threshold_stddev=self.ela_stddev, 
                    min_anomaly_mean=self.ela_min_mean, 
                    grid_size=self.ela_grid
                )
                res = ela_engine.analyze(output_ela_path=output_ela_path)
                
                # Also run double JPEG check
                jpeg_engine = DoubleJPEGAnalyzer(self.file_path)
                jpeg_res = jpeg_engine.analyze()
                if "red_flags" not in res:
                    res["red_flags"] = []
                res["red_flags"].extend(jpeg_res.get("red_flags", []))
                
                return res
            return None

        def run_text_task():
            # 4. Text/Font level analysis
            font_engine = FontAnalyzer(self.file_path)
            return font_engine.analyze()

        # Execute tasks concurrently using ThreadPoolExecutor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_meta = executor.submit(run_metadata_task)
            future_pixel = executor.submit(run_pixel_task)
            future_text = executor.submit(run_text_task)

            meta_score = future_meta.result()
            pixel_report_res = future_pixel.result()
            text_report_res = future_text.result()
            
            # Incorporate text report into main report
            self.report["text_report"] = text_report_res
            for flag in text_report_res.get("red_flags", []):
                self.add_red_flag(flag["rule_id"], flag["description"], flag["severity"], flag["points"])

            # Recalculate metadata risk score to include text flags
            meta_points = sum(flag["points"] for flag in self.report["metadata_report"]["red_flags"])
            meta_score = min(100, meta_points)
            self.report["metadata_report"]["risk_score"] = meta_score
            if meta_score >= 45:
                self.report["metadata_report"]["risk_level"] = "High"
            elif meta_score >= 16:
                self.report["metadata_report"]["risk_level"] = "Medium"
            else:
                self.report["metadata_report"]["risk_level"] = "Low"

        # Run Document Rule Verification & Extraction
        font_info = text_report_res.get("font_info", {}) if text_report_res else {}
        extracted_text = font_info.get("extracted_text", "")
        text_lines = font_info.get("text_lines", [])

        # Import dynamic rule validator & processors
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        rule_engine_path = os.path.join(current_dir, "rule-engine")
        if rule_engine_path not in sys.path:
            sys.path.append(rule_engine_path)
            
        from processors.registry import DocumentProcessorRegistry
        from validator import DocumentRuleValidator

        extracted_data = {}
        detected_doc_type = "UNKNOWN"
        rule_score = 0
        rule_report = {
            "document_type": "UNKNOWN",
            "extracted_data": {},
            "validation_flags": [],
            "risk_score": 0,
            "risk_level": "Low",
            "verification_method": "None"
        }

        if extracted_text:
            extracted_data = DocumentProcessorRegistry.extract_document(extracted_text, text_lines, doc_type=self.doc_type)
            detected_doc_type = extracted_data.get("document_type", "UNKNOWN")
            # Set values
            rule_report["document_type"] = detected_doc_type
            rule_report["extracted_data"] = extracted_data

            if detected_doc_type != "UNKNOWN":
                validation_res = DocumentRuleValidator.validate(detected_doc_type, extracted_data, extracted_text, text_lines, font_info, self.file_path)
                rule_report["validation_flags"] = validation_res.get("flags", [])
                rule_report["risk_score"] = validation_res.get("points", 0)
                rule_report["verification_method"] = validation_res.get("verification_method", "Format Matching")
                rule_score = rule_report["risk_score"]

                for flag in rule_report["validation_flags"]:
                    self.add_red_flag(flag["rule_id"], flag["description"], flag["severity"], flag["points"])

        if rule_score >= 45:
            rule_report["risk_level"] = "High"
        elif rule_score >= 16:
            rule_report["risk_level"] = "Medium"
        else:
            rule_report["risk_level"] = "Low"

        self.report["rule_report"] = rule_report

        # Merge pixel report findings
        pixel_score = 0
        if pixel_report_res is not None:
            self.report["pixel_report"] = pixel_report_res
            if "error" not in self.report["pixel_report"]:
                pixel_score = self.report["pixel_report"]["tampering_score"]

        # 4. Calculate Combined Overall Score
        self.report["overall_risk_score"] = max(meta_score, pixel_score, rule_score)
        
        if self.report["overall_risk_score"] >= 45:
            self.report["overall_risk_level"] = "High"
        elif self.report["overall_risk_score"] >= 16:
            self.report["overall_risk_level"] = "Medium"
        else:
            self.report["overall_risk_level"] = "Low"
            
        return self.report

    def analyze_filesystem(self):
        stat_info = os.stat(self.file_path)
        created_time = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
        modified_time = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
        
        md5_hash = hashlib.md5()
        with open(self.file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                md5_hash.update(chunk)
                
        self.report["file_system"] = {
            "file_name": self.file_name,
            "file_extension": self.file_ext,
            "mime_type": self.mime_type,
            "size_bytes": stat_info.st_size,
            "created_time": created_time,
            "modified_time": modified_time,
            "md5_checksum": md5_hash.hexdigest()
        }

    def analyze_image(self):
        try:
            # 1. Run modular metadata forensics
            meta_forensics = MetadataForensics(self.file_path, self.file_ext)
            img_details, meta_flags = meta_forensics.analyze()
            
            # Save extracted metadata
            self.report["metadata_report"]["extracted"] = img_details
            
            # Add metadata flags to report
            for flag in meta_flags:
                self.add_red_flag(flag["rule_id"], flag["description"], flag["severity"], flag["points"])
                
            # 2. Run modular watermark detection
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "gemini_watermark_template.png")
            
            wm_detector = WatermarkDetector(self.file_path)
            wm_flags = wm_detector.analyze(template_path)
            
            for flag in wm_flags:
                self.add_red_flag(flag["rule_id"], flag["description"], flag["severity"], flag["points"])
                
        except Exception as e:
            self.report["error"] = f"Failed to parse image: {e}"


    def _threaded_analyze_embedded_images(self, img_paths):
        if not img_paths:
            return
            
        def analyze_single(img_path):
            flags = []
            try:
                # ELA Analyzer
                ela_engine = ELAAnalyzer(img_path, quality=self.ela_quality, threshold_stddev=self.ela_stddev, min_anomaly_mean=self.ela_min_mean, grid_size=self.ela_grid)
                ela_res = ela_engine.analyze(output_ela_path=None)
                if ela_res and "grid_analysis" in ela_res:
                    if ela_res["grid_analysis"].get("anomalous_blocks"):
                        flags.append({
                            "rule_id": "DOCUMENT_EMBEDDED_FORGERY_ELA",
                            "description": f"An embedded image triggered ELA pixel anomaly flags.",
                            "severity": "High",
                            "points": 40
                        })
                
                # Double JPEG Analyzer
                jpeg_engine = DoubleJPEGAnalyzer(img_path)
                jpeg_res = jpeg_engine.analyze()
                if jpeg_res and "red_flags" in jpeg_res and jpeg_res["red_flags"]:
                    flags.append({
                        "rule_id": "DOCUMENT_EMBEDDED_FORGERY_JPEG",
                        "description": f"An embedded image triggered Double JPEG compression anomaly flags.",
                        "severity": "High",
                        "points": 40
                    })
            except Exception as e:
                print(f"Error analyzing embedded image {img_path}: {e}", file=sys.stderr)
            return flags

        # Thread the image analysis
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(analyze_single, path) for path in img_paths]
            for future in concurrent.futures.as_completed(futures):
                res_flags = future.result()
                if res_flags:
                    for flag in res_flags:
                        # Prevent duplicate flags
                        if not any(f["rule_id"] == flag["rule_id"] for f in self.report["metadata_report"]["red_flags"]):
                            self.add_red_flag(flag["rule_id"], flag["description"], flag["severity"], flag["points"])

    def analyze_pdf(self):
        pdf_details = {}
        try:
            with open(self.file_path, 'rb') as f:
                content = f.read()
                
            for tag in [b'Producer', b'Creator', b'Author', b'CreationDate', b'ModDate']:
                pattern = re.compile(rb'/' + tag + rb'\s*\((.*?)\)')
                matches = pattern.findall(content)
                if matches:
                    decoded_vals = []
                    for m in matches:
                        try:
                            val = m.decode('utf-8', errors='ignore').strip()
                            decoded_vals.append(val)
                        except Exception:
                            pass
                    if decoded_vals:
                        tag_str = tag.decode()
                        pdf_details[tag_str] = decoded_vals[-1]
                        
                        if tag_str in ['Producer', 'Creator']:
                            meta_f = MetadataForensics(self.file_path, self.file_ext)
                            red_flags = []
                            meta_f.check_software_string(decoded_vals[-1], f"PDF:{tag_str}", red_flags)
                            meta_f.check_ai_software_string(decoded_vals[-1], f"PDF:{tag_str}", red_flags)
                            for flag in red_flags:
                                self.add_red_flag(flag["rule_id"], flag["description"], flag["severity"], flag["points"])
            
            eof_count = content.count(b'%%EOF')
            pdf_details["revision_markers_count"] = eof_count
            if eof_count > 1:
                self.add_red_flag(
                    rule_id="PDF_MULTI_REVISION",
                    description=f"PDF contains {eof_count} revision markers (%%EOF). This suggests incremental saves/modifications that may hide original text/values.",
                    severity="High",
                    points=30
                )
                
            creation_date = pdf_details.get("CreationDate")
            mod_date = pdf_details.get("ModDate")
            if creation_date and mod_date:
                c_num = "".join(filter(str.isdigit, creation_date))[:8]
                m_num = "".join(filter(str.isdigit, mod_date))[:8]
                if c_num and m_num and c_num != m_num:
                    self.add_red_flag(
                        rule_id="PDF_DATE_MISMATCH",
                        description=f"PDF creation date ({creation_date}) and modification date ({mod_date}) do not match, indicating the document was modified after creation.",
                        severity="Medium",
                        points=15
                    )
            
            for sw in EDITING_SOFTWARE_KEYWORDS:
                if sw.encode() in content.lower():
                    if not any(sw in flag["description"] for flag in self.report["metadata_report"]["red_flags"]):
                        self.add_red_flag(
                            rule_id="PDF_SOFTWARE_SIGNATURE",
                            description=f"Raw PDF content references editing application keyword '{sw}'.",
                            severity="Medium",
                            points=20
                        )
                        break
            
            # Extract and analyze embedded images using Threading
            import fitz
            doc = fitz.open(self.file_path)
            embedded_imgs = []
            tmp_dir = tempfile.mkdtemp()
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    img_path = os.path.join(tmp_dir, f"img_{page_num}_{img_index}.{ext}")
                    with open(img_path, "wb") as f_out:
                        f_out.write(image_bytes)
                    embedded_imgs.append(img_path)
            doc.close()
            
            self._threaded_analyze_embedded_images(embedded_imgs)
            
        except Exception as e:
            self.report["error"] = f"Failed to parse PDF: {e}"
            
        self.report["metadata_report"]["extracted"] = pdf_details

    def analyze_office_document(self):
        office_details = {}
        try:
            with zipfile.ZipFile(self.file_path) as z:
                if 'docProps/core.xml' in z.namelist():
                    core_data = z.read('docProps/core.xml')
                    root = ET.fromstring(core_data)
                    ns = {
                        'dc': 'http://purl.org/dc/elements/1.1/',
                        'dcterms': 'http://purl.org/dc/terms/',
                        'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
                    }
                    for tag, path, ns_dict in [
                        ("creator", ".//dc:creator", ns),
                        ("last_modified_by", ".//cp:lastModifiedBy", ns),
                        ("created", ".//dcterms:created", ns),
                        ("modified", ".//dcterms:modified", ns)
                    ]:
                        el = root.find(path, ns_dict)
                        if el is not None and el.text:
                            office_details[tag] = el.text.strip()
                            
                if 'docProps/app.xml' in z.namelist():
                    app_data = z.read('docProps/app.xml')
                    root = ET.fromstring(app_data)
                    ns = {'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'}
                    app_el = root.find('.//ep:Application', ns)
                    if app_el is not None and app_el.text:
                        office_details["application"] = app_el.text.strip()
                        
            app_name = office_details.get("application")
            if app_name:
                meta_f = MetadataForensics(self.file_path, self.file_ext)
                red_flags = []
                meta_f.check_software_string(app_name, "Office:Application", red_flags)
                for flag in red_flags:
                    self.add_red_flag(flag["rule_id"], flag["description"], flag["severity"], flag["points"])
                
            created = office_details.get("created")
            modified = office_details.get("modified")
            if created and modified:
                c_day = created.split('T')[0]
                m_day = modified.split('T')[0]
                if c_day != m_day:
                    self.add_red_flag(
                        rule_id="OFFICE_DATE_MISMATCH",
                        description=f"Office document created date ({c_day}) and modification date ({m_day}) do not match, indicating post-creation changes.",
                        severity="Medium",
                        points=15
                    )
                    
            creator = office_details.get("creator")
            if creator and creator.lower() in ["admin", "administrator", "user", "root"]:
                self.add_red_flag(
                    rule_id="GENERIC_CREATOR",
                    description=f"Office document author is registered as generic '{creator}'. Genuine high-trust documents usually contain specific individual/company authors.",
                    severity="Low",
                    points=5
                )
                
            # Extract and analyze embedded images using Threading
            embedded_imgs = []
            tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(self.file_path) as z:
                for item in z.namelist():
                    if item.startswith('word/media/') or item.startswith('xl/media/') or item.startswith('ppt/media/'):
                        if item.lower().endswith(('.png', '.jpg', '.jpeg')):
                            img_data = z.read(item)
                            img_path = os.path.join(tmp_dir, os.path.basename(item))
                            with open(img_path, "wb") as f_out:
                                f_out.write(img_data)
                            embedded_imgs.append(img_path)
                            
            self._threaded_analyze_embedded_images(embedded_imgs)
            
        except Exception as e:
            self.report["error"] = f"Failed to parse Office document: {e}"
            
        self.report["metadata_report"]["extracted"] = office_details

def main():
    parser = argparse.ArgumentParser(
        description="Unified Metadata & Pixel-Level (ELA) Document Fraud Detector."
    )
    parser.add_argument("file_path", help="Path to document file to analyze")
    parser.add_argument("-o", "--output-report", help="Path to save report (prints to console if omitted)")
    parser.add_argument("--ela-output", help="Path to save ELA visualization image")
    parser.add_argument(
        "-f", "--format", 
        choices=["json", "text"], 
        default="text",
        help="Report format: json or text (default)"
    )
    parser.add_argument(
        "-g", "--grid", 
        type=int, 
        default=30, 
        help="Grid size for block analysis (default: 30x30)"
    )
    parser.add_argument(
        "-m", "--min-mean", 
        type=float, 
        default=0.8, 
        help="Minimum mean ELA error to qualify as an anomaly (default: 0.8)"
    )
    parser.add_argument(
        "-q", "--quality", 
        type=int, 
        default=90, 
        help="JPEG resave quality for ELA comparison (default: 90)"
    )
    parser.add_argument(
        "--doc-type",
        help="Explicit document type classification override (optional)"
    )
    
    args = parser.parse_args()
    
    # Pre-checks for file existence and type
    if not os.path.exists(args.file_path):
        print(f"Error: File not found at '{args.file_path}'", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.isfile(args.file_path):
        print(f"Error: '{args.file_path}' is not a regular file", file=sys.stderr)
        sys.exit(1)
        
    detector = FraudDetector(
        args.file_path,
        ela_quality=args.quality,
        ela_stddev=3.5,
        ela_min_mean=args.min_mean,
        ela_grid=args.grid,
        doc_type=args.doc_type
    )
    report = detector.run_analysis(output_ela_path=args.ela_output)
    
    if args.format == "json":
        output_content = json.dumps(report, indent=4, ensure_ascii=False)
    else:
        # Custom formatted text report
        lines = []
        lines.append("=" * 60)
        lines.append("UNIFIED DOCUMENT FRAUD DETECTION REPORT")
        lines.append("=" * 60)
        
        if "error" in report:
            lines.append(f"ERROR OCCURRED DURING SCAN: {report['error']}")
            lines.append("=" * 60)
            output_content = "\n".join(lines)
        else:
            lines.append(f"File Name:     {report['file_system'].get('file_name', 'N/A')}")
            lines.append(f"File Path:     {report.get('file_path', args.file_path)}")
            lines.append(f"MIME Type:     {report['file_system'].get('mime_type', 'N/A')}")
            lines.append(f"MD5 Checksum:  {report['file_system'].get('md5_checksum', 'N/A')}")
            lines.append("-" * 60)
            
            lines.append(f"OVERALL FRAUD RISK LEVEL:  {report['overall_risk_level'].upper()} (Score: {report['overall_risk_score']}/100)")
            lines.append(f"  - Metadata Risk:          {report['metadata_report']['risk_level'].upper()} (Score: {report['metadata_report']['risk_score']})")
            
            if report.get("pixel_report"):
                lines.append(f"  - Pixel ELA Risk:         {report['pixel_report']['tampering_risk'].upper()} (Score: {report['pixel_report']['tampering_score']})")
            lines.append("-" * 60)
            
            # Metadata report section
            red_flags = report['metadata_report'].get("red_flags", [])
            if red_flags:
                lines.append(f"METADATA DETECTION ANOMALIES & RED FLAGS ({len(red_flags)} found):")
                for idx, flag in enumerate(red_flags, 1):
                    lines.append(f" {idx}. [{flag['severity']}] {flag['rule_id']}: {flag['description']}")
            else:
                lines.append("No metadata anomalies or red flags detected.")
            lines.append("-" * 60)
            
            # Pixel report section
            if report.get("pixel_report"):
                p_rep = report["pixel_report"]
                lines.append(f"PIXEL GRID ANOMALY ANALYSIS ({p_rep['grid_analysis']['rows']}x{p_rep['grid_analysis']['cols']}):")
                anomalies = p_rep['grid_analysis']['anomalous_blocks']
                if anomalies:
                    lines.append(f"  Suspicious Anomalies Found ({len(anomalies)} blocks):")
                    for idx, a in enumerate(anomalies[:10], 1):
                        lines.append(f"    {idx}. Block (Row {a['row']}, Col {a['col']}) at bbox {a['bbox']}")
                        lines.append(f"       Mean Error: {a['mean_error']} ({a['std_dev_deviations']} std devs from average)")
                    if len(anomalies) > 10:
                        lines.append(f"    ... ({len(anomalies) - 10} more anomalous blocks)")
                else:
                    lines.append("  No localized statistical anomalies found. Error levels are uniform.")
                lines.append("-" * 60)
            
            lines.append("=" * 60)
            output_content = "\n".join(lines)

    if args.output_report:
        try:
            with open(args.output_report, "w", encoding="utf-8") as f:
                f.write(output_content)
                if not output_content.endswith("\n"):
                    f.write("\n")
            print(f"Report successfully saved to: {args.output_report}")
        except Exception as e:
            print(f"Error saving report to '{args.output_report}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_content)

if __name__ == "__main__":
    main()
