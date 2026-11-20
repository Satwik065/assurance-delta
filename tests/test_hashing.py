"""Tests for canonical JSON and SHA-256 helpers."""
from constitution.hashing import (
    canonical_json_dumps,
    sha256_bytes,
    sha256_canonical,
    sha256_file,
    sha256_text,
)


def test_canonical_json_order_independent():
    a = canonical_json_dumps({"b": 2, "a": 1})
    b = canonical_json_dumps({"a": 1, "b": 2})
    assert a == b
    assert a == '{"a":1,"b":2}'


def test_canonical_json_no_whitespace():
    s = canonical_json_dumps({"x": [1, 2, 3], "y": "z"})
    assert " " not in s
    assert s == '{"x":[1,2,3],"y":"z"}'


def test_sha256_text_matches_known_vector():
    # Standard SHA-256 of the empty string
    assert sha256_text("") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_sha256_bytes_and_text_agree():
    s = "hello"
    assert sha256_bytes(s.encode("utf-8")) == sha256_text(s)


def test_sha256_canonical_is_order_independent():
    a = {"x": 1, "y": [2, 3]}
    b = {"y": [2, 3], "x": 1}
    assert sha256_canonical(a) == sha256_canonical(b)


def test_sha256_canonical_detects_changes():
    assert sha256_canonical({"x": 1}) != sha256_canonical({"x": 2})


def test_sha256_file_round_trip(tmp_path):
    p = tmp_path / "data.bin"
    p.write_bytes(b"assurance delta")
    assert sha256_file(p) == sha256_text("assurance delta")


def test_sha256_file_detects_byte_changes(tmp_path):
    p = tmp_path / "data.bin"
    p.write_bytes(b"assurance delta")
    before = sha256_file(p)
    p.write_bytes(b"assurance delta!")
    assert sha256_file(p) != before
