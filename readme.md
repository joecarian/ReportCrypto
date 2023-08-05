# REPORTER CRYPTO
The reporter crypto module is a cryptocurrency reporting system. Its purpose is to retrieve information about cryptocurrencies, from [CoinMarketCap](https://coinmarketcap.com/) platform such as:

1. The cryptocurrency with the highest volume (in $) in the last 24 hours.
2. The best and worst cryptocurrencies (by percentage increase over the past 24 hours).
3. The amount of money needed to buy one unit of each of the top cryptocurrencies.
4. The amount of money needed to buy one unit of all cryptocurrencies whose volume in the last 24 hours is more than set threshold.
5. The percentage gain or loss you would have made if you had bought one unit of each of the top 20 cryptocurrencies the day before (assuming the rankings did not change).
6. Cryptocurrencies classified by circulating supply.
7. Cryptocurrencies classified by market cap.
8. Cryptocurrencies ranked by chronological order of addition to CoinMarketCap platform.

The module runs on a regular schedule, at the time specified in the configuration file, and writes the information retrieved to a json file. In addition to the information shown above it also writes the date on which that information was retrieved.
The json file is saved at the path report/report.json.

At the path /res/conf.yaml is the configuration file. Below is the explanation of the fields:
1. API-URL: the endpoint to make the request to the CoinMarketCap platform.
2. API-KEY: the api key to make the request to the CoinMarketCap platform.
3. API-PARAMS: the params to the pass to the http request.
4. MAX-THRESHOLD-VOLUME: it indicates the maximum threshold of cryptocurrency volume, above which they are considered.
5. RANKING_CRYPTO: the number of cryptocurrencies to be classified, for the information where a ranking is required.
6. NUM_CRYPTO: the number of cryptocurrencies to be purchased in the simulation of investment.
7. TIME: the time when run the module. It can have the following formats:   %H:%M or :%M. Where %h indicates hours and %M indicates minutes.
8. REPEAT_INTERVAL: the way to run the module, daily, weekly or every minutes.

---
## EXAMPLE CONFIGURATION FILE
---
The following example shows how to set the configuration file to run every day at the 10:30 AM.

    MAX-THRESHOLD-VOLUME: !!int 76000000

    RANKING_CRYPTO: !!int 10

    NUM_CRYPTO: !!int 20

    TIME: !!str "10:30"

    REPEAT_INTERVAL: !!str "daily"
---
## RUN
---
To run the module, just run `python reporter_crypto.py` 
in the directory where the module is located. 