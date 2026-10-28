# Data

Source: CMS *Medicare Part D Opioid Prescriber Summary File*, 2013–2016 (public data, ~75 MB per year).
Downloaded from Kaggle (search "Medicare Part D Opioid Prescriber Summary File").

Place these four files in this folder:

- medicare-part-d-opioid-prescriber-summary-file-2013.csv
- medicare-part-d-opioid-prescriber-summary-file-2014.csv
- medicare-part-d-opioid-prescriber-summary-file-2015.csv
- medicare-part-d-opioid-prescriber-summary-file-2016.csv

The CSVs are not committed to GitHub because they are too large (GitHub's file limit is 100 MB, and the set is ~310 MB).

One row = one prescriber in one year. Columns used: NPI, state, ZIP code, specialty, total claim count,
opioid claim count, opioid prescribing rate. Opioid counts from 1 to 10 are suppressed by CMS for privacy.
