import requests
import locale
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta
import random
from sqlalchemy import desc

from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new_base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Ue234DU@#%^&^*&^@$g'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    new_login = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    view_name = db.Column(db.String(100), nullable=False)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    quiz_answer = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"Question('{self.text}', '{self.quiz_answer}')"


class QuizLeaderboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', backref=db.backref(
        'table_leader_quiz', lazy=True))


class UserWeather:
    def __init__(self, day_of_week, date, day_temperature, night_temperature):
        self.day_of_week = day_of_week
        self.date = date
        self.day_temperature = round(day_temperature)
        self.night_temperature = night_temperature


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html', current_user=current_user)


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    error = ''
    if request.method == 'POST':
        new_login = request.form['new_login']
        password = request.form['password']
        view_name = request.form['view_name']

        existing_user_by_view_name = User.query.filter_by(
            view_name=view_name).first()
        if existing_user_by_view_name:
            error = 'Пользователь с таким именем уже существует'
            return render_template('registration.html', error=error)

        existing_user_by_new_login = User.query.filter_by(
            new_login=new_login).first()
        if existing_user_by_new_login:
            error = 'Пользователь с таким логином уже существует'
            return render_template('registration.html', error=error)
        new_user = User(new_login=new_login, password=password,
                        view_name=view_name)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        new_login = request.form['new_login']
        password = request.form['password']

        user = User.query.filter_by(new_login=new_login).first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            error = 'Неправильно указан пользователь или пароль'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/quiz')
@login_required
def quiz():
    oq2 = ["Python 2", "ИИ", "Узкий ИИ", "Только Узкий ИИ", "NumPy",
           "Pygame", "Возможность конфликтов между выбранными библиотеками."]
    oq3 = ["Python 1", "Лекое обучение", "Общий ИИ", "Возможный ИИ и Легкий ИИ",
           "Pandas", "Pydantic", "Прототипно-ориентированный сценарный язык программирования."]
    oq4 = ["Любая", "Искуственное обучение", "Средний ИИ", "Только Общий ИИ", "PyTorch",
           "Flask", "Cкриптовый язык программирования и имеет открытый исходный код"]
    question = Question.query.order_by(func.random()).first()
    options = [question.quiz_answer, random.choice(
        oq2), random.choice(oq3), random.choice(oq4)]
    random.shuffle(options)
    return render_template('quiz.html', question=question, options=options)


@app.route('/table_leader_quiz')
def table_leader_quiz():
    leaderboard_data = db.session.query(
        User.view_name, User.score).order_by(desc(User.score)).all()
    leaderboard_data_with_rank = [(i+1, name, score)
                                  for i, (name, score) in enumerate(leaderboard_data)]
    return render_template('table_leader_quiz.html', leaderboard_data=leaderboard_data_with_rank)


@app.route('/quiz/answer', methods=['POST'])
@login_required
def quiz_answer():
    selected_answer = request.form.get('answer')
    question_id = request.form.get('question_id')

    if not selected_answer or not question_id:
        return redirect(url_for('quiz'))

    question = Question.query.get(int(question_id))

    if not question:
        abort(404)

    if selected_answer == question.quiz_answer:
        current_user.score += 1
        db.session.commit()

        leaderboard_entry = QuizLeaderboard.query.filter_by(
            user_id=current_user.id).first()
        if leaderboard_entry:
            leaderboard_entry.score = current_user.score
        else:
            leaderboard_entry = QuizLeaderboard(
                user_id=current_user.id, score=current_user.score)
            db.session.add(leaderboard_entry)
        db.session.commit()

    else:
        pass

    return redirect(url_for('quiz'))


@app.route('/weather', methods=['POST'])
def user_weather():
    try:
        city = request.form['city']
        api_key = 'b1b15e88fa797225412429c1c50c122a1'
        url = f'http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
        response = requests.get(url)
        data = response.json()

        if data['cod'] == '200':
            user_weather = {}
            today = datetime.now().date()
            locale.setlocale(locale.LC_ALL, 'ru_RU')
            for forecast in data['list']:
                date_time = forecast['dt_txt']
                date_obj = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                if date_obj.hour == 12 or (date_obj.hour > 12 and date_obj.date() == today):
                    day_of_week = date_obj.strftime('%A')
                    date = date_obj.strftime('%Y-%m-%d')
                    day_temperature = forecast['main']['temp']
                    if date not in user_weather:
                        user_weather[date] = UserWeather(
                            day_of_week, date, day_temperature, None)
                elif date_obj.hour == 0:
                    date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                    night_temperature = forecast['main']['temp']
                    if date in user_weather:
                        user_weather[
                            date].night_temperature = round(night_temperature)

            filtered_forecast = [forecast for forecast in user_weather.values() if
                                 datetime.strptime(forecast.date, '%Y-%m-%d').date() in [today, today + timedelta(days=1), today + timedelta(days=2)]]
            return render_template('index.html', user_weather=filtered_forecast)
        else:
            error_message = f"Сбой сервера: {data['message']}"
            return render_template('index.html', error=error_message)
    except Exception as e:
        return render_template('index.html', error=str(e))


if __name__ == '__main__':
    app.run(debug=False)
