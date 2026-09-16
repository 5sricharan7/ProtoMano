"""Test that preprocessing_pipeline.pkl loads in a clean Python process.

This verifies the artifact is production-ready and doesn't depend on
__main__ injection or runtime compatibility shims.
"""

import subprocess
import sys
from pathlib import Path


def test_preprocessing_loads_in_clean_process():
    """Load preprocessing_pipeline.pkl in a fresh Python subprocess."""
    test_script = """
import sys
import joblib

# Load the artifact - this must not fail
pipeline = joblib.load('../artifacts/preprocessing_pipeline.pkl')

# Verify it's a FunctionTransformer
from sklearn.preprocessing import FunctionTransformer
assert isinstance(pipeline, FunctionTransformer), f"Expected FunctionTransformer, got {type(pipeline)}"

# Verify function reference is stable (not __main__)
func = pipeline.func
assert func.__module__ != '__main__', f"Function still references __main__: {func.__module__}"
assert 'preprocess_for_inference' in func.__name__, f"Wrong function: {func.__name__}"

# Verify it works
import pandas as pd
import numpy as np
df = pd.DataFrame([[1.0] * 44])
result = pipeline.transform(df)
assert result.shape == (1, 44), f"Wrong shape: {result.shape}"
assert result.dtype == np.float64, f"Wrong dtype: {result.dtype}"

print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to load in clean process:\n{result.stderr}"
    assert "OK" in result.stdout, f"Test did not pass:\n{result.stdout}"