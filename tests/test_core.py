import unittest

from quoted_printable_codec import encode, decode, encode_bytes, decode_to_bytes


class TestEncode(unittest.TestCase):
    def test_ascii_unchanged(self):
        self.assertEqual(encode("Hello, World!"), "Hello,=20World!\r\n")

    def test_high_bit_escaped(self):
        self.assertEqual(encode("=AB",), "=3DAB\r\n")

    def test_tab_escaped(self):
        self.assertEqual(encode("\t"), "=09\r\n")

    def test_trailing_space_escaped(self):
        self.assertEqual(encode("x "), "x=20\r\n")

    def test_soft_line_break_long_input(self):
        data = "A" * 100
        result = encode(data)
        lines = result.split("\r\n")
        self.assertEqual(lines[-1], "")
        body = lines[:-1]
        self.assertTrue(all(len(ln) <= 76 for ln in body))
        joined = "".join(ln[:-1] if ln.endswith("=") else ln for ln in body)
        self.assertEqual(joined, "A" * 100)

    def test_custom_terminator(self):
        self.assertEqual(encode("hi", line_terminator="\n"), "hi\n")

    def test_empty(self):
        self.assertEqual(encode(""), "\r\n")

    def test_bytes_input(self):
        self.assertEqual(encode(b"\xff"), "=FF\r\n")

    def test_utf8_multibyte(self):
        self.assertEqual(encode("\u00e9"), "=C3=A9\r\n")


class TestDecode(unittest.TestCase):
    def test_ascii_unchanged(self):
        self.assertEqual(decode("Hello, World!\r\n"), "Hello, World!\n")

    def test_hex_escape(self):
        self.assertEqual(decode("=41=42\r\n"), "AB\n")

    def test_literal_equals_escaped(self):
        self.assertEqual(decode("=3D\r\n"), "=\n")

    def test_soft_line_break_concatenates(self):
        self.assertEqual(decode("Aaaa=\r\nbb\r\n"), "Aaaabb\n")

    def test_decode_to_bytes_binary(self):
        self.assertEqual(decode_to_bytes("=FF\r\n"), b"\xff\n")

    def test_lf_only(self):
        self.assertEqual(decode("AB\n"), "AB\n")

    def test_trailing_ws_stripped(self):
        self.assertEqual(decode("AB   \r\n"), "AB   \n")

    def test_empty_decode(self):
        self.assertEqual(decode(""), "")

    def test_lowercase_hex_rejected(self):
        with self.assertRaises(ValueError):
            decode("=ab\r\n")

    def test_bad_escape_rejected(self):
        with self.assertRaises(ValueError):
            decode("=ZZ\r\n")

    def test_non_ascii_rejected(self):
        with self.assertRaises(ValueError):
            decode("caf\u00e9\r\n")

    def test_soft_break_trailing_ws_consumed(self):
        self.assertEqual(decode("AB =\r\nCD\r\n"), "AB CD\n")

    def test_multiple_blank_lines_preserved(self):
        self.assertEqual(decode("A\r\n\r\nB\r\n"), "A\n\nB\n")


if __name__ == "__main__":
    unittest.main()
