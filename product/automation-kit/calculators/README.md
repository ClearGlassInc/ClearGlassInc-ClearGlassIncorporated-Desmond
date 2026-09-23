# Automation Value Calculator

The calculator uses user-entered assumptions to estimate:

- annual hours saved;
- annual labor value;
- net annual value after stated automation cost; and
- simple payback months when monthly net value is positive.

## Assumptions

- `hours_per_run`: manual hours per workflow run
- `runs_per_week`: average weekly frequency
- `automation_fraction`: estimated fraction of the manual effort affected, from 0 to 1
- `hourly_cost`: user-entered planning cost per hour
- `annual_automation_cost`: user-entered annual automation cost
- `initial_cost`: user-entered initial cost

The formulas are intentionally transparent and are not a forecast model.

> Outputs are estimates based on user-entered assumptions. They are planning aids only and do not guarantee savings, financial results, return on investment, operational performance, or business outcomes.
