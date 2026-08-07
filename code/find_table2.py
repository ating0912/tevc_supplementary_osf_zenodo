import sys
from pathlib import Path
try:
    from PyPDF2 import PdfReader
except Exception as e:
    print('NO_PYPDF2', e)
    raise
pdf = Path(sys.argv[1])
reader = PdfReader(str(pdf))
for i, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or ''
    if 'Table 2' in text or 'TABLE 2' in text or 'Table2' in text:
        print('--- PAGE', i, '---')
        print(text[:4000])
