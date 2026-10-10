# 1KOMMA5° Heartbeat & Energidata

Home Assistant-integration til 1KOMMA5°-anlæg, der bruger det ældre **gridX API** via `my.1komma5.io`.

**Version:** 0.3.0 · **Integrationens domæne:** `heartbeat_comparison`

> Projektet er en uofficiel integration og er ikke udviklet eller supporteret af 1KOMMA5° eller gridX.

## Funktioner

### Heartbeat-beslutninger

Integrationen henter batteriets optimeringsbeslutninger fra `GET /systems/{system_id}/timeofuse/decisions`. Disse sensorer oprettes:

| Sensor | Indhold |
| --- | --- |
| Aktuel beslutning | Batteribeslutning, der gælder netop nu |
| Seneste beslutning | Senest påbegyndte batteribeslutning |
| Antal beslutninger | Antal batteribeslutninger i API-svaret; seneste og kommende ligger som attributter |

Der filtreres på beslutningskoder, der begynder med `BATTERY_`. Planlagte fremtidige beslutninger rapporteres ikke som allerede indtrufne. Beslutningsdata hentes hvert **5. minut**. Tidsafhængige sensortilstande opdateres også lokalt hvert minut.

### Energidata

Integrationen forsøger at hente live-data fra `GET /systems/{system_id}/live` hvert **60. sekund**.

| Sensor | Enhed |
| --- | --- |
| Solproduktion | W |
| Husforbrug | W |
| Netto neteffekt | W |
| Batterieffekt | W |
| Batteriets ladestand | % |

Hvis et felt mangler i API-svaret, rapporterer sensoren ingen værdi frem for at gætte. **Bemærk:** Feltstruktur, enheder og fortegn skal kontrolleres mod faktiske GridX-data. Det er endnu ikke verificeret, at alle fem sensorer får korrekte værdier på alle anlæg. Manglende adgang til live-endpointet bør ikke forhindre de eksisterende beslutningssensorer i at fungere.

### Energy Management-kontakt

En `switch` med navnet **Energy Management** efterligner portalens indstilling *Energy Management*.

- **Status** aflæses fra `GET /systems/{system_id}` → `metadata.energy.ems.agreedEMSTerms`.
- **Tænd/sluk** sender `PATCH /systems/{system_id}` og ændrer **kun** `metadata.energy.ems.agreedEMSTerms` til `true` eller `false`.
- Efter ændringen læses status igen for at bekræfte resultatet.
- Status opdateres normalt hvert **2. minut**.

**Vigtigt:** Kontakten styrer portalens accept-/aktiveringsindstilling `agreedEMSTerms`. Den ændrer **ikke** `enabledEMS` eller `/timeofuse/settings.enabled`, og den er ikke dokumenteret som en fysisk afbryder for batterioptimering. Brug den med forståelse for, at den ændrer EMS-vilkårsstatus i 1KOMMA5°.

## Installation med HACS

1. Åbn **HACS** i Home Assistant, vælg menuen **Custom repositories**, og tilføj `https://github.com/hinge83/1KOMMA5-Heartbeat-Energidata` som typen **Integration**.
2. Download integrationen gennem HACS.
3. Genstart Home Assistant.
4. Gå til **Indstillinger → Enheder og tjenester → Tilføj integration**, og vælg **1KOMMA5° Heartbeat & Energidata**.
5. Indtast dine loginoplysninger til den ældre 1KOMMA5°/gridX-portal. System-id er valgfrit, hvis kontoen kun har ét anlæg.

Har du allerede tilføjet integrationen, skal du **opdatere** den i HACS og genstarte Home Assistant – du behøver ikke oprette den igen.

## Kompatibilitet og begrænsninger

- Virker kun med konti, der kan autentificeres mod den **ældre gridX Auth0 password-realm** og tilgå de anvendte API-endpoints.
- Understøtter ikke automatisk den nyere 1KOMMA5° OAuth2/PKCE-platform.
- Integrationens interne domæne hedder fortsat `heartbeat_comparison`, så eksisterende konfigurationsposter og sensoridentifikatorer kan bevares.
- Adgangskode opbevares i Home Assistants konfigurationspost; adgangstoken holdes i hukommelsen. Læg aldrig credentials, tokens eller systemdata i GitHub-issues.
- GridX' API kan ændre sig uden varsel. Særligt de nye energisensorer og kontakten bør kontrolleres efter opdatering.
- Integrationen styrer ikke Sungrow-inverter eller EVCC direkte.

## Udvikling og fejlmelding

Kildekode: [GitHub](https://github.com/hinge83/1KOMMA5-Heartbeat-Energidata) · [Issues](https://github.com/hinge83/1KOMMA5-Heartbeat-Energidata/issues)

Integrationsfilerne ligger i `custom_components/heartbeat_comparison/`. Udviklingsændringer bør testes på en separat branch og helst i et separat Home Assistant-miljø før udrulning.
