#!/usr/bin/env python3
import os
import sys
import re
import json
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
from metadata_forensics import MetadataForensics
from watermark_detector import WatermarkDetector

def extract_metadata(image_path):
    _, ext = os.path.splitext(image_path)
    meta_forensics = MetadataForensics(image_path, ext)
    img_details, meta_flags = meta_forensics.analyze()
    
    wm_detector = WatermarkDetector(image_path)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "gemini_watermark_template.png")
    wm_flags = wm_detector.analyze(template_path)
    
    metadata = {
        "File Properties": {
            "File Name": os.path.basename(image_path),
            "File Size (Bytes)": os.path.getsize(image_path),
            "Absolute Path": os.path.abspath(image_path)
        },
        "Image Attributes": {
            "Format": img_details.get("format"),
            "Size": f"{img_details.get('width', 0)}x{img_details.get('height', 0)}",
            "Mode": img_details.get("mode")
        },
        "EXIF Metadata": img_details.get("exif", {}),
        "PNG Info Chunks": img_details.get("png_info", {}),
        "Raw XMP Metadata": {
            "RawXmpFound": img_details.get("raw_xmp_found", False),
            "CreatorTool": img_details.get("xmp_creator_tool"),
            "Title": img_details.get("xmp_title"),
            "Author": img_details.get("xmp_author"),
            "AiGenerated": img_details.get("xmp_ai_generated"),
            "History": img_details.get("xmp_history")
        }
    }
    
    # IPTC
    if "iptc" in img_details:
        metadata["IPTC Metadata"] = img_details["iptc"]
        
    # ICC Profile
    if "icc_profile" in img_details:
        metadata["ICC Profile"] = {
            "Found": True,
            "Size (Bytes)": img_details["icc_profile"].get("size"),
            "Profile Name": img_details["icc_profile"].get("profile_name")
        }
        
    # C2PA Manifest
    c2pa = img_details.get("c2pa_manifest", {})
    metadata["C2PA Manifest"] = {
        "Found": c2pa.get("found", False),
        "Details": c2pa.get("indicators", [])
    }
    
    # PNG Chunks or GIF extensions
    fmt = img_details.get("format")
    if fmt == "PNG":
        metadata["Structural Blocks (PNG Chunks)"] = [
            {"Chunk Type": b["type"], "Size (Bytes)": b["size"]} for b in img_details.get("structural_blocks", [])
        ]
    elif fmt == "GIF":
        metadata["Structural Blocks (GIF Extensions)"] = [
            {"Extension Type": b["type"], "Identifier": b["identifier"], "Offset": b["offset"]} for b in img_details.get("structural_blocks", [])
        ]
        
    # Steganography & Watermarks
    stego = img_details.get("steganography_tail", {})
    metadata["Steganographic / Watermark Payloads"] = {
        "Tail Payload Detected": stego.get("detected", False),
        "Extra Bytes After EOF": stego.get("extra_bytes", 0),
        "AI Watermarks": []
    }
    
    # Add visual watermarks from both meta_flags and wm_flags
    all_flags = meta_flags + wm_flags
    for flag in all_flags:
        if flag["rule_id"] == "AI_WATERMARK_DETECTED":
            name = "Google Gemini Sparkle Watermark" if "gemini" in flag["description"].lower() else "OpenAI DALL-E Signature"
            metadata["Steganographic / Watermark Payloads"]["AI Watermarks"].append({
                "Type": name,
                "Match Score": 1.0 if "dall-e" in name.lower() else 0.8,
                "Details": flag["description"]
            })
            
    return metadata

def print_formatted_report(metadata):
    print("\n" + "=" * 80)
    print("                      METADATA ANALYSIS REPORT                      ")
    print("=" * 80)

    # File Properties
    fp = metadata["File Properties"]
    print(f"\n📂 [FILE PROPERTIES]")
    print(f"  • File Name:      {fp.get('File Name')}")
    size_kb = round(fp.get('File Size (Bytes)', 0) / 1024, 2)
    print(f"  • File Size:      {size_kb} KB ({fp.get('File Size (Bytes)')} bytes)")
    print(f"  • Absolute Path:  {fp.get('Absolute Path')}")

    # Image Attributes
    ia = metadata["Image Attributes"]
    print(f"\n🖼️ [IMAGE ATTRIBUTES]")
    print(f"  • Format:         {ia.get('Format')}")
    print(f"  • Dimensions:     {ia.get('Size')}")
    print(f"  • Color Mode:     {ia.get('Mode')}")

    # EXIF
    exif = metadata["EXIF Metadata"]
    if exif:
        print(f"\n📷 [EXIF METADATA]")
        for k, v in exif.items():
            if k == "GPSInfo" and isinstance(v, dict):
                print("  • GPSInfo:")
                for gk, gv in v.items():
                    print(f"      - {gk:<15}: {gv}")
            else:
                print(f"  • {k:<15}: {v}")
    else:
        print(f"\n📷 [EXIF METADATA]: None found.")

    # IPTC Metadata
    iptc = metadata.get("IPTC Metadata")
    if iptc:
        print(f"\n🏷️ [IPTC IIM METADATA]")
        for k, v in iptc.items():
            print(f"  • {k:<15}: {v}")
    else:
        print(f"\n🏷️ [IPTC IIM METADATA]: None found.")

    # ICC Profile
    icc = metadata.get("ICC Profile")
    if icc:
        print(f"\n🎨 [ICC COLOR PROFILE]")
        print(f"  • Profile Size:   {icc.get('Size (Bytes)')} bytes")
        if "Profile Name" in icc:
            print(f"  • Profile Name:   {icc.get('Profile Name')}")
    else:
        print(f"\n🎨 [ICC COLOR PROFILE]: None found.")

    # C2PA Provenance Manifests
    c2pa = metadata.get("C2PA Manifest")
    if c2pa and c2pa.get("Found"):
        print(f"\n🛡️ [C2PA CONTENT PROVENANCE MANIFEST]")
        print(f"  • Status:         \033[92mC2PA manifest detected (Content Credentials)\033[0m")
        for detail in c2pa.get("Details", []):
            print(f"  • Details:        {detail}")
    else:
        print(f"\n🛡️ [C2PA CONTENT PROVENANCE MANIFEST]: None found.")

    # Format Specific Structural Blocks
    png_chunks = metadata.get("Structural Blocks (PNG Chunks)")
    if png_chunks:
        print(f"\n📦 [FORMAT-SPECIFIC STRUCTURAL BLOCKS (PNG CHUNKS)]")
        counts = {}
        for chunk in png_chunks:
            counts[chunk["Chunk Type"]] = counts.get(chunk["Chunk Type"], 0) + 1
        chunks_str = ", ".join([f"{k} (x{v})" for k, v in counts.items()])
        print(f"  • Chunks found:   {chunks_str}")
        print(f"  • Total Chunks:   {len(png_chunks)}")
    
    gif_exts = metadata.get("Structural Blocks (GIF Extensions)")
    if gif_exts:
        print(f"\n📦 [FORMAT-SPECIFIC STRUCTURAL BLOCKS (GIF EXTENSIONS)]")
        for ext in gif_exts:
            print(f"  • {ext['Extension']}: ID={ext['Identifier']} at offset {ext['Offset']}")

    # PNG Info Chunks
    png = metadata["PNG Info Chunks"]
    clean_png = {}
    for k, v in png.items():
        if k.lower() in ["exif", "xmp", "xml:com.adobe.xmp", "icc_profile"]:
            clean_png[k] = f"<Truncated: {len(v)} chars of raw XML/binary data>"
        else:
            clean_png[k] = v
    if clean_png:
        print(f"\n📎 [RAW PNG INFO CHUNKS]")
        for k, v in clean_png.items():
            print(f"  • {k:<15}: {v}")

    # Raw XMP
    xmp = metadata["Raw XMP Metadata"]
    if xmp.get("Found"):
        print(f"\n🧠 [AI & DIGITAL CREATION PROPERTIES (XMP)]")
        if "Title" in xmp:
            print(f"  • Document Title:              {xmp.get('Title')}")
        if "Author" in xmp:
            print(f"  • Author/Publisher:            {xmp.get('Author')}")
        if "CreatorTool" in xmp:
            print(f"  • Creator Software / Tool:     {xmp.get('CreatorTool')}")
        if "AiGenerated" in xmp:
            print(f"  • Contains AI-Generated Media: \033[93m{xmp.get('AiGenerated')}\033[0m")
        if "History" in xmp:
            print(f"  • Modification History:")
            for entry in xmp["History"]:
                print(f"    - Action '{entry['action']}' performed by: {entry['software']}")
    else:
        print(f"\n🧠 [AI & DIGITAL CREATION PROPERTIES (XMP)]: No digital creation metadata found.")

    # Steganography / Watermarks
    stego = metadata.get("Steganographic / Watermark Payloads")
    if stego:
        print(f"\n🕵️ [STEGANOGRAPHIC / WATERMARK PAYLOADS]")
        if stego.get("Tail Payload Detected"):
            print(f"  • Tail Payload:   \033[91mDETECTED ({stego.get('Extra Bytes After EOF')} extra bytes found after file EOF marker)\033[0m")
        else:
            print(f"  • Tail Payload:   Clean (No bytes trailing the file EOF marker)")
            
        if stego.get("AI Watermarks"):
            print(f"  • AI Watermarks:")
            for wm in stego["AI Watermarks"]:
                print(f"    - {wm['Type']} (Confidence Match: {wm['Match Score']}): {wm['Details']}")
        else:
            print(f"  • AI Watermarks:  None detected visually in bottom-right corner.")
    
    print("\n" + "=" * 80 + "\n")

def main():
    print("=" * 80)
    print("IMAGE METADATA DETAILED EXTRACTOR (FULL STRUCTURAL REPORT)")
    print("Type 'exit' or hit Ctrl+C to quit.")
    print("=" * 80)

    while True:
        try:
            path_input = input("Enter image file path: ").strip()
            
            if not path_input:
                continue
                
            if path_input.lower() == 'exit':
                print("Exiting program. Goodbye!")
                break

            # Remove quotes if copied from terminal
            if (path_input.startswith("'") and path_input.endswith("'")) or \
               (path_input.startswith('"') and path_input.endswith('"')):
                path_input = path_input[1:-1]

            if not os.path.exists(path_input):
                print(f"Error: File not found at '{path_input}'\n")
                continue

            if not os.path.isfile(path_input):
                print(f"Error: '{path_input}' is not a file\n")
                continue

            print("\nParsing metadata...")
            metadata = extract_metadata(path_input)
            print_formatted_report(metadata)

        except KeyboardInterrupt:
            print("\nExiting program. Goodbye!")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}\n")

if __name__ == "__main__":
    main()
