import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    """Gets a list of Yandex Market store products.

    Args:
        page (str): ID of the results page
        campaign_id (int): Campaign ID and Store ID
        access_token (str): Employee token

    Returns:
        dict: Product data dictionary

    Raises:
        TypeError
        requests.exceptions

    Сorrect Example:
        {
            "paging": {
                "nextPageToken": "string",
                "prevPageToken": "string"
            }, ...
        }

    Incorrect Example:
        {
            "status": "OK",
            "errors": [
                        {
                            "code": "string",
                            "message": "string"
                        }
                    ]
        }

    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    """Refreshes the stocks.

        Args:
            stocks (list): Stocks list
            campaign_id (int): Campaign ID and Store ID
            access_token (str): Employee token

        Returns:
            dict: Stocks data dictionary

        Raises:
            TypeError
            requests.exceptions

        Сorrect Example:
            {
                "status": "OK"
            }


        Incorrect Example:
            {
                "status": "OK",
                "errors": [
                        {
                            "code": "string",
                            "message": "string"
                        }
                ]
            }

        """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    """Update product prices.

        Args:
            prices (list): Price list
            campaign_id (int): Campaign ID and Store ID
            access_token (str): Employee token

        Returns:
            dict: List of product SKUs

        Raises:
            TypeError
            requests.exceptions

        Сorrect Example:
            {
                "status": "OK"
            }


        Incorrect Example:
            {
                "status": "OK",
                "errors": [
                        {
                            "code": "string",
                            "message": "string"
                        }
                ]
            }

        """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Gets the SKUs of the Yandex Market store products.

    Args:
        campaign_id (int): Campaign ID and Store ID
        market_token (str): Employee token

    Returns:
        list: List of product SKUs

    Raises:
        TypeError

    Examples:
        ["136748",...]

    """
    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    """Creates a list of data for each product in the form of its article and number of copies.

        Args:
            watch_remnants (dict): Clock remnants
            offer_ids (list): List of product SKUs
            warehouse_id (int): Warehouse ID

        Returns:
            list: Stocks data list

        Raises:
            TypeError

        Examples:
            [
                {
                    "sku": '145',
                    "warehouseId": 0,
                    "items": [
                        {
                            "count": 0,
                            "type": "FIT",
                            "updatedAt": "2022-12-29T18:02:01Z",
                        }
                    ],
                },...
            ]

        """
    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))

    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
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
                    "id": '45',
                    "price": {
                        "value": 2400,
                        "currencyId": "RUR",
                    }
                }
            ]

        """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "id": str(watch.get("Код")),
                # "feed": {"id": 0},
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    # "discountBase": 0,
                    "currencyId": "RUR",
                    # "vat": 0,
                },
                # "marketSku": 0,
                # "shopSku": "string",
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    """Assigns prices for each product.

    Returns the new prices for each item.

    Args:
        watch_remnants (dict): Clock remnants
        campaign_id (int): Campaign ID and Store ID
        market_token (str): Employee token

    Returns:
        list: Prices data list

    Raises:
        TypeError

    Examples:
        [
            {
                "id": '45',
                "price": {
                    "value": 2400,
                    "currencyId": "RUR",
                }
            }
        ]

        """
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id):
    """Assigns the remaining quantity for each item.

    Args:
        watch_remnants (dict): Clock remnants
        campaign_id (int): Campaign ID and Store ID
        market_token (str): Employee token
        warehouse_id (int): Warehouse ID

    Returns:
        tuple: Products left in stock, Product stocks

    Raises:
        TypeError

    Examples:
        (

            [
                {
                    "sku": '145',
                    "warehouseId": 0,
                    "items": [
                        {
                            "count": 0,
                            "type": "FIT",
                            "updatedAt": "2022-12-29T18:02:01Z",
                        }
                    ],
                },...
            ],

            [
                {
                    "sku": '146',
                    "warehouseId": 0,
                    "items": [
                        {
                            "count": 5,
                            "type": "FIT",
                            "updatedAt": "2022-12-29T18:02:01Z",
                        }
                    ],
                },...
            ]

        )

        """
    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks


def main():
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        # FBS
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        # Обновить остатки FBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        # Поменять цены FBS
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        # DBS
        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        # Обновить остатки DBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        # Поменять цены DBS
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
