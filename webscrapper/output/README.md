# webscrapper/output — README

Purpose
- Store generated artifacts produced by the webscraper (scraped pages, structured exports, logs, snapshots).
- This directory is a build/output folder — contents are generated, not source.

Typical contents
- JSON / NDJSON (.json, .ndjson)
- CSV (.csv)
- Raw HTML (.html)
- Logs (.log, .txt)
- Binary/export bundles (.zip, .tar, .parquet)
- Media assets (images/, screenshots/)

Guidelines
- Do not edit files here manually. Treat as ephemeral build output.
- Add this folder to .gitignore unless you intentionally want to commit a specific artifact.
    ```
    # Ignore scraper outputs
    /webscrapper/output/
    ```
- Keep output data size in check; large dumps should be archived externally.

Common tasks
- Regenerate outputs (example; adjust to your project entrypoint):
    ```
    python webscrapper/main.py --output ./webscrapper/output
    ```
- Inspect sample files:
    ```
    head -n 50 webscrapper/output/sample.json
    jq . webscrapper/output/sample.json             # for JSON
    csvcut -n webscrapper/output/sample.csv         # for CSV (csvkit)
    ```
- Disk usage:
    ```
    du -sh webscrapper/output
    ```
- Clean output directory:
    ```
    rm -rf webscrapper/output/*    # CAREFUL: irreversible
    ```

Reproducibility
- Record the scraper version, command-line args, and timestamp alongside outputs (e.g., save a metadata.json) to make results reproducible.

Troubleshooting
- If outputs are missing or empty: check scraper logs, network connectivity, rate-limiting, and selectors used for scraping.
- For corrupted binary/export files: verify the archiving step and re-run the export.

See also
- Project root README.md for how to run and configure the scraper.
- webscrapper/README or docs for scraping rules, selectors, and config.

Maintainer
- Refer to the project repository for owner/contact and contribution guidelines.