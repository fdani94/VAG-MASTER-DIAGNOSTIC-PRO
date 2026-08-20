# KID VAG MASTER — Diagnostic PRO V2

Versiunea V2 este o aplicație desktop separată, construită în Python și PySide6, cu o interfață aerisită inspirată de echipamentele profesionale de diagnoză auto.

## Ce funcționează în V2

- dashboard profesional cu opt carduri ilustrate;
- fiecare funcție se deschide într-o fereastră separată;
- import Auto-Scan VCDS din `.txt`, `.log` sau `.csv`;
- detectare VIN, kilometraj, module și coduri DTC din raport;
- fereastră DTC cu explicații, cauze, verificări, reparație și localizarea piesei;
- ghiduri separate pentru codări, adaptări și operații service;
- panou Date Live demonstrativ cu grafice animate;
- ghid de reparații cu căutare;
- generare raport PDF profesional;
- build automat `.exe` pentru Windows prin GitHub Actions.

## Siguranță

V2 rulează momentan în mod de **import, analiză, raportare și ghidare**. Nu scrie direct în ECU și nu simulează o conexiune hardware reală. Integrarea cu un driver de interfață va fi adăugată separat numai după validare.

## Pornire locală

Necesită Python 3.11 sau 3.12, pe Windows 10/11 64-bit.

```bat
cd versiune-v2
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Pe macOS/Linux, înlocuiește activarea mediului cu:

```bash
source .venv/bin/activate
```

## Build Windows

Rulează:

```bat
scripts\build_windows.bat
```

Executabilul va fi creat în:

```text
dist\KID-VAG-MASTER-V2\KID-VAG-MASTER-V2.exe
```

## Teste

```bash
python -m unittest discover -s tests -v
```

## Structură

```text
versiune-v2/
├── main.py
├── app.py
├── widgets.py
├── window_base.py
├── scan_window.py
├── dtc_window.py
├── feature_windows.py
├── data.py
├── parser.py
├── reporting.py
├── theme.py
├── assets/
├── scripts/
└── tests/
```

## Observație importantă

Codurile DTC indică sistemul care a detectat o abatere, nu confirmă automat piesa defectă. Raportul și ghidurile V2 trebuie folosite împreună cu măsurători, schema electrică și documentația exactă pentru codul motor/modulul identificat.
