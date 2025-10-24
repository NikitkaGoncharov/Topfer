"""
Сервисы для работы с внешними API
"""
import requests
from django.core.cache import cache
from decimal import Decimal


class BinanceService:
    """Сервис для получения данных о криптовалютах с Binance"""

    BASE_URL = "https://api.binance.com/api/v3"
    CACHE_TIMEOUT = 300  # 5 минут кэширования

    @classmethod
    def get_top_cryptos(cls, limit=5):
        """
        Получает топ криптовалют по объему торгов за 24 часа

        Args:
            limit (int): Количество криптовалют для получения (по умолчанию 5)

        Returns:
            list: Список словарей с информацией о криптовалютах
        """
        cache_key = f'binance_top_cryptos_{limit}'

        # Проверяем кэш
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            # Получаем данные о торгах за 24 часа для USDT пар
            response = requests.get(
                f"{cls.BASE_URL}/ticker/24hr",
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Фильтруем только USDT пары и исключаем некоторые токены
            usdt_pairs = [
                item for item in data
                if item['symbol'].endswith('USDT')
                and not any(x in item['symbol'] for x in ['DOWN', 'UP', 'BEAR', 'BULL'])
            ]

            # Сортируем по объему торгов (quoteVolume) в убывающем порядке
            sorted_pairs = sorted(
                usdt_pairs,
                key=lambda x: float(x.get('quoteVolume', 0)),
                reverse=True
            )[:limit]

            # Форматируем результат
            result = []
            for pair in sorted_pairs:
                symbol = pair['symbol'].replace('USDT', '')
                price = float(pair['lastPrice'])
                change_percent = float(pair['priceChangePercent'])
                volume_24h = float(pair['quoteVolume'])

                result.append({
                    'symbol': symbol,
                    'name': cls._get_crypto_name(symbol),
                    'price': price,
                    'change_24h': change_percent,
                    'volume_24h': volume_24h,
                    'price_formatted': cls._format_price(price),
                    'volume_formatted': cls._format_volume(volume_24h),
                })

            # Сохраняем в кэш
            cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            return result

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении данных с Binance: {e}")
            return []
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return []

    @staticmethod
    def _get_crypto_name(symbol):
        """
        Возвращает полное название криптовалюты по символу

        Args:
            symbol (str): Символ криптовалюты (например, BTC)

        Returns:
            str: Полное название
        """
        names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'BNB': 'Binance Coin',
            'XRP': 'Ripple',
            'ADA': 'Cardano',
            'DOGE': 'Dogecoin',
            'SOL': 'Solana',
            'DOT': 'Polkadot',
            'MATIC': 'Polygon',
            'SHIB': 'Shiba Inu',
            'TRX': 'TRON',
            'AVAX': 'Avalanche',
            'LINK': 'Chainlink',
            'UNI': 'Uniswap',
            'ATOM': 'Cosmos',
        }
        return names.get(symbol, symbol)

    @staticmethod
    def _format_price(price):
        """
        Форматирует цену для отображения

        Args:
            price (float): Цена

        Returns:
            str: Отформатированная цена
        """
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.2f}"
        elif price >= 0.01:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"

    @staticmethod
    def _format_volume(volume):
        """
        Форматирует объем торгов для отображения

        Args:
            volume (float): Объем в долларах

        Returns:
            str: Отформатированный объем
        """
        if volume >= 1_000_000_000:
            return f"${volume / 1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"${volume / 1_000_000:.2f}M"
        else:
            return f"${volume / 1_000:.2f}K"


class StockService:
    """Сервис для получения данных об акциях"""

    CACHE_TIMEOUT = 600  # 10 минут кэширования

    @classmethod
    def get_stock_price(cls, ticker):
        """
        Получает текущую цену акции через Yahoo Finance API

        Args:
            ticker (str): Тикер акции (например, AAPL)

        Returns:
            dict: Словарь с информацией об акции или None в случае ошибки
        """
        cache_key = f'stock_price_{ticker.upper()}'

        # Проверяем кэш
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            # Используем Yahoo Finance API через query1.finance.yahoo.com
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
            params = {
                'interval': '1d',
                'range': '1d'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'chart' not in data or 'result' not in data['chart']:
                return None

            result = data['chart']['result'][0]
            meta = result.get('meta', {})

            # Получаем текущую цену
            current_price = meta.get('regularMarketPrice')
            previous_close = meta.get('previousClose')

            if not current_price:
                return None

            # Рассчитываем изменение
            change = current_price - previous_close if previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close else 0

            stock_data = {
                'ticker': ticker.upper(),
                'name': meta.get('longName', ticker.upper()),
                'price': float(current_price),
                'previous_close': float(previous_close) if previous_close else None,
                'change': float(change),
                'change_percent': float(change_percent),
                'currency': meta.get('currency', 'USD'),
                'market_state': meta.get('marketState', 'REGULAR'),
            }

            # Сохраняем в кэш
            cache.set(cache_key, stock_data, cls.CACHE_TIMEOUT)

            return stock_data

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении данных об акции {ticker}: {e}")
            return None
        except Exception as e:
            print(f"Неожиданная ошибка при получении данных об акции {ticker}: {e}")
            return None

    @classmethod
    def get_stock_info(cls, ticker):
        """
        Получает подробную информацию об акции

        Args:
            ticker (str): Тикер акции

        Returns:
            dict: Подробная информация об акции
        """
        cache_key = f'stock_info_{ticker.upper()}'

        # Проверяем кэш
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker.upper()}"
            params = {
                'modules': 'price,summaryDetail'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'quoteSummary' not in data or 'result' not in data['quoteSummary']:
                return None

            result = data['quoteSummary']['result'][0]
            price_data = result.get('price', {})
            summary = result.get('summaryDetail', {})

            stock_info = {
                'ticker': ticker.upper(),
                'name': price_data.get('longName', ticker.upper()),
                'price': price_data.get('regularMarketPrice', {}).get('raw'),
                'market_cap': price_data.get('marketCap', {}).get('raw'),
                'day_high': summary.get('dayHigh', {}).get('raw'),
                'day_low': summary.get('dayLow', {}).get('raw'),
                'year_high': summary.get('fiftyTwoWeekHigh', {}).get('raw'),
                'year_low': summary.get('fiftyTwoWeekLow', {}).get('raw'),
                'volume': summary.get('volume', {}).get('raw'),
            }

            # Сохраняем в кэш
            cache.set(cache_key, stock_info, cls.CACHE_TIMEOUT)

            return stock_info

        except Exception as e:
            print(f"Ошибка при получении информации об акции {ticker}: {e}")
            return None

    @staticmethod
    def calculate_profit(purchase_price, current_price, quantity):
        """
        Рассчитывает прибыль/убыток по позиции

        Args:
            purchase_price (Decimal): Цена покупки
            current_price (float): Текущая цена
            quantity (Decimal): Количество акций

        Returns:
            dict: Информация о прибыли/убытке
        """
        total_investment = Decimal(str(purchase_price)) * quantity
        current_value = Decimal(str(current_price)) * quantity
        profit = current_value - total_investment
        profit_percent = (profit / total_investment * 100) if total_investment else 0

        return {
            'total_investment': float(total_investment),
            'current_value': float(current_value),
            'profit': float(profit),
            'profit_percent': float(profit_percent),
        }
