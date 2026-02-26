# Квалиас — Flask версия

Система тестирования студентов на Flask + PostgreSQL.

## Структура проекта

```
flask_quiz/
├── app.py              ← весь бэкенд (маршруты, модели, логика)
├── requirements.txt
├── .env.example
└── templates/
    ├── base.html
    ├── login.html / register.html
    ├── home.html
    ├── quiz_detail.html
    ├── take_quiz.html
    ├── quiz_result.html
    ├── my_results.html
    ├── teacher_dashboard.html
    ├── edit_quiz.html
    ├── quiz_form.html
    ├── question_form.html
    ├── quiz_stats.html
    ├── subjects.html / subject_form.html
    └── error.html
```

## Установка

### 1. Создать виртуальное окружение

```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Создать базу данных PostgreSQL

```sql
CREATE DATABASE quiz_db;
```

### 3. Настроить .env

```bash
cp .env.example .env
```

Открыть `.env` и заполнить:
```
SECRET_KEY=придумайте-секретный-ключ
DATABASE_URL=postgresql://postgres:ваш_пароль@localhost:5432/quiz_db
```

### 4. Создать таблицы в БД

```bash
flask init-db
```

### 5. Создать аккаунт преподавателя

```bash
flask create-teacher
```

Введите логин, email, имя и пароль. Этот пользователь будет преподавателем.

### 6. Запустить сервер

```bash
flask run
```

Открыть: **http://127.0.0.1:5000**

---

## Роли

| Роль | Как создать | Возможности |
|------|-------------|-------------|
| **Студент** | Регистрация через сайт `/register` | Проходить тесты, смотреть результаты |
| **Преподаватель** | Команда `flask create-teacher` | Создавать тесты, вопросы, смотреть статистику |

---

## Функционал

**Студент:**
- Регистрация / авторизация
- Список доступных тестов с информацией (предмет, кол-во вопросов, время)
- Прохождение теста с таймером
- Автоматическая проверка ответов
- Подробный разбор с правильными ответами и объяснениями
- История всех попыток и личная статистика

**Преподаватель:**
- Управление предметами (категории)
- Создание и редактирование тестов
- Добавление вопросов: один правильный / несколько правильных
- Статистика по тесту: кто сдал, средний балл, каждая попытка

## Команды Flask CLI

```bash
flask init-db          # Создать таблицы
flask create-teacher   # Создать преподавателя
flask run              # Запустить dev-сервер
flask run --debug      # С автоперезагрузкой
```
