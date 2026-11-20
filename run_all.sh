#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/src"
python model.py
python phone_analysis.py
python figures.py
python build_workbook.py
python build_report.py
python build_letter.py
if command -v soffice >/dev/null; then
  soffice --headless --convert-to pdf --outdir ../outputs ../outputs/report.docx ../outputs/letter_istanbul_governorship.docx
fi
echo "Done – see outputs/"
