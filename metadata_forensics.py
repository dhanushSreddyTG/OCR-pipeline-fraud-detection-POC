#!/usr/bin/env python3
import os
import re
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

# List of known editing software keywords (case-insensitive)
EDITING_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "canva", "illustrator", "inkscape", "paint.net",
    "acrobat", "nitro", "foxit", "soda pdf", "pdf element", "sejda", 
    "smallpdf", "pdfescape", "pdf2go", "pdfcandy", "pdfzen", "pdfedit",
    "fotor", "pixlr", "snapseed", "lightroom", "coreldraw", "quark",
    "affinity", "picmonkey", "befunky", "clipping magic", "remove.bg",
    "paint", "mspaint", "ms paint", "paint 3d", "windows photo editor",
    "snagit", "sketch", "figma", "luminar", "capture one", "dxo photolab",
    "on1 photo raw", "photopea", "polarr", "vsco", "afterlight", "facetune",
    "autodesk", "sketchbook", "procreate", "zoner draw", "corel painter", 
    "clip studio paint", "krita"
]

# List of known AI generator keywords (case-insensitive)
AI_GENERATOR_KEYWORDS = [
    "gemini", "synthid", "dall-e", "dalle", "midjourney", "stable diffusion", "stablediffusion",
    "sdxl", "novelai", "fooocus", "comfyui", "automatic1111", "dreamstudio", "adobe firefly", 
    "firefly", "bing image creator", "copilot image", "microsoft designer", "imagine with ai", 
    "meta ai", "llama", "leonardo.ai", "leonardo ai", "runwayml", "runway", "trainedalgorithmicmedia", 
    "c2pa",
    # Requested providers
    "adobe", "alibaba", "qwen", "amazon", "titan image", "artbreeder", "baidu", "wenxin", "yiyi",
    "black forest labs", "flux.1", "flux1", "bria", "canva", "civitai", "craiyon", "dalle mini",
    "deep dream", "deepdream", "deepart", "dezgo", "fal.ai", "fal-ai", "fotor", "google", "imagen",
    "grok", "xai", "hugging face", "huggingface", "ideogram", "jasper", "kling", "krea", "lexica",
    "lucid origin", "mage.space", "meta", "microsoft", "bing", "nightcafe", "openai", "photoroom",
    "picsart", "playground", "prodia", "recraft", "replicate", "reve", "riverflow", "runware",
    "seaart", "seedream", "siliconflow", "stability", "tencent", "hunyuan", "tensor.art", "tensorart",
    "wombo", "yandex"
]

class MetadataForensics:
    """Performs deep image metadata forensics and digital provenance checks."""
    def __init__(self, file_path, file_ext):
        self.file_path = file_path
        self.file_ext = file_ext.lower()
        
    def check_software_string(self, text, source_field, red_flags, rule_id="EDITING_SOFTWARE_DETECTED"):
        if not text:
            return False
        text_lower = text.lower()
        for sw in EDITING_SOFTWARE_KEYWORDS:
            if sw in text_lower:
                red_flags.append({
                    "rule_id": rule_id,
                    "description": f"File contains traces of editing software ('{sw}') in metadata field '{source_field}'.",
                    "severity": "High",
                    "points": 45
                })
                return True
        return False

    def check_ai_software_string(self, text, source_field, red_flags, rule_id="AI_GENERATION_METADATA_FOUND"):
        if not text:
            return False
        text_lower = text.lower()
        for sw in AI_GENERATOR_KEYWORDS:
            if sw in text_lower:
                red_flags.append({
                    "rule_id": rule_id,
                    "description": f"File contains AI generator signature/traces ('{sw}') in metadata field '{source_field}'.",
                    "severity": "High",
                    "points": 50
                })
                return True
        return False

    def analyze(self):
        img_details = {}
        red_flags = []
        
        try:
            with Image.open(self.file_path) as img:
                img_details["format"] = img.format
                img_details["width"] = img.width
                img_details["height"] = img.height
                img_details["mode"] = img.mode
                
                # Check Pillow info dictionary for AI parameters
                if img.info:
                    img_details["png_info"] = {}
                    for key, val in img.info.items():
                        if isinstance(val, str):
                            val_lower = val.lower()
                            img_details["png_info"][str(key)] = str(val)[:500]
                            for kw in AI_GENERATOR_KEYWORDS:
                                if kw in val_lower:
                                    red_flags.append({
                                        "rule_id": "AI_GENERATION_METADATA_FOUND",
                                        "description": f"Found AI generation metadata reference ('{kw}') in PNG chunk '{key}'.",
                                        "severity": "High",
                                        "points": 50
                                    })
                                    break
                
                # EXIF Metadata (and Sub-IFDs / GPS info)
                exif_data = img.getexif()
                if exif_data:
                    decoded_exif = {}
                    for tag_id, val in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if isinstance(val, bytes):
                            try:
                                val = val.decode('utf-8', errors='replace').strip()
                            except Exception:
                                val = val.hex()
                        decoded_exif[str(tag_name)] = str(val)
                    
                    # GPS IFD Tag extraction
                    try:
                        gps_ifd = exif_data.get_ifd(34853)
                        if gps_ifd:
                            from PIL.ExifTags import GPSTAGS
                            gps_dict = {}
                            for tag_id, val in gps_ifd.items():
                                tag_name = GPSTAGS.get(tag_id, tag_id)
                                gps_dict[str(tag_name)] = str(val)
                            if gps_dict:
                                decoded_exif["GPSInfo"] = gps_dict
                    except Exception:
                        pass
                        
                    img_details["exif"] = decoded_exif
                    
                    self.check_software_string(decoded_exif.get("Software"), "EXIF:Software", red_flags)
                    
                    # Scan EXIF fields for AI keywords
                    for tag, val in decoded_exif.items():
                        if isinstance(val, str):
                            self.check_ai_software_string(val, f"EXIF:{tag}", red_flags)
                    
                    is_jpeg = self.file_ext in [".jpg", ".jpeg"]
                    has_camera_make = "Make" in decoded_exif
                    has_camera_model = "Model" in decoded_exif
                    
                    if is_jpeg and (img.width > 800 and img.height > 800) and not (has_camera_make or has_camera_model):
                        red_flags.append({
                            "rule_id": "MISSING_CAMERA_SIGNATURE",
                            "description": "JPEG photo is high resolution but contains no camera model/brand EXIF metadata (often happens with edited/saved-for-web files).",
                            "severity": "Low",
                            "points": 10
                        })
                else:
                    is_jpeg = self.file_ext in [".jpg", ".jpeg"]
                    if is_jpeg and (img.width > 800 or img.height > 800):
                        red_flags.append({
                            "rule_id": "MISSING_EXIF_METADATA",
                            "description": "JPEG document lacks EXIF metadata entirely, suggesting it may be a digital generation, a screenshot, or stripped of camera properties.",
                            "severity": "Medium",
                            "points": 15
                        })
                
                # IPTC IIM Metadata
                try:
                    from PIL import IptcImagePlugin
                    iptc_info = IptcImagePlugin.getiptcinfo(img)
                    if iptc_info:
                        iptc_dict = {}
                        iptc_tags = {
                            (2, 5): "ObjectName",
                            (2, 25): "Keywords",
                            (2, 80): "Byline",
                            (2, 85): "BylineTitle",
                            (2, 110): "Credit",
                            (2, 115): "Source",
                            (2, 116): "CopyrightNotice",
                            (2, 120): "Caption",
                        }
                        for key, val in iptc_info.items():
                            tag_name = iptc_tags.get(key, str(key))
                            if isinstance(val, list):
                                decoded_vals = []
                                for item in val:
                                    try:
                                        decoded_vals.append(item.decode('utf-8', errors='replace'))
                                    except Exception:
                                        decoded_vals.append(str(item))
                                iptc_dict[tag_name] = decoded_vals
                            else:
                                try:
                                    iptc_dict[tag_name] = val.decode('utf-8', errors='replace')
                                except Exception:
                                    iptc_dict[tag_name] = str(val)
                        if iptc_dict:
                            img_details["iptc"] = iptc_dict
                except Exception:
                    pass

                # ICC Color Profile Info
                icc = img.info.get("icc_profile")
                if icc:
                    img_details["icc_profile"] = {
                        "size": len(icc)
                    }
                    desc_idx = icc.find(b'desc')
                    if desc_idx != -1:
                        desc_chunk = icc[desc_idx + 4:desc_idx + 120]
                        printable = re.findall(rb'[a-zA-Z0-9\s\-\.\_]{4,}', desc_chunk)
                        if printable:
                            img_details["icc_profile"]["profile_name"] = printable[0].decode('utf-8', errors='ignore').strip()

        except Exception as e:
            pass

        # Read raw binary for format-specific structure, C2PA, Steganography
        try:
            with open(self.file_path, 'rb') as f:
                content = f.read()
                
            # C2PA Provenance Manifest Check
            c2pa_indicators = []
            if b'c2pa' in content:
                c2pa_indicators.append("c2pa signature bytes")
            if b'jumb' in content:
                c2pa_indicators.append("jumb (JUMBF) signature bytes")
            if b'urn:uuid:00000000-0000-0000-0000-000000000000' in content or b'c2pa.manifest' in content:
                c2pa_indicators.append("C2PA manifest URI reference")
            if c2pa_indicators:
                img_details["c2pa_manifest"] = {
                    "found": True,
                    "indicators": c2pa_indicators
                }
                
            # Format-Specific Structural Blocks & Steganography checks
            fmt = img_details.get("format")
            if fmt == "PNG":
                img_details["structural_blocks"] = []
                f_seek = 8
                while f_seek < len(content):
                    length_bytes = content[f_seek:f_seek+4]
                    if len(length_bytes) < 4:
                        break
                    length = int.from_bytes(length_bytes, byteorder='big')
                    chunk_type = content[f_seek+4:f_seek+8]
                    if len(chunk_type) < 4:
                        break
                    type_str = chunk_type.decode('ascii', errors='ignore')
                    img_details["structural_blocks"].append({
                        "type": type_str,
                        "size": length
                    })
                    f_seek += 12 + length
                    if type_str == "IEND":
                        break
                
                # Stego trailing bytes
                iend_idx = content.find(b'IEND')
                if iend_idx != -1:
                    expected_end = iend_idx + 8
                    extra_bytes = len(content) - expected_end
                    if extra_bytes > 0:
                        img_details["steganography_tail"] = {
                            "detected": True,
                            "extra_bytes": extra_bytes
                        }
                        red_flags.append({
                            "rule_id": "STEGANOGRAPHY_DETECTED",
                            "description": f"Detected {extra_bytes} trailing bytes after the PNG IEND EOF marker. File may contain hidden steganographic payloads or hidden layers.",
                            "severity": "High",
                            "points": 35
                        })
            elif fmt == "GIF":
                img_details["structural_blocks"] = []
                app_ext_idx = 0
                while True:
                    app_ext_idx = content.find(b'\x21\xff', app_ext_idx)
                    if app_ext_idx == -1:
                        break
                    id_bytes = content[app_ext_idx+3:app_ext_idx+14]
                    id_str = id_bytes.decode('ascii', errors='ignore').strip()
                    img_details["structural_blocks"].append({
                        "type": "Application Extension",
                        "identifier": id_str if id_str else id_bytes.hex(),
                        "offset": app_ext_idx
                    })
                    app_ext_idx += 2
            elif fmt in ["JPEG", "MPO"]:
                # Stego trailing bytes
                ffd9_idx = content.rfind(b'\xff\xd9')
                if ffd9_idx != -1:
                    expected_end = ffd9_idx + 2
                    extra_bytes = len(content) - expected_end
                    if extra_bytes > 0:
                        img_details["steganography_tail"] = {
                            "detected": True,
                            "extra_bytes": extra_bytes
                        }
                        red_flags.append({
                            "rule_id": "STEGANOGRAPHY_DETECTED",
                            "description": f"Detected {extra_bytes} trailing bytes after the JPEG FFD9 EOF marker. File may contain hidden steganographic payloads.",
                            "severity": "High",
                            "points": 35
                        })

            # XMP scan
            xmp_match = re.search(b'<x:xmpmeta.*?</x:xmpmeta>', content, re.DOTALL)
            if xmp_match:
                xmp_text = xmp_match.group(0).decode('utf-8', errors='ignore')
                img_details["raw_xmp_found"] = True
                
                # Creator tool
                creator_tool_match = re.search(r'CreatorTool="([^"]+)"', xmp_text)
                if not creator_tool_match:
                    creator_tool_match = re.search(r'<xmp:CreatorTool>([^<]+)</xmp:CreatorTool>', xmp_text)
                if creator_tool_match:
                    tool = creator_tool_match.group(1).strip()
                    img_details["xmp_creator_tool"] = tool
                    self.check_software_string(tool, "XMP:CreatorTool", red_flags)
                    
                # Document title
                title_match = re.search(r'<dc:title>\s*<rdf:Alt>\s*<rdf:li[^>]*>([^<]+)</rdf:li>', xmp_text, re.DOTALL)
                if title_match:
                    img_details["xmp_title"] = title_match.group(1).strip()
                    
                # Author
                author_match = re.search(r'<pdf:Author>([^<]+)</pdf:Author>', xmp_text)
                if author_match:
                    img_details["xmp_author"] = author_match.group(1).strip()
                    
                # Contains AI Generated content flag
                ai_match = re.search(r'<ContainsAiGeneratedContent:ContainsAiGeneratedContent>([^<]+)</ContainsAiGeneratedContent:ContainsAiGeneratedContent>', xmp_text)
                if not ai_match:
                    ai_match = re.search(r'ContainsAiGeneratedContent="([^"]+)"', xmp_text)
                if ai_match:
                    ai_flag = ai_match.group(1).strip()
                    img_details["xmp_ai_generated"] = ai_flag
                    if ai_flag.lower() in ["yes", "true"]:
                        red_flags.append({
                            "rule_id": "AI_GENERATION_METADATA_FOUND",
                            "description": "File metadata explicitly declares containing AI-generated content (ContainsAiGeneratedContent: Yes).",
                            "severity": "High",
                            "points": 50
                        })
                    
                history_entries = re.findall(r'<rdf:li[^>]*?action="([^"]+)"[^>]*?softwareAgent="([^"]+)"', xmp_text)
                if history_entries:
                    img_details["xmp_history"] = [
                        {"action": action, "software": sw} for action, sw in history_entries
                    ]
                    for action, sw in history_entries:
                        self.check_software_string(sw, f"XMP:History (action: {action})", red_flags, rule_id="EDITING_HISTORY_FOUND")
                
                for sw in EDITING_SOFTWARE_KEYWORDS:
                    if sw in xmp_text.lower():
                        # Prevent duplicates
                        if not any(sw in flag["description"] for flag in red_flags):
                            red_flags.append({
                                "rule_id": "XMP_SOFTWARE_FOOTPRINT",
                                "description": f"Found raw XMP reference to '{sw}'.",
                                "severity": "High",
                                "points": 45
                            })
                            break

            # Scan raw binary for AI footprints
            content_lower = content.lower()
            for keyword in AI_GENERATOR_KEYWORDS:
                kb = keyword.encode('utf-8')
                if kb in content_lower:
                    if not any(flag["rule_id"] == "AI_GENERATION_METADATA_FOUND" for flag in red_flags):
                        red_flags.append({
                            "rule_id": "AI_GENERATION_METADATA_FOUND",
                            "description": f"Found raw binary/XMP footprint of AI generator service ('{keyword}').",
                            "severity": "High",
                            "points": 50
                        })
                        break

        except Exception:
            pass
            
        return img_details, red_flags
