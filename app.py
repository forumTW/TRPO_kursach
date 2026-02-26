import os
from datetime import datetime, timezone
from dotenv import load_dotenv

from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

# ─── App & Config ─────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/quiz_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите, чтобы продолжить.'
login_manager.login_message_category = 'warning'


# ─── Models ───────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    first_name    = db.Column(db.String(50), nullable=False, default='')
    last_name     = db.Column(db.String(50), nullable=False, default='')
    password_hash = db.Column(db.String(256), nullable=False)
    is_teacher    = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    attempts = db.relationship('Attempt', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    quizzes  = db.relationship('Quiz', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.username

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper() or self.username[:2].upper()


class Subject(db.Model):
    __tablename__ = 'subjects'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    quizzes     = db.relationship('Quiz', backref='subject', lazy='dynamic', cascade='all, delete-orphan')


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(255), nullable=False)
    description   = db.Column(db.Text, default='')
    time_limit    = db.Column(db.Integer, default=0)   # minutes, 0 = no limit
    passing_score = db.Column(db.Integer, default=60)  # percent
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    subject_id    = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    author_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    questions = db.relationship('Question', backref='quiz', lazy='dynamic',
                                cascade='all, delete-orphan', order_by='Question.order')
    attempts  = db.relationship('Attempt', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def question_count(self):
        return self.questions.count()


class Question(db.Model):
    __tablename__ = 'questions'
    id              = db.Column(db.Integer, primary_key=True)
    text            = db.Column(db.Text, nullable=False)
    question_type   = db.Column(db.String(10), default='single')  # 'single' | 'multiple'
    order           = db.Column(db.Integer, default=0)
    explanation     = db.Column(db.Text, default='')
    quiz_id         = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)

    answers = db.relationship('Answer', backref='question', lazy='select',
                              cascade='all, delete-orphan', order_by='Answer.order')

    @property
    def correct_answers(self):
        return [a for a in self.answers if a.is_correct]


class Answer(db.Model):
    __tablename__ = 'answers'
    id         = db.Column(db.Integer, primary_key=True)
    text       = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order      = db.Column(db.Integer, default=0)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)


# Many-to-many: student_answer <-> answer
student_answer_choices = db.Table('student_answer_choices',
    db.Column('student_answer_id', db.Integer, db.ForeignKey('student_answers.id'), primary_key=True),
    db.Column('answer_id', db.Integer, db.ForeignKey('answers.id'), primary_key=True)
)


class Attempt(db.Model):
    __tablename__ = 'attempts'
    id              = db.Column(db.Integer, primary_key=True)
    score           = db.Column(db.Float, default=0)
    correct_count   = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    status          = db.Column(db.String(15), default='in_progress')  # in_progress | completed
    started_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at     = db.Column(db.DateTime, nullable=True)
    student_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id         = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)

    student_answers = db.relationship('StudentAnswer', backref='attempt',
                                      lazy='select', cascade='all, delete-orphan')

    @property
    def is_passed(self):
        return self.score >= self.quiz.passing_score

    @property
    def duration(self):
        if self.finished_at:
            delta = self.finished_at - self.started_at
            m, s = divmod(int(delta.total_seconds()), 60)
            return f'{m} мин {s} сек'
        return '—'


class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'
    id          = db.Column(db.Integer, primary_key=True)
    is_correct  = db.Column(db.Boolean, default=False)
    attempt_id  = db.Column(db.Integer, db.ForeignKey('attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)

    question         = db.relationship('Question')
    selected_answers = db.relationship('Answer', secondary=student_answer_choices)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def teacher_required(f):
    """Decorator: only teachers can access this route."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username   = request.form.get('username', '').strip()
        email      = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        password   = request.form.get('password', '')
        password2  = request.form.get('password2', '')

        errors = []
        if not username: errors.append('Введите имя пользователя.')
        if not email: errors.append('Введите email.')
        if not first_name: errors.append('Введите имя.')
        if len(password) < 6: errors.append('Пароль должен быть не менее 6 символов.')
        if password != password2: errors.append('Пароли не совпадают.')
        if User.query.filter_by(username=username).first(): errors.append('Такой логин уже занят.')
        if User.query.filter_by(email=email).first(): errors.append('Такой email уже зарегистрирован.')

        if errors:
            for e in errors:
                flash(e, 'error')
        else:
            user = User(username=username, email=email,
                        first_name=first_name, last_name=last_name)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(f'Добро пожаловать, {user.first_name}!', 'success')
            return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Неверный логин или пароль.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ─── Student Routes ───────────────────────────────────────────────────────────

@app.route('/')
@login_required
def home():
    if current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))

    quizzes = Quiz.query.filter_by(is_active=True).join(Subject).order_by(Quiz.created_at.desc()).all()
    recent  = Attempt.query.filter_by(student_id=current_user.id)\
                           .order_by(Attempt.started_at.desc()).limit(5).all()

    completed = Attempt.query.filter_by(student_id=current_user.id, status='completed').all()
    stats = {
        'total': len(completed),
        'avg_score': round(sum(a.score for a in completed) / len(completed), 1) if completed else 0,
        'passed': sum(1 for a in completed if a.is_passed),
    }
    return render_template('home.html', quizzes=quizzes, recent=recent, stats=stats)


@app.route('/quiz/<int:quiz_id>')
@login_required
def quiz_detail(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.is_active and not current_user.is_teacher:
        abort(403)
    prev = Attempt.query.filter_by(student_id=current_user.id, quiz_id=quiz_id)\
                        .order_by(Attempt.started_at.desc()).all()
    return render_template('quiz_detail.html', quiz=quiz, prev_attempts=prev)


@app.route('/quiz/<int:quiz_id>/start', methods=['POST'])
@login_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.question_count == 0:
        flash('В этом тесте пока нет вопросов.', 'warning')
        return redirect(url_for('quiz_detail', quiz_id=quiz_id))

    attempt = Attempt(student_id=current_user.id, quiz_id=quiz_id,
                      total_questions=quiz.question_count)
    db.session.add(attempt)
    db.session.commit()
    return redirect(url_for('take_quiz', attempt_id=attempt.id))


@app.route('/attempt/<int:attempt_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(attempt_id):
    attempt = Attempt.query.get_or_404(attempt_id)
    if attempt.student_id != current_user.id:
        abort(403)
    if attempt.status != 'in_progress':
        return redirect(url_for('quiz_result', attempt_id=attempt_id))

    quiz      = attempt.quiz
    questions = quiz.questions.order_by(Question.order).all()

    # Check timer
    remaining = None
    if quiz.time_limit > 0:
        elapsed   = (datetime.now(timezone.utc) - attempt.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        remaining = max(0, quiz.time_limit * 60 - elapsed)
        if remaining <= 0:
            return _finish_attempt(attempt, questions)

    if request.method == 'POST':
        return _finish_attempt(attempt, questions)

    return render_template('take_quiz.html', attempt=attempt, questions=questions,
                           remaining=int(remaining) if remaining is not None else None)


def _finish_attempt(attempt, questions):
    """Save student answers and calculate score."""
    correct_count = 0
    for q in questions:
        selected_ids = [int(x) for x in request.form.getlist(f'q_{q.id}')]
        correct_ids  = {a.id for a in q.correct_answers}

        sa = StudentAnswer(attempt_id=attempt.id, question_id=q.id)
        db.session.add(sa)
        db.session.flush()  # get sa.id

        if selected_ids:
            selected = Answer.query.filter(Answer.id.in_(selected_ids), Answer.question_id == q.id).all()
            sa.selected_answers = selected
            is_correct = {a.id for a in selected} == correct_ids
        else:
            is_correct = len(correct_ids) == 0

        sa.is_correct = is_correct
        if is_correct:
            correct_count += 1

    total = len(questions)
    attempt.correct_count   = correct_count
    attempt.score           = round(correct_count / total * 100, 1) if total else 0
    attempt.status          = 'completed'
    attempt.finished_at     = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for('quiz_result', attempt_id=attempt.id))


@app.route('/attempt/<int:attempt_id>/result')
@login_required
def quiz_result(attempt_id):
    attempt = Attempt.query.get_or_404(attempt_id)
    if attempt.student_id != current_user.id and not current_user.is_teacher:
        abort(403)
    return render_template('quiz_result.html', attempt=attempt)


@app.route('/my-results')
@login_required
def my_results():
    attempts = Attempt.query.filter_by(student_id=current_user.id, status='completed')\
                            .order_by(Attempt.started_at.desc()).all()
    stats = {
        'total': len(attempts),
        'avg_score': round(sum(a.score for a in attempts) / len(attempts), 1) if attempts else 0,
        'passed': sum(1 for a in attempts if a.is_passed),
    }
    return render_template('my_results.html', attempts=attempts, stats=stats)


# ─── Teacher Routes ───────────────────────────────────────────────────────────

@app.route('/teacher')
@login_required
@teacher_required
def teacher_dashboard():
    quizzes  = Quiz.query.filter_by(author_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    subjects = Subject.query.all()
    recent   = Attempt.query.join(Quiz).filter(Quiz.author_id == current_user.id,
                                               Attempt.status == 'completed')\
                            .order_by(Attempt.finished_at.desc()).limit(10).all()
    total_students = User.query.filter_by(is_teacher=False).count()
    return render_template('teacher_dashboard.html', quizzes=quizzes, subjects=subjects,
                           recent=recent, total_students=total_students)


@app.route('/teacher/quiz/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_quiz():
    subjects = Subject.query.order_by(Subject.name).all()
    if request.method == 'POST':
        quiz = Quiz(
            title         = request.form['title'].strip(),
            description   = request.form.get('description', '').strip(),
            subject_id    = int(request.form['subject_id']),
            time_limit    = int(request.form.get('time_limit', 0) or 0),
            passing_score = int(request.form.get('passing_score', 60) or 60),
            is_active     = 'is_active' in request.form,
            author_id     = current_user.id,
        )
        db.session.add(quiz)
        db.session.commit()
        flash(f'Тест «{quiz.title}» создан. Добавьте вопросы!', 'success')
        return redirect(url_for('edit_quiz', quiz_id=quiz.id))
    return render_template('quiz_form.html', quiz=None, subjects=subjects)


@app.route('/teacher/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_quiz(quiz_id):
    quiz     = Quiz.query.get_or_404(quiz_id)
    subjects = Subject.query.order_by(Subject.name).all()
    if quiz.author_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        quiz.title         = request.form['title'].strip()
        quiz.description   = request.form.get('description', '').strip()
        quiz.subject_id    = int(request.form['subject_id'])
        quiz.time_limit    = int(request.form.get('time_limit', 0) or 0)
        quiz.passing_score = int(request.form.get('passing_score', 60) or 60)
        quiz.is_active     = 'is_active' in request.form
        db.session.commit()
        flash('Тест обновлён.', 'success')

    questions = quiz.questions.order_by(Question.order).all()
    return render_template('edit_quiz.html', quiz=quiz, subjects=subjects, questions=questions)


@app.route('/teacher/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id:
        abort(403)
    db.session.delete(quiz)
    db.session.commit()
    flash(f'Тест «{quiz.title}» удалён.', 'success')
    return redirect(url_for('teacher_dashboard'))


@app.route('/teacher/quiz/<int:quiz_id>/question/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        q = Question(
            text          = request.form['text'].strip(),
            question_type = request.form.get('question_type', 'single'),
            order         = int(request.form.get('order', 0) or 0),
            explanation   = request.form.get('explanation', '').strip(),
            quiz_id       = quiz_id,
        )
        db.session.add(q)
        db.session.flush()

        # Parse answers from form: answer_text_1, answer_correct_1, ...
        i = 1
        while f'answer_text_{i}' in request.form:
            text = request.form[f'answer_text_{i}'].strip()
            if text:
                a = Answer(
                    text       = text,
                    is_correct = f'answer_correct_{i}' in request.form,
                    order      = i,
                    question_id = q.id,
                )
                db.session.add(a)
            i += 1

        db.session.commit()
        flash('Вопрос добавлен.', 'success')
        return redirect(url_for('edit_quiz', quiz_id=quiz_id))

    next_order = quiz.question_count + 1
    return render_template('question_form.html', quiz=quiz, question=None, next_order=next_order)


@app.route('/teacher/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_question(question_id):
    q = Question.query.get_or_404(question_id)
    if q.quiz.author_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        q.text          = request.form['text'].strip()
        q.question_type = request.form.get('question_type', 'single')
        q.order         = int(request.form.get('order', 0) or 0)
        q.explanation   = request.form.get('explanation', '').strip()

        # Delete old answers and recreate
        # First delete all references from student_answer_choices table
        answers = Answer.query.filter_by(question_id=q.id).all()
        for answer in answers:
            db.session.execute(
                student_answer_choices.delete().where(
                    student_answer_choices.c.answer_id == answer.id
                )
            )
        
        # Then delete the answers
        Answer.query.filter_by(question_id=q.id).delete()
        
        # Create new answers
        i = 1
        while f'answer_text_{i}' in request.form:
            text = request.form[f'answer_text_{i}'].strip()
            if text:
                db.session.add(Answer(
                    text        = text,
                    is_correct  = f'answer_correct_{i}' in request.form,
                    order       = i,
                    question_id = q.id,
                ))
            i += 1

        db.session.commit()
        flash('Вопрос обновлён.', 'success')
        return redirect(url_for('edit_quiz', quiz_id=q.quiz_id))

    return render_template('question_form.html', quiz=q.quiz, question=q, next_order=q.order)


@app.route('/teacher/question/<int:question_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_question(question_id):
    q = Question.query.get_or_404(question_id)
    if q.quiz.author_id != current_user.id:
        abort(403)
    quiz_id = q.quiz_id
    db.session.delete(q)
    db.session.commit()
    flash('Вопрос удалён.', 'success')
    return redirect(url_for('edit_quiz', quiz_id=quiz_id))


@app.route('/teacher/quiz/<int:quiz_id>/stats')
@login_required
@teacher_required
def quiz_stats(quiz_id):
    quiz     = Quiz.query.get_or_404(quiz_id)
    attempts = Attempt.query.filter_by(quiz_id=quiz_id, status='completed')\
                            .order_by(Attempt.finished_at.desc()).all()
    stats = {
        'total':     len(attempts),
        'avg_score': round(sum(a.score for a in attempts) / len(attempts), 1) if attempts else 0,
        'passed':    sum(1 for a in attempts if a.is_passed),
    }
    return render_template('quiz_stats.html', quiz=quiz, attempts=attempts, stats=stats)


@app.route('/teacher/subjects')
@login_required
@teacher_required
def subjects():
    all_subjects = Subject.query.order_by(Subject.name).all()
    return render_template('subjects.html', subjects=all_subjects)


@app.route('/teacher/subjects/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_subject():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        desc = request.form.get('description', '').strip()
        if not name:
            flash('Введите название предмета.', 'error')
        else:
            db.session.add(Subject(name=name, description=desc))
            db.session.commit()
            flash(f'Предмет «{name}» добавлен.', 'success')
            return redirect(url_for('subjects'))
    return render_template('subject_form.html')


# ─── Error handlers ───────────────────────────────────────────────────────────

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Доступ запрещён'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Страница не найдена'), 404


# ─── CLI: init DB & create teacher ────────────────────────────────────────────

@app.cli.command('init-db')
def init_db():
    """Create all tables."""
    db.create_all()
    print('✓ База данных создана.')


@app.cli.command('create-teacher')
def create_teacher():
    """Create a teacher account interactively."""
    import getpass
    username   = input('Логин: ').strip()
    email      = input('Email: ').strip()
    first_name = input('Имя: ').strip()
    last_name  = input('Фамилия: ').strip()
    password   = getpass.getpass('Пароль: ')

    if User.query.filter_by(username=username).first():
        print(f'✗ Пользователь {username} уже существует.')
        return

    u = User(username=username, email=email, first_name=first_name,
             last_name=last_name, is_teacher=True)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    print(f'✓ Преподаватель {username} создан.')


if __name__ == '__main__':
    app.run(debug=True)
