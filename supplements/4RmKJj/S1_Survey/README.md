# S1 · Practitioner survey and Table 5

Twelve dated Google Forms responses between 15 and 20 April 2025 form the denominator for item nonresponse. These are receipt dates. Recruitment took place approximately from mid-March to mid-April 2025. The quantitative display in dissertation Appendix I.2 is headed P1 through P11; the present calculations use the twelve records in the original form export. The appendix is not the input dataset. Individual records, timestamps, identifiers and verbatim responses are not distributed here.

## What is in the survey supplement?

**Response_distributions.pdf** is the short reading guide. **all_likert_counts.csv** gives the original-scale frequency at each score, missingness, n, median and quartile categories for every five-point item. Q7 (video clarity), Q8 (relevance) and Q13 (frequency of existing errors) are descriptive context. Q14–Q18 are the five outcomes in the manuscript. The extra context items are not additional significance tests. **testing_interest.csv** gives the categorical Q9 responses; other text is not released. **item_completion.csv** reports answered/missing for Q1–Q21; the optional contact field Q22 was excluded entirely.

From S1, run **python survey_audit.py --out reproduced** to check the aggregate tables against one another. A data holder can pass **--raw original-export.csv** to regenerate them from the fielded questions. No response-level data are needed by readers to verify the published item statistics. The public checks establish numerical consistency; only the data holder can verify the original records.

The included `SHA256SUMS` verifies the files as supplied (`sha256sum -c SHA256SUMS` from this directory).

## Reproduce Tables 5 and 6

Use CPython 3.13.5; the audit used NumPy 2.2.4 and SciPy 1.15.3. From this directory:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python table5.py --counts item_counts.csv --output reproduced.csv
diff -u table5_results.csv reproduced.csv
```

For controlled verification by the data holder, run `python table5.py --raw private-original.csv --output from_source.csv`. The script matches the five question labels, accepts integer values 1–5 and empty cells, ignores unfilled export padding based on timestamp, and emits aggregates only. The public frequency input and the private response-level calculation returned identical outputs at the displayed precision. The raw mode requires the original `Timestamp` and the five named columns; the remaining columns are never used. Do not send the private input with the paper.

`item_counts.csv` reports counts for each response value **in the original direction** plus the missing count. Each row sums to 12 including missing values. `questionnaire.csv` and `Questionnaire.md` contain all 22 field labels, including optional contact, but no answers. `table5_results.csv` gives numeric results to ten decimal places and a Bonferroni-adjusted p-value for each item. Public counts suffice for each univariate test, but do not identify pairs, correlations or participant-level missingness patterns.

## Calculation and interpretation

For Q14–Q17, transform each nonmissing response with `y = 6 − x`; Q18 uses `y = x`. For each item, `s` is the sample SD with divisor `n − 1`. Use `t = (mean(y) − 3) / (s/√n)` and the upper tail of Student's t distribution with `n − 1` degrees of freedom. Tests use unrounded data; the published table rounds last. The Q18 alternative is greater anticipated difficulty, not easier integration. Empty cells are excluded from that item only; there is no imputation or listwise deletion. Individual items are ordinal; these small-sample tests are exploratory. Q16 is the only unadjusted p below .01, equivalent to the only Bonferroni-adjusted p below .05 (adjusted p = .0216).

## Study and qualitative records

The instrument was reviewed by one questionnaire-design expert and two domain experts, then piloted with two additional respondents. These counts do not identify the analysts who coded the field responses. Candidates were selected from professional and academic networks and contacted by email and LinkedIn; the stated criterion was work with production ML or MLOps. One reminder to nonrespondents is described as re-invitation; its date is not documented here. Diverse or limited self-reported experience should be kept in mind. The author confirmed that 23 practitioners received invitations, as reported in §19.1 (p. 126) of the dissertation. The figure of 20 in §19.2 (p. 127) is incorrect. Twelve of 23 invitees responded (52.2%).

The 12 roles are summarized as research/data science (7), engineering (2), technical/product leadership (2), and consulting (1). Primary domains were automotive (4), semiconductors (2) and six other contexts (one each). Marginals are reported separately. Q10 (advantages), Q11 (concerns), Q19 (integration explanation), Q20 (further comments) and Q21 (improvements) had 11, 12, 7, 5 and 10 nonblank responses, respectively. These are field-completion counts, not thematic frequencies.

The documented coding procedure grouped text by demographic context; experience, practice and clarity; substantive feedback (advantages, limits, improvements, XAI); and comparison with current practice (challenges, relevance, time). Coded material was summarized by category. The author alone coded the written responses. There was no second coder and no assessment of inter-coder agreement. Response-level code assignments are not distributed. The questionnaire has no dedicated item measuring explanation quality. Source: [dissertation, §§19.1–19.3 and Appendix I](https://doi.org/10.25528/372). For a restricted audit, contact the corresponding author with the purpose and minimum fields needed; access depends on consent and data-protection constraints.

## Reviewer 1: ordinal reanalysis

The main inference is now the **two-sided exact sign test**. After applying the analysis direction, count scores below, at, and above 3. The test drops ties only for that item and evaluates equal probabilities for the two directions among responses other than 3. Report the effect as the above-midpoint share among the responses other than 3 with a pointwise 95% Clopper–Pearson interval. This conditional share is not the share among all respondents. Scores 2–4 were numbers without verbal labels. The CSV column names “neutral” and “nonneutral” denote scores equal to 3 and different from 3, respectively; they do not imply that respondents expressed neutrality or no effect. The median and quartile categories are the lowest observed score reaching the respective proportion of the observed cumulative count. Percentages in the figure exclude item nonresponses; counts are shown inside segments. Here the smallest nonzero segment exceeds 7%, so every nonzero count is visible. No participant linkage is used.

Run from S1:

    python ordinal.py --output reproduced_ordinal.csv
    diff -u ordinal_results.csv reproduced_ordinal.csv

For the vector figure, also install matplotlib 3.10.8, and add --plot reproduced_likert.pdf to the first command. The CSV was checked in both SciPy 1.15.3 and 1.17.0. The original one-sided t calculations above are preserved to audit the editor's requested Table 5. No a priori choice to use a one-sided decision rule was documented; they are not the primary analysis in this revision. For setup-time reduction, 8 of 9 responses other than 3 were above 3 (3 midpoint ties); exact two-sided p = .0391 and Bonferroni-adjusted p = .1953. None of the five exact tests meets the multiplicity threshold. A larger, controlled study is needed to evaluate actual changes. No a priori sample-size calculation was documented; the achieved sample reflects the usable responses from the 23 invitees.
