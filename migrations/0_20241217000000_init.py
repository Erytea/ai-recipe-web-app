"""
Initial migration for AI Recipe Bot
"""
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
            "id" CHAR(36) NOT NULL PRIMARY KEY,
            "email" VARCHAR(255) NOT NULL UNIQUE,
            "password_hash" VARCHAR(255) NOT NULL,
            "username" VARCHAR(255),
            "first_name" VARCHAR(255),
            "last_name" VARCHAR(255),
            "is_active" INT NOT NULL DEFAULT 1,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS "recipe_base" (
            "id" CHAR(36) NOT NULL PRIMARY KEY,
            "title" VARCHAR(500) NOT NULL,
            "tags" TEXT,
            "cooking_time" VARCHAR(100),
            "difficulty" VARCHAR(50),
            "calories_per_100g" REAL NOT NULL,
            "protein_per_100g" REAL NOT NULL,
            "fat_per_100g" REAL NOT NULL,
            "carbs_per_100g" REAL NOT NULL,
            "ingredients" TEXT NOT NULL,
            "instructions" TEXT NOT NULL,
            "notes" TEXT,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS "recipes" (
            "id" CHAR(36) NOT NULL PRIMARY KEY,
            "user_id" CHAR(36) NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
            "photo_file_id" VARCHAR(500) NOT NULL,
            "ingredients_detected" TEXT NOT NULL,
            "clarifications" TEXT,
            "target_calories" INT NOT NULL,
            "target_protein" REAL NOT NULL,
            "target_fat" REAL NOT NULL,
            "target_carbs" REAL NOT NULL,
            "greens_weight" REAL NOT NULL,
            "recipe_text" TEXT NOT NULL,
            "calculated_calories" REAL NOT NULL,
            "calculated_protein" REAL NOT NULL,
            "calculated_fat" REAL NOT NULL,
            "calculated_carbs" REAL NOT NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS "meal_plans" (
            "id" CHAR(36) NOT NULL PRIMARY KEY,
            "user_id" CHAR(36) NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
            "photo_file_id" VARCHAR(500) NOT NULL,
            "ingredients_detected" TEXT NOT NULL,
            "clarifications" TEXT,
            "meals_count" INT NOT NULL,
            "target_daily_calories" INT NOT NULL,
            "target_daily_protein" REAL NOT NULL,
            "target_daily_fat" REAL NOT NULL,
            "target_daily_carbs" REAL NOT NULL,
            "daily_greens_weight" REAL NOT NULL,
            "meal_plan_text" TEXT NOT NULL,
            "calculated_daily_calories" REAL NOT NULL,
            "calculated_daily_protein" REAL NOT NULL,
            "calculated_daily_fat" REAL NOT NULL,
            "calculated_daily_carbs" REAL NOT NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS "aerich" (
            "version" VARCHAR(255) NOT NULL,
            "app" VARCHAR(100) NOT NULL,
            "content" JSON NOT NULL
        );
        CREATE INDEX IF NOT EXISTS "idx_users_email_8d1b" ON "users" ("email");
        CREATE INDEX IF NOT EXISTS "idx_users_username_6e3b" ON "users" ("username");
        CREATE INDEX IF NOT EXISTS "idx_recipe_base_created_6d2d" ON "recipe_base" ("created_at");
        CREATE INDEX IF NOT EXISTS "idx_recipes_user_id_3b0d" ON "recipes" ("user_id");
        CREATE INDEX IF NOT EXISTS "idx_recipes_created_a_9d9d" ON "recipes" ("created_at");
        CREATE INDEX IF NOT EXISTS "idx_meal_plans_user__7b7d" ON "meal_plans" ("user_id");
        CREATE INDEX IF NOT EXISTS "idx_meal_plans_created_8d7d" ON "meal_plans" ("created_at");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "meal_plans";
        DROP TABLE IF EXISTS "recipes";
        DROP TABLE IF EXISTS "recipe_base";
        DROP TABLE IF EXISTS "users";
        DROP TABLE IF EXISTS "aerich";
    """
