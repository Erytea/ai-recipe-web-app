"""
Парсер базы продуктов с сайта calorizator.ru
"""

import asyncio
import json
from typing import Dict, List
import httpx
from bs4 import BeautifulSoup


class CalorizatorParser:
    """Парсер для получения данных о продуктах с calorizator.ru"""
    
    BASE_URL = "https://calorizator.ru"
    
    # Основные категории продуктов для парсинга
    CATEGORIES = {
        "myaso": "Мясо и птица",
        "ryba": "Рыба и морепродукты",
        "yajca": "Яйца",
        "moloko": "Молочные продукты",
        "krupy": "Крупы и каши",
        "xleb": "Хлеб и хлебобулочные",
        "ovoshhi": "Овощи",
        "frukty": "Фрукты и ягоды",
        "orexi": "Орехи и семена",
        "maslo": "Масла и жиры",
    }
    
    def __init__(self):
        self.products = {}
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
    
    async def parse_category(self, category_slug: str) -> List[Dict]:
        """Парсит одну категорию продуктов"""
        url = f"{self.BASE_URL}/product/{category_slug}"
        
        try:
            print(f"📥 Парсим категорию: {self.CATEGORIES[category_slug]}...")
            response = await self.client.get(url)
            
            if response.status_code != 200:
                print(f"❌ Ошибка {response.status_code} для {url}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            
            # Ищем таблицу с продуктами
            # Структура может отличаться, нужно будет адаптировать
            table = soup.find('table', class_='product_table')
            if not table:
                # Пробуем альтернативные варианты
                table = soup.find('table')
            
            if table:
                rows = table.find_all('tr')[1:]  # Пропускаем заголовок
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        try:
                            name = cols[0].get_text(strip=True)
                            calories = float(cols[1].get_text(strip=True).replace(',', '.'))
                            protein = float(cols[2].get_text(strip=True).replace(',', '.'))
                            fat = float(cols[3].get_text(strip=True).replace(',', '.'))
                            carbs = float(cols[4].get_text(strip=True).replace(',', '.'))
                            
                            product = {
                                "name": name.lower(),
                                "calories": calories,
                                "protein": protein,
                                "fat": fat,
                                "carbs": carbs,
                                "category": category_slug
                            }
                            products.append(product)
                            
                        except (ValueError, AttributeError) as e:
                            # Пропускаем строки с ошибками парсинга
                            continue
            
            print(f"✅ Найдено продуктов: {len(products)}")
            return products
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге {category_slug}: {e}")
            return []
    
    async def parse_all_categories(self) -> Dict:
        """Парсит все категории"""
        all_products = {}
        
        for slug, name in self.CATEGORIES.items():
            products = await self.parse_category(slug)
            for product in products:
                # Используем название продукта как ключ
                all_products[product["name"]] = {
                    "calories": product["calories"],
                    "protein": product["protein"],
                    "fat": product["fat"],
                    "carbs": product["carbs"],
                    "category": product["category"]
                }
            
            # Небольшая задержка между запросами
            await asyncio.sleep(1)
        
        return all_products
    
    async def save_to_json(self, filename: str = "products_database.json"):
        """Сохраняет спарсенные данные в JSON"""
        products = await self.parse_all_categories()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Сохранено {len(products)} продуктов в {filename}")
        return products
    
    async def save_to_python(self, filename: str = "parsed_products.py"):
        """Сохраняет данные в формате Python словаря"""
        products = await self.parse_all_categories()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('"""Автоматически сгенерированная база продуктов"""\n\n')
            f.write('PRODUCTS = ')
            f.write(json.dumps(products, ensure_ascii=False, indent=4))
        
        print(f"\n✅ Сохранено {len(products)} продуктов в {filename}")
        return products
    
    async def close(self):
        """Закрывает HTTP клиент"""
        await self.client.aclose()


async def main():
    """Основная функция для запуска парсера"""
    parser = CalorizatorParser()
    
    try:
        print("🚀 Начинаем парсинг calorizator.ru...\n")
        
        # Сохраняем в оба формата
        await parser.save_to_json("products_database.json")
        await parser.save_to_python("bot/services/parsed_products.py")
        
        print("\n🎉 Парсинг завершен!")
        print("📁 Файлы созданы:")
        print("   - products_database.json (формат JSON)")
        print("   - bot/services/parsed_products.py (формат Python)")
        
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(main())






