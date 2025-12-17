from tortoise import fields, Tortoise
from tortoise.models import Model
import uuid


class RecipeBase(Model):
    """Базовая библиотека рецептов (общая база)"""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    # Основная информация
    title = fields.CharField(max_length=500, description="Название рецепта")
    tags = fields.TextField(null=True, description="Теги через запятую")

    # Метаданные
    cooking_time = fields.CharField(
        max_length=100, null=True, description="Время приготовления"
    )
    difficulty = fields.CharField(max_length=50, null=True, description="Сложность")

    # КБЖУ на 100 г
    calories_per_100g = fields.FloatField(description="Калории на 100г")
    protein_per_100g = fields.FloatField(description="Белки на 100г")
    fat_per_100g = fields.FloatField(description="Жиры на 100г")
    carbs_per_100g = fields.FloatField(description="Углеводы на 100г")

    # Содержимое
    ingredients = fields.TextField(description="Список ингредиентов")
    instructions = fields.TextField(description="Инструкция приготовления")

    # Дополнительные заметки
    notes = fields.TextField(null=True, description="Дополнительные заметки")

    created_at = fields.DatetimeField(auto_now_add=True, description="Дата добавления")

    class Meta:
        table = "recipe_base"
        ordering = ["-created_at"]

    def __str__(self):
        return f"RecipeBase: {self.title}"

    @property
    def kbzhu_formatted(self) -> str:
        """Форматированное КБЖУ на 100г"""
        return (
            f"КБЖУ на 100 г:\n"
            f"{self.calories_per_100g:.0f} ккал "
            f"{self.protein_per_100g:.1f}/"
            f"{self.fat_per_100g:.1f}/"
            f"{self.carbs_per_100g:.1f}"
        )


class Recipe(Model):
    """Модель рецепта"""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    # Исходные данные
    photo_file_id = fields.CharField(max_length=500, description="Путь к файлу фото")
    ingredients_detected = fields.TextField(description="Обнаруженные ингредиенты")
    clarifications = fields.TextField(null=True, description="Уточнения пользователя")

    # Пожелания пользователя
    target_calories = fields.IntField(description="Желаемые калории")
    target_protein = fields.FloatField(description="Желаемый белок (г)")
    target_fat = fields.FloatField(description="Желаемые жиры (г)")
    target_carbs = fields.FloatField(description="Желаемые углеводы (г)")
    greens_weight = fields.FloatField(description="Количество растительности (г)")

    # Результат
    recipe_text = fields.TextField(description="Текст рецепта")
    calculated_calories = fields.FloatField(description="Рассчитанные калории")
    calculated_protein = fields.FloatField(description="Рассчитанный белок (г)")
    calculated_fat = fields.FloatField(description="Рассчитанные жиры (г)")
    calculated_carbs = fields.FloatField(description="Рассчитанные углеводы (г)")

    created_at = fields.DatetimeField(auto_now_add=True, description="Дата создания")

    class Meta:
        table = "recipes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recipe {self.id}"

    @property
    def kbzhu_formatted(self) -> str:
        """Форматированное КБЖУ"""
        return (
            f"Калории: {self.calculated_calories:.0f} ккал\n"
            f"Белки: {self.calculated_protein:.1f} г\n"
            f"Жиры: {self.calculated_fat:.1f} г\n"
            f"Углеводы: {self.calculated_carbs:.1f} г"
        )


# --- Конфигурация Tortoise ORM для Aerich ---
TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://db.sqlite3?charset=utf8"  # Явно указываем UTF-8 для поддержки Unicode
    },
    "apps": {
        "models": {
            "models": ["bot.core.models"],
            "default_connection": "default",
        },
    },
}


# --- Вспомогательные функции инициализации БД ---
async def init_db(db_url: str):
    """Инициализация подключения к базе"""
    await Tortoise.init(db_url=db_url, modules={"models": ["bot.core.models"]})
    await Tortoise.generate_schemas()


async def close_db():
    """Закрытие подключения к базе"""
    await Tortoise.close_connections()
