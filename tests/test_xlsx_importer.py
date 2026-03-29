import tempfile
import unittest
import zipfile
from pathlib import Path

from karpuzvet.xlsx_importer import load_cases_from_xlsx


class XlsxImporterTests(unittest.TestCase):
    def test_reads_minimal_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sayfa2" sheetId="1" r:id="rId1"/></sheets></workbook>""")
                archive.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>""")
                archive.writestr("xl/sharedStrings.xml", """<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>PROTOKOL NO</t></si><si><t>GONDEREN KURUM</t></si><si><t>FATIH VET</t></si><si><t>Kedi</t></si><si><t>Mavi</t></si><si><t>Deri biyopsisi</t></si></sst>""")
                archive.writestr("xl/worksheets/sheet1.xml", """<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>SIRA</t></is></c><c r="B1" t="s"><v>0</v></c><c r="E1" t="s"><v>1</v></c></row><row r="2"><c r="A2"><v>1</v></c><c r="B2" t="inlineStr"><is><t>26-201</t></is></c><c r="C2"><v>46038</v></c><c r="E2" t="s"><v>2</v></c><c r="G2" t="s"><v>4</v></c><c r="H2" t="s"><v>3</v></c><c r="M2" t="s"><v>5</v></c></row></sheetData></worksheet>""")
            records = load_cases_from_xlsx(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].protocol_no, "26-201")
            self.assertEqual(records[0].sender_clinic, "FATIH VET")
            self.assertEqual(records[0].patient_name, "Mavi")
            self.assertEqual(records[0].acceptance_date, "2026-01-16")


if __name__ == "__main__":
    unittest.main()
