"""The reporter crypto module is a cryptocurrency reporting system. Its purpose is to retrieve information about cryptocurrencies such as, 
    the best or worst by percentage increase in the last 24 hours, the percentage gain or loss on a hypothetical investment. 
    The information is retrieved from the CoinMarketCap platform.
"""
import json
import os
import time
import datetime
import sys
from abc import ABC, abstractmethod
from pathlib import Path
import requests
import yaml
import schedule


def singleton(class_):
    """Decorator function for singleton design pattern.

    Args:
        class_: Class on which want to become a singleton.

    Returns:
        Return a unique instance of class every time constructor class is called.
    """
    instances = {}

    def get_instance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return get_instance


class Observer(ABC):
    """
    The Observer interface declares the notify method, used by subjects.
    """
    @abstractmethod
    def notify(self, message) -> None:
        """Receive update from subject.
        """


@singleton
class LoadConfiguration:
    """Class to load configuration options from yaml file.

    This class is a Singleton class that load configuration from yaml file
    contained in the same directory of module.
    It makes available in all module the configuration parameters.
    Attributes:
        self._NAME_OF_FILE (str): The name of the YAML file to load configuration options from.
    """

    _NAME_OF_FILE = Path("res/conf.yaml")

    def __init__(self):
        """Constructor of singleton LoadConfiguration class.

        Load configuration from yaml configuration file contained in res directory.
        """
        self._path_file = Path(__file__).resolve(
        ).parent.parent / self._NAME_OF_FILE
        try:
            with open(self._path_file, encoding='utf-8',
                      mode='r') as configuration_file:
                self._config = yaml.safe_load(configuration_file)
        except FileNotFoundError as ex:
            print(
                ex,
                f"Impossible to find conf.json in provided path {self._NAME_OF_FILE}!!!\n"
                f"Please insert the file into the correct path and run the application again."
            )
            sys.exit(1)
        except PermissionError as exc:
            print(
                exc,
                "Permission denied, please give permission to app and run it again"
            )
            sys.exit(1)

    @property
    def get_api_url(self):
        """URL to make the get request.
        """
        return self._config.get("API-URL")

    @property
    def get_api_key(self):
        """API key for make the request.
        """
        return self._config.get("API-KEY")

    @property
    def get_api_params(self):
        """The parameters to pass to the request.

        Returns:
            dict : the parameters to pass to the request.
        """
        params = {}
        for param in self._config.get("API-PARAMS"):
            params.update(param)
        return params

    @property
    def get_max_threshold(self):
        """The property representing the maximum threshold for cryptocurrency volume 
            over the past 24 hours to buy a unit of all cryptocurrencies greater than the threshold.

        Returns:
            int : the maximum threshold.
        """
        return self._config.get('MAX-THRESHOLD-VOLUME', 76000000)

    @property
    def get_ranking_crypto(self):
        """The property representing the number of cryptos to be ranked.

        Returns:
            int : the number of cryptos to be ranked.
        """
        return self._config.get('RANKING_CRYPTO', 10)

    @property
    def get_num_crypto(self):
        """The property representing the number of the cryptos to be

        Returns:
            int: number of the cryptos.
        """
        return self._config.get('NUM_CRYPTO', 20)

    @property
    def get_time(self):
        """Property representing time to make the report.

        Returns:
            str : time to make the report.
        """
        return self._config.get('TIME', '16:30')

    @property
    def get_repeat_interval(self):
        """Property representing how to run the module, whether daily or weekly. 

        Returns:
            str: the way of execution of module.
        """
        return self._config.get('REPEAT_INTERVAL', 'day')


class Subject(ABC):
    """ The Subject interface declares a set of methods for managing subscribers.

        Attributes:
            self._observers: set, set of observers subscribed to the subject

    """
    @abstractmethod
    def notify(self, message):
        """Notify all observers about an event
        """

    @abstractmethod
    def subscribe(self, observer):
        """Subscribe an observer to the subject

        Args:
            observer: an observer to be subscribe
        """

    @abstractmethod
    def unsubscribe(self, observer):
        """Unsubscribe an observer to the subject

        Args:
            observer: an observer to be unsubscribe
        """


class CoinMarketCapApi(Subject):
    """The class make the request to the endpoint specified in the yaml file. 
        If the request gets a successful response then it alerts the observers.

    Args:
        self._observers: set of observers for Observer design pattern.
        self._api_url: url for make the request.
        self._api_key: the key of api.
        self._headers: the header of the request.
        self._params: the params to pass to the request.
    """

    def __init__(self) -> None:
        self._observers: "set[Observer]" = set()
        self._api_url = LoadConfiguration().get_api_url
        self._api_key = LoadConfiguration().get_api_key
        self._headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self._api_key
        }
        self._params = LoadConfiguration().get_api_params

    def get_crypt_info(self):
        """Get request to CoinMarketCap.
        """
        try:
            response = requests.get(
                url=self._api_url, headers=self._headers, params=self._params, timeout=10).json()
            if response['status']['error_code'] == 0:
                self.notify(response['data'])
            else:
                print(
                    f"{response['status']['error_code']: {response['status']['error_message']}}")
        except requests.exceptions.HTTPError as errh:
            print("HTTP Error")
        except requests.exceptions.ReadTimeout as errrt:
            print("Time out")
        except requests.exceptions.ConnectionError as conerr:
            print("Connection error")
        except requests.exceptions.RequestException as errex:
            print("Exception request")

    def subscribe(self, observer):
        self._observers.add(observer)

    def unsubscribe(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, message):
        for observer in self._observers:
            observer.notify(message)


class CryptoInfoDetector(Observer):
    """This class processes the information received from the response to the http request. 
        It deals with retrieving the following information:
            1. The cryptocurrency with the highest volume (in $) in the last 24 hours.
            2. The best and worst cryptocurrencies (by percentage increase over the past 24 hours).
            3. The amount of money needed to buy one unit of each of the top cryptocurrencies.
            4. The amount of money needed to buy one unit of all cryptocurrencies whose volume in the last 24 hours is more than set threshold.
            5. The percentage gain or loss you would have made if you had bought one unit of each of the top 20 cryptocurrencies the day before (assuming the rankings did not change).
            6. Cryptocurrencies classified by circulating supply.
            7. Cryptocurrencies classified by market cap.
            8. Cryptocurrencies ranked by chronological order of addition to CoinMarketCap platform.
    Args:
        self._converter: the currency of the crypto information.
        self._api_response: the data of response of http request.
        self._max_threshold: the maximum threshold.
        self._ranking_crypto: the number of cryptos to be ranked.
        self._logger: instance of Logger class.
    """

    def __init__(self) -> None:
        self._converter = LoadConfiguration().get_api_params.get('convert')
        self._api_responses = {}
        self._max_threshold = LoadConfiguration().get_max_threshold
        self._ranking_crypto = LoadConfiguration().get_ranking_crypto
        self._num_crypto = LoadConfiguration().get_num_crypto
        self._logger = ReportWriter()

    def notify(self, message) -> None:
        self._api_responses = message
        percent_change = "7d"
        crypto_info = [
            ("max_volume_24h:", self.get_max_volume_24h()),
            (f"top_{self._ranking_crypto}_percentage_change_24h",
             self.get_info_about_percent_change(reverse=True)),
            (f"last_{self._ranking_crypto}_percentage_change_24h",
             self.get_info_about_percent_change(reverse=False)),
            (f"top_{self._ranking_crypto}_percentage_change_{percent_change}",
             self.get_info_about_percent_change(reverse=True, time_percentage=percent_change)),
            ("price_first_20", self.get_amount_money()),
            ("price_first_30", self.get_amount_money(num_crypto=30)),
            (f"price_volume_greater_than_{self._max_threshold}_24h",
             self.get_amount_money_threshold_last_24h()),
            ("earn_percent", self.get_info_investment()),
            ("circulating_supply_ranking", self.get_circulating_supply_ranking()),
            ("market_cap_ranking", self.get_market_capitalization()),
            ("date_added_ranking", self.get_date_added_ranking())
        ]
        self._logger.write_report(dict(crypto_info))

    def get_max_volume_24h(self):
        """Gets the cryptocurrency with the highest volume (in $) in the last 24 hours

        Returns:
            str: The cryptocurrency with the highest volume (in $) in the last 24 hours
        """
        max_volume = 0
        index_max_volume = 0
        for index, mex in enumerate(self._api_responses):
            volume = mex.get('quote').get(self._converter).get('volume_24h')

            if volume > max_volume:
                max_volume = volume
                index_max_volume = index

        return f"{self._api_responses[index_max_volume].get('name')} {max_volume}$"

    def get_amount_money(self, num_crypto: int = 0):
        """Gets the amount of money needed to purchase one unit of each of the top of the specified number of cryptocurrencies.

        Args:
            num_crypyto (int): number of cryptos to be considered

        Returns:
            float: the amount of money needed to buy one unit of each of the top of the specified number of cryptocurrencies.
        """
        if num_crypto == 0:
            num_crypto = self._num_crypto
        prices = [
            response.get('quote').get(self._converter).get('price')
            for response in self._api_responses[:num_crypto]
        ]
        amount_total = sum(prices)
        return amount_total

    def get_info_about_percent_change(self, reverse: bool = False, time_percentage: str = '24h'):
        """Gets cryptocurrencies ranked by percentage change.

        Args:
            reverse (bool, optional): Indicates whether to run a ranking of best or worst. Defaults to False.
            percentage (str, optional): Indicates the time interval to estimate the percentage change. Defaults to 'percent_change_24h'.

        Returns:
            list: gets cryptocurrencies ranked by percentage change.
        """
        percents = (
            (f"{api_response.get('name')} {api_response.get('symbol')}: {api_response.get('quote').get(self._converter).get(f'percent_change_{time_percentage}')}")
            for api_response in self._api_responses
        )
        percents = sorted(percents, key=lambda perc: perc[1], reverse=reverse)
        return percents[:self._ranking_crypto]

    def get_amount_money_threshold_last_24h(self):
        """Gets the amount of money needed to buy one unit of all cryptocurrencies whose volume in the last 24 hours is more than $76,000,000.

        Returns:
            float: the amount of money needed to buy one unit of all cryptocurrencies whose volume in the last 24 hours is more than $76,000,000.
        """
        amount = sum(
            response.get('quote').get(self._converter).get('price')
            for response in self._api_responses
            if response.get('quote').get(self._converter).get('volume_24h') > self._max_threshold
        )
        return amount

    def get_info_investment(self):
        """Gets the percentage gain or loss you would have made if you had bought one unit of each of the top 20 cryptocurrencies the day before (assuming the rankings did not change).

        Returns:
            float: the earn percent.
        """
        prices = []
        purchase_prices = []
        for response in self._api_responses[:self._num_crypto]:
            price = response.get('quote').get(self._converter).get('price')
            increment = response.get('quote').get(
                self._converter).get('percent_change_24h')
            purchase_price = price - (price * (increment / 100))
            prices.append(price)
            purchase_prices.append(purchase_price)

        total_purchase = sum(purchase_prices)
        earn = (sum(prices) - total_purchase) / total_purchase
        earn_percent = earn * 100
        return earn_percent

    def get_circulating_supply_ranking(self, order=False):
        """Gets cryptocurrencies classified by circulating supply.

        Args:
            order (bool, optional): Indicates whether to run a ranking of best or worst. 
                                        If it is False then the method gets the worst, otherwise gets the best. Defaults to False.

        Returns:
            list: the cryptocurrencies classified by circulating supply.
        """
        circulating_supplys = (
            (f"{response.get('name')} {response.get('symbol')}: {response.get('circulating_supply')}")
            for response in self._api_responses
        )
        circulating_supplys = sorted(
            circulating_supplys, key=lambda c_supply: c_supply[1], reverse=order)
        return circulating_supplys

    def get_market_capitalization(self, order: bool = False):
        """Gets cryptocurrencies classified by market cap.

        Args:
            order (bool, optional): Indicates whether to run a ranking of best or worst. 
                                        If it is False then the method gets the worst, otherwise gets the best. Defaults to False.

        Returns:
            list: the cryptocurrencies classified by market cap.
        """
        market_caps = (
            (f"{response.get('name')} {response.get('symbol')}: {response.get('quote').get(self._converter).get('market_cap')}")
            for response in self._api_responses
        )
        market_caps = sorted(
            market_caps, key=lambda cap: cap[1], reverse=order)
        return market_caps

    def get_date_added_ranking(self, order: bool = False):
        """Gets cryptocurrencies ranked by chronological order of addition to CoinMarketCap platform.

        Args:
            order (bool, optional): Indicates whether to run a ranking of best or worst. 
                                        If it is False then the method gets the worst, otherwise gets the best. Defaults to False.

        Returns:
            list: the cryptocurrencies ranked by chronological order of addition to CoinMarketCap platform.
        """
        dates = (
            (f"{response.get('name')} {response.get('symbol')}: {response.get('date_added')}")
            for response in self._api_responses
        )
        dates = sorted(dates, key=lambda cap: cap[1], reverse=order)
        return dates


class IReportCryptoLayer:
    """Interface to use the module reporter crypto.
    """

    def main(self):
        """The main of the application.
        """
        retrieve = CoinMarketCapApi()
        parser = CryptoInfoDetector()
        retrieve.subscribe(parser)
        retrieve.get_crypt_info()


class Scheduler:
    """This class deals with scheduling the execution of the reporting system.

        Args:
            self._time (str): time to make the report.
            self._repeat_interval (str): the way of execution of module, weekly or daily.
            self._report_crypto (IReportCryptoLayer): the instance of IReportCryptoLayer.
    """

    def __init__(self) -> None:
        self._time = LoadConfiguration().get_time
        self._repeat_interval = LoadConfiguration().get_repeat_interval
        self. _report_crypto = IReportCryptoLayer()
        self.set_schedule()

    def set_schedule(self):
        """The method sets the time interval of the module.
        """
        if self._repeat_interval == "daily":
            schedule.every().day.at(self._time).do(self._report_crypto.main)
        elif self._repeat_interval == "weekly":
            schedule.every().week.at(self._time).do(self._report_crypto.main)
        else:
            schedule.every().minutes.at(self._time).do(self._report_crypto.main)

    def run(self):
        """It runs the reporting system according to the set scheduling.
        """
        while True:
            schedule.run_pending()
            time.sleep(1)


class ReportWriter:
    """This class is responsible for writing the reportable information of cryptocurrencies to the json file.

        Args:
            self.filename: the path of the report json file.
    """
    _NAME_OF_FILE = Path(f"report/report_{datetime.datetime.now().strftime('%d-%m-%y')}.json")

    def __init__(self):
        self.filename = Path(__file__).resolve(
        ).parent.parent / self._NAME_OF_FILE
        project_root = os.path.abspath(
            os.path.dirname(__file__)).replace("src", "")
        directory = os.path.join(project_root, 'report')
        filename = os.path.abspath(os.path.join(directory, 'report.json'))
        if not os.path.exists(directory):
            os.makedirs(directory)
        if not os.path.exists(filename):
            file = open(filename, "x", encoding="utf-8")
            file.close()

    def write_report(self, data):
        """The method writes in the report file the informations.

        Args:
            data (dict): the informations about the cryptos.
        """
        print("Writing in the report file...")
        with open(self.filename, 'a+', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
            file.write('\n')


if __name__ == "__main__":
    Scheduler().run()
