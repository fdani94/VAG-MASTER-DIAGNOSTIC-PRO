# KID Diagnostic — VAG MASTER PRO V2

Versiunea 2 păstrează motorul de diagnostic și baza locală extinsă din aplicația existentă, dar folosește o interfață complet nouă.

## Interfață V2

- dashboard modern, aerisit, în limba română;
- temă light modernă, alb / gri-albăstrui, cu accente blue;
- carduri mari ilustrate pentru funcțiile principale;
- selectarea vehiculului înainte de intrarea în workspace;
- ferestre separate pentru Auto-Scan, DTC, Codări, Adaptări, Service & Resetări, Date Live, Module & Ghiduri și Rapoarte;
- layout responsive pentru rezoluții desktop mici și mari;
- logo KID Diagnostic și raport PDF cu antet compact;
- fără mod demo.

## Funcții conectate

- baza VAG existentă 1996–2024;
- Auto-Scan VCDS TXT / LOG / PDF;
- interpretare DTC și plan diagnostic automat;
- cauze, simptome, localizare componentă, valori de verificat și pași de reparație unde există în baza locală;
- codări, adaptări și proceduri de service filtrate pe vehicul;
- module și trasee VCDS;
- raport PDF KID Diagnostic pe baza Auto-Scan-ului analizat.

## Validare finală

Build-ul final trebuie să treacă testele funcționale Windows pentru toate cele 8 ferestre, Auto-Scan cu DTC de probă, plan diagnostic, DTC, codări/adaptări/service, Live Data, module, generare PDF și pornirea executabilului PyInstaller.

## Pornire locală

Din rădăcina repository-ului:

```bash
python versiune-v2/main_v2.py
```

V2 este dezvoltată separat de V1 pentru ca versiunea stabilă existentă să rămână funcțională în timpul dezvoltării.
