"""Byte-integrity tests for OWNER financial evidence without a running DB."""
import base64
import hashlib
import sys
import unittest
from pathlib import Path
from fastapi import HTTPException

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services/api"))
from app.owner_revenue_evidence import MAX_BYTES, decode_and_verify, content_type_matches


class FinancialEvidenceBytes(unittest.TestCase):
    def setUp(self):
        self.pdf=b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
        self.sha=hashlib.sha256(self.pdf).hexdigest()
        self.encoded=base64.b64encode(self.pdf).decode("ascii")

    def test_exact_stored_pdf_bytes_can_be_hashed(self):
        self.assertEqual(decode_and_verify(self.encoded,self.sha,"application/pdf"),
                         self.pdf)

    def test_file_type_is_verified_from_bytes_not_filename(self):
        with self.assertRaises(HTTPException) as err:
            decode_and_verify(self.encoded,self.sha,"image/png")
        self.assertEqual(err.exception.status_code,422)

    def test_declared_hash_mismatch_fails(self):
        with self.assertRaises(HTTPException) as err:
            decode_and_verify(self.encoded,"a"*64,"application/pdf")
        self.assertEqual(err.exception.status_code,409)

    def test_non_base64_input_rejected(self):
        with self.assertRaises(HTTPException) as err:
            decode_and_verify("invalid!!!!",self.sha,"application/pdf")
        self.assertEqual(err.exception.status_code,422)

    def test_size_caps_before_and_after_decode(self):
        over=base64.b64encode(b"%PDF-1.4"+b"0"*MAX_BYTES).decode()
        with self.assertRaises(HTTPException) as err:
            decode_and_verify(over,"0"*64,"application/pdf")
        self.assertEqual(err.exception.status_code,413)
        with self.assertRaises(HTTPException):
            decode_and_verify("QUJD",hashlib.sha256(b"ABC").hexdigest(),
                              "application/pdf")

    def test_png_and_jpeg_signatures(self):
        png=bytes.fromhex("89504e470d0a1a0a")+b"\x00"*40
        jpg=bytes.fromhex("ffd8ff")+b"\x00"*20+bytes.fromhex("ffd9")
        self.assertTrue(content_type_matches(png,"image/png"))
        self.assertTrue(content_type_matches(jpg,"image/jpeg"))
        self.assertFalse(content_type_matches(png,"image/jpeg"))
        self.assertFalse(content_type_matches(jpg,"image/png"))


if __name__=="__main__":
    unittest.main()
