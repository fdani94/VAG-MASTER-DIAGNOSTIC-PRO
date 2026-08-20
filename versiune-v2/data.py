from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Vehicle:
    brand: str = "Volkswagen"
    model: str = "Golf VII"
    year: int = 2017
    engine: str = "2.0 TDI"
    vin: str = "WVWZZZAUZHW123456"
    mileage_km: int = 164_250
    modules: int = 27

    @property
    def display_name(self) -> str:
        return f"{self.brand} {self.model}"

    @property
    def subtitle(self) -> str:
        return f"{self.year} • {self.engine}"


@dataclass(frozen=True)
class ModuleResult:
    address: str
    name: str
    status: str = "În așteptare"
    dtc_count: int = 0


@dataclass(frozen=True)
class DTCInfo:
    code: str
    title: str
    severity: str
    system: str
    summary: str
    causes: tuple[str, ...]
    checks: tuple[str, ...]
    repairs: tuple[str, ...]
    location: str
    warning: str = "Confirmați cauza prin măsurători înainte de înlocuirea pieselor."


@dataclass(frozen=True)
class GuidedProcedure:
    title: str
    category: str
    module: str
    platform: str
    duration: str
    description: str
    prerequisites: tuple[str, ...]
    steps: tuple[str, ...]
    verification: tuple[str, ...]
    safety: str


@dataclass
class ScanResult:
    vehicle: Vehicle = field(default_factory=Vehicle)
    modules: list[ModuleResult] = field(default_factory=list)
    dtc_codes: list[str] = field(default_factory=list)
    source_name: str = "Demonstrație V2"
    raw_text: str = ""

    @property
    def fault_modules(self) -> int:
        return sum(1 for module in self.modules if module.dtc_count > 0)

    @property
    def total_dtc(self) -> int:
        explicit = sum(module.dtc_count for module in self.modules)
        return max(explicit, len(self.dtc_codes))


SAMPLE_MODULES: tuple[ModuleResult, ...] = (
    ModuleResult("01", "Motor", "OK"),
    ModuleResult("02", "Transmisie automată", "OK"),
    ModuleResult("03", "ABS / ESP", "OK"),
    ModuleResult("08", "Climatizare", "OK"),
    ModuleResult("09", "Electronică centrală", "OK"),
    ModuleResult("15", "Airbag", "1 eroare", 1),
    ModuleResult("16", "Coloana direcției", "OK"),
    ModuleResult("17", "Bord / Instrumente", "OK"),
    ModuleResult("19", "CAN Gateway", "OK"),
    ModuleResult("42", "Ușa șofer", "OK"),
    ModuleResult("52", "Ușa pasager", "OK"),
    ModuleResult("5F", "Sistem multimedia", "OK"),
)


DTC_DATABASE: dict[str, DTCInfo] = {
    "P0401": DTCInfo(
        code="P0401",
        title="Debit insuficient în sistemul EGR",
        severity="Ridicată",
        system="Motor / Emisii",
        summary="ECU detectează un debit EGR mai mic decât valoarea solicitată.",
        causes=(
            "Supapă EGR încărcată cu depuneri sau blocată",
            "Conducte ori răcitor EGR obturate",
            "Senzor de poziție EGR sau cablaj defect",
            "Debitmetru cu valori neplauzibile",
        ),
        checks=(
            "Salvați freeze-frame-ul și verificați când apare eroarea",
            "Comparați poziția EGR solicitată cu poziția reală",
            "Verificați debitul de aer măsurat și etanșeitatea admisiei",
            "Testați alimentarea, masa și semnalul actuatorului EGR",
        ),
        repairs=(
            "Curățați traseul EGR numai după inspecție",
            "Reparați cablajul sau conectorii deteriorați",
            "Înlocuiți componenta doar dacă testele confirmă defectul",
            "Ștergeți DTC, efectuați test rutier și rescanați",
        ),
        location="Între galeria de evacuare și galeria de admisie; poziția exactă depinde de codul motor.",
    ),
    "P0299": DTCInfo(
        code="P0299",
        title="Presiune de supraalimentare prea mică",
        severity="Ridicată",
        system="Motor / Turbo",
        summary="Presiunea reală de supraalimentare rămâne sub valoarea cerută.",
        causes=(
            "Pierdere pe furtunurile sau intercoolerul de supraalimentare",
            "Actuator turbo, geometrie variabilă sau electrovalvă defectă",
            "Vacuum insuficient la sistemele pneumatice",
            "Senzor MAP sau debitmetru cu valori incorecte",
        ),
        checks=(
            "Comparați boost specified cu boost actual în sarcină",
            "Efectuați test de etanșeitate pe traseul de aer",
            "Verificați vacuumul și cursa actuatorului",
            "Inspectați furtunurile, colierele și intercoolerul",
        ),
        repairs=(
            "Remediați pierderile de aer sau vacuum",
            "Curățați ori reparați mecanismul doar după confirmare",
            "Calibrați actuatorul conform procedurii modelului",
            "Test rutier, ștergere DTC și rescanare",
        ),
        location="Turbocompresorul este montat pe galeria de evacuare; actuatorul se află pe carcasa turbinei.",
    ),
    "P2002": DTCInfo(
        code="P2002",
        title="Eficiența filtrului de particule sub limită",
        severity="Ridicată",
        system="Motor / DPF",
        summary="Valorile calculate indică o eficiență DPF necorespunzătoare.",
        causes=(
            "Filtru încărcat, fisurat sau înlocuit necorespunzător",
            "Senzor de presiune diferențială ori conducte defecte",
            "Senzori temperatură gaze cu valori neplauzibile",
            "Regenerări întrerupte din cauza altor erori de motor",
        ),
        checks=(
            "Citiți masa de funingine, masa de cenușă și presiunea diferențială",
            "Verificați conductele senzorului de presiune",
            "Confirmați temperaturile EGT înainte și după DPF",
            "Verificați condițiile și istoricul regenerărilor",
        ),
        repairs=(
            "Remediați întâi erorile care blochează regenerarea",
            "Curățați profesional ori înlocuiți DPF dacă testele o cer",
            "Nu resetați cenușa fără o intervenție reală asupra filtrului",
            "Verificați presiunea după reparație și rescanați",
        ),
        location="Pe linia de evacuare, după turbocompresor și catalizatorul de oxidare, în funcție de motorizare.",
    ),
    "P0671": DTCInfo(
        code="P0671",
        title="Circuit bujie incandescentă cilindrul 1",
        severity="Medie",
        system="Motor / Preîncălzire",
        summary="Circuitul electric al bujiei cilindrului 1 este în afara parametrilor.",
        causes=(
            "Bujie incandescentă întreruptă sau cu rezistență incorectă",
            "Contact slab în fișă sau cablaj",
            "Modul de comandă bujii defect",
        ),
        checks=(
            "Măsurați rezistența fără a aplica direct 12 V",
            "Comparați cu celelalte bujii la aceeași temperatură",
            "Verificați ieșirea modulului și cablajul",
        ),
        repairs=(
            "Reparați contactele ori cablajul",
            "Înlocuiți bujia cu specificația corectă",
            "Ștergeți eroarea și testați la pornire rece",
        ),
        location="În chiulasă, lângă injectorul cilindrului 1; accesul diferă după codul motor.",
    ),
    "U1121": DTCInfo(
        code="U1121",
        title="Mesaj CAN lipsă sau neplauzibil",
        severity="Medie",
        system="Rețea CAN",
        summary="Un modul nu primește mesajul așteptat de la altă unitate de comandă.",
        causes=(
            "Tensiune joasă sau alimentare instabilă",
            "Modul offline ori configurat incorect",
            "Cablaj CAN sau conector cu rezistență de contact",
        ),
        checks=(
            "Efectuați Auto-Scan complet și identificați modulul sursă",
            "Verificați tensiunea bateriei și istoricul erorii",
            "Verificați alimentările și integritatea rețelei CAN",
        ),
        repairs=(
            "Reparați alimentarea sau cablajul confirmat defect",
            "Restabiliți codarea originală dacă eroarea a apărut după modificări",
            "Ștergeți DTC și rescanați toate modulele",
        ),
        location="Rețeaua CAN traversează mai multe module; diagnosticul trebuie pornit de la modulul care nu comunică.",
    ),
}


GENERIC_DTC = DTCInfo(
    code="DTC",
    title="Cod nerecunoscut în baza locală",
    severity="De verificat",
    system="Necunoscut",
    summary="Codul a fost găsit în Auto-Scan, dar nu are încă o fișă dedicată în baza V2.",
    causes=("Consultați descrierea exactă din modul și freeze-frame-ul.",),
    checks=(
        "Salvați Auto-Scan-ul original",
        "Identificați modulul, piesa și condițiile în care apare",
        "Verificați alimentările, cablajul și valorile măsurate",
    ),
    repairs=(
        "Remediați cauza confirmată prin măsurători",
        "Nu înlocuiți piese doar pe baza codului",
        "Ștergeți DTC și verificați dacă reapare",
    ),
    location="Poziția depinde de modul, model, an și codul motor.",
)


CODING_PROCEDURES: tuple[GuidedProcedure, ...] = (
    GuidedProcedure(
        "Coming Home / Leaving Home",
        "Codare",
        "09 – Electronică centrală",
        "PQ35 / MQB, în funcție de echipare",
        "10–15 min",
        "Configurarea funcțiilor de iluminare la încuiere și descuiere.",
        ("Tensiune stabilă", "Auto-Scan salvat", "Codarea originală exportată"),
        (
            "Selectați exact vehiculul și identificați BCM-ul",
            "Deschideți Adaptation sau Long Coding, după platformă",
            "Căutați funcția denumită Coming Home / Leaving Home",
            "Modificați numai opțiunea documentată pentru modulul identificat",
            "Salvați și ciclizați contactul",
        ),
        ("Funcția lucrează conform setării", "Nu apar DTC noi", "Codarea originală rămâne arhivată"),
        "Nu folosiți valori copiate de la alt număr de piesă BCM.",
    ),
    GuidedProcedure(
        "Închidere automată la deplasare",
        "Codare",
        "09 / 46 – Confort",
        "PQ / MQB",
        "5–10 min",
        "Activează blocarea automată a ușilor la viteza suportată de modul.",
        ("Vehicul staționat", "Geam șofer deschis", "Backup codare"),
        (
            "Identificați modulul care gestionează închiderea centralizată",
            "Căutați Auto Lock / locking while driving",
            "Activați funcția disponibilă în modul",
            "Salvați și testați la viteză redusă într-o zonă sigură",
        ),
        ("Ușile se blochează o singură dată", "Deblocarea interioară funcționează", "Fără DTC"),
        "Păstrați posibilitatea de deschidere din interior și respectați echiparea vehiculului.",
    ),
    GuidedProcedure(
        "Mișcare ace la pornire",
        "Codare",
        "17 – Instrumente",
        "UDS / MQB",
        "5 min",
        "Activează testul acelor la punerea contactului, dacă este suportat.",
        ("Cluster compatibil", "Backup adaptări"),
        (
            "Deschideți modulul 17 – Instrumente",
            "În Adaptation căutați staging / indicator celebration",
            "Activați funcția dacă apare nominal în modul",
            "Ciclizați contactul și verificați bordul",
        ),
        ("Acele execută o singură cursă", "Nicio avertizare nouă"),
        "Nu forțați o funcție absentă din datasetul modulului.",
    ),
)


ADAPTATION_PROCEDURES: tuple[GuidedProcedure, ...] = (
    GuidedProcedure(
        "Înregistrare baterie",
        "Adaptare",
        "19 / 61 / 01 – dependent de platformă",
        "VAG cu management energetic",
        "10 min",
        "Înregistrează o baterie nouă cu tehnologia și capacitatea corecte.",
        ("Baterie montată corect", "Încărcător stabil", "Tip și capacitate cunoscute"),
        (
            "Identificați modulul de management al energiei",
            "Citiți și salvați datele bateriei vechi",
            "Introduceți producătorul, capacitatea, tehnologia și serialul conform suportului modulului",
            "Confirmați adaptarea și ciclizați contactul",
        ),
        ("Noua baterie este memorată", "Tensiunea de încărcare este plauzibilă", "Fără DTC energetic"),
        "AGM/EFB/plumb-acid și capacitatea trebuie să corespundă bateriei montate.",
    ),
    GuidedProcedure(
        "Calibrare senzor unghi volan",
        "Adaptare",
        "03 / 44 – ABS / Direcție",
        "Dependent de platformă",
        "10–20 min",
        "Inițializează poziția zero după intervenții autorizate.",
        ("Geometrie corectă", "Volan centrat", "Fără defect mecanic"),
        (
            "Verificați DTC și poziția volanului",
            "Selectați Basic Settings nominal pentru steering angle",
            "Urmați instrucțiunile afișate de modul",
            "Efectuați testul rutier cerut de procedură",
        ),
        ("Unghi aproape de 0° cu roțile drepte", "Martorii se sting", "Basic setting: OK"),
        "Nu calibrați pentru a masca o geometrie sau o piesă defectă.",
    ),
    GuidedProcedure(
        "Setare de bază clapetă accelerație",
        "Adaptare",
        "01 – Motor",
        "Benzină, dacă ECU suportă",
        "5–10 min",
        "Rulează învățarea pozițiilor clapetei după curățare sau înlocuire.",
        ("Motor oprit", "Contact pus", "Baterie stabilă", "Fără DTC de alimentare"),
        (
            "Selectați Basic Settings nominal pentru throttle adaptation",
            "Porniți procedura fără a atinge accelerația",
            "Așteptați mesajul Finished correctly / ADP OK",
            "Opriți contactul conform instrucțiunilor ECU",
        ),
        ("Adaptarea este acceptată", "Ralanti stabil după pornire", "DTC nu reapare"),
        "Procedura și condițiile exacte diferă după ECU și cod motor.",
    ),
)


SERVICE_PROCEDURES: tuple[GuidedProcedure, ...] = (
    GuidedProcedure(
        "Resetare interval service",
        "Service",
        "17 – Instrumente / SRI Reset",
        "Toate platformele suportate",
        "5 min",
        "Resetează intervalul numai după efectuarea reală a operației de întreținere.",
        ("Revizie efectuată", "Ulei cu specificația corectă", "Kilometraj notat"),
        (
            "Deschideți Applications → SRI Reset sau funcția nominală a modulului 17",
            "Citiți valorile curente și salvați-le",
            "Selectați tipul corect de service fix sau flexibil",
            "Aplicați și verificați noua scadență în bord",
        ),
        ("Noua scadență este corectă", "Avertizarea nu reapare", "Istoricul este salvat"),
        "Nu resetați intervalul fără ca revizia să fi fost efectuată.",
    ),
    GuidedProcedure(
        "Setare de bază frână de parcare",
        "Service",
        "53 – Parking Brake",
        "Vehicule cu EPB",
        "15–25 min",
        "Deschide și închide etrierele prin funcția de service suportată.",
        ("Vehicul securizat", "Încărcător stabil", "Piese montate corect"),
        (
            "Salvați DTC și selectați modul de schimb plăcuțe",
            "Comandați deschiderea numai când mecanismul este liber",
            "Efectuați lucrarea mecanică",
            "Comandați închiderea și rulați basic setting dacă este cerut",
        ),
        ("EPB funcționează simetric", "Fără zgomote anormale", "Fără DTC"),
        "Nu acționați EPB cu etrierul demontat sau fără sursă stabilă.",
    ),
    GuidedProcedure(
        "Verificare regenerare DPF",
        "Service",
        "01 – Motor",
        "TDI cu DPF",
        "20–40 min",
        "Ghidează verificarea condițiilor înaintea unei regenerări controlate.",
        ("Nivel ulei corect", "Fără scurgeri", "Fără DTC care blochează regenerarea"),
        (
            "Citiți funinginea, cenușa, presiunea și temperaturile",
            "Verificați dacă regenerarea este permisă de ECU",
            "Alegeți numai procedura nominală pentru codul motor",
            "Monitorizați temperaturile și opriți dacă apar condiții nesigure",
        ),
        ("Presiunea și funinginea scad plauzibil", "Temperaturile revin normal", "Fără DTC nou"),
        "Nu forțați regenerarea la un filtru deteriorat, supraîncărcat sau cu ulei diluat.",
    ),
)


def dtc_info(code: str) -> DTCInfo:
    normalized = code.strip().upper()
    if normalized in DTC_DATABASE:
        return DTC_DATABASE[normalized]
    return DTCInfo(
        code=normalized or GENERIC_DTC.code,
        title=GENERIC_DTC.title,
        severity=GENERIC_DTC.severity,
        system=GENERIC_DTC.system,
        summary=GENERIC_DTC.summary,
        causes=GENERIC_DTC.causes,
        checks=GENERIC_DTC.checks,
        repairs=GENERIC_DTC.repairs,
        location=GENERIC_DTC.location,
        warning=GENERIC_DTC.warning,
    )


def default_scan() -> ScanResult:
    return ScanResult(
        vehicle=Vehicle(),
        modules=list(SAMPLE_MODULES),
        dtc_codes=["P0401"],
        source_name="Demonstrație V2",
    )


def find_procedures(items: Iterable[GuidedProcedure], query: str) -> list[GuidedProcedure]:
    needle = query.strip().casefold()
    if not needle:
        return list(items)
    return [
        item
        for item in items
        if needle
        in f"{item.title} {item.category} {item.module} {item.platform} {item.description}".casefold()
    ]
