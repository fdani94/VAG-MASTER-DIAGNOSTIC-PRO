# KID Diagnostic V2.2.1 — audit autoritar

Acest release folosește un singur workflow autoritar: `KID Diagnostic V2.2.1 FINAL Audit`.

Invariante verificate:
- motorul este filtrat după generație și intervalul de ani din `vehicle_engines`;
- un Auto-Scan cu `Chassis Type` incompatibil este respins pentru confirmarea vehiculului;
- un Auto-Scan fără chassis poate fi analizat, dar nu confirmă codări sau controllerul;
- `MODUL GĂSIT AUTOSCAN` nu este echivalent cu `CONTROLLER CONFIRMAT`;
- `CONTROLLER CONFIRMAT` necesită identitate SW/HW/ASAM corelată cu procedura/sursa;
- pagina Module nu face fallback la întreg catalogul când `generation_modules` nu are mapări;
- schimbarea vehiculului șterge dovezile Auto-Scan ale vehiculului anterior;
- buildul final verifică sursa, UI/AI lifecycle, teste adversariale, PyInstaller, EXE smoke, pornire normală, installer și SHA-256.

Workflow-urile KID V2 vechi au fost eliminate pentru a nu produce verdicturi contradictorii pe PR-ul final.
