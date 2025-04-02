# Plutus Project Template

Template repository of a Plutus Project.

This templte project sturcture also specifies how to store and structure the source code and report of a standard Plutus Project.

This `README.md` file serves as an example how a this will look like in a standard Plutus project. Below listed out the sample section.

## Abstract
- Summarize the project: motivation, methods, findings, etc. 

## Introduction
- Briefly introduce the project.
- Problem statement, research question or the hypothesis.
- Method(s) to solve the problem
- What are the results?

## Related Work (or Background)
- Prerequisite reading if the audience needs knowledge before exploring the project.
- Optional

## Trading (Algorithm) Hypotheses
- Describe the Trading Hypotheses
- Step 1 of the Nine-Step

## Data
- Data source
- Data type
- Data period
- How to get the input data?
- How to store the output data?
### Data collection
- Step 2 of the Nine-Step
### Data Processing
- Step 3 of the Nine-Step

## Implementation
- Briefly describe the implemetation.
    - How to set up the enviroment to run the source code and required steps to replicate the results
    - Discuss the concrete implementation if there are any essential details
    - How to run each step from `In-sample Backtesting`, Step 4 to `Out-of-sample Backtesting`, Step 6 (or `Paper Trading`, Step 7).
    - How to change the algorithm configurations for different run.
- Most important section and need the most details to correctly replicate the results.
### Environment Setup
1. Set up python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate # for Linux/MacOS
.\venv\Scripts\activate.bat # for Windows command line
.\venv\Scripts\Activate.ps1 # for Windows PowerShell
```
2. Install the required packages
```bash
pip install -r requirements.txt
```
3. Create `.env` file in the root directory of the project and fill in the required information. The `.env` file is used to store environment variables that are used in the project. The following is an example of a `.env` file:
```bash
# Example .env file
```env
DB_NAME=<database name>
DB_USER=<database user name>
DB_PASSWORD=<database password>
DB_HOST=<host name or IP address>
DB_PORT=<database port>
DATA_PATH=<path to the data folder of your choice, if not specified, the default is `data`>
```
The `DATA_PATH` variable is used to specify the path to the data folder where the input data is stored. The other variables are used to connect to the database (the project is tested on Algotrade internship database, these variables can be ignored if you are not using the database).

### Data Collection
1. Retrieve VCBF open-end fund financial portfolio 
```bash
python -m src.crawler.vcbf_crawler
```
The result will be stored in the `<DATA_PATH>/VCBF/fund_portfolios.csv` file. The data is stored with the following format:
```csv
Fund Code,Date,Category,Quantity,Market Price,Value,Total Asset Ratio
VCBF-BCF,2023-01-01,ACB,504488.0,26050.0,13141912400.0,0.0352110336932618
...
```
2. Retrieve daily price, quantity and financial data of Vietnamese stocks
If you have access to Algotrade internship database, you can use the following command to retrieve the data. 
```bash
python -m src.stocks_crawler --start_date 2022-01-01 --end_date 2025-01-31
```
The daily stock price results will be stored in the `<DATA_PATH>/daily_data.csv` file. The data is stored with the following format:
```csv
datetime,tickersymbol,price,quantity
2024-12-31,VIC,40.55,1784400
...
```

Stocks financial portfolio data will be stored in the `<DATA_PATH>/financial_data.csv` file. The data is stored with the following format:
```csv
Revenue,year,quarter,Cash,Liabilities,P/E,ROE,Financial Leverage,Debt/Equity,tickersymbol
9053845000000,2022,1,6281931000000,480433095000000,7.7889284027,0.236563115,10.966802399327864,9.9668023993,ACB
...
```

### Data processing
Now we preprocess the financial data and institutional data to prepare for backtesting step.
```bash
python -m src.preprocess
```
The result will be stored in the `<DATA_PATH>/monthly_scores.csv` file. The data is stored with the following format:
```csv
symbol,fund_net_buying,number_fund_holdings,net_fund_change,roe,debt_to_equity,revenue_growth,pe,month,year
ACB,0.18949771689497716,3.0,3.0,0.2649167736,9.401935188,15.362221323862574,6.1561819167,2,2023
...
```

### In-sample Backtesting
- To init parameters for the first run, access `config/config.yaml` file and adjust the `default_backtest_params`.
- For this project, we use data of the period from 2023-02-01 to 2024-01-31 as the in-sample period. 
```bash
python -m src.backtest --start_date 2023-02-01 --end_date 2024-01-31 --name in_sample
```
The result will be stored in the `<DATA_PATH>/backtest/in_sample` folder.

### Optimization
Run this command to start the optimization process. You can specify the number of trials to run using the `--trials` argument if needed. You can also adjust the random seed by editing `random_seed` in the `config/config.yaml` file. The default random seed is 42.
```bash
py -m src.optimize  
```
The result will be stored in the `<DATA_PATH>/optimization` folder.

## In-sample Backtesting
- Describe the In-sample Backtesting step
    - Parameters
    - Data
- Step 4 of the Nine-Step


### In-sample Backtesting Result
- Brieftly shown the result: table, image, etc.
- Has link to the In-sample Backtesting Report
- [Backtesting report file](/doc/report/backtesting/backtesting-report.pdf)

## Optimization
- Describe the Optimization step
    - Optimization process/methods/library
    - Parameters to optimize
    - Hyper-parameter of the optimize process
- Step 5 of the Nine-Step

### Optimization Result
- Brieftly shown the result: table, image, etc.
- Has link to the Optimization Report

## Out-of-sample Backtesting
- Describe the Out-of-sample Backtesting step
    - Parameter
    - Data
- Step 6 of th Nine-Step
### Out-of-sample Backtesting Result
- Brieftly shown the result: table, image, etc.
- Has link to the Out-of-sample Backtesting Report

## Paper Trading
- Describe the Paper Trading step
- Step 7 of the Nine-Step
- Optional
### Optimization Result
- Brieftly shown the result: table, image, etc.
- Has link to the Paper Trading Report


## Conclusion
- What is the conclusion?
- Optional

## Reference
- All the reference goes here.

## Other information
- Link to the Final Report (Paper) should be somewhere in the `README.md` file.
- Please make sure this file is relatively easy to follow.
