# hk-alerts

An [AlreadyOpen](https://github.com/AlreadyOpen) pipeline: Hong Kong alert feeds that a web page cannot read directly (their
servers send no CORS header), republished every 15 minutes to the Hugging Face bucket `alreadyopen/hk-alerts` for WorldViews.
The feeds that a page *can* read (TD Special Traffic News, HKO warnings, HA A&E waiting times) are read by WorldViews itself.

| File on the bucket | From | Contents |
|---|---|---|
| `live/aqhi.json` | EPD AQHI RSS (`aqhi.gov.hk`), station positions from the CSDI layer "Air Quality Monitoring Network of Hong Kong" | GeoJSON: one point per station with AQHI, health risk, general or roadside, time |
| `live/press.json` | Government press releases RSS (`info.gov.hk`) | the newest 100: title, link, time (no body text) |

| File | Does |
|---|---|
| `live.py` | Fetches both, writes both; one failing source keeps its last file. `python3 live.py test` writes `./data/` and uploads nothing |
| `live.yml` | Every 15 minutes, dispatched by `AlreadyOpen/heartbeat`; its cron is the backup |

No history is kept yet (each run overwrites). Data: Government of the HKSAR (DATA.GOV.HK and CSDI terms, free reuse with
attribution). Code: Apache-2.0.
