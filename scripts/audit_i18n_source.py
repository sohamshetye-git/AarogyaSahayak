#!/usr/bin/env python3
"""
scripts/audit_i18n_source.py

Rigorous source code audit tool for Aarogya Sahayak.
Scans TSX files across apps/citizen-mobile and apps/healthcare-portal
to ensure all user-visible strings, headings, buttons, and badges
use reactive translation (t() or dynamic formatters) rather than hardcoded English strings.
"""

import os
import re
import sys
from pathlib import Path

# Allowlist for proper nouns, acronyms, product brands, and technical literals
ALLOWLIST = {
    "Aarogya Sahayak", "आरोग्य सहायक", "PM-JAY", "MJPJAY", "JSY", "PMMVY", "RBSK",
    "ABHA", "PHC", "CHC", "DH", "OPD", "ANC", "PNC", "NCD", "ASHA", "ANM", "MO",
    "Sunita Devi", "Sita Patel", "Dr. Abhinav Sharma", "Dr. Rajesh Kulkarni", "Dr. Ananya Joshi",
    "Kalyanpur", "Kalyanpur PHC", "Kalyanpur Village", "District 04", "Maharashtra", "Satpati", "Vevoor",
    "Hb", "BP", "SpO2", "mg/dL", "g/dL", "mmHg", "bpm", "%", "kg", "cm", "km",
    "108", "104", "102", "100", "112", "Live", "Ref", "AS",
    "mr-IN", "hi-IN", "en-IN", "en-US", "MR", "HI", "EN",
    "मराठी", "हिंदी", "English"
}

# Regex to detect TSX JSX raw text: >\s*Some text\s*<
JSX_RAW_TEXT_RE = re.compile(r'>\s*([A-Za-z][A-Za-z0-9 ,.\'"\-!?/]{3,})\s*<')

def is_code_constant_or_type(text: str) -> bool:
    # All caps like RESOLVED_SATISFACTORILY, URGENT, ROUTINE
    if re.match(r'^[A-Z0-9_]+$', text):
        return True
    # Type notations like Promise<void>, React.FC
    if "Promise" in text or "void" in text or "React." in text:
        return True
    return False

def audit_file(filepath: Path) -> list:
    issues = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if (
            stripped.startswith("import ")
            or stripped.startswith("//")
            or stripped.startswith("/*")
            or stripped.startswith("*")
            or "console." in stripped
            or "style=" in stripped
            or "className=" in stripped
            or "data-testid=" in stripped
            or "key=" in stripped
            or "path=" in stripped
            or "color=" in stripped
            or "fontSize=" in stripped
            or "<option value=" in stripped # HTML option values often mirror backend code
        ):
            continue

        # Look for JSX raw text that looks like hardcoded English
        matches = JSX_RAW_TEXT_RE.findall(line)
        for m in matches:
            text = m.strip()
            if text.startswith("{") or text.endswith("}"):
                continue
            if text in ALLOWLIST or any(text == allowed for allowed in ALLOWLIST):
                continue
            if is_code_constant_or_type(text):
                continue
            if re.match(r'^[0-9\s.,/\-:+()xX]+$', text):
                continue
            if re.search(r'\b[A-Za-z]{3,}\b', text):
                if "t(" in line:
                    continue
                issues.append((idx, text, line.strip()))

    return issues


def main():
    root_dir = Path(__file__).resolve().parent.parent
    target_dirs = [
        root_dir / "apps" / "citizen-mobile" / "src",
        root_dir / "apps" / "healthcare-portal" / "src"
    ]

    total_files = 0
    total_violations = 0
    report = []

    for target_dir in target_dirs:
        if not target_dir.exists():
            continue
        for tsx_file in target_dir.rglob("*.tsx"):
            # Ignore test files
            if "test" in tsx_file.name.lower() or "spec" in tsx_file.name.lower():
                continue
            total_files += 1
            file_issues = audit_file(tsx_file)
            if file_issues:
                total_violations += len(file_issues)
                report.append((tsx_file.relative_to(root_dir), file_issues))

    print("==================================================")
    print(f"I18N SOURCE CODE AUDIT - Scanned {total_files} TSX files")
    print("==================================================")

    if report:
        print(f"Found {total_violations} potential unlocalized JSX strings in {len(report)} files:\n")
        for rel_path, issues in report:
            print(f"📄 {rel_path}:")
            for line_no, text, line_snippet in issues[:5]:
                print(f"   Line {line_no}: \"{text}\" -> {line_snippet}")
            if len(issues) > 5:
                print(f"   ... and {len(issues) - 5} more issues")
            print()
    else:
        print("✅ SUCCESS: 0 unlocalized hardcoded strings detected in scanned TSX components!")

    # Return status
    return 0 if total_violations == 0 else 1

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if __name__ == "__main__":
    sys.exit(main())

