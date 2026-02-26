# Тесты для приложения КВАЛИАС

## Описание

Набор автоматических тестов для Flask-приложения КВАЛИАС с использованием **pytest**.

Тесты покрывают следующие функции:
- Аутентификация (регистрация, вход, выход)
- Контроль доступа (роли, права)
- Функциональность студента (просмотр тестов, прохождение, результаты)
- Функциональность преподавателя (создание тестов, вопросов, статистика)
- Граничные случаи и валидация

## Установка зависимостей

```bash
pip install pytest pytest-flask
```

Или установите все зависимости:

```bash
pip install -r requirements.txt
```

## Запуск тестов

### Запустить все тесты

```bash
pytest
```

### Запустить с подробным выводом

```bash
pytest -v
```

### Запустить только тесты аутентификации

```bash
pytest tests/test_app.py::TestAuthentication -v
```

### Запустить только тесты студента

```bash
pytest tests/test_app.py::TestStudentFunctionality -v
```

### Запустить только тесты преподавателя

```bash
pytest tests/test_app.py::TestTeacherFunctionality -v
```

### Показать покрытие кода

```bash
pip install pytest-cov
pytest --cov=app tests/
```

## Структура тестов

```
tests/
├── conftest.py          # Fixtures для всех тестов
├── test_app.py          # Основной файл с тестами
└── __init__.py          # Инициализация пакета
```

### conftest.py

Содержит fixtures для создания:
- **test_app** — Flask приложение с in-memory SQLite БД
- **client** — тестовый HTTP клиент
- **db_session** — сессия для доступа к БД
- **student_user** — тестовый студент
- **student_user2** — второй тестовый студент
- **teacher_user** — тестовый преподаватель
- **subject** — тестовый предмет
- **quiz_single** — тест с вопросом single-choice
- **quiz_multiple** — тест с вопросом multiple-choice
- **quiz_inactive** — неактивный тест

### test_app.py

Содержит 25+ тестов, распределённых по классам:

1. **TestAuthentication** (8 тестов)
   - Регистрация (успешная, ошибки)
   - Вход (успешный, ошибочный)
   - Выход

2. **TestAccessControl** (5 тестов)
   - Проверка 403 для студентов на /teacher
   - Редирект на /login для неавторизованных
   - Проверка прав на редактирование

3. **TestStudentFunctionality** (9 тестов)
   - Просмотр тестов
   - Прохождение тестов
   - Подсчёт баллов (100%, 0%, частичное)
   - История результатов

4. **TestTeacherFunctionality** (6 тестов)
   - Создание тестов
   - Создаление вопросов (single, multiple)
   - Удаление каскадно
   - Статистика
   - Управление предметами

5. **TestEdgeCases** (3 теста)
   - Пустая форма
   - Показ предыдущих попыток
   - Хеширование паролей

## Базы данных для тестирования

Все тесты используют **in-memory SQLite** БД для скорости и независимости:
- Не требуется PostgreSQL для тестов
- Каждый тест получает свежую БД
- Автоматический rollback после каждого теста

## Особенности

✅ **Полная независимость** — тесты не влияют на production БД
✅ **Fixtures для переиспользования** — максимум code reuse
✅ **Русские комментарии** — понятное описание каждого теста
✅ **Быстрое выполнение** — in-memory SQLite вместо PostgreSQL
✅ **Подробный вывод** — легко найти причину ошибки

## Примеры запуска

### Запустить один конкретный тест

```bash
pytest tests/test_app.py::TestAuthentication::test_register_successful -v
```

### Запустить тесты, содержащие слово "quiz"

```bash
pytest tests/test_app.py -k quiz -v
```

### Запустить с выводом print() результатов

```bash
pytest -s
```

### Запустить с остановкой на первой ошибке

```bash
pytest -x
```

## Написание новых тестов

Пример структуры нового теста:

```python
def test_something_important(self, client, student_user):
    """Описание что тестируется"""
    # Логирование
    client.post('/login', data={
        'username': 'student1',
        'password': 'password123'
    })
    
    # Действие
    response = client.get('/some-page')
    
    # Проверка
    assert response.status_code == 200
    assert b'ожидаемый текст' in response.data
```

## Troubleshooting

### Ошибка: "ModuleNotFoundError: No module named 'pytest'"

Установите pytest:
```bash
pip install pytest pytest-flask
```

### Ошибка: "ImportError: cannot import name 'app'"

Убедитесь что запускаете тесты из корневой папки проекта:
```bash
cd c:\flask_quiz
pytest
```

### Ошибка: "FAILED tests/test_app.py::TestAuthentication::test_register_successful - sqlalchemy.exc.OperationalError"

Проверьте что app.py корректно импортируется, и conftest.py находится в папке tests/.

## Отчётность и метрики

Для получения отчёта о покрытии кода:

```bash
pip install pytest-cov
pytest --cov=. --cov-report=html tests/
```

Это создаст папку `htmlcov/` с детальным HTML отчётом.

## License

Тесты являются частью проекта КВАЛИАС и используют ту же лицензию.
