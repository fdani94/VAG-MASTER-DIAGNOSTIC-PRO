# KID Diagnostic — VAG MASTER PRO V2

Versiunea 2 păstrează motorul de diagnostic și baza locală extinsă din aplicația existentă, dar folosește o interfață complet nouă.

## Interfață V2

- dashboard modern, aerisit, în limba română;
- carduri mari ilustrate pentru funcțiile principale;
- selectarea vehiculului înainte de intrarea în workspace;
- pagini separate pentru Auto-Scan, DTC, Codări, Adaptări, Service & Resetări, Date Live, Module & Ghiduri și Rapoarte;
- logo KID Diagnostic și aspect unitar dark / automotive;
- fără mod demo.

## Funcții conectate

- baza VAG existentă 1996–2024;
- Auto-Scan VCDS TXT / LOG / PDF;
- interpretare DTC și plan diagnostic automat;
- cauze, simptome, localizare componentă, valori de verificat și pași de reparație unde există în baza locală;
- codări, adaptări și proceduri de service filtrate pe vehicul;
- module și trasee VCDS;
- raport PDF KID Diagnostic pe baza Auto-Scan-ului analizat.

## Pornire locală

Din rădăcina repository-ului:

```bash
python versiune-v2/main_v2.py
```

V2 este dezvoltată separat de V1 pentru ca versiunea stabilă existentă să rămână funcțională în timpul dezvoltării.
