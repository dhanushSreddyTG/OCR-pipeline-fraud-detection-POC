#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
from fraud_detector import FraudDetector

def run_batch():
    dataset_dir = "/home/dhanush/ocr-fraud-detection-poc/forged-dataset"
    results_dir = "/home/dhanush/ocr-fraud-detection-poc/batch_results"
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 80)
    print("STARTING FORENSIC PIPELINE BATCH TEST ON FORGED DATASET")
    print(f"Dataset path: {dataset_dir}")
    print(f"Results path: {results_dir}")
    print("=" * 80)

    # Walk and collect all image files
    files_to_test = []
    for root, dirs, files in os.walk(dataset_dir):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                filepath = os.path.join(root, f)
                files_to_test.append(filepath)

    files_to_test.sort()
    print(f"Found {len(files_to_test)} images to analyze.")

    summary = []
    low_risk_false_negatives = []

    for idx, path in enumerate(files_to_test, 1):
        rel_path = os.path.relpath(path, dataset_dir)
        print(f"[{idx}/{len(files_to_test)}] Analyzing: {rel_path} ... ", end="", flush=True)

        try:
            # Run pipeline
            detector = FraudDetector(path)
            report = detector.run_analysis(output_ela_path=None)

            # Generate a safe result filename
            # e.g. Forged_Aadhar_Fully_morphed_1.json
            name_parts = rel_path.replace(" ", "_").replace("/", "_").split(".")
            result_filename = f"{'_'.join(name_parts[:-1])}.json"
            result_path = os.path.join(results_dir, result_filename)

            with open(result_path, "w", encoding="utf-8") as out:
                json.dump(report, out, indent=4, ensure_ascii=False)

            risk_score = report.get("overall_risk_score", 0)
            risk_level = report.get("overall_risk_level", "Low")
            doc_type = report.get("rule_report", {}).get("document_type", "UNKNOWN")
            
            # Extract ELA and rule scores
            pixel_score = report.get("pixel_report", {}).get("tampering_score", 0) if report.get("pixel_report") else 0
            rule_score = report.get("rule_report", {}).get("risk_score", 0) if report.get("rule_report") else 0
            meta_score = report.get("metadata_report", {}).get("risk_score", 0)
            
            flags_list = report.get("metadata_report", {}).get("red_flags", [])
            flag_ids = [flag.get("rule_id") for flag in flags_list]

            item = {
                "file": rel_path,
                "document_type": doc_type,
                "overall_score": risk_score,
                "overall_level": risk_level,
                "pixel_score": pixel_score,
                "rule_score": rule_score,
                "meta_score": meta_score,
                "flags": flag_ids
            }
            summary.append(item)

            if risk_level == "Low":
                low_risk_false_negatives.append(item)
                print(f"FAILED (Risk Level: {risk_level}, Score: {risk_score})")
            else:
                print(f"SUCCESS (Risk Level: {risk_level}, Score: {risk_score})")

        except Exception as e:
            print(f"ERROR: {e}")

    # Print Summary Report
    print("\n" + "=" * 80)
    print("BATCH TESTING RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'FILE PATH':<45} | {'TYPE':<12} | {'RISK':<6} | {'SCORE':<5} | {'FLAGS':<10}")
    print("-" * 80)
    
    high_count = 0
    med_count = 0
    low_count = 0

    for item in summary:
        short_file = item["file"]
        if len(short_file) > 45:
            short_file = "..." + short_file[-42:]
            
        print(f"{short_file:<45} | {item['document_type']:<12} | {item['overall_level']:<6} | {item['overall_score']:<5} | {len(item['flags'])} flags")
        
        if item["overall_level"] == "High":
            high_count += 1
        elif item["overall_level"] == "Medium":
            med_count += 1
        else:
            low_count += 1

    print("=" * 80)
    print(f"Total Processed: {len(summary)}")
    print(f"High Risk (Flagged): {high_count}")
    print(f"Medium Risk (Flagged): {med_count}")
    print(f"Low Risk (False Negatives): {low_count}")
    print("=" * 80)

    if low_risk_false_negatives:
        print("\n[WARNING] The following files were NOT flagged as suspicious (False Negatives):")
        for fn in low_risk_false_negatives:
            print(f"  - {fn['file']} (Score: {fn['overall_score']}, Document Type: {fn['document_type']})")
        print("\nWe must review their extracted text, metadata, and pixel stats to make the rules stricter.")
    else:
        print("\n[SUCCESS] All forged files were successfully flagged as High or Medium risk!")
    print("=" * 80)

if __name__ == "__main__":
    run_batch()
