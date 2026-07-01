# RF / Wi-Fi Spatial Intelligence Repositories

This directory houses the cloned open-source repositories utilized for researching and implementing our integrated RF-based human tracking system.

## Cloned Repositories

1. **[indolocate](https://github.com/intentlab-iitk/indolocate)**
   * **Purpose**: Provides a comprehensive framework for CSI and RSSI-based positioning, incorporating filtering techniques such as Kalman and Particle Filters.
   * **Integration**: The trilateration solver and Kalman-smoothing principles implemented in `backend/services/rf_sensor.py` are based on the algorithms documented in this repository.

2. **[wlan_localization](https://github.com/sharan-naribole/wlan_localization)**
   * **Purpose**: A production-grade system for Wi-Fi fingerprint-based indoor positioning utilizing machine learning.
   * **Integration**: Informative for designing radio map / fingerprint-based database storage schemas and calibrating access point RSSI signals.

## System Integration Architecture

```
[WiFi Access Points]  --> (RSSI/CSI Disruptions) --> [RFSensorService]
                                                           |
                                                (Trilateration / Kalman)
                                                           |
                                                           v
[SOC Tactical Map]   <--   (WebSocket Broadcast) <-- [FastAPI Backend]
```
