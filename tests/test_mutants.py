from mutants.catalog import generate_m1_weakened_threshold, generate_m3c_scope_mismatch

def test_m1_has_weakened_bound():
    m1 = generate_m1_weakened_threshold()
    assert m1["changes"][0]["new_bound"] == 100.0
    assert m1["changes"][0]["req_class"] == "RETAIN"

def test_m3c_uses_bulk_scope_for_control():
    m3c = generate_m3c_scope_mismatch()
    assert m3c["changes"][0]["target_metric"] == "CONTROL_p99"
    assert m3c["changes"][0]["scope_text"] == "class == 'BULK'"
