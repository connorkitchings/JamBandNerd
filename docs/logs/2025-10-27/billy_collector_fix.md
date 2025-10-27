We are now ending our development session for today. Please generate the dev log using the standard template structure.

-   **Task Completed**: Debugged and improved the Billy Strings data collection pipeline, addressing performance bottlenecks and a critical bug in setlist processing.
-   **Key Outcomes**:
    *   Increased the request timeout for the Billy Strings collector to 120 seconds to mitigate frequent timeout errors.
    *   Parallelized the show page fetching in `BillyCollector.collect_shows`, significantly improving the speed of data collection for shows.
    *   Resolved a `ModuleNotFoundError` by adding explicit `sys.path` manipulation to `scripts/run_billy_collection.py`.
    *   Identified and fixed a bug in `scripts/run_billy_collection.py` where the `_normalize_setlists` function was not being called, leading to all setlist data being discarded.
    *   Updated `BillyCollector._scrape_show_setlist` with new CSS selectors to correctly parse setlist data from the updated `bmfsdb.com` HTML structure.
    *   Added a `--skip-setlists` flag to `scripts/run_billy_collection.py` to allow for staged verification of songs/shows collection before setlists.
-   **Blockers Encountered**:
    *   Persistent `ModuleNotFoundError` due to environment setup issues, resolved by explicit `sys.path` manipulation.
    *   Inability to use `web_fetch` to retrieve raw HTML from `bmfsdb.com`, necessitating a temporary script to inspect the website's structure.
    *   Changes in `bmfsdb.com`'s HTML structure for setlist pages required re-evaluation and update of scraping strategy.
-   **Session Handoff & Next Steps**:
    *   The `_scrape_show_setlist` method has been updated, and a `--skip-setlists` flag has been added. The next step is to verify the songs and shows collection using the new flag, and then verify the setlist collection.
    *   Clean up the temporary `debug_fetch_html.py` script.
-   **Updated Documents**:
    *   `src/jambandnerd/data_collection/config.py`
    *   `src/jambandnerd/data_collection/billy/collector.py`
    *   `scripts/run_billy_collection.py`
    *   `debug_fetch_html.py` (created, to be deleted)

The file path for this log will be `docs/logs/2025-10-27/billy_collector_fix.md`.

I will now clean up the temporary `debug_fetch_html.py` script.