import pytest
from app import app, db, User, Quiz, Subject, Question, Answer
from datetime import datetime, timezone


@pytest.fixture(scope='function')
def test_app():
    """Создание Flask приложения для тестирования с in-memory SQLite БД"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key-for-testing'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(test_app):
    """Тестовый клиент Flask"""
    return test_app.test_client()


@pytest.fixture(scope='function')
def db_session(test_app):
    """Сессия БД для доступа в тестах"""
    with test_app.app_context():
        yield db


@pytest.fixture(scope='function')
def student_user(test_app):
    """Создание тестового студента"""
    with test_app.app_context():
        user = User(
            username='student1',
            email='student1@test.com',
            first_name='Иван',
            last_name='Сидоров',
            is_teacher=False
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()  # ✅ commit чтобы сохранить в БД
        # Получить ID после commit
        user_id = user.id
        yield user  # ✅ Используем yield, но объект все еще имеет ID


@pytest.fixture(scope='function')
def student_user2(test_app):
    """Создание второго тестового студента"""
    with test_app.app_context():
        user = User(
            username='student2',
            email='student2@test.com',
            first_name='Пётр',
            last_name='Петров',
            is_teacher=False
        )
        user.set_password('password456')
        db.session.add(user)
        db.session.commit()  # ✅ commit чтобы сохранить в БД
        yield user  # ✅ Используем yield


@pytest.fixture(scope='function')
def teacher_user(test_app):
    """Создание тестового преподавателя"""
    with test_app.app_context():
        user = User(
            username='teacher1',
            email='teacher1@test.com',
            first_name='Анна',
            last_name='Иванова',
            is_teacher=True
        )
        user.set_password('teacher123')
        db.session.add(user)
        db.session.commit()  # ✅ commit чтобы сохранить в БД
        yield user  # ✅ Используем yield


@pytest.fixture(scope='function')
def subject(test_app):
    """Создание тестового предмета"""
    with test_app.app_context():
        subj = Subject(
            name='Математика',
            description='Тесты по математике'
        )
        db.session.add(subj)
        db.session.commit()  # ✅ commit чтобы сохранить в БД
        yield subj  # ✅ Используем yield


@pytest.fixture(scope='function')
def quiz_single(test_app, teacher_user):
    """Создание теста с вопросом type='single'"""
    with test_app.app_context():
        # ✅ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Используем ID teacher_user внутри контекста
        teacher_id = teacher_user.id
        
        # ✅ Subject создаётся в ОДНОМ контексте с Quiz
        subject = Subject(
            name='Математика',
            description='Тесты по математике'
        )
        db.session.add(subject)
        db.session.flush()
        
        quiz = Quiz(
            title='Тест Математика',
            description='Простой тест',
            time_limit=30,
            passing_score=60,
            is_active=True,
            subject_id=subject.id,  # ✅ Subject в той же сессии!
            author_id=teacher_id  # ✅ Используем ID teacher_user!
        )
        db.session.add(quiz)
        db.session.flush()
        
        # Добавить вопрос
        question = Question(
            text='Сколько будет 2 + 2?',
            question_type='single',
            order=1,
            explanation='Это базовая арифметика',
            quiz_id=quiz.id
        )
        db.session.add(question)
        db.session.flush()
        
        # Добавить ответы
        answer1 = Answer(text='3', is_correct=False, order=1, question_id=question.id)
        answer2 = Answer(text='4', is_correct=True, order=2, question_id=question.id)
        answer3 = Answer(text='5', is_correct=False, order=3, question_id=question.id)
        db.session.add_all([answer1, answer2, answer3])
        db.session.commit()  # ✅ commit чтобы сохранить все в БД
        
        yield quiz


@pytest.fixture(scope='function')
def quiz_multiple(test_app, teacher_user):
    """Создание теста с вопросом type='multiple'"""
    with test_app.app_context():
        # ✅ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Используем ID teacher_user внутри контекста
        teacher_id = teacher_user.id
        
        # ✅ Subject создаётся в ОДНОМ контексте с Quiz
        subject = Subject(
            name='Чётные числа',
            description='Выбор нескольких вариантов'
        )
        db.session.add(subject)
        db.session.flush()
        
        quiz = Quiz(
            title='Тест Чётные числа',
            description='Выбор нескольких вариантов',
            time_limit=20,
            passing_score=70,
            is_active=True,
            subject_id=subject.id,  # ✅ Subject в той же сессии!
            author_id=teacher_id  # ✅ Используем ID teacher_user!
        )
        db.session.add(quiz)
        db.session.flush()
        
        # Добавить вопрос
        question = Question(
            text='Выберите все чётные числа из списка: 2, 3, 4, 5, 6',
            question_type='multiple',
            order=1,
            explanation='Чётные числа делятся на 2 нацело',
            quiz_id=quiz.id
        )
        db.session.add(question)
        db.session.flush()
        
        # Добавить ответы
        answer1 = Answer(text='2', is_correct=True, order=1, question_id=question.id)
        answer2 = Answer(text='3', is_correct=False, order=2, question_id=question.id)
        answer3 = Answer(text='4', is_correct=True, order=3, question_id=question.id)
        answer4 = Answer(text='5', is_correct=False, order=4, question_id=question.id)
        answer5 = Answer(text='6', is_correct=True, order=5, question_id=question.id)
        db.session.add_all([answer1, answer2, answer3, answer4, answer5])
        db.session.commit()  # ✅ commit чтобы сохранить все в БД
        
        yield quiz


@pytest.fixture(scope='function')
def quiz_inactive(test_app, teacher_user):
    """Создание неактивного теста"""
    with test_app.app_context():
        # ✅ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Используем ID teacher_user внутри контекста
        teacher_id = teacher_user.id
        
        # ✅ Subject создаётся в ОДНОМ контексте с Quiz
        subject = Subject(
            name='Скрытый предмет',
            description='Неактивный тест'
        )
        db.session.add(subject)
        db.session.flush()
        
        quiz = Quiz(
            title='Тест скрытый',
            description='Неактивный тест',
            time_limit=0,
            passing_score=50,
            is_active=False,
            subject_id=subject.id,  # ✅ Subject в той же сессии!
            author_id=teacher_id  # ✅ Используем ID teacher_user!
        )
        db.session.add(quiz)
        db.session.commit()  # ✅ commit чтобы сохранить в БД
        
        yield quiz
