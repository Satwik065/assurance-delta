import os
import pytest
from gate.sandbox import run_in_sandbox

def test_sandbox_scrubs_secret_key(tmp_path):
    # Create a malicious script that tries to print the secret key
    script = tmp_path / "malicious.py"
    script.write_text("import os\nprint(os.environ.get('AD_TOKEN_KEY', 'NOT_FOUND'))")
    
    # Set the key in our parent environment
    os.environ["AD_TOKEN_KEY"] = "super_secret"
    
    # The sandbox should scrub it
    output = run_in_sandbox(str(script))
    assert output.strip() == "NOT_FOUND"
    
    # Clean up
    del os.environ["AD_TOKEN_KEY"]
