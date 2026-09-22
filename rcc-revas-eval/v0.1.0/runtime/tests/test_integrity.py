import unittest
import tempfile
from pathlib import Path
from rcc_revas_eval.integrity import *

class StrictIntegrity(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ContractError,'DUPLICATE_JSON_KEY'):loads('{"x":1,"x":2}')
    def test_nan_and_infinity_rejected(self):
        for value in ('NaN','Infinity','-Infinity'):
            with self.subTest(value=value),self.assertRaises(ContractError):loads('{"x":'+value+'}')
    def test_float_rejected_instead_of_false_canonical_claim(self):
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_JSON_TYPE'):loads('{"x":0.1}')
    def test_large_integer_rejected(self):
        with self.assertRaisesRegex(ContractError,'UNSAFE_INTEGER'):loads('{"x":9007199254740992}')
    def test_bool_not_number(self):
        self.assertNotEqual(canonical(True),canonical(1))
    def test_unicode_not_normalized(self):
        self.assertNotEqual(canonical('é'),canonical('e\u0301'))
    def test_keys_sorted_arrays_not_sorted(self):
        self.assertEqual(canonical({'b':1,'a':2}),canonical({'a':2,'b':1}))
        self.assertNotEqual(canonical([1,2]),canonical([2,1]))
    def test_surrogates_rejected(self):
        with self.assertRaisesRegex(ContractError,'INVALID_UNICODE'):canonical('\ud800')
    def test_depth_limited(self):
        value=0
        for _ in range(60):value=[value]
        with self.assertRaisesRegex(ContractError,'JSON_TOO_DEEP'):canonical(value)
    def test_domain_separation(self):
        self.assertNotEqual(digest({'x':1},'candidate'),digest({'x':1},'decision'))
    def test_path_traversal(self):
        for rel in ('../secret','/etc/passwd','a/../b','./x','a//x','a\\x',''):
            with self.subTest(rel=rel),self.assertRaises(ContractError):safe_path(Path('/tmp/root'),rel)
    def test_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'target').write_text('x');(root/'sym').symlink_to(root/'target')
            with self.assertRaisesRegex(ContractError,'SYMLINK_FORBIDDEN'):safe_path(root,'sym')
    def test_write_once(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';write_json(p,{'a':1})
            with self.assertRaisesRegex(ContractError,'REFUSE_OVERWRITE'):write_json(p,{'a':2})
    def test_UTC_required(self):
        for ts in ('2026-09-21T00:00:00','2026-09-21T00:00:00+00:00','2026-02-31T00:00:00Z'):
            with self.subTest(ts=ts),self.assertRaises(ContractError):timestamp(ts)
    def test_jsonl_no_blank_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.jsonl';p.write_text('{"a":1}\n\n')
            with self.assertRaisesRegex(ContractError,'BLANK_JSONL_ROW'):read_jsonl(p)
