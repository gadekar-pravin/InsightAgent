# Business Metrics Definitions

This document defines the key business metrics used across TechCorp's analytics and reporting.

## Revenue Metrics

### Monthly Recurring Revenue (MRR)
- **Definition**: The predictable revenue that a company expects to receive every month from active subscriptions.
- **Calculation**: Sum of all active subscription values normalized to monthly amounts.
- **Target**: $4.5M MRR by end of Q4 2024.

### Annual Recurring Revenue (ARR)
- **Definition**: MRR multiplied by 12, representing annualized subscription revenue.
- **Calculation**: MRR × 12

## Customer Metrics

### Churn Rate
- **Definition**: The percentage of customers who cancel or don't renew their subscription within a given period.
- **Measurement Window**: 90-day rolling window
- **Calculation**: (Customers Lost in Period / Customers at Start of Period) × 100
- **Company Target**: 3.5% quarterly churn rate
- **Industry Benchmark**: 5.1% (SaaS industry average)
- **Alert Threshold**: Any region exceeding 4.5% triggers investigation

### Customer Lifetime Value (LTV)
- **Definition**: The total revenue a company can expect from a single customer account over the entire relationship.
- **Calculation**: (Average Revenue per Customer × Gross Margin %) / Churn Rate
- **Benchmarks by Segment**:
  - Enterprise: $45,000 - $120,000
  - SMB: $8,000 - $25,000
  - Consumer: $500 - $2,000

### Customer Acquisition Cost (CAC)
- **Definition**: The total cost of acquiring a new customer, including marketing and sales expenses.
- **Calculation**: Total Sales & Marketing Spend / Number of New Customers Acquired
- **Target LTV:CAC Ratio**: 3:1 or higher

## Performance Indicators

### Revenue Target Variance
- **Definition**: The percentage difference between actual revenue and target revenue.
- **Calculation**: ((Actual Revenue - Target Revenue) / Target Revenue) × 100
- **Underperformance Threshold**: Greater than 10% negative variance triggers executive review
- **Significant Underperformance**: Greater than 20% negative variance triggers immediate action plan

### Year-over-Year (YoY) Growth
- **Definition**: Percentage change in revenue compared to the same period in the previous year.
- **Calculation**: ((Current Period Revenue - Prior Year Period Revenue) / Prior Year Period Revenue) × 100
- **Company Target**: 25% YoY growth

### Quarter-over-Quarter (QoQ) Change
- **Definition**: Percentage change in a metric compared to the previous quarter.
- **Calculation**: ((Current Quarter Value - Previous Quarter Value) / Previous Quarter Value) × 100
