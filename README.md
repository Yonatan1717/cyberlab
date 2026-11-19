# VaffelOps – Operation Broken Trust

En liten, fungerende og humoristisk intern velferdsportal til CyberOps-laben.
Ingen Python-pakker må installeres. Koden bruker bare Python 3 sitt standardbibliotek.

## Kjør lokalt

Åpne terminal i denne mappen og kjør:

```bash
python app.py
```

Åpne `http://127.0.0.1:8000` i nettleseren.

Nettsiden støtter vaffelbestilling, etterforsyning, kaffestatus og hendelseslogg.
Endringene lagres i minnet til serveren. Startes den på nytt, starter lageret på 12 %.

## Simulert beaconing (kun isolert, autorisert cyber-range)

I `app.py` finnes en tydelig blokk:

```text
# --------- SÅRBARHET / ØVELSESKODE STARTER HER ----------------
...
# --------- SÅRBARHET / ØVELSESKODE SLUTTER HER ----------------
```

Dette er **ingen faktisk fjernstyringsbakdør**. Den sender kun et ufarlig statisk status-JSON til en forhåndsvalgt lab-server. Den kjører ikke kommandoer, henter ikke filer eller legitimasjonsopplysninger og behandler ikke eventuelle kommandoer fra mottakeren.

I **terminal A**, start lab-mottakeren:

```bash
python collector.py
```

I **terminal B** (Windows PowerShell), start VaffelOps med lab-beacon aktivert:

```powershell
$env:ENABLE_LAB_BEACON = "1"
$env:LAB_COLLECTOR_URL = "http://127.0.0.1:5050/checkin"
$env:LAB_NODE_NAME = "WELFARE-01"
$env:LAB_BEACON_INTERVAL = "30"
python app.py
```

På Linux/macOS:

```bash
ENABLE_LAB_BEACON=1 LAB_COLLECTOR_URL=http://127.0.0.1:5050/checkin LAB_NODE_NAME=WELFARE-01 LAB_BEACON_INTERVAL=30 python3 app.py
```

**I lab med separate maskiner:** erstatt `127.0.0.1` i `LAB_COLLECTOR_URL` med IP-adressen til mottaker-VM-en. På mottakeren må du starte med `COLLECTOR_BIND=0.0.0.0` (eller ønsket interface/IP) og gi tilgang til TCP/5050 gjennom brannmuren. Ikke eksponer mottakeren på internett. Test kun på nett dere har tillatelse til å bruke.

Python-prosessen sender et HTTP POST-checkin straks etter oppstart og deretter hvert 30. sekund (minst 15 sekunder). Mottakeren skriver hver hendelse til `collector_events.jsonl`.

## Forslag til Blue Team-observasjoner

- Zeek: regelmessige HTTP POST-forespørsler fra WELFARE-01 til lab-mottakeren.
- Brannmur: utgående forbindelse til destinasjons-IP/port.
- Sysmon (med passende konfigurasjon): prosessen som etablerer nettverksforbindelsen, gjerne Event ID 3.
- Host forensics: uventet Python-kode i en intern velferdstjeneste og en vedvarende nettverksforbindelse.
- Sammenlign kildekode/revisjoner for å finne den avgrensede øvingsblokken.

## Skille fra øvrige øvingsfaser

Credential dumping, WinRM lateral movement, ekte fjernkontroll og sabotasje er **ikke** implementert i denne demonstrasjonen. Disse må behandles som separate, autoriserte øvingsmomenter og med sikre simuleringer eller forhåndslagde artefakter.

## Bytt adresse/port for nettsiden

På Windows PowerShell:

```powershell
$env:WEB_BIND = "0.0.0.0"
$env:WEB_PORT = "8000"
python app.py
```

`0.0.0.0` gjør at nettsiden kan nås fra andre maskiner på et nett dere kontrollerer.
