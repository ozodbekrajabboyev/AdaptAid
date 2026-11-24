# Results

Generated from research/outputs/*.json (run `make research` to regenerate).

## Simulation study (synthetic course)

Seeds: report [1, 2, 3, 4, 5, 6, 7, 8], 80 learners x 40 sessions.

### Paired differences in area under the learning curve

| comparison | format effect | difference | 95% CI |
|---|---|---|---|
| hybrid − static | none | 0.0365 | [0.0261, 0.0468] |
| hybrid − no_style | none | 0.0061 | [-0.0085, 0.0207] |
| hybrid − random | none | 0.0116 | [0.0008, 0.0223] |
| hybrid − static | small | 0.0318 | [0.0148, 0.0487] |
| hybrid − no_style | small | -0.0038 | [-0.02, 0.0124] |
| hybrid − random | small | 0.0052 | [-0.008, 0.0183] |
| hybrid − static | large | 0.037 | [0.0229, 0.0511] |
| hybrid − no_style | large | 0.0058 | [-0.0046, 0.0161] |
| hybrid − random | large | 0.0097 | [0.0007, 0.0188] |

### Policies (mean over reporting seeds)

| affinity level | policy | auc known | auc known sd | final known | steps to all |
|---|---|---|---|---|---|
| none | random | 0.2777 | 0.0131 | 0.4548 | 40.92 |
| none | static | 0.2528 | 0.0139 | 0.4106 | 40.94 |
| none | need_only | 0.2808 | 0.0124 | 0.4595 | 40.91 |
| none | style_only | 0.2827 | 0.0126 | 0.4656 | 40.95 |
| none | level_only | 0.2866 | 0.0127 | 0.47 | 40.84 |
| none | cf_only | 0.2801 | 0.0124 | 0.4606 | 40.91 |
| none | no_style | 0.2832 | 0.0117 | 0.4625 | 40.95 |
| none | hybrid | 0.2893 | 0.0129 | 0.4681 | 40.87 |
| small | random | 0.2825 | 0.0116 | 0.4666 | 40.82 |
| small | static | 0.2559 | 0.0173 | 0.4128 | 40.94 |
| small | need_only | 0.2789 | 0.0144 | 0.4547 | 40.82 |
| small | style_only | 0.2822 | 0.0136 | 0.465 | 40.97 |
| small | level_only | 0.2888 | 0.0118 | 0.48 | 40.89 |
| small | cf_only | 0.2851 | 0.0139 | 0.4709 | 40.84 |
| small | no_style | 0.2915 | 0.0115 | 0.4819 | 40.92 |
| small | hybrid | 0.2877 | 0.0156 | 0.473 | 40.88 |
| large | random | 0.2909 | 0.0099 | 0.4788 | 40.86 |
| large | static | 0.2636 | 0.0177 | 0.4348 | 40.9 |
| large | need_only | 0.2932 | 0.0192 | 0.4803 | 40.85 |
| large | style_only | 0.3027 | 0.0045 | 0.5042 | 40.8 |
| large | level_only | 0.2988 | 0.0123 | 0.4925 | 40.85 |
| large | cf_only | 0.2846 | 0.0107 | 0.4702 | 40.88 |
| large | no_style | 0.2949 | 0.0154 | 0.4867 | 40.86 |
| large | hybrid | 0.3006 | 0.012 | 0.4945 | 40.77 |

### Learning-preference recovery

| style case | start style cos | final style cos |
|---|---|---|
| noisy/with_update | 0.8546 | 0.826 |
| noisy/prior_only | 0.8695 | 0.8695 |
| none/with_update | -0.0096 | 0.1051 |
| none/prior_only | 0.0 | 0.0 |
| wrong/with_update | -0.9712 | -0.8683 |
| wrong/prior_only | -1.0 | -1.0 |

Weights: blueprint weights kept (rule: adopt if mean validation gain >= 0.005 AUC and no affinity level loses > 0.005); validation difference {'none': 0.0003, 'small': -0.0031, 'large': 0.0064}.

Checks: hybrid_ge_static_every_level = True, hybrid_gt_static_when_style_matters = True, learned_style_beats_no_questionnaire = True, learned_style_recovers_from_wrong_questionnaire = True, aids_beat_checks_alone = True

## Simulation study (real DSA course)

Seeds: report [1, 2, 3, 4, 5, 6, 7, 8], 80 learners x 40 sessions.

### Paired differences in area under the learning curve

| comparison | format effect | difference | 95% CI |
|---|---|---|---|
| hybrid − static | none | 0.0329 | [0.028, 0.0378] |
| hybrid − no_style | none | 0.0019 | [-0.0058, 0.0095] |
| hybrid − random | none | -0.0012 | [-0.0086, 0.0062] |
| hybrid − static | small | 0.0391 | [0.0302, 0.0481] |
| hybrid − no_style | small | 0.0086 | [-0.0027, 0.0199] |
| hybrid − random | small | 0.0032 | [-0.0085, 0.0148] |
| hybrid − static | large | 0.0469 | [0.0343, 0.0595] |
| hybrid − no_style | large | 0.0192 | [0.0086, 0.0298] |
| hybrid − random | large | 0.0081 | [-0.0016, 0.0177] |

### Policies (mean over reporting seeds)

| affinity level | policy | auc known | auc known sd | final known | steps to all |
|---|---|---|---|---|---|
| none | random | 0.2752 | 0.0111 | 0.447 | 41.0 |
| none | static | 0.2411 | 0.0137 | 0.373 | 41.0 |
| none | need_only | 0.2802 | 0.0126 | 0.4452 | 40.97 |
| none | style_only | 0.2723 | 0.0104 | 0.4486 | 40.99 |
| none | level_only | 0.273 | 0.0139 | 0.4357 | 41.0 |
| none | cf_only | 0.2732 | 0.0098 | 0.448 | 41.0 |
| none | no_style | 0.2722 | 0.015 | 0.4375 | 40.99 |
| none | hybrid | 0.274 | 0.0121 | 0.4389 | 40.97 |
| small | random | 0.2846 | 0.0129 | 0.4617 | 40.98 |
| small | static | 0.2486 | 0.0179 | 0.3899 | 40.99 |
| small | need_only | 0.2732 | 0.0123 | 0.4412 | 40.97 |
| small | style_only | 0.2924 | 0.0135 | 0.4797 | 40.97 |
| small | level_only | 0.277 | 0.0103 | 0.4413 | 40.97 |
| small | cf_only | 0.2749 | 0.0111 | 0.4493 | 40.99 |
| small | no_style | 0.2792 | 0.0093 | 0.4507 | 40.99 |
| small | hybrid | 0.2878 | 0.0147 | 0.4661 | 40.97 |
| large | random | 0.2945 | 0.0075 | 0.4874 | 40.96 |
| large | static | 0.2556 | 0.0124 | 0.4017 | 41.0 |
| large | need_only | 0.2777 | 0.0127 | 0.4514 | 40.97 |
| large | style_only | 0.3182 | 0.0197 | 0.5423 | 40.92 |
| large | level_only | 0.2816 | 0.0112 | 0.4607 | 40.96 |
| large | cf_only | 0.2832 | 0.0193 | 0.472 | 40.97 |
| large | no_style | 0.2834 | 0.0119 | 0.4662 | 40.99 |
| large | hybrid | 0.3026 | 0.0109 | 0.4867 | 40.89 |

### Learning-preference recovery

| style case | start style cos | final style cos |
|---|---|---|
| noisy/with_update | 0.8457 | 0.8266 |
| noisy/prior_only | 0.865 | 0.865 |
| none/with_update | 0.005 | 0.136 |
| none/prior_only | 0.0 | 0.0 |
| wrong/with_update | -0.9638 | -0.8592 |
| wrong/prior_only | -1.0 | -1.0 |

Weights: blueprint weights kept (rule: adopt if mean validation gain >= 0.005 AUC and no affinity level loses > 0.005); validation difference {'none': -0.0029, 'small': 0.0052, 'large': 0.0058}.

Checks: hybrid_ge_static_every_level = True, hybrid_gt_static_when_style_matters = True, learned_style_beats_no_questionnaire = True, learned_style_recovers_from_wrong_questionnaire = True, aids_beat_checks_alone = True

## Knowledge tracing on ASSISTments 2009

ASSISTments 2009 skill builder, 40 skills with the most students, 205546 answers. 5-fold cross-validation by student; parameters fitted on training folds only; one-step-ahead predictions. pyBKT is compared head to head on the largest skills (its EM is slow), with our BKT scored on exactly the same predictions.

| model | scope | auc | rmse | predictions |
|---|---|---|---|---|
| Global mean | 40 skills | 0.4901 | 0.4714 | 205546 |
| Per-skill mean | 40 skills | 0.604 | 0.4641 | 205546 |
| BKT, brute force (ours) | 40 skills | 0.7111 | 0.4381 | 205546 |
| BKT, brute force (ours) | 10 largest skills | 0.7001 | 0.4382 | 94350 |
| BKT, EM (pyBKT) | 10 largest skills | 0.7033 | 0.4376 | 94350 |

Median fitted parameters: {'prior': 0.7167, 'learn': 0.11, 'guess': 0.2192, 'slip': 0.1983}. Cleaning: {'raw_rows': 525534, 'after_original': 449220, 'final_rows': 251405}.

## At-risk classifier on OULAD

OULAD, features from the first 42 days only; trained on 2013 presentations (11620 students), tested on 2014 (15404 students). At-risk = Withdrawn or Fail (43% of the test set). Students who withdrew before day 42 are excluded.

| model | roc auc | pr auc | f1 | recall at risk |
|---|---|---|---|---|
| Logistic regression | 0.7284 | 0.7027 | 0.6365 | 0.7532 |
| Random forest | 0.7686 | 0.7478 | 0.6583 | 0.6852 |
| Gradient boosting | 0.766 | 0.7365 | 0.6609 | 0.6962 |

Top random-forest features: {'mean_score': 0.179, 'clicks_last2w': 0.1252, 'active_days': 0.0794, 'clicks_total': 0.0782, 'clicks_homepage': 0.0773, 'clicks_content': 0.0772, 'clicks_forum': 0.0765, 'n_missing': 0.0644}.

## Collaborative filtering on OULAD

OULAD CCC 2014J: 2084 students, 220 course materials. Per-student time split (first 80% of materials opened = training, last 20% = target); training items excluded from candidates. This validates the CF methods on implicit clicks; the app's CF learns from outcome gain instead.

| model | precision at 5 | recall at 5 | ndcg at 5 | hit rate at 5 | coverage |
|---|---|---|---|---|---|
| Random | 0.0697 | 0.0291 | 0.0709 | 0.2812 | 0.9955 |
| Most popular | 0.2143 | 0.1554 | 0.2414 | 0.6204 | 0.3773 |
| Item-kNN (ours) | 0.2584 | 0.1762 | 0.2965 | 0.7183 | 0.4318 |
| ALS (ours, implicit) | 0.2313 | 0.1461 | 0.2464 | 0.6847 | 0.7273 |
| LightFM hybrid (WARP + item type) | 0.2671 | 0.1701 | 0.286 | 0.7817 | 0.7 |

## Personas on OULAD

OULAD 2014 presentations, 15521 students with at least 50 clicks; K-Means on standardised click shares, active days and log clicks.

| k | silhouette | stability ari |
|---|---|---|
| 3 | 0.2114 | 0.9871 |
| 4 | 0.2183 | 0.9731 |
| 5 | 0.225 | 0.9795 |
| 6 | 0.2351 | 0.9871 |

| cluster | students | activity | leans on | active days z |
|---|---|---|---|---|
| 0 | 4484 | low | content | -0.65 |
| 1 | 3325 | high | content | 0.92 |
| 2 | 1665 | low | links | -0.45 |
| 3 | 116 | low | other | -0.37 |
| 4 | 3289 | medium | quiz | -0.38 |
| 5 | 2642 | high | forum | 0.72 |

