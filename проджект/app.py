from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'modex-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///modex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите'


#пользователь
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # только имя
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='buyer')
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# регистр
class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=4)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Такое имя уже занято')


# входик
class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


# закгрузка юзера
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# создание бд
with app.app_context():
    db.create_all()

    # админка
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('✅ Админ создан: логин "admin", пароль "admin123"')




# роуты

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # пока только покупатель
        user = User(
            username=form.username.data,
            role='buyer'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash(f'Регистрация успешна! Теперь войдите, {user.username}', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        # ищем имя
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            if user.is_blocked:
                flash('Аккаунт заблокирован', 'danger')
                return redirect(url_for('login'))

            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


if __name__ == '__main__':
    app.run(debug=True)