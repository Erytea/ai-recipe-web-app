import base64
import json
from typing import Dict, List, Optional
from openai import AsyncOpenAI

from bot.core.config import settings
from bot.services.nutrition_database import nutrition_db


class OpenAIService:
    """Сервис для работы с OpenAI API"""
    
    def __init__(self):
        # Создаем клиент только если есть API ключ
        if settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            self.client = None
    
    async def analyze_food_image(self, image_data: bytes) -> Dict:
        """
        Анализирует изображение продуктов и возвращает список ингредиентов.
        
        Args:
            image_data: Байты изображения
            
        Returns:
            Dict с ключами:
                - ingredients: список обнаруженных продуктов
                - uncertainties: список продуктов, требующих уточнения
        """
        # Кодируем изображение в base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        prompt = """
        Проанализируй это изображение продуктов. Определи, что там есть.
        
        Верни результат в JSON формате:
        {
            "ingredients": ["продукт 1", "продукт 2", ...],
            "uncertainties": [
                {
                    "item": "описание того, что видно",
                    "options": ["вариант 1", "вариант 2"]
                }
            ]
        }
        
        В "uncertainties" помещай продукты, которые сложно определить точно 
        (например, непонятно - это ветчина или колбаса, курица или индейка).
        
        Будь точным и конкретным в определении продуктов.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Модель с поддержкой изображений
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                timeout=30.0  # Таймаут 30 секунд
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            # Обработка ошибок OpenAI API
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise Exception("Превышен лимит запросов к OpenAI. Попробуй позже.")
            elif "timeout" in error_msg.lower():
                raise Exception("Превышено время ожидания ответа от OpenAI. Попробуй еще раз.")
            elif "invalid_api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise Exception("Ошибка аутентификации OpenAI API. Проверь настройки.")
            else:
                raise Exception(f"Ошибка при обращении к OpenAI: {error_msg}")
    
    async def generate_recipe(
        self,
        ingredients: List[str],
        target_calories: int,
        target_protein: Optional[float] = None,
        target_fat: Optional[float] = None,
        target_carbs: Optional[float] = None,
        greens_weight: Optional[float] = None,
        cooking_tags: Optional[str] = None
    ) -> Dict:
        """
        Генерирует рецепт на основе ингредиентов и целевых показателей КБЖУ.
        
        Args:
            ingredients: Список доступных ингредиентов
            target_calories: Целевые калории (обязательно)
            target_protein: Целевой белок (г, опционально)
            target_fat: Целевые жиры (г, опционально)
            target_carbs: Целевые углеводы (г, опционально)
            greens_weight: Количество растительности (г, опционально)
            cooking_tags: Теги способов приготовления (опционально)
            
        Returns:
            Dict с ключами:
                - recipe_title: Название блюда
                - recipe_text: Полный текст рецепта с порциями ингредиентов
                - cooking_steps: Пошаговая инструкция
                - calculated_nutrition: Рассчитанное КБЖУ
        """
        
        ingredients_text = ", ".join(ingredients)
        
        # Формируем список целевых показателей (только указанные)
        target_indicators = [f"- Калории: {target_calories} ккал (ОБЯЗАТЕЛЬНО)"]
        
        if target_protein is not None and target_protein > 0:
            target_indicators.append(f"- Белки: {target_protein} г")
        
        if target_fat is not None and target_fat > 0:
            target_indicators.append(f"- Жиры: {target_fat} г")
        
        if target_carbs is not None and target_carbs > 0:
            target_indicators.append(f"- Углеводы: {target_carbs} г")
        
        if greens_weight is not None and greens_weight > 0:
            target_indicators.append(f"- Растительность (зелень, овощи): {greens_weight} г")
        
        target_indicators_text = "\n        ".join(target_indicators)
        
        # Формируем требования
        requirements = [
            "Используй ТОЛЬКО указанные ингредиенты",
            "ОБЯЗАТЕЛЬНО соблюдай целевые калории",
        ]
        
        if target_protein is not None and target_protein > 0:
            requirements.append("Старайся приблизиться к целевому количеству белков")
        if target_fat is not None and target_fat > 0:
            requirements.append("Старайся приблизиться к целевому количеству жиров")
        if target_carbs is not None and target_carbs > 0:
            requirements.append("Старайся приблизиться к целевому количеству углеводов")
        if greens_weight is not None and greens_weight > 0:
            requirements.append(f"ОБЯЗАТЕЛЬНО включи {greens_weight}г растительности (зелень, овощи)")
        
        # Добавляем требования по способам приготовления, если указаны теги
        if cooking_tags:
            tags_list = [tag.strip() for tag in cooking_tags.split(',') if tag.strip()]
            if tags_list:
                requirements.append(f"ОБЯЗАТЕЛЬНО используй следующие способы приготовления: {', '.join(tags_list)}")
        
        requirements.append("Укажи точный вес каждого ингредиента в граммах")
        requirements.append("Рассчитай итоговое КБЖУ блюда на основе указанных порций")
        
        # Нумеруем требования
        requirements_text = "\n        ".join([f"{i+1}. {req}" for i, req in enumerate(requirements)])
        
        prompt = f"""
        Создай рецепт блюда на основе следующих данных:
        
        Доступные ингредиенты: {ingredients_text}
        
        Целевые показатели:
        {target_indicators_text}
        
        Требования:
        {requirements_text}
        
        Верни результат в JSON формате:
        {{
            "recipe_title": "Название блюда",
            "ingredients_with_weights": [
                {{"name": "Ингредиент", "weight_g": 100}}
            ],
            "cooking_steps": [
                "Шаг 1",
                "Шаг 2"
            ],
            "calculated_nutrition": {{
                "calories": 500.0,
                "protein_g": 30.0,
                "fat_g": 20.0,
                "carbs_g": 40.0
            }}
        }}
        
        Будь точным в расчетах КБЖУ и весе продуктов.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты опытный шеф-повар и диетолог. Ты умеешь точно рассчитывать КБЖУ блюд."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000,
                timeout=60.0  # Таймаут 60 секунд для генерации рецепта
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise Exception("Превышен лимит запросов к OpenAI. Попробуй позже.")
            elif "timeout" in error_msg.lower():
                raise Exception("Превышено время ожидания ответа от OpenAI. Попробуй еще раз.")
            else:
                raise Exception(f"Ошибка при генерации рецепта: {error_msg}")
    
    @staticmethod
    def format_recipe_response(recipe_data: Dict) -> str:
        """
        Форматирует данные рецепта в красивый текст для отправки пользователю.
        
        Args:
            recipe_data: Данные рецепта из generate_recipe
            
        Returns:
            Отформатированный текст рецепта
        """
        lines = []
        lines.append(f"🍽 *{recipe_data['recipe_title']}*\n")
        
        lines.append("📋 *Ингредиенты:*")
        for ing in recipe_data['ingredients_with_weights']:
            lines.append(f"• {ing['name']}: {ing['weight_g']} г")
        
        lines.append("\n👨‍🍳 *Приготовление:*")
        for i, step in enumerate(recipe_data['cooking_steps'], 1):
            lines.append(f"{i}. {step}")
        
        nutrition = recipe_data['calculated_nutrition']
        lines.append("\n📊 *КБЖУ на всё блюдо:*")
        lines.append(f"🔥 Калории: {nutrition['calories']:.0f} ккал")
        lines.append(f"🥩 Белки: {nutrition['protein_g']:.1f} г")
        lines.append(f"🧈 Жиры: {nutrition['fat_g']:.1f} г")
        lines.append(f"🍞 Углеводы: {nutrition['carbs_g']:.1f} г")
        
        return "\n".join(lines)
    
    async def generate_meal_plan(
        self,
        ingredients: List[str],
        meals_count: int,
        target_daily_calories: int,
        target_daily_protein: float,
        target_daily_fat: float,
        target_daily_carbs: float,
        daily_greens_weight: float
    ) -> Dict:
        """
        Генерирует рацион питания на день с точными расчетами КБЖУ.
        
        Использует двухэтапный подход:
        1. GPT выбирает продукты и распределяет их по приемам пищи
        2. Python точно рассчитывает КБЖУ из базы данных
        """
        
        ingredients_text = ", ".join(ingredients)
        
        # Определяем названия приемов пищи
        meal_names = {
            1: ["Прием пищи"],
            2: ["Первый прием", "Второй прием"],
            3: ["Завтрак", "Обед", "Ужин"],
            4: ["Завтрак", "Обед", "Полдник", "Ужин"],
            5: ["Завтрак", "Второй завтрак", "Обед", "Полдник", "Ужин"],
            6: ["Завтрак", "Второй завтрак", "Обед", "Полдник", "Ужин", "Поздний ужин"]
        }
        
        meals_names_list = meal_names.get(meals_count, [f"Прием {i+1}" for i in range(meals_count)])
        
        # Получаем список доступных продуктов из базы данных
        available_products_in_db = list(nutrition_db.PRODUCTS.keys())
        
        # Пытаемся сопоставить продукты пользователя с базой данных
        matched_products = []
        for ingredient in ingredients:
            ingredient_lower = ingredient.lower()
            # Ищем совпадения
            found = False
            for db_product in available_products_in_db:
                if ingredient_lower in db_product or db_product in ingredient_lower:
                    matched_products.append(db_product)
                    found = True
                    break
            if not found:
                # Если не нашли, добавляем как есть (будем искать позже)
                matched_products.append(ingredient)
        
        # Формируем список продуктов для промпта
        products_for_prompt = list(set(matched_products))  # Убираем дубликаты
        products_text = ", ".join([f'"{p}"' for p in products_for_prompt])
        
        # Получаем правила для каждого приема пищи
        meal_rules_text = ""
        for meal_name in meals_names_list:
            rules = nutrition_db.get_meal_rules(meal_name)
            if rules:
                meal_rules_text += f"\n{meal_name}: {rules['description']}\n"
                meal_rules_text += f"  Примеры: {'; '.join(rules['examples'])}\n"
        
        prompt = f"""
        Ты профессиональный диетолог. Составь СБАЛАНСИРОВАННЫЙ рацион питания на день.
        
        ДОСТУПНЫЕ ПРОДУКТЫ (используй ТОЛЬКО эти названия!):
        {products_text}
        
        Целевые показатели ЗА ВЕСЬ ДЕНЬ:
        - Калории: {target_daily_calories} ккал
        - Белки: {target_daily_protein} г
        - Жиры: {target_daily_fat} г
        - Углеводы: {target_daily_carbs} г
        - Овощи/фрукты: {daily_greens_weight} г
        
        Количество приемов пищи: {meals_count} ({', '.join(meals_names_list)})
        
        ПРАВИЛА для каждого приема пищи:
        {meal_rules_text}
        
        КРИТИЧЕСКИ ВАЖНО:
        0. ИСПОЛЬЗУЙ ТОЛЬКО ТОЧНЫЕ НАЗВАНИЯ ПРОДУКТОВ ИЗ СПИСКА ВЫШЕ!
           ❌ НЕЛЬЗЯ писать: "жареная курица", "салат с овощами", "жёлтый перец"
           ✅ МОЖНО писать только: "курица грудка", "помидоры", "перец болгарский"
        
        1. Завтрак: ОБЯЗАТЕЛЬНО белок + сложные углеводы (каша/хлеб) + овощи
           ❌ НЕЛЬЗЯ: только яйца и салат, яйца с фруктами без каши
           ✅ МОЖНО: яйца + овсянка + огурцы, творог + хлеб + помидоры
        
        2. Обед: ОБЯЗАТЕЛЬНО белок + гарнир (рис/гречка/макароны) + овощной салат
           ❌ НЕЛЬЗЯ: только мясо с овощами без гарнира
           ✅ МОЖНО: курица + рис + салат из овощей
        
        3. Ужин: ОБЯЗАТЕЛЬНО белок + много овощей, МИНИМУМ углеводов
           ❌ НЕЛЬЗЯ: фрукты, сладкое, много каши
           ✅ МОЖНО: рыба + тушеные овощи, творог + огурцы
        
        4. Сочетай продукты ЛОГИЧНО (как в ресторане):
           ❌ НЕЛЬЗЯ: яйца + малина, арбуз + лук + черника, курица + ананас
           ✅ МОЖНО: яйца + огурцы + хлеб, салат из огурцов и помидоров
        
        5. Распредели калории грамотно:
           - Завтрак: 25-30% от дневной нормы
           - Обед: 35-40% от дневной нормы
           - Ужин: 20-25% от дневной нормы
           - Перекусы: 5-10% каждый
        
        6. НАЗВАНИЯ ПРОДУКТОВ:
           - Копируй названия ТОЧНО из списка доступных продуктов
           - НЕ добавляй слова "жареный", "запеченный", "салат из"
           - НЕ объединяй несколько продуктов в один (типа "салат с овощами")
           - Каждый продукт отдельной строкой!
        
        Верни результат в JSON:
        {{
            "meals": [
                {{
                    "meal_name": "Завтрак",
                    "foods": [
                        {{"name": "яйца куриные", "weight_g": 100}},
                        {{"name": "овсянка", "weight_g": 50}},
                        {{"name": "огурцы", "weight_g": 100}}
                    ]
                }}
            ]
        }}
        
        Будь профессионалом! Создавай РЕАЛЬНЫЕ сочетания продуктов, как в настоящем меню!
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты профессиональный диетолог с 15-летним стажем. "
                            "Ты составляешь рационы для реальных людей. "
                            "Ты знаешь, как правильно сочетать продукты. "
                            "Ты НИКОГДА не создашь абсурдные комбинации типа 'яйца + малина' или 'арбуз + лук'."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Снизили температуру для более предсказуемых результатов
                max_tokens=2000,
                timeout=60.0  # Таймаут 60 секунд
            )
            
            gpt_result = json.loads(response.choices[0].message.content)
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise Exception("Превышен лимит запросов к OpenAI. Попробуй позже.")
            elif "timeout" in error_msg.lower():
                raise Exception("Превышено время ожидания ответа от OpenAI. Попробуй еще раз.")
            else:
                raise Exception(f"Ошибка при генерации плана питания: {error_msg}")
        
        # Теперь ТОЧНО рассчитываем КБЖУ из нашей базы данных
        meals_with_nutrition = []
        total_calories = 0
        total_protein = 0
        total_fat = 0
        total_carbs = 0
        
        for meal in gpt_result.get("meals", []):
            meal_calories = 0
            meal_protein = 0
            meal_fat = 0
            meal_carbs = 0
            
            foods_with_nutrition = []
            for food in meal.get("foods", []):
                product_name = food["name"]
                weight_g = food["weight_g"]
                
                # Получаем точное КБЖУ из базы данных
                nutrition = nutrition_db.calculate_nutrition(product_name, weight_g)
                
                if nutrition:
                    meal_calories += nutrition["calories"]
                    meal_protein += nutrition["protein"]
                    meal_fat += nutrition["fat"]
                    meal_carbs += nutrition["carbs"]
                    
                    foods_with_nutrition.append({
                        "name": product_name,
                        "weight_g": weight_g
                    })
                else:
                    # Если продукт не найден в базе, пытаемся найти похожие
                    similar = nutrition_db.find_similar_products(product_name, limit=1)
                    if similar:
                        print(f"⚠️ Продукт '{product_name}' не найден, используем '{similar[0]}'")
                        nutrition = nutrition_db.calculate_nutrition(similar[0], weight_g)
                        if nutrition:
                            meal_calories += nutrition["calories"]
                            meal_protein += nutrition["protein"]
                            meal_fat += nutrition["fat"]
                            meal_carbs += nutrition["carbs"]
                            
                            foods_with_nutrition.append({
                                "name": similar[0],
                                "weight_g": weight_g
                            })
                        else:
                            print(f"❌ Продукт '{product_name}' пропущен (не найден в базе)")
                            foods_with_nutrition.append({
                                "name": product_name + " (не найден в БД)",
                                "weight_g": weight_g
                            })
                    else:
                        print(f"❌ Продукт '{product_name}' пропущен (не найден в базе)")
                        foods_with_nutrition.append({
                            "name": product_name + " (не найден в БД)",
                            "weight_g": weight_g
                        })
            
            total_calories += meal_calories
            total_protein += meal_protein
            total_fat += meal_fat
            total_carbs += meal_carbs
            
            meals_with_nutrition.append({
                "meal_name": meal["meal_name"],
                "foods": foods_with_nutrition,
                "nutrition": {
                    "calories": round(meal_calories, 1),
                    "protein_g": round(meal_protein, 1),
                    "fat_g": round(meal_fat, 1),
                    "carbs_g": round(meal_carbs, 1)
                }
            })
        
        return {
            "meals": meals_with_nutrition,
            "calculated_daily_nutrition": {
                "calories": round(total_calories, 1),
                "protein_g": round(total_protein, 1),
                "fat_g": round(total_fat, 1),
                "carbs_g": round(total_carbs, 1)
            }
        }
    
    @staticmethod
    def format_meal_plan_response(meal_plan_data: Dict) -> str:
        """
        Форматирует данные рациона в красивый текст для отправки пользователю.
        
        Args:
            meal_plan_data: Данные рациона из generate_meal_plan
            
        Returns:
            Отформатированный текст рациона
        """
        lines = []
        lines.append("📅 *Рацион питания на день*\n")
        
        for meal in meal_plan_data['meals']:
            lines.append(f"🍽 *{meal['meal_name']}:*")
            for food in meal['foods']:
                lines.append(f"  • {food['name']} — {food['weight_g']} г")
            
            # КБЖУ приема пищи
            nutrition = meal['nutrition']
            lines.append(
                f"  _КБЖУ: {nutrition['calories']:.0f} ккал, "
                f"Б: {nutrition['protein_g']:.1f}г, "
                f"Ж: {nutrition['fat_g']:.1f}г, "
                f"У: {nutrition['carbs_g']:.1f}г_\n"
            )
        
        # Итоговое КБЖУ за день
        daily_nutrition = meal_plan_data['calculated_daily_nutrition']
        lines.append("📊 *Итого за день:*")
        lines.append(f"🔥 Калории: {daily_nutrition['calories']:.0f} ккал")
        lines.append(f"🥩 Белки: {daily_nutrition['protein_g']:.1f} г")
        lines.append(f"🧈 Жиры: {daily_nutrition['fat_g']:.1f} г")
        lines.append(f"🍞 Углеводы: {daily_nutrition['carbs_g']:.1f} г")
        
        return "\n".join(lines)


# Глобальный экземпляр сервиса
openai_service = OpenAIService()

