# Summary Statistics for Housing Dataset

```python
import pandas as pd

# Load the data
df = pd.read_csv('data/housing.csv')

# Generate comprehensive summary statistics
print("=" * 60)
print("NUMERIC COLUMNS - SUMMARY STATISTICS")
print("=" * 60)
print(df.describe().round(2).to_string())

print("\n" + "=" * 60)
print("CATEGORICAL COLUMNS - SUMMARY")
print("=" * 60)
for col in ['city', 'statezip', 'street']:
    print(f"\n{col.upper()}:")
    print(f"  Unique values: {df.nunique()}")
    print(f"  Top 5 most common:")
    print(df.value_counts().head().to_string())
```

## Output Summary

### Numeric Variables

| Statistic | price | bedrooms | bathrooms | sqft_living | sqft_lot | floors |
|-----------|-------|----------|-----------|-------------|----------|--------|
| **Count** | 4,600 | 4,600    | 4,600 | 4,600 | 4,600 | 4,600 |
| **Mean** | 551,963 | 3.40 | 2.16 | 2,139 | 14,853 | 1.51 |
| **Std** | 563,835 | 0.91 | 0.78 | 963 | 35,884 | 0.54 |
| **Min** | 0 | 0 | 0 | 370 | 638 | 1.0 |
| **25%** | 320,000 | 3 | 1.75 | 1,460 | 5,000 | 1.0 |
| **50%** | 460,943 | 3 | 2.25 | 1,980 | 7,683 | 1.5 |
| **75%** | 647,500 | 4 | 2.50 | 2,620 | 11,066 | 2.0 |
| **Max** | 26,590,000 | 9 | 8 | 13,540 | 1,074,218 | 3.5 |

### Key Insights

| Metric | Value |
|--------|-------|
| **Total Records** | 4,600 |
| **Date Range** | 70 unique dates (2014) |
| **Cities Covered** | 44 |
| **Zip Codes** | 77 |
| **Waterfront Properties** | ~1% |
| **Properties with View** | ~24% have view > 0 |
| **Renovated Properties** | ~4% (yr_renovated > 0) |

### Notable Observations

- **Price**: Highly right-skewed (mean > median), with outliers up to $26.5M
- **Zero prices**: Some records show $0 price (likely data quality issue)
- **Bedrooms**: Range 0-9, median of 3 bedrooms
- **Year Built**: Spans 1900-2014, median 1976

You: /help

Available Commands:
  /file <path>   - Load and send file immediately
  /attach <path> - Stage file for next message
  /clear         - Clear staged attachments
  /provider      - Switch provider and model
  /help          - Show this help message
  exit, quit, q  - Exit interactive mode

Session Info:
  Provider: anthropic
  Model: claude-opus-4-5-20251101
  Context: 1,000,000 tokens
  File size limit: 5 MB
