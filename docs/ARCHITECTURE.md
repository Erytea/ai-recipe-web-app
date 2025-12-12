# Архитектура AI Recipe Web App

## Диаграмма зависимостей

```mermaid
graph TD
    %% --- Стили ---
    classDef entry fill:#f9f,stroke:#333,stroke-width:2px;
    classDef route fill:#bbf,stroke:#333,stroke-width:2px;
    classDef service fill:#dfd,stroke:#333,stroke-width:2px;
    classDef model fill:#fdd,stroke:#333,stroke-width:2px;
    classDef external fill:#eee,stroke:#333,stroke-dasharray: 5 5;

    %% --- Узлы ---

    subgraph "Entry Point"
        Main[main.py<br/>FastAPI App]:::entry
        Config[core/config.py<br/>Settings]:::entry
    end

    subgraph "External APIs"
        OpenAI_API(OpenAI API):::external
    end

    subgraph "Web Routes (Presentation)"
        R_Auth[auth.py<br/>Authentication]:::route
        R_Recipes[recipes.py<br/>Recipe Management]:::route
        R_MealPlans[meal_plans.py<br/>Meal Plans]:::route
        R_Main[main.py<br/>General Pages]:::route
    end

    subgraph "Services (Business Logic)"
        S_OpenAI[openai_service.py<br/>AI Image & Text Gen]:::service
        S_Search[recipe_search.py<br/>Recipe Search & Filter]:::service
        S_Parser[recipe_parser.py<br/>Recipe Parsing]:::service
        S_Nutrition[nutrition_database.py<br/>Nutrition Data]:::service
    end

    subgraph "Data Layer (Models & DB)"
        DB[(SQLite DB<br/>Tortoise ORM)]:::model
        M_User[Model: User<br/>Web Authentication]:::model
        M_Recipe[Model: Recipe<br/>User Generated]:::model
        M_MealPlan[Model: MealPlan]:::model
        M_RecipeBase[Model: RecipeBase<br/>Curated Database]:::model
    end

    %% --- Связи ---

    %% Инициализация
    Main -->|Load| Config
    Main -->|Init| DB

    %% Роутинг (подключение маршрутов)
    Main -->|Include Router| R_Auth
    Main -->|Include Router| R_Recipes
    Main -->|Include Router| R_MealPlans
    Main -->|Include Router| R_Main

    %% Логика маршрутов
    R_Auth -->|Auth/Save| M_User
    R_Recipes -->|Analyze/Gen| S_OpenAI
    R_Recipes -->|Get/Save| M_User
    R_Recipes -->|Save| M_Recipe
    R_MealPlans -->|Analyze/Gen| S_OpenAI
    R_MealPlans -->|Save| M_MealPlan

    %% Логика сервисов
    S_OpenAI -->|Request| OpenAI_API
    S_Search -->|Query| M_RecipeBase
    S_Parser -->|Parse| M_RecipeBase

    %% Связь моделей с БД
    M_User --- DB
    M_Recipe --- DB
    M_MealPlan --- DB
    M_RecipeBase --- DB
```

## Описание слоев

1.  **Entry Point (`main.py`)**
    *   Точка входа FastAPI приложения. Инициализирует базу данных, подключает маршруты, настраивает middleware.

2.  **Web Routes (`bot/web/routes/`)**
    *   `auth.py`: Аутентификация пользователей (регистрация, вход, JWT токены).
    *   `recipes.py`: Управление рецептами (создание, просмотр, загрузка фото).
    *   `meal_plans.py`: Рационы питания на день.
    *   `main.py`: Общие страницы (главная, профиль, о приложении).

3.  **Services (`bot/services/`)**
    *   `openai_service.py`: Вся логика работы с AI (распознавание фото продуктов, генерация рецептов).
    *   `recipe_search.py`: Логика поиска и фильтрации рецептов по базе данных.
    *   `recipe_parser.py`: Парсинг текстов рецептов.
    *   `nutrition_database.py`: Работа с базой данных продуктов и их nutritional value.

4.  **Models (`bot/core/models.py`)**
    *   `User`: Пользователи с email/password аутентификацией.
    *   `Recipe`: Персональные рецепты, созданные пользователями.
    *   `MealPlan`: Рационы питания на день.
    *   `RecipeBase`: Общая база проверенных рецептов.

