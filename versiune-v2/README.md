# KID VAG MASTER - Diagnostic PRO V2

V2 este aplicația desktop profesională pentru importul, validarea și analiza rapoartelor Auto-Scan VCDS. Interfața este integral în română, fiecare funcție se deschide într-o fereastră separată, iar aplicația nu generează date artificiale.

Textele de interpretare sunt prezentate în română. Denumirea originală a erorii și identificatorii exacți ai canalelor VCDS sunt păstrați separat pentru trasabilitate și pentru a nu altera informația de atelier.

## Funcții principale

- panou principal aerisit, cu opt carduri ilustrate și ferestre independente;
- import Auto-Scan VCDS din `.txt`, `.log`, `.csv` și `.pdf` cu text extractibil;
- motor de interpretare pentru formate VCDS vechi K-Line, CAN și UDS;
- identificare VIN, șasiu, platformă, an, cod motor, kilometraj, module, numere de piesă, codări și DTC;
- validare automată între numărul de erori declarat de VCDS și numărul extras;
- eliminarea modulelor duplicate din sumarul și secțiunile detaliate ale aceluiași raport;
- 9.616 coduri DTC unice: acoperire pentru 9.533 coduri OBD-II generice CC0, iar definițiile suprapuse sunt înlocuite de fișele VAG detaliate;
- 266 proceduri de codare, adaptare, calibrare și service, cu 16.144 asocieri de aplicabilitate;
- 150 generații VAG și 43 familii/coduri de motor în baza locală;
- fișă de atelier în română pentru fiecare cod: simptome, cauze, localizare, verificări, trasee VCDS, valori așteptate, reparație, înlocuire și surse;
- afișarea exclusivă a parametrilor reali memorați la apariția erorilor în raportul importat;
- raport PDF de atelier cu rezumat executiv, corelări, prioritizare, inventar module, fișă completă pentru fiecare DTC, anexa VCDS și checklist final;
- build automat `.exe` pentru Windows prin GitHub Actions.

## Siguranță și limite

V2 importă, analizează, raportează și ghidează. Nu scrie direct în ECU și nu pretinde existența unei conexiuni hardware. Codările și adaptările sunt proceduri de atelier care trebuie aplicate numai după identificarea exactă a vehiculului, salvarea valorilor originale și confirmarea compatibilității unității.

Un PDF scanat ca imagine necesită OCR înainte de import. PDF-urile exportate direct din VCDS, care conțin text, sunt citite local cu `pypdf`.

Catalogul generic provine din [OBDex](https://github.com/foerbsnavi/OBDex), date CC0-1.0. Constructorul bazei verifică numărul de 9.533 de intrări, duplicatele, integritatea SQLite și definiții-etalon precum P0130/P0131/P0132, pentru a detecta automat un catalog deplasat sau incomplet.

Snapshotul profesional este păstrat în repository ca arhivă SQLite comprimată și verificată. La prima pornire din surse, aplicația îl extrage atomic într-un cache local și îi verifică integritatea, limba și dimensiunea catalogului. Buildul Windows regenerează și include direct baza SQLite completă.

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

Pentru regenerarea snapshotului din catalogul și pachetele-sursă incluse:

```bash
python scripts/build_database.py
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
python scripts/build_database.py
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
├── database.py
├── localization.py
├── analysis_engine.py
├── parser.py
├── reporting.py
├── theme.py
├── assets/
├── scripts/
└── tests/
```

## Observație profesională

Codurile DTC indică sistemul care a detectat o abatere, nu confirmă automat piesa defectă. Raportul și ghidurile V2 se folosesc împreună cu măsurători, schema electrică și documentația exactă pentru codul motor și numărul piesei identificate.
