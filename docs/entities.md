# Entities

Entities are added to each Niimbot printer device. Availability depends on the printer model, firmware capabilities, and the selected integration options.

| Entity type | Entities | Availability / notes |
|---|---|---|
| Sensors | Battery, Label Type, Print Density, Print Speed | Printer information; some printers may not report every value |
| Sensors | Print Progress, Print Duration, Last Error, Last Failure, Error Count | Print status and diagnostics; Last Failure includes BLE stage timings and radio details |
| Sensors | Protocol Version, Colour Support, Print Area | Diagnostic entities; disabled by default |
| Sensors | Labels Remaining / Used / Total, Consumable Usage, Label SKU / Type / UUID | Added for printers with label RFID support; UUID is disabled by default |
| Sensors | Ribbon Remaining / Used / Total, Ribbon Usage, Ribbon SKU / Type / UUID | Added for printers with ribbon RFID support; UUID is disabled by default |
| Sensors | Printhead Temperature, Wi-Fi RSSI, Voltage State, Lighting Error | Added when the printer reports these Advanced2 heartbeat values; some are disabled by default |
| Sensor | Cloud Label Info | Added when **Fetch Label Info Online** is enabled; reports lookup status and label details |
| Binary sensors | Connection, Cover, Paper, RFID, Ribbon, Ribbon RFID | Connection is always available; other state sensors appear when reported by the printer |
| Select | Auto Shutdown | Read and change the printer's automatic shutdown interval |
| Switch | Connection Sound | Enable or disable the Bluetooth connection beep |
| Image | Last Label Made | Updated with the rendered image after each print or preview |
| Buttons | Printer Settings Reset, Print Test Page | Diagnostic/configuration actions; reset and test page are disabled by default and model-dependent |
| Buttons | Calibrate Label Position, Calibrate Roll Feed | Model-dependent maintenance actions; label-position calibration is disabled by default |

Some devices expose only a subset of sensors and buttons. Unsupported actions are omitted or return a clear unsupported-command error.
