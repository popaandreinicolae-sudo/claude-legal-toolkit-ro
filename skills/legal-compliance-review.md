---
name: legal-compliance-review
description: Use when an AI application, workflow, or sandbox execution must be reviewed for legal compliance by testing hypotheses, runtime evidence, reasoning traceability, and framework-specific obligations.
---

# Legal Compliance Review

Use this skill for end-to-end legal review of an AI application.

## Review Steps

1. Identify applicable frameworks.
2. Form sandbox hypotheses for each framework.
3. Check whether the application exposes runtime evidence for each hypothesis.
4. Verify that legal reasoning is source-anchored.
5. Return one of: `compliant`, `review required`, `non-compliant`.

## Framework Prompts

- `AI_ACT`: prohibited practices, high-risk duties, transparency, robustness.
- `GDPR`: legal basis, special data, privacy by design, DPIA.
- `NIS2`: security measures, incident response, reporting timelines.
- `DORA`: ICT resilience, testing, third-party oversight.
- `DSA`: content governance, transparency, systemic risk.

## Blocking Conditions

- Missing source for a decisive legal claim
- No runtime evidence for a claimed control
- Automatic verdict on a high-risk scenario without human review
