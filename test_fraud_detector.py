#!/usr/bin/env python3
"""
Unit tests for fraud_detector.py (Unified Report format)
"""

import os
import sys
import unittest
import tempfile
import zipfile
from PIL import Image

import fraud_detector

class TestFraudDetector(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_clean_image(self):
        """Test image that mimics a clean camera shot (has make/model, no editing software tags)."""
        file_path = os.path.join(self.test_dir.name, "camera_shot.jpg")
        img = Image.new("RGB", (1000, 1000), color="white")
        
        # Camera EXIF
        exif = img.getexif()
        exif[271] = "Canon"        # Make
        exif[272] = "EOS Rebel T7" # Model
        exif[305] = "Firmware v1.0"# Software (not editor)
        
        img.save(file_path, "JPEG", exif=exif)
        
        detector = fraud_detector.FraudDetector(file_path)
        report = detector.run_analysis()
        
        self.assertEqual(report["metadata_report"]["risk_level"], "Low")
        self.assertEqual(report["metadata_report"]["risk_score"], 0)
        self.assertEqual(len(report["metadata_report"]["red_flags"]), 0)

    def test_tampered_image_exif_software(self):
        """Test image with EXIF software indicating GIMP editing."""
        file_path = os.path.join(self.test_dir.name, "edited.jpg")
        img = Image.new("RGB", (500, 500), color="red")
        
        exif = img.getexif()
        exif[305] = "GIMP 2.10.30" # Software (editor)
        
        img.save(file_path, "JPEG", exif=exif)
        
        detector = fraud_detector.FraudDetector(file_path)
        report = detector.run_analysis()
        
        self.assertEqual(report["metadata_report"]["risk_level"], "High")
        self.assertGreaterEqual(report["metadata_report"]["risk_score"], 45)
        # Check that EDITING_SOFTWARE_DETECTED is present
        flag_rules = [f["rule_id"] for f in report["metadata_report"]["red_flags"]]
        self.assertIn("EDITING_SOFTWARE_DETECTED", flag_rules)

    def test_tampered_image_raw_xmp(self):
        """Test image that contains raw Adobe Photoshop references in its binary bytes."""
        file_path = os.path.join(self.test_dir.name, "photoshop_raw.jpg")
        img = Image.new("RGB", (300, 300), color="blue")
        img.save(file_path, "JPEG")
        
        # Append mock Photoshop XMP meta block to the end of the file
        xmp_block = b"""
        <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.6-c140">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmp:CreatorTool="Adobe Photoshop CC 2019 (Windows)"/>
          </rdf:RDF>
        </x:xmpmeta>
        """
        with open(file_path, "ab") as f:
            f.write(xmp_block)
            
        detector = fraud_detector.FraudDetector(file_path)
        report = detector.run_analysis()
        
        self.assertEqual(report["metadata_report"]["risk_level"], "High")
        self.assertGreaterEqual(report["metadata_report"]["risk_score"], 45)
        flag_rules = [f["rule_id"] for f in report["metadata_report"]["red_flags"]]
        self.assertIn("EDITING_SOFTWARE_DETECTED", flag_rules)

    def test_clean_pdf(self):
        """Test a simple clean PDF document (no editing tags, single EOF)."""
        file_path = os.path.join(self.test_dir.name, "clean.pdf")
        pdf_content = b"""%PDF-1.4
        1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
        2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
        3 0 obj <</Type /Page /Parent 2 0 R /Resources <<>> /Contents 4 0 R>> endobj
        4 0 obj <</Length 44>> stream
        BT /F1 12 Tf 50 700 Td (Hello World) Tj ET
        endstream
        endobj
        xref
        0 5
        0000000000 65535 f
        0000000009 00000 n
        0000000056 00000 n
        0000000111 00000 n
        0000000192 00000 n
        trailer <</Size 5 /Root 1 0 R>>
        startxref
        287
        %%EOF"""
        
        with open(file_path, "wb") as f:
            f.write(pdf_content)
            
        detector = fraud_detector.FraudDetector(file_path)
        report = detector.run_analysis()
        
        self.assertEqual(report["metadata_report"]["risk_level"], "Low")
        self.assertEqual(report["metadata_report"]["risk_score"], 0)

    def test_tampered_pdf_multi_revision(self):
        """Test a PDF containing multiple %%EOF markers."""
        file_path = os.path.join(self.test_dir.name, "tampered_revs.pdf")
        pdf_content = b"""%PDF-1.4
        1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
        ...
        %%EOF
        %%PDF-1.4
        2 0 obj <</Type /Catalog /Pages 2 0 R /Metadata 3 0 R>> endobj
        ...
        %%EOF"""
        
        with open(file_path, "wb") as f:
            f.write(pdf_content)
            
        detector = fraud_detector.FraudDetector(file_path)
        report = detector.run_analysis()
        
        self.assertEqual(report["metadata_report"]["risk_level"], "Medium") # 30 points is Medium
        flag_rules = [f["rule_id"] for f in report["metadata_report"]["red_flags"]]
        self.assertIn("PDF_MULTI_REVISION", flag_rules)

    def test_tampered_office_document(self):
        """Test an Office document built by a generic user and edited by Canva."""
        file_path = os.path.join(self.test_dir.name, "document.docx")
        
        core_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                           xmlns:dc="http://purl.org/dc/elements/1.1/"
                           xmlns:dcterms="http://purl.org/dc/terms/">
          <dc:creator>administrator</dc:creator>
          <cp:lastModifiedBy>editor</cp:lastModifiedBy>
          <dcterms:created>2026-07-01T12:00:00Z</dcterms:created>
          <dcterms:modified>2026-07-02T12:00:00Z</dcterms:modified>
        </cp:coreProperties>"""
        
        app_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
          <Application>Canva Document Editor</Application>
        </Properties>"""
        
        with zipfile.ZipFile(file_path, 'w') as z:
            z.writestr("docProps/core.xml", core_xml)
            z.writestr("docProps/app.xml", app_xml)
            
        detector = fraud_detector.FraudDetector(file_path)
        report = detector.run_analysis()
        
        flag_rules = [f["rule_id"] for f in report["metadata_report"]["red_flags"]]
        self.assertIn("EDITING_SOFTWARE_DETECTED", flag_rules)
        self.assertIn("OFFICE_DATE_MISMATCH", flag_rules)
        self.assertIn("GENERIC_CREATOR", flag_rules)
        self.assertEqual(report["metadata_report"]["risk_level"], "High")

    def test_docx_text_extraction(self):
        """Test that text is extracted from word/document.xml and passed to rule validations."""
        file_path = os.path.join(self.test_dir.name, "valid_aadhaar.docx")
        
        doc_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body>
            <w:p>
              <w:r>
                <w:t>Aadhaar Card: 3660 1782 9942</w:t>
              </w:r>
            </w:p>
            <w:p>
              <w:r>
                <w:t>DOB: 12-10-1995</w:t>
              </w:r>
            </w:p>
            <w:p>
              <w:r>
                <w:t>Gender: Male</w:t>
              </w:r>
            </w:p>
          </w:body>
        </w:document>"""
        
        with zipfile.ZipFile(file_path, 'w') as z:
            z.writestr("word/document.xml", doc_xml)
            
        detector = fraud_detector.FraudDetector(file_path, doc_type="AADHAAR")
        report = detector.run_analysis()
        
        self.assertEqual(report["rule_report"]["document_type"], "Aadhaar Card")
        self.assertEqual(report["rule_report"]["risk_score"], 0)

    def test_rule_verification_aadhaar(self):
        import sys
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rule-engine"))
        from validator import DocumentRuleValidator
        
        # Valid Aadhaar (using valid Verhoeff checksum)
        res = DocumentRuleValidator.validate(
            "AADHAAR",
            {"aadhaar_number": "3660 1782 9942", "dob": "12-10-1995", "gender": "Male"},
            "Aadhaar 3660 1782 9942",
            [],
            {}
        )
        self.assertEqual(res["points"], 0)

        # Invalid Aadhaar
        res_invalid = DocumentRuleValidator.validate(
            "AADHAAR",
            {"aadhaar_number": "3660 1782 9943", "dob": "12-10-1995", "gender": "Male"},
            "Aadhaar 3660 1782 9943",
            [],
            {}
        )
        self.assertGreater(res_invalid["points"], 0)
        flag_rules = [f["rule_id"] for f in res_invalid["flags"]]
        self.assertIn("AADHAAR_CHECKSUM_FAILED", flag_rules)

    def test_rule_verification_pan(self):
        from validator import DocumentRuleValidator
        # Valid PAN (4th character P = Individual, 5th character D = Doe)
        res = DocumentRuleValidator.validate(
            "PAN",
            {"pan_number": "ABCPD1234F", "name": "John Doe", "dob": "01-01-1990"},
            "ABCPD1234F John Doe",
            [],
            {}
        )
        self.assertEqual(res["points"], 0)

        # PAN Name Mismatch (Individual PAN expects 5th character 'D' for Doe, but got 'S')
        res_mismatch = DocumentRuleValidator.validate(
            "PAN",
            {"pan_number": "ABCPS1234F", "name": "John Doe", "dob": "01-01-1990"},
            "ABCPS1234F John Doe",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_mismatch["flags"]]
        self.assertIn("PAN_NAME_MISMATCH", flag_rules)

    def test_rule_verification_passport(self):
        from validator import DocumentRuleValidator
        # Valid Passport
        res = DocumentRuleValidator.validate(
            "PASSPORT",
            {"passport_number": "A1234567", "dob": "01-01-1990", "doi": "01-01-2015", "doe": "01-01-2025", "gender": "M"},
            "A1234567 01/01/1990 01/01/2015 01/01/2025 M",
            [],
            {}
        )
        self.assertEqual(res["points"], 0)

        # Chronology / Validity period check failure (15 year validity instead of 10)
        res_chrono = DocumentRuleValidator.validate(
            "PASSPORT",
            {"passport_number": "A1234567", "dob": "01-01-1990", "doi": "01-01-2015", "doe": "01-01-2030", "gender": "M"},
            "A1234567 01/01/1990 01/01/2015 01/01/2030 M",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_chrono["flags"]]
        self.assertIn("PASSPORT_VALIDITY_ANOMALY", flag_rules)

    def test_rule_verification_marksheet(self):
        from validator import DocumentRuleValidator
        # Valid Marksheet
        res = DocumentRuleValidator.validate(
            "VTU",
            {
                "university_name": "VTU",
                "subjects": [
                    {"internal_marks": "30", "external_marks": "70", "total": "100"},
                    {"internal_marks": "25", "external_marks": "50", "total": "75"}
                ]
            },
            "VTU marksheet",
            [],
            {}
        )
        self.assertEqual(res["points"], 0)

        # Summary additions failure
        res_addition = DocumentRuleValidator.validate(
            "VTU",
            {
                "university_name": "VTU",
                "subjects": [
                    {"internal_marks": "30", "external_marks": "70", "total": "90"},
                ]
            },
            "VTU marksheet",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_addition["flags"]]
        self.assertIn("MARKS_SUM_MISMATCH", flag_rules)

    def test_rule_verification_dl(self):
        from validator import DocumentRuleValidator
        # Underage issuance
        res_underage = DocumentRuleValidator.validate(
            "DL",
            {"dl_number": "KA5120150002345", "dob": "01-01-2005", "doi": "01-01-2015"},
            "KA5120150002345 DOB 01-01-2005 DOI 01-01-2015",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_underage["flags"]]
        self.assertIn("DL_UNDERAGE_ISSUANCE", flag_rules)

    def test_rule_verification_gst(self):
        from validator import DocumentRuleValidator
        # GST PAN mismatch
        res_gst = DocumentRuleValidator.validate(
            "GST",
            {"gstin": "29ABCDE1234F1Z5", "pan": "XYZZY1234Z"},
            "29ABCDE1234F1Z5 XYZZY1234Z",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_gst["flags"]]
        self.assertIn("GSTIN_PAN_MISMATCH", flag_rules)

    def test_rule_verification_mca(self):
        from validator import DocumentRuleValidator
        # CIN Year mismatch
        res_mca = DocumentRuleValidator.validate(
            "INCORPORATION",
            {"cin": "U72900KA2021PTC145678", "incorporation_date": "15-05-2022"},
            "U72900KA2021PTC145678 15-05-2022",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_mca["flags"]]
        self.assertIn("CIN_YEAR_MISMATCH", flag_rules)

    def test_dmv_database_verification(self):
        from validator import DocumentRuleValidator
        
        # 1. Indian DL DMV not found check
        res_in = DocumentRuleValidator.validate(
            "DL",
            {"dl_number": "KA5120159999999", "dob": "12-10-1995", "name": "GIRISH KUMAR"},
            "KA5120159999999 GIRISH KUMAR 12-10-1995",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_in["flags"]]
        self.assertIn("DMV_RECORD_NOT_FOUND", flag_rules)

        # 2. California DL DMV verify success and mismatch check
        res_ca = DocumentRuleValidator.validate(
            "US_DL_CA",
            {"document_type": "California Driver License", "dl_number": "1234568", "dob": "08/31/1977", "name": "JOHN DOE"},
            "California DL 1234568 JOHN DOE 08/31/1977",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_ca["flags"]]
        self.assertIn("DMV_RECORD_NAME_MISMATCH", flag_rules)

        # 3. Florida DL DMV verify success
        res_fl = DocumentRuleValidator.validate(
            "US_DL_FL",
            {"document_type": "Florida Driver License", "dl_number": "S514-172-80-844-0", "dob": "08-16-1960", "first_name": "JOE", "last_name": "SAMPLE"},
            "Florida DL S514-172-80-844-0 JOE SAMPLE 08-16-1960",
            [],
            {}
        )
        self.assertEqual(res_fl["points"], 0)

        # 4. Aadhaar Name Mismatch in Registry
        res_aadhaar = DocumentRuleValidator.validate(
            "AADHAAR",
            {"aadhaar_number": "3660 1782 9942", "dob": "12-10-1995", "name": "AMIT SHARMA"},
            "Aadhaar 3660 1782 9942 AMIT SHARMA 12-10-1995",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_aadhaar["flags"]]
        self.assertIn("REGISTRY_NAME_MISMATCH", flag_rules)

        # 5. PAN Registry Verification Success
        res_pan = DocumentRuleValidator.validate(
            "PAN",
            {"pan_number": "ABCPD1234F", "name": "John Doe", "dob": "01-01-1990"},
            "ABCPD1234F John Doe",
            [],
            {}
        )
        self.assertEqual(res_pan["points"], 0)

        # 6. Passport Registry Not Found
        res_passport = DocumentRuleValidator.validate(
            "PASSPORT",
            {"passport_number": "Z9999999", "dob": "01-01-1990", "name": "John Doe"},
            "Z9999999 John Doe 01-01-1990",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_passport["flags"]]
        self.assertIn("REGISTRY_RECORD_NOT_FOUND", flag_rules)

        # 7. GST Registry Not Found
        res_gst = DocumentRuleValidator.validate(
            "GST",
            {"gstin": "29ABCDE9999F1Z5"},
            "29ABCDE9999F1Z5",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_gst["flags"]]
        self.assertIn("REGISTRY_RECORD_NOT_FOUND", flag_rules)

        # 8. MCA Registry Not Found
        res_mca = DocumentRuleValidator.validate(
            "INCORPORATION",
            {"cin": "U72900KA9999PTC145678", "incorporation_date": "15-05-2021"},
            "U72900KA9999PTC145678 15-05-2021",
            [],
            {}
        )
        flag_rules = [f["rule_id"] for f in res_mca["flags"]]
        self.assertIn("REGISTRY_RECORD_NOT_FOUND", flag_rules)

if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
