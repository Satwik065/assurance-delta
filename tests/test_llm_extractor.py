from llm.extractor import extract_python_code

def test_extract_python_markdown():
    raw = "Here is your code:\n```python\nclass ProposedScheduler:\n    pass\n```\nHope this helps!"
    assert extract_python_code(raw) == "class ProposedScheduler:\n    pass"

def test_extract_plain_markdown():
    raw = "```\nclass ProposedScheduler:\n    pass\n```"
    assert extract_python_code(raw) == "class ProposedScheduler:\n    pass"

def test_extract_no_markdown():
    raw = "class ProposedScheduler:\n    pass"
    assert extract_python_code(raw) == "class ProposedScheduler:\n    pass"
