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
