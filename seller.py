import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Gets a list of Ozone store products.

    Args:
        last_id (str): The ID of the last value on the page
        client_id (str): Client ID
        seller_token (str): API key

    Returns:
        dict: Product data dictionary

    Raises:
        TypeError
        requests.exceptions

    Correct Example:
        {
            "items": [
                        {
                            "product_id": 223681945,
                            "offer_id": "136748"
                        }
                    ],
            total": 1,
            "last_id": "bnVсbA=="
        }

    Incorrect Example:
        {
            "code": 0,
            "details": [
                {
                    "typeUrl": "string",
                    "value": "string"
                }
            ],
            "message": "string"
        }

    """
    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Gets the SKUs of the Ozone store products.

    Args:
        client_id (str): Client ID
        seller_token (str): API key

    Returns:
        list: List of product SKUs

    Raises:
        TypeError

    Examples:
        ["136748"]

    """
    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """Update product prices.

    Args:
        prices (list): Price list
        client_id (str): Client ID
        seller_token (str): API key

    Returns:
        dict: List of product SKUs

    Raises:
        TypeError
        requests.exceptions

    Correct Example:
        {
            "prices": [
                {
                    "auto_action_enabled": "UNKNOWN",
                    "currency_code": "RUB",
                    "min_price": "800",
                    "offer_id": "",
                    "old_price": "0",
                    "price": "1448",
                    "price_strategy_enabled": "UNKNOWN",
                    "product_id": 1386
                }
            ]
        }

    Incorrect Example:
        {
            "code": 0,
            "details": [
                {
                    "typeUrl": "string",
                    "value": "string"
                }
            ],
            "message": "string"
        }

    """
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Refreshes the stocks.

    Args:
        stocks (list): Stocks list
        client_id (str): Client ID
        seller_token (str): API key

    Returns:
        dict: Stocks data dictionary

    Raises:
        TypeError
        requests.exceptions

    Correct Example:
        {
            "stocks": [
                {
                    "offer_id": "PG-2404С1",
                    "product_id": 55946,
                    "stock": 4
                }
            ]
        }

    Incorrect Example:
        {
            "code": 0,
            "details": [
                {
                    "typeUrl": "string",
                    "value": "string"
                }
            ],
            "message": "string"
        }

    """
    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Downloads the ostatki file from the casio website.

    Returns:
        dict: Clock remnants

    Raises:
        requests.exceptions

    """
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Creates a list of data for each product in the form of its article and number of copies.

    Args:
        watch_remnants (dict): Clock remnants
        offer_ids (list): List of product SKUs

    Returns:
        list: Stocks data list

    Raises:
        TypeError

    Examples:
        [
            {
               "offer_id": "136748",
                "stock": 0
            }
        ]

    """
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Forms the price of goods.

    Args:
        watch_remnants (dict): Clock remnants
        offer_ids (list): List of product SKUs

    Returns:
        list: Prices data list

    Raises:
        TypeError

    Examples:
        [
            {
               "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": "136748",
                "old_price": "0",
                "price": 5990,
            }
        ]

    """

    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Converts the price to a specific format.

    Args:
        price (str) : Numeric value in string format

    Returns:
        str: Numeric value in string format

    Raises:
        AttributeError: 'float' object has no attribute 'split'
        TypeError: price_conversion() missing 1 required positional argument: 'price'

    Examples:
        >>> price_conversion("5'990.00 руб.")
        5990

    """
    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Splits the list lst into parts of n elements.

    Args:
        lst (list): List
        n (int): Amount of elements

    Returns:
        list

    Raises:
        TypeError

    """
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Assigns prices for each product.

    Returns the new prices for each item.

    Args:
        watch_remnants (dict): Clock remnants
        client_id (str): Client ID
        seller_token (str): API key

    Returns:
        list: Prices data list

    Raises:
        TypeError

    Examples:
        [
            {
               "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": "136748",
                "old_price": "0",
                "price": 5990,
            }
        ]

    """
    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Assigns the remaining quantity for each item.

    Args:
        watch_remnants (dict): Clock remnants
        client_id (str): Client ID
        seller_token (str): API key

    Returns:
        tuple: Products left in stock, Product stocks

    Raises:
        TypeError

    Example:
        (
            [
                {
                   "offer_id": "136748",
                    "stock": 4
                }
            ],

            [
                {
                   "offer_id": "55",
                    "stock": 16
                }
            ]
                    
        )

    """
    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        # Обновить остатки
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        # Поменять цены
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
