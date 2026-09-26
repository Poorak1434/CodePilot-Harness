"""
Failure classifier to categorize root causes from tracebacks and output logs.
"""
import re
from typing import Dict, Any


class FailureCategory:
    TEST_FAILURE = "TEST_FAILURE"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    IMPORT_ERROR = "IMPORT_ERROR"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    RUNTIME_ERROR = "RUNTIME_ERROR"


class FailureClassifier:
    @staticmethod
    def classify(error_msg: str, output_log: str) -> Dict[str, Any]:
        full_text = f"{error_msg}\n{output_log}"

        category = FailureCategory.RUNTIME_ERROR
        extract = ""

        if "Safety Policy Violation" in full_text:
            category = FailureCategory.SAFETY_VIOLATION
            extract = "Command or path prohibited by Safety Policy."

        elif "TimeoutExpired" in full_text or "timed out" in full_text.lower():
            category = FailureCategory.COMMAND_TIMEOUT
            extract = "Process execution exceeded allowed timeout limit."

        elif "SyntaxError" in full_text or "IndentationError" in full_text:
            category = FailureCategory.SYNTAX_ERROR
            match = re.search(r"(SyntaxError|IndentationError): [^\n]+", full_text)
            extract = match.group(0) if match else "Syntax or Indentation error."

        elif "ModuleNotFoundError" in full_text or "ImportError" in full_text:
            category = FailureCategory.IMPORT_ERROR
            match = re.search(r"(ModuleNotFoundError|ImportError): [^\n]+", full_text)
            extract = match.group(0) if match else "Missing module or import error."

        elif "FileNotFoundError" in full_text or "File not found" in full_text:
            category = FailureCategory.FILE_NOT_FOUND
            extract = "Target file or directory not found."

        elif "AssertionError" in full_text or "FAILED" in full_text or "FAIL:" in full_text:
            category = FailureCategory.TEST_FAILURE
            match = re.search(r"(AssertionError|FAIL|FAILED): [^\n]+", full_text)
            extract = match.group(0) if match else "Unit test assertion failure."

        return {
            "category": category,
            "extract": extract,
            "raw_log": full_text[:2000]
        }
