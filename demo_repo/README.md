# Deterministic Demo Repository

This directory contains a sample repository with a known software bug in `math_utils.py` and unit tests in `test_math_utils.py`.

## Running Demo Test with CodePilot Harness:
```bash
python3 -m codepilot.cli fix --repo ./demo_repo --issue "Fix the discount calculation bug in math_utils.py where discount percentage formula is incorrect"
```
