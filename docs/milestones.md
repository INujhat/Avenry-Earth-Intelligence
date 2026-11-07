# Delivery tracker

| Area | Actual status |
| --- | --- |
| Foundation | FastAPI, isolated Python environment, tests and documentation implemented. |
| Real data | Eight verified real scenes downloaded. Ghana/India train, Mekong validation, Nigeria held-out test. Original Spain demonstration retained privately. |
| ML | Small U-Net trained for 35 epochs; held-out pilot results recorded. Performance is weak and uneven; no broad generalization claim. |
| API | Scene catalog, bounded background jobs, persistent history, results, GeoTIFF and JSON downloads implemented and tested. |
| Website | Avenry Earth Intelligence React/TypeScript catalog, MapLibre map, layers, metrics, history and methodology. Production build and browser checks passed. |
| NASA HLS | Real CMR search passed. Mask/preparation tests pass. Protected download requires Earthdata authentication; optical-to-radar inference is disabled. |
| Persistence | SQLite and PostgreSQL/PostGIS migrations, spatial query and container persistence tested. |
| Delivery | GitHub branch and Codespaces launch configuration prepared. Codespaces provisioning needs the user's account; no permanently public hosted service. |
| Research | Official Prithvi configuration reviewed; no weights or comparison run. Broader evaluation and error analysis remain future work. |

Dataset STAC declares a proprietary license. Data, trained weights and screenshots
are not published in Git. A private Codespace fetches source data during setup.
