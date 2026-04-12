
# Data Dictionary 
This document outlines the structure and characteristics of the synthetic accounting data generated for testing and development purposes. The dataset includes various fields relevant to accounting processes, such as transaction details, vendor information, payment statuses, asset categories, and depreciation methods.

- 30 realistic vendor names across industries
- Invoice/PO numbers with unique prefixes
- 5 payment statuses: Paid, Pending, Overdue, Partial, Scheduled
- 5 asset categories: IT, Vehicles, Furniture, Equipment, Building improvements
- 5 depreciation methods: Straight-Line, DDB, SYD, Units of Production, MACRS
- Useful life: 3–20 years
- Salvage values: 5–20% of cost basis

## Asset Categories

| Category               | prefix  | Description                                       |
|------------------------|---------|---------------------------------------------------|
| IT                     | IT      | Computers, software, and related technology       |
| Vehicles               | VH      | Company cars, trucks, and other transportation    |
| Furniture              | FF      | Desks, chairs, and office furnishings             |
| Equipment              | EQ      | Machinery, tools, and other operational equipment |
| Building improvements  | BL      | Renovations and enhancements to company buildings |

## Depreciation Methods

| Method              | Description                                      |
|---------------------|--------------------------------------------------|
| Straight-Line       | Equal depreciation expense each year             |
| DDB                 | Higher depreciation in early years               |
| SYD                 | Depreciation based on sum of years' digits       |
| Units of Production | Depreciation based on usage or output            |
| MACRS               | Modified Accelerated Cost Recovery System        |


