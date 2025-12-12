from tortoise import fields, Tortoise
from tortoise.models import Model
import uuid


class User(Model):
    """Модель пользователя веб-приложения"""

    id = fields.UUIDField(pk=True, default=uuid.uuid4, description="Уникальный ID пользователя")

    # Аутентификация
    email = fields.CharField(max_length=255, unique=True, description="Email пользователя")
    password_hash = fields.CharField(max_length=255, description="Хэш пароля")

    # Профиль
    username = fields.CharField(
        max_length=255, null=True, unique=True, description="Username пользователя"
    )
    first_name = fields.CharField(
        max_length=255, null=True, description="Имя пользователя"
    )
    last_name = fields.CharField(
        max_length=255, null=True, description="Фамилия пользователя"
    )

    # Мета
    is_active = fields.BooleanField(default=True, description="Активен ли аккаунт")
    created_at = fields.DatetimeField(auto_now_add=True, description="Дата регистрации")
    updated_at = fields.DatetimeField(auto_now=True, description="Дата последнего обновления")

    class Meta:
        table = "users"

    def __str__(self):
        return f"User {self.email} ({self.username or self.first_name})"


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
    user = fields.ForeignKeyField(
        "models.User", related_name="recipes", on_delete=fields.CASCADE,
        to_field="id", description="Пользователь, создавший рецепт"
    )

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
        return f"Recipe {self.id} for user {self.user_id}"

    @property
    def kbzhu_formatted(self) -> str:
        """Форматированное КБЖУ"""
        return (
            f"Калории: {self.calculated_calories:.0f} ккал\n"
            f"Белки: {self.calculated_protein:.1f} г\n"
            f"Жиры: {self.calculated_fat:.1f} г\n"
            f"Углеводы: {self.calculated_carbs:.1f} г"
        )


class MealPlan(Model):
    """Модель рациона на день"""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user = fields.ForeignKeyField(
        "models.User", related_name="meal_plans", on_delete=fields.CASCADE,
        to_field="id", description="Пользователь, создавший рацион"
    )

    # Исходные данные
    photo_file_id = fields.CharField(max_length=500, description="Путь к файлу фото")
    ingredients_detected = fields.TextField(description="Обнаруженные ингредиенты")
    clarifications = fields.TextField(null=True, description="Уточнения пользователя")

    # Параметры рациона
    meals_count = fields.IntField(description="Количество приемов пищи")
    target_daily_calories = fields.IntField(description="Желаемые калории за день")
    target_daily_protein = fields.FloatField(description="Желаемый белок за день (г)")
    target_daily_fat = fields.FloatField(description="Желаемые жиры за день (г)")
    target_daily_carbs = fields.FloatField(description="Желаемые углеводы за день (г)")
    daily_greens_weight = fields.FloatField(
        description="Количество растительности за день (г)"
    )

    # Результат
    meal_plan_text = fields.TextField(description="Текст рациона")
    calculated_daily_calories = fields.FloatField(
        description="Рассчитанные калории за день"
    )
    calculated_daily_protein = fields.FloatField(
        description="Рассчитанный белок за день (г)"
    )
    calculated_daily_fat = fields.FloatField(
        description="Рассчитанные жиры за день (г)"
    )
    calculated_daily_carbs = fields.FloatField(
        description="Рассчитанные углеводы за день (г)"
    )

    created_at = fields.DatetimeField(auto_now_add=True, description="Дата создания")

    class Meta:
        table = "meal_plans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"MealPlan {self.id} for user {self.user_id}"

    @property
    def kbzhu_formatted(self) -> str:
        """Форматированное КБЖУ за день"""
        return (
            f"Калории за день: {self.calculated_daily_calories:.0f} ккал\n"
            f"Белки: {self.calculated_daily_protein:.1f} г\n"
            f"Жиры: {self.calculated_daily_fat:.1f} г\n"
            f"Углеводы: {self.calculated_daily_carbs:.1f} г"
        )


# --- Вспомогательные функции инициализации БД ---
async def init_db(db_url: str):
    """Инициализация подключения к базе"""
    await Tortoise.init(db_url=db_url, modules={"models": ["bot.core.models"]})
    await Tortoise.generate_schemas()


async def close_db():
    """Закрытие подключения к базе"""
    await Tortoise.close_connections()
