# 🛠️ Fehleranalyse & Bugfix-Leitfaden für Home Assistant

Dieses Dokument enthält eine strukturierte Analyse der kritischen Systemfehler deiner Home Assistant-Instanz (Version **2026.6.0**), aktualisiert basierend auf den Logs vom **22. Juni 2026**.

Die Fehler wurden nach Priorität und Ursache gruppiert.

---

## 🔥 Hohe Priorität (Fehler mit hoher Frequenz oder Systemabstürze)

### 1. Modbus-Verbindungsfehler (Sungrow Wechselrichter)
> [!WARNING]
> **Häufigkeit:** 13.956 Mal aufgetreten  
> **Fehlermeldung:** `Pymodbus: SungrowSHx: Error: device: 1 address: 5741 -> pymodbus returned isError True` (Betrifft Register 5741 bis 5745)

* **Ursache:** Die Modbus-Integration versucht Register (`5741-5745`) abzufragen, die vom Wechselrichter nicht unterstützt werden oder gesperrt sind.
* **Lösungsschritte:**
  1. Kontrolliere das Datenblatt deines Sungrow-Wechselrichtermodells bezüglich der Register `5741-5745`.
  2. Passe die Modbus-Konfigurationsdatei in Home Assistant an und entferne diese Register aus der Abfrageliste.

### 2. Code-Crash in EVCC Integration (`evcc_intg`)
> [!CAUTION]
> **Häufigkeit:** 20 Mal aufgetreten  
> **Fehlermeldung:** `KeyError: 'device_name_meter_aux'` in `custom_components/evcc_intg/__init__.py` auf Zeile 1058

* **Ursache:** In der Custom-Integration `evcc_intg` versucht die Methode `device_info_dict_for_meter`, den Namen für das Messgerät über `self.lang_map[device_name_meter]` zu übersetzen. Für Hilfszähler (`device_name_meter_aux`) existiert dieser Schlüssel jedoch nicht in der Übersetzungsdatei.
* **Lösungsschritte:**
  1. Öffne die Datei [`__init__.py`](file:///config/custom_components/evcc_intg/__init__.py) auf Zeile 1058.
  2. Ändere den Zugriff auf `self.lang_map` so ab, dass ein Fallback genutzt wird, falls der Schlüssel fehlt:
     ```python
     # Vorher:
     "name": f"{NAME_SHORT} - {self.lang_map[device_name_meter]} {addon} [{self._system_id}]",
     # Nachher:
     "name": f"{NAME_SHORT} - {self.lang_map.get(device_name_meter, device_name_meter)} {addon} [{self._system_id}]",
     ```

### 3. HACS Deaktivierung & Reload-Fehler
> [!CAUTION]
> **Häufigkeit:** 1 Mal aufgetreten (führt aber zum Ausfall aller HACS-Dienste)  
> **Fehlermeldung:** `HACS is disabled - invalid_token` gefolgt von `homeassistant.config_entries.OperationNotAllowed` beim Versuch des Reloads.

* **Ursache:** Der in HACS hinterlegte GitHub-Token ist ungültig oder abgelaufen. Ein Versuch, die Integration neu zu laden, scheiterte, da HACS-Entitäten (`switch` und `update`) sich im Zustand `FAILED_UNLOAD` befanden (Fehlermeldung: `ValueError: Config entry was never loaded!`).
* **Lösungsschritte:**
  1. Generiere einen neuen GitHub-Token für HACS.
  2. Starte Home Assistant neu, um den Blockierungszustand (`FAILED_UNLOAD`) aufzuheben.
  3. Führe die HACS-Reauthentifizierung in den Einstellungen durch.

---

## ☁️ Cloud & API-Authentifizierungsprobleme

### 4. Toshiba Klimaanlagen-Verbindung (`toshiba_ac`)
> [!IMPORTANT]
> **Häufigkeit:** 558 Mal aufgetreten (Warnungen) / 20 Mal (Fehler)  
> **Fehlermeldung:** `Non-200 response from Toshiba API (status=403...)` und `State reload failed`

* **Ursache:** Die API-Anfragen an die Toshiba-Cloud werden mit einem *403 Forbidden* abgewiesen. Das liegt in der Regel an abgelaufenen Sitzungstoken oder geänderten API-Bedingungen.
* **Lösungsschritte:**
  * Gehe in Home Assistant zu **Einstellungen -> Geräte & Dienste** und starte die Authentifizierung (Reauth) für deine Toshiba-Integration neu.

### 5. Google Assistant Setup-Fehler
> [!IMPORTANT]
> **Häufigkeit:** 1 Mal aufgetreten  
> **Fehlermeldung:** `KeyError: 'google_assistant'` beim Einrichten von `homewayio`

* **Ursache:** Die Integration bricht ab, weil der Konfigurationsschlüssel `google_assistant` in der `configuration.yaml` nicht gefunden wurde.
* **Lösungsschritte:**
  * Überprüfe deine `configuration.yaml` und stelle sicher, dass die Google Assistant Integration korrekt deklariert und formatiert ist.

---

## 📡 Netzwerk- & Geräte-Erreichbarkeit

### 6. LocalTuya Disconnects
> [!WARNING]
> **Häufigkeit:** 59 Mal aufgetreten  
> **Fehlermeldung:** `Disconnected - waiting for discovery broadcast` für mehrere Geräte

* **Ursache:** Lokale Tuya-Geräte verlieren die Verbindung und warten auf das Discovery-Signal.
* **Lösungsschritte:** WLAN-Abdeckung für die betroffenen Geräte prüfen und sicherstellen, dass die IP-Adressen statisch vergeben sind.

### 7. Apple TV Verbindungsabbrüche
> [!WARNING]
> **Häufigkeit:** 1 Mal aufgetreten  
> **Fehlermeldung:** `ProtocolError: Command FetchAttentionState failed` / `Failed to update app list`

* **Ursache:** Die Verbindung zur Apple TV Companion-Schnittstelle schlägt fehl, da das Gerät im Ruhezustand (Deep Sleep) ist oder die Verbindung abgebrochen wurde.
* **Lösungsschritte:** Apple TV Netzwerk- und Ruhezustandseinstellungen überprüfen.

### 8. iCloud3 Geräte-Tracker fehlt
> [!ERROR]
> **Häufigkeit:** 1 Mal aufgetreten  
> **Fehlermeldung:** `Mobile App Device Tracker Entity was not found in the HA Devices List`

* **Ursache:** iCloud3 versucht den Tracker `iphone_jessica` abzufragen, dieser existiert aber unter diesem Namen nicht mehr in Home Assistant.
* **Lösungsschritte:** Überprüfe in den Integrationen den Namen deines Mobile-App-Trackers und passe die iCloud3-Konfiguration entsprechend an.

---

## ⚠️ Veraltete & Fehlende Entitäten (Konfigurationsleichen)

### 9. Fehlende Lichter und Schalter in Automationen/Szenen
> [!WARNING]
> **Häufigkeit:** 85 Mal aufgetreten  
> **Fehlermeldung:** `Referenced entities [...] are missing or not currently available` und `Unable to find entity [...]`

* **Betroffene Entitäten:** 
  * `switch.waterheater_switch`
  * `light.ormanas_led_strip_licht_2`
  * `light.stoftmoln_ceiling_wall_lamp_ww24_licht_2`
  * `light.stoftmoln_ceiling_wall_lamp_ww24_licht_3`
  * `light.stoftmoln_ceiling_wall_lamp_ww37_licht`
  * `light.tradfri_bulb_gu10_ww_400lm_licht`
  * `light.tradfri_bulb_gu10_ww_400lm_licht_2`
  * `light.tradfri_bulb_gu10_ww_400lm_licht_3`
* **Ursache:** Automationen oder Szenen versuchen, Lichter/Schalter anzusteuern, die gelöscht, umbenannt oder nicht erreichbar sind.
* **Lösungsschritte:** Nutze den **Safe Refactoring Workflow** (siehe `home-assistant-best-practices` Skill), um alle veralteten Referenzen in `automations.yaml` und `scenes.yaml` zu finden und zu bereinigen.

---

## 💻 Core- & Integrations-Bugs (Warten auf Updates)

### 10. Tado Repairs Platform Crash
> [!ERROR]
> **Häufigkeit:** 1 Mal aufgetreten  
> **Fehlermeldung:** `homeassistant.exceptions.HomeAssistantError: Invalid repairs platform <module 'homeassistant.components.tado.repairs'...>`

* **Ursache:** Ein Bug in der integrierten `tado` Integration bei der Registrierung der Reparatur-Schnittstelle.
* **Lösungsschritte:** Hierbei handelt es sich um einen Fehler im Home Assistant Core. Keine manuelle Aktion möglich, ein Update auf eine neuere Core-Version behebt dieses Problem.

### 11. IPP Integration veraltet
> [!WARNING]
> **Häufigkeit:** 1 Mal aufgetreten  
> **Fehlermeldung:** `Detected that integration 'ipp' passes a non-string value of type list as sw_version... This will stop working in Home Assistant 2026.12.0`

* **Ursache:** Die integrierte IPP-Druckerintegration nutzt ein veraltetes Datenformat für die Software-Version.
* **Lösungsschritte:** Wird durch zukünftige HA Core-Updates automatisch behoben.

