# incidents-brasaland.csv

Source file for the read-only incident API. The copy in this folder is the Company Incident File Analyzer dataset `incidents-brasaland.csv`, copied unchanged from the sibling project folder `Monorepo-Centralized Incident File Analyzer/`.

SHA-256: `63dea89c3cc133a66d4a42c2acc674820efcbca6b5d2bbe006a884d75742c849`

100 data rows plus a header. Columns, in order: `incident_id`, `date`, `location_id`, `category`, `description`, `status`, `customer_id`, `satisfaction_score`, `reporter_id`.

`incident_id` values are strings of the form `BRS-######`. `customer_id` and `reporter_id` are opaque identifiers. `uv run seed` from `services/api` loads this file into the TinyDB `incidents` table. Blank cells are stored as null. Rows are not removed.
