"""
Обработчик PDF файлов с рецептами
Извлекает текст из PDF, очищает его через OpenAI и рассчитывает КБЖУ
"""
import asyncio
import json
import re
from typing import Dict, List, Optional
from pathlib import Path

from PyPDF2 import PdfReader
from openai import AsyncOpenAI

from bot.core.config import settings


class PDFRecipeProcessor:
    """Обработчик PDF с рецептами"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Извлекает весь текст из PDF файла
        
        Args:
            pdf_path: Путь к PDF файлу
            
        Returns:
            Извлеченный текст
        """
        print(f"📄 Извлекаю текст из {pdf_path}...")
        
        reader = PdfReader(pdf_path)
        text_parts = []
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text:
                text_parts.append(text)
                print(f"   Страница {page_num}: извлечено {len(text)} символов")
        
        full_text = "\n\n".join(text_parts)
        print(f"✅ Всего извлечено {len(full_text)} символов из {len(reader.pages)} страниц\n")
        
        return full_text
    
    async def split_recipes(self, raw_text: str) -> List[str]:
        """
        Разделяет текст на отдельные рецепты с помощью OpenAI
        
        Args:
            raw_text: Сырой текст из PDF
            
        Returns:
            Список текстов отдельных рецептов
        """
        print("🤖 Разделяю текст на отдельные рецепты через OpenAI...")
        
        prompt = f"""
Перед тобой текст, извлеченный из PDF файла с рецептами.
Твоя задача - разделить его на отдельные рецепты.

Текст может содержать:
- Несколько рецептов подряд
- Номера страниц, колонтитулы
- Мусорные символы из-за проблем с извлечением из PDF

Верни JSON массив, где каждый элемент - это текст одного рецепта:
{{
    "recipes": [
        {{
            "title": "Название рецепта",
            "raw_text": "Полный текст рецепта как есть"
        }}
    ]
}}

Сохраняй весь текст рецепта полностью, включая все детали.

ТЕКСТ ДЛЯ ОБРАБОТКИ:
{raw_text[:15000]}
"""
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник для обработки кулинарных рецептов из текстовых файлов."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=16000
        )
        
        result = json.loads(response.choices[0].message.content)
        recipes = [r["raw_text"] for r in result.get("recipes", [])]
        
        print(f"✅ Найдено рецептов: {len(recipes)}\n")
        return recipes
    
    async def clean_and_calculate_recipe(
        self, 
        raw_recipe_text: str, 
        recipe_num: int = 1
    ) -> Optional[Dict]:
        """
        Очищает текст рецепта от мусора и рассчитывает КБЖУ
        
        Args:
            raw_recipe_text: Сырой текст рецепта
            recipe_num: Номер рецепта для отображения
            
        Returns:
            Словарь с очищенными данными рецепта в формате для RecipeBase
        """
        print(f"[{recipe_num}] 🧹 Очищаю текст и рассчитываю КБЖУ...")
        
        prompt = f"""
Перед тобой рецепт, извлеченный из PDF. 
Он может содержать мусорные символы, опечатки, проблемы с форматированием.

Твоя задача:
1. Очистить текст от мусора
2. Извлечь структурированную информацию
3. Рассчитать КБЖУ на 100г готового блюда (используй стандартные таблицы калорийности)

Верни результат в JSON формате:
{{
    "title": "Название блюда",
    "tags": "тег1, тег2, тег3",
    "cooking_time": "~30 мин",
    "difficulty": "Легкая/Средняя/Сложная",
    "ingredients": "Список ингредиентов с количеством (каждый с новой строки)",
    "instructions": "Пошаговая инструкция приготовления (шаги разделены двойным переносом строки)",
    "notes": "Дополнительные заметки (если есть)",
    "calories_per_100g": 150.0,
    "protein_per_100g": 12.5,
    "fat_per_100g": 5.0,
    "carbs_per_100g": 15.0
}}

Важно:
- Рассчитывай КБЖУ максимально точно на основе ингредиентов
- Если в рецепте не указаны точные граммы, сделай разумные предположения
- Инструкции должны быть четкими и последовательными
- Удали все мусорные символы, номера страниц, колонтитулы

РЕЦЕПТ ДЛЯ ОБРАБОТКИ:
{raw_recipe_text}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты опытный повар и диетолог. Ты умеешь точно рассчитывать КБЖУ блюд на основе ингредиентов."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=3000
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Валидация обязательных полей
            required_fields = [
                'title', 'ingredients', 'instructions',
                'calories_per_100g', 'protein_per_100g', 
                'fat_per_100g', 'carbs_per_100g'
            ]
            
            for field in required_fields:
                if field not in result or result[field] in [None, '', 0]:
                    print(f"   ⚠️  Поле {field} отсутствует или пустое")
                    return None
            
            print(f"   ✅ {result['title']}")
            print(f"   КБЖУ на 100г: {result['calories_per_100g']:.0f} ккал "
                  f"{result['protein_per_100g']:.1f}/"
                  f"{result['fat_per_100g']:.1f}/"
                  f"{result['carbs_per_100g']:.1f}\n")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Ошибка при обработке рецепта: {e}\n")
            return None
    
    async def process_pdf(
        self, 
        pdf_path: str,
        batch_size: int = 3
    ) -> List[Dict]:
        """
        Полная обработка PDF файла с рецептами
        
        Args:
            pdf_path: Путь к PDF файлу
            batch_size: Количество рецептов для обработки за раз
            
        Returns:
            Список словарей с обработанными рецептами
        """
        # Проверяем существование файла
        if not Path(pdf_path).exists():
            print(f"❌ Файл не найден: {pdf_path}")
            return []
        
        print("\n" + "="*70)
        print("📚 ОБРАБОТКА PDF С РЕЦЕПТАМИ")
        print("="*70 + "\n")
        
        # Шаг 1: Извлекаем текст из PDF
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        if not raw_text or len(raw_text) < 100:
            print("❌ Не удалось извлечь текст из PDF или текст слишком короткий")
            return []
        
        # Шаг 2: Разделяем на отдельные рецепты
        raw_recipes = await self.split_recipes(raw_text)
        
        if not raw_recipes:
            print("❌ Не удалось найти рецепты в тексте")
            return []
        
        print(f"🔄 Начинаю обработку {len(raw_recipes)} рецептов...\n")
        print("-"*70 + "\n")
        
        # Шаг 3: Обрабатываем каждый рецепт (с батчингом для экономии токенов)
        processed_recipes = []
        
        for i, raw_recipe in enumerate(raw_recipes, 1):
            recipe_data = await self.clean_and_calculate_recipe(raw_recipe, i)
            
            if recipe_data:
                processed_recipes.append(recipe_data)
            
            # Небольшая пауза между запросами
            if i < len(raw_recipes):
                await asyncio.sleep(1)
        
        print("-"*70)
        print(f"\n✅ Обработка завершена!")
        print(f"   Всего рецептов: {len(raw_recipes)}")
        print(f"   Успешно обработано: {len(processed_recipes)}")
        print(f"   Не удалось обработать: {len(raw_recipes) - len(processed_recipes)}")
        print()
        
        return processed_recipes


async def main():
    """Главная функция для тестирования"""
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python pdf_processor.py <путь_к_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    processor = PDFRecipeProcessor()
    recipes = await processor.process_pdf(pdf_path)
    
    # Сохраняем результат в JSON для проверки
    if recipes:
        output_file = "processed_recipes.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        
        print(f"📝 Результат сохранен в {output_file}")


if __name__ == '__main__':
    asyncio.run(main())


