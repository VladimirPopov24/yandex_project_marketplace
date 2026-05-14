--
-- Файл сгенерирован с помощью SQLiteStudio v3.4.21 в Пн апр 20 18:45:36 2026
--
-- Использованная кодировка текста: UTF-8
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Таблица: cart
CREATE TABLE IF NOT EXISTS cart (user_id INTEGER PRIMARY KEY NOT NULL);

-- Таблица: category
CREATE TABLE IF NOT EXISTS category (id_category INTEGER PRIMARY KEY UNIQUE NOT NULL, category TEXT NOT NULL UNIQUE, parent_id INTEGER);

-- Таблица: log
CREATE TABLE IF NOT EXISTS log (log_id INTEGER PRIMARY KEY UNIQUE NOT NULL, msg INTEGER NOT NULL, time INTEGER NOT NULL);

-- Таблица: order
CREATE TABLE IF NOT EXISTS "order" (order_id PRIMARY KEY NOT NULL UNIQUE, status TEXT NOT NULL, cart_id NOT NULL);

-- Таблица: product
CREATE TABLE IF NOT EXISTS product (id_product INTEGER PRIMARY KEY UNIQUE NOT NULL, price INTEGER NOT NULL, name TEXT NOT NULL, description, id_seller INTEGER, category TEXT, img_id);

-- Таблица: reviews
CREATE TABLE IF NOT EXISTS reviews (review_id PRIMARY KEY NOT NULL UNIQUE, product_id, review5 INTEGER NOT NULL, review_text TEXT);

-- Таблица: users
CREATE TABLE IF NOT EXISTS users (id PRIMARY KEY UNIQUE NOT NULL, pass_hash TEXT NOT NULL, login UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, telephone INTEGER UNIQUE NOT NULL, is_seller Bool NOT NULL, address TEXT, name TEXT NOT NULL);

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
