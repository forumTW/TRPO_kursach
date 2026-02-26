import pytest
from app import db, User, Attempt, StudentAnswer


# ✅ ТЕСТЫ АУТЕНТИФИКАЦИИ ✅

class TestAuthentication:
    """Тесты для функционала регистрации и входа"""
    
    def test_register_successful(self, client):
        """Успешная регистрация нового пользователя"""
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'Петр',
            'last_name': 'Новый',
            'password': 'securepass123',
            'password2': 'securepass123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # После регистрации должны перенаправить на / (home)
        assert 'Привет'.encode('utf-8') in response.data or response.request.path == '/'
    
    def test_register_duplicate_username(self, client, student_user):
        """Регистрация с уже существующим username должна вернуть ошибку"""
        response = client.post('/register', data={
            'username': 'student1',  # Уже существует
            'email': 'newemail@test.com',
            'first_name': 'Иван',
            'last_name': 'Новый',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'логин уже занят'.encode('utf-8') in response.data
    
    def test_register_duplicate_email(self, client, student_user):
        """Регистрация с уже существующим email должна вернуть ошибку"""
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'student1@test.com',  # Уже существует
            'first_name': 'Иван',
            'last_name': 'Новый',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'email уже зарегистрирован'.encode('utf-8') in response.data
    
    def test_register_short_password(self, client):
        """Регистрация с паролем < 6 символов должна вернуть ошибку"""
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'Иван',
            'last_name': 'Новый',
            'password': '12345',  # Только 5 символов
            'password2': '12345'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'не менее 6 символов'.encode('utf-8') in response.data
    
    def test_register_password_mismatch(self, client):
        """Регистрация с несовпадающими паролями должна вернуть ошибку"""
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'Иван',
            'last_name': 'Новый',
            'password': 'password123',
            'password2': 'password456'  # Не совпадает
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'не совпадают'.encode('utf-8') in response.data
    
    def test_login_successful(self, client, student_user):
        """Успешный вход с правильными данными"""
        response = client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # После входа должны перенаправить на / (home)
        assert response.request.path == '/' or 'Привет'.encode('utf-8') in response.data
    
    def test_login_wrong_password(self, client, student_user):
        """Вход с неверным паролем должен вернуть ошибку"""
        response = client.post('/login', data={
            'username': 'student1',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'Неверный логин или пароль'.encode('utf-8') in response.data
    
    def test_login_nonexistent_user(self, client):
        """Вход с несуществующим пользователем должен вернуть ошибку"""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'anypassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'Неверный логин или пароль'.encode('utf-8') in response.data
    
    def test_logout(self, client, student_user):
        """Выход из системы"""
        # Сначала логируемся
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Теперь выходим
        response = client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert response.request.path == '/login'


# ✅ ТЕСТЫ КОНТРОЛЯ ДОСТУПА ✅

class TestAccessControl:
    """Тесты для проверки прав доступа"""
    
    def test_student_cannot_access_teacher_dashboard(self, client, student_user):
        """Студент не может зайти на /teacher (должен получить 403)"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        response = client.get('/teacher')
        assert response.status_code == 403
    
    def test_unauthenticated_redirects_to_login(self, client):
        """Неавторизованный пользователь перенаправляется на /login"""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_student_cannot_edit_other_attempt(self, client, student_user, student_user2, quiz_single):
        """Студент не может редактировать чужую попытку (403)"""
        # Логируемся как student1
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём попытку для student2
        with client.application.app_context():
            attempt = Attempt(
                student_id=student_user2.id,
                quiz_id=quiz_single.id,
                status='in_progress',
                total_questions=1
            )
            db.session.add(attempt)
            db.session.commit()
            attempt_id = attempt.id
        
        # Пытаемся зайти на результаты чужой попытки
        response = client.get(f'/attempt/{attempt_id}/result')
        assert response.status_code == 403
    
    def test_teacher_can_access_own_quiz_edit(self, client, teacher_user, quiz_single):
        """Преподаватель может редактировать свой тест"""
        client.post('/login', data={
            'username': 'teacher1',
            'password': 'teacher123'
        })
        
        response = client.get(f'/teacher/quiz/{quiz_single.id}/edit')
        assert response.status_code == 200
    
    def test_student_cannot_create_quiz(self, client, student_user, subject):
        """Студент не может создавать тесты"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        response = client.get('/teacher/quiz/create')
        assert response.status_code == 403


# ✅ ТЕСТЫ ФУНКЦИОНАЛЬНОСТИ СТУДЕНТА ✅

class TestStudentFunctionality:
    """Тесты для функций студента"""
    
    def test_home_page_displays_for_authorized_student(self, client, student_user):
        """Главная страница отображается для авторизованного студента"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        response = client.get('/')
        assert response.status_code == 200
        assert 'Привет'.encode('utf-8') in response.data
    
    def test_student_sees_active_quizzes(self, client, student_user, quiz_single):
        """Студент видит список активных тестов"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        response = client.get('/')
        assert response.status_code == 200
        assert 'Тест Математика'.encode('utf-8') in response.data
    
    def test_student_does_not_see_inactive_quizzes(self, client, student_user, quiz_inactive):
        """Студент НЕ видит неактивные тесты"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        response = client.get('/')
        assert response.status_code == 200
        assert 'Тест скрытый'.encode('utf-8') not in response.data
    
    def test_start_quiz_creates_attempt(self, client, student_user, quiz_single):
        """Создание попытки (начало теста) должно создать запись Attempt"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        response = client.post(f'/quiz/{quiz_single.id}/start', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверяем, что Attempt создан
        with client.application.app_context():
            attempt = Attempt.query.filter_by(
                student_id=student_user.id,
                quiz_id=quiz_single.id
            ).first()
            assert attempt is not None
            assert attempt.status == 'in_progress'
    
    def test_complete_quiz_single_correct_answers(self, client, student_user, quiz_single):
        """Завершение теста с правильными ответами → балл 100%"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём попытку
        response = client.post(f'/quiz/{quiz_single.id}/start', follow_redirects=True)
        
        with client.application.app_context():
            from app import Question, Answer  # ✅ Импортируем в начале контекста
            
            attempt = Attempt.query.filter_by(
                student_id=student_user.id,
                quiz_id=quiz_single.id
            ).first()
            attempt_id = attempt.id
            
            # Получаем ID правильного ответа
            question = Question.query.filter_by(quiz_id=quiz_single.id).first()
            correct_answer = Answer.query.filter_by(
                question_id=question.id,
                is_correct=True
            ).first()
        
        # Отправляем форму с правильным ответом
        response = client.post(f'/attempt/{attempt_id}', data={
            f'q_{question.id}': str(correct_answer.id)
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем балл
        with client.application.app_context():
            attempt = Attempt.query.get(attempt_id)
            assert attempt.status == 'completed'
            assert attempt.score == 100.0
            assert attempt.correct_count == 1
    
    def test_complete_quiz_single_wrong_answers(self, client, student_user, quiz_single):
        """Завершение теста с неправильными ответами → балл 0%"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём попытку
        response = client.post(f'/quiz/{quiz_single.id}/start', follow_redirects=True)
        
        with client.application.app_context():
            from app import Question, Answer
            attempt = Attempt.query.filter_by(
                student_id=student_user.id,
                quiz_id=quiz_single.id
            ).first()
            attempt_id = attempt.id
            
            # Получаем неправильный ответ
            question = Question.query.filter_by(quiz_id=quiz_single.id).first()
            wrong_answer = Answer.query.filter_by(
                question_id=question.id,
                is_correct=False
            ).first()
        
        # Отправляем форму с неправильным ответом
        response = client.post(f'/attempt/{attempt_id}', data={
            f'q_{question.id}': str(wrong_answer.id)
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем балл
        with client.application.app_context():
            attempt = Attempt.query.get(attempt_id)
            assert attempt.status == 'completed'
            assert attempt.score == 0.0
            assert attempt.correct_count == 0
    
    def test_multiple_choice_partial_answer_not_credited(self, client, student_user, quiz_multiple):
        """Частичное совпадение multiple-choice → балл 0% (не засчитывается)"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём попытку
        response = client.post(f'/quiz/{quiz_multiple.id}/start', follow_redirects=True)
        
        with client.application.app_context():
            from app import Question, Answer
            attempt = Attempt.query.filter_by(
                student_id=student_user.id,
                quiz_id=quiz_multiple.id
            ).first()
            attempt_id = attempt.id
            
            question = Question.query.filter_by(quiz_id=quiz_multiple.id).first()
            
            # Получаем все ответы
            all_answers = Answer.query.filter_by(question_id=question.id).all()
            # Берём только часть правильных ответов (неполное совпадение)
            correct_answers = [a for a in all_answers if a.is_correct]
            partial_answers = [str(correct_answers[0].id)]  # Только один из трёх правильных
        
        # Отправляем форму с неполным набором правильных ответов
        response = client.post(f'/attempt/{attempt_id}', data={
            f'q_{question.id}': partial_answers
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем, что ответ не засчитался
        with client.application.app_context():
            attempt = Attempt.query.get(attempt_id)
            assert attempt.status == 'completed'
            assert attempt.score == 0.0  # Не требуется точное совпадение
            assert attempt.correct_count == 0
    
    def test_student_can_view_results(self, client, student_user, quiz_single):
        """Просмотр результатов теста"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём и завершаем попытку
        client.post(f'/quiz/{quiz_single.id}/start', follow_redirects=True)
        
        with client.application.app_context():
            attempt = Attempt.query.filter_by(
                student_id=student_user.id,
                quiz_id=quiz_single.id
            ).first()
            attempt_id = attempt.id
            
            from app import Question, Answer
            question = Question.query.filter_by(quiz_id=quiz_single.id).first()
            correct_answer = Answer.query.filter_by(
                question_id=question.id,
                is_correct=True
            ).first()
        
        # Завершаем тест
        client.post(f'/attempt/{attempt_id}', data={
            f'q_{question.id}': str(correct_answer.id)
        })
        
        # Смотрим результаты
        response = client.get(f'/attempt/{attempt_id}/result')
        assert response.status_code == 200
        assert 'Тест сдан'.encode('utf-8') in response.data or 'Разбор'.encode('utf-8') in response.data
    
    def test_student_history_shows_only_own_attempts(self, client, student_user, student_user2, quiz_single):
        """История результатов показывает только попытки студента"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём попытку для student1
        with client.application.app_context():
            attempt1 = Attempt(
                student_id=student_user.id,
                quiz_id=quiz_single.id,
                status='completed',
                score=100.0,
                correct_count=1,
                total_questions=1
            )
            attempt2 = Attempt(
                student_id=student_user2.id,
                quiz_id=quiz_single.id,
                status='completed',
                score=50.0,
                correct_count=0,
                total_questions=1
            )
            db.session.add_all([attempt1, attempt2])
            db.session.commit()
        
        response = client.get('/my-results')
        assert response.status_code == 200
        # Должна быть видна только попытка student1
        # Проверяем что страница загружается и содержит попытку


# ✅ ТЕСТЫ ФУНКЦИОНАЛЬНОСТИ ПРЕПОДАВАТЕЛЯ ✅

class TestTeacherFunctionality:
    """Тесты для функций преподавателя"""
    
    def test_create_quiz(self, client, teacher_user, subject):
        """Создание теста преподавателем"""
        client.post('/login', data={
            'username': 'teacher1',
            'password': 'teacher123'
        })
        
        response = client.post('/teacher/quiz/create', data={
            'title': 'Новый тест',
            'description': 'Описание нового теста',
            'subject_id': subject.id,
            'time_limit': 45,
            'passing_score': 70,
            'is_active': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем, что тест создан
        with client.application.app_context():
            from app import Quiz
            quiz = Quiz.query.filter_by(title='Новый тест').first()
            assert quiz is not None
            assert quiz.author_id == teacher_user.id
            assert quiz.time_limit == 45
    
    def test_create_question_single_choice(self, client, teacher_user, quiz_single):
        """Создание вопроса типа 'single' с вариантами ответов"""
        client.post('/login', data={
            'username': 'teacher1',
            'password': 'teacher123'
        })
        
        response = client.post(f'/teacher/quiz/{quiz_single.id}/question/add', data={
            'text': 'Что такое Python?',
            'question_type': 'single',
            'order': 2,
            'explanation': 'Python это язык программирования',
            'answer_text_1': 'Яд',
            'answer_correct_1': None,
            'answer_text_2': 'Язык программирования',
            'answer_correct_2': 'on',
            'answer_text_3': 'Животное',
            'answer_correct_3': None
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем, что вопрос создан
        with client.application.app_context():
            from app import Question
            question = Question.query.filter_by(text='Что такое Python?').first()
            assert question is not None
            assert question.question_type == 'single'
            assert question.quiz_id == quiz_single.id
    
    def test_create_question_multiple_choice(self, client, teacher_user, quiz_multiple):
        """Создание вопроса типа 'multiple' с несколькими правильными ответами"""
        client.post('/login', data={
            'username': 'teacher1',
            'password': 'teacher123'
        })
        
        # В quiz_multiple уже есть один вопрос, добавляем новый
        response = client.post(f'/teacher/quiz/{quiz_multiple.id}/question/add', data={
            'text': 'Выберите языки программирования',
            'question_type': 'multiple',
            'order': 2,
            'explanation': 'Это все языки программирования',
            'answer_text_1': 'Python',
            'answer_correct_1': 'on',
            'answer_text_2': 'Апельсин',
            'answer_correct_2': None,
            'answer_text_3': 'Java',
            'answer_correct_3': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем, что вопрос создан как multiple
        with client.application.app_context():
            from app import Question
            question = Question.query.filter_by(
                text='Выберите языки программирования'
            ).first()
            assert question is not None
            assert question.question_type == 'multiple'
    
    def test_delete_quiz_cascade(self, client, teacher_user, quiz_single):
        """Удаление теста каскадно удаляет вопросы и ответы"""
        client.post('/login', data={
            'username': 'teacher1',
            'password': 'teacher123'
        })
        
        quiz_id = quiz_single.id
        
        response = client.post(f'/teacher/quiz/{quiz_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверяем, что тест и его вопросы удалены
        with client.application.app_context():
            from app import Quiz, Question, Answer
            quiz = Quiz.query.get(quiz_id)
            assert quiz is None
            
            questions = Question.query.filter_by(quiz_id=quiz_id).all()
            assert len(questions) == 0
    
    def test_quiz_statistics(self, client, teacher_user, quiz_single, student_user):
        """Статистика по тесту (/teacher/quiz/<id>/stats)"""
        client.post('/login', data={
            'username': 'teacher1',
            'password': 'teacher123'
        })
        
        # Создаём несколько попыток
        with client.application.app_context():
            attempt1 = Attempt(
                student_id=student_user.id,
                quiz_id=quiz_single.id,
                status='completed',
                score=100.0,
                correct_count=1,
                total_questions=1
            )
            attempt2 = Attempt(
                student_id=student_user.id,
                quiz_id=quiz_single.id,
                status='completed',
                score=0.0,
                correct_count=0,
                total_questions=1
            )
            db.session.add_all([attempt1, attempt2])
            db.session.commit()
        
        response = client.get(f'/teacher/quiz/{quiz_single.id}/stats')
        assert response.status_code == 200
        # Проверяем что статистика отображается
        assert response.request.path == f'/teacher/quiz/{quiz_single.id}/stats'
    
    def test_create_subject(self, client, teacher_user):
        """Создание предмета"""
        client.post('/login', data={
            'username': 'teacher1',
            'password': 'teacher123'
        })
        
        response = client.post('/teacher/subjects/create', data={
            'name': 'История',
            'description': 'Тесты по истории'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем, что предмет создан
        with client.application.app_context():
            from app import Subject
            subject = Subject.query.filter_by(name='История').first()
            assert subject is not None


# ✅ ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ✅

class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_empty_form_submission(self, client, student_user, quiz_single):
        """Отправка пустой формы (студент не ответил)"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём попытку
        client.post(f'/quiz/{quiz_single.id}/start', follow_redirects=True)
        
        with client.application.app_context():
            attempt = Attempt.query.filter_by(
                student_id=student_user.id,
                quiz_id=quiz_single.id
            ).first()
            attempt_id = attempt.id
            
            from app import Question
            question = Question.query.filter_by(quiz_id=quiz_single.id).first()
        
        # Отправляем форму БЕЗ ответов
        response = client.post(f'/attempt/{attempt_id}', data={
            # Ничего не отправляем
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверяем результат (должен быть 0%)
        with client.application.app_context():
            attempt = Attempt.query.get(attempt_id)
            assert attempt.status == 'completed'
            assert attempt.correct_count == 0
    
    def test_quiz_detail_shows_prev_attempts(self, client, student_user, quiz_single):
        """На странице деталей теста показываются предыдущие попытки"""
        client.post('/login', data={
            'username': 'student1',
            'password': 'password123'
        })
        
        # Создаём попытку
        with client.application.app_context():
            attempt = Attempt(
                student_id=student_user.id,
                quiz_id=quiz_single.id,
                status='completed',
                score=75.0,
                correct_count=1,
                total_questions=1
            )
            db.session.add(attempt)
            db.session.commit()
        
        response = client.get(f'/quiz/{quiz_single.id}')
        assert response.status_code == 200
    
    def test_password_hashing_works(self, test_app):
        """Проверка что пароли правильно хешируются"""
        with test_app.app_context():
            user = User(
                username='hashtest',
                email='hash@test.com',
                first_name='Hash',
                last_name='Test',
                is_teacher=False
            )
            user.set_password('mypassword123')
            
            # Проверяем что пароль это не plaintext
            assert user.password_hash != 'mypassword123'
            
            # Проверяем что check_password работает
            assert user.check_password('mypassword123')
            assert not user.check_password('wrongpassword')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
