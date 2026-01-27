# Financial Analyst Skill Suite

A Capability Pack for financial data analysis workflows.

## Contents

- **Capabilities:**
  - `io.pdf.extract_table` - Extract financial tables from PDF documents
  - `math.pandas.calculate` - Calculate financial metrics using Pandas

- **Workflows:**
  - `financial_report` - Complete workflow for extracting, analyzing, and reporting financial data

## Risk Profile

- **Max Risk:** HIGH
- **Requires Human Approval:** Yes
- **Justification:** Financial data processing requires high accuracy and may involve sensitive information.

## Registration

This pack must be registered through a governance proposal:

1. Create a `PACK_CREATE` proposal with this pack spec
2. Get admin approval
3. Pack will transition to `ACTIVE` state upon approval

## Usage

Once the pack is `ACTIVE`, workflows can reference it via metadata:

```yaml
metadata:
  pack_name: financial-analyst
  pack_version: 1.0.0
```

If the pack is `FROZEN`, all workflow executions will be rejected by the Runtime.
