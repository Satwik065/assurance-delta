import pytest
from pathlib import Path
from gate.tamper import verify_frozen_files, verify_ledger_head, TamperError
from constitution.hashing import sha256_file
from constitution import constants as C

def test_clean_files_pass(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    hashes = {str(f): sha256_file(f)}
    # Should not raise an exception
    verify_frozen_files(hashes)

def test_tampered_file_caught(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    hashes = {str(f): sha256_file(f)}
    
    # AI sneaks in and modifies the file
    f.write_text("print('malicious')")
    
    with pytest.raises(TamperError, match="TAMPER: File modified"):
        verify_frozen_files(hashes)

def test_missing_file_caught(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    hashes = {str(f): sha256_file(f)}
    
    # AI deletes the file
    f.unlink()
    
    with pytest.raises(TamperError, match="TAMPER: Frozen file missing"):
        verify_frozen_files(hashes)

def test_ledger_head_clean(tmp_path, monkeypatch):
    f = tmp_path / "head.hash"
    f.write_text("abcd1234")
    monkeypatch.setattr(C, "LEDGER_HEAD_PATH", str(f))
    
    # Should not raise
    verify_ledger_head("abcd1234")

def test_ledger_head_tampered(tmp_path, monkeypatch):
    f = tmp_path / "head.hash"
    f.write_text("abcd1234")
    monkeypatch.setattr(C, "LEDGER_HEAD_PATH", str(f))
    
    # AI tries to rewrite the head hash to hide a deleted ledger entry
    f.write_text("fake5678")
    
    with pytest.raises(TamperError, match="TAMPER: Ledger head modified"):
        verify_ledger_head("abcd1234")
