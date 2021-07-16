from flask import Flask, render_template, url_for, redirect, request, flash, jsonify
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from forms import Task, Login, Register, Forgot
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer
import os
import psycopg2


app = Flask(__name__)
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI')
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config["SECURITY_PASSWORD_SALT"] = os.environ.get('SECURITY_PASSWORD_SALT')
login_manager = LoginManager()
login_manager.init_app(app)

mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.environ.get('MAIL_USERNAME'),
    "MAIL_PASSWORD": os.environ.get('MAIL_PASSWORD')
}
app.config.update(mail_settings)
mail = Mail(app)



class TodoList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    sortable = db.Column(db.Integer, nullable=False)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    confirmed = db.Column(db.Integer, nullable=False)
db.create_all()



@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('todo'))
    return render_template('index.html')


@app.route('/todo')
@login_required
def todo():
    todo_list = TodoList.query.filter_by(user_id=current_user.id).order_by(TodoList.sortable).all()
    for item in todo_list:
        if item.end_date:
            end_date = datetime.strptime(item.end_date, '%Y-%m-%d %H:%M')
            current_time = datetime.now()
            timeleft = end_date - current_time
            if timeleft.days < 0:
                item.end_date = 'expired'
            elif timeleft.days > 0:
                if timeleft.days == 1:
                    item.end_date = f'{timeleft.days} day'
                else:
                    item.end_date = f'{timeleft.days} days'
            elif timeleft.seconds < 60:
                if timeleft.seconds == 1:
                    item.end_date = f'{timeleft.seconds} second'
                else:
                    item.end_date = f'{timeleft.seconds} seconds'
            elif 60 <= timeleft.seconds < 3600:
                if timeleft.seconds < 120:
                    item.end_date = f'{timeleft.seconds // 60} minute'
                else:
                    item.end_date = f'{timeleft.seconds // 60} minutes'
            elif 3600 <= timeleft.seconds < 86400:
                if timeleft.seconds < 7200:
                    item.end_date = f'{timeleft.seconds // 3600} hour'
                else:
                    item.end_date = f'{timeleft.seconds // 3600} hours'
            else:
                item.end_date = 'expired'
    return render_template('todo.html', todo_list=todo_list)


@app.route('/new_task', methods=['GET', 'POST'])
@login_required
def add_task():
    form = Task()
    if form.validate_on_submit():
        todo_list = TodoList.query.filter_by(user_id=current_user.id).all()
        count = len(todo_list)
        text = form.text.data
        end_date = form.end_date.data
        new_item = TodoList(
            text=text,
            end_date=end_date,
            user_id=current_user.id,
            sortable=count+1
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('todo'))
    return render_template('task.html', form=form, title='Add new task')


@app.route('/edit_task', methods=['GET', 'POST'])
@login_required
def edit_task():
    task_id = request.args.get('id')
    task = TodoList.query.get(task_id)
    if task is None:
        task_id = request.form['id']
        task = TodoList.query.get(task_id)
    if task.user_id == current_user.id:
        if request.method == 'POST':
            task.text = request.form['text']
            task.end_date = request.form['end_date']
            db.session.commit()
            return redirect(url_for('todo'))
        form = Task(
            id=task_id,
            text=task.text,
            end_date=task.end_date
        )
        return render_template('task.html', form=form, title='Edit task')
    else:
	    return redirect(url_for('todo'))


@app.route('/delete_task', methods=['GET'])
@login_required
def delete_task():
    task_id = request.args.get('id')
    task = TodoList.query.get(task_id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('todo'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = Register()
    if form.validate_on_submit():
        password = generate_password_hash(form.password.data, salt_length=24)
        token = generate_confirm_token(form.email.data)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=password,
            confirmed=0
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            confirm_url = 'http://todoxv.herokuapp.com' + url_for('confirm', token=token)
            html = render_template('confirm.html', confirm_url=confirm_url)
            msg = Message(
                subject='Email Confirm',
                sender=app.config.get('MAIL_USERNAME'),
                recipients=form.email.data.split(),
                html=html
            )
            mail.send(msg)
        except IntegrityError:
            flash('Name or email already exists...', 'error')
            return render_template('register-login.html', form=form, form_title='Register User')
        login_user(new_user)
        flash('Thanks for sign up. Please confirm email address. Activation link was sent on your email.', 'success')
        return redirect(url_for('todo'))
    return render_template('register-login.html', form=form, form_title='Register User')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('todo'))
        else:
            flash('Invalid email or password', 'error')
            return render_template('register-login.html', form=form, form_title='Login User')
    return render_template('register-login.html', form=form, form_title='Login User')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/post_sort', methods=['GET', 'POST'])
def post_sort():
    if request.method == 'POST':
        json = request.json
        x = json.replace('item[]=', ',')
        x = x.replace(',', '')
        indexes = x.split('&')
        i = 0
        for index in indexes:
            i += 1
            db_item = TodoList.query.filter_by(id=int(index)).first()
            db_item.sortable = i
        db.session.commit()
    return jsonify(json)


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = Login()
    form.submit.label.text = 'Restore'
    if request.method == 'POST':
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_confirm_token(user.email)
            confirm_url = 'http://todoxv.herokuapp.com' + url_for('forgot', token=token)
            html = render_template('forgot.html', confirm_url=confirm_url)
            msg = Message(
                subject='Restore Password',
                sender=app.config.get('MAIL_USERNAME'),
                recipients=form.email.data.split(),
                html=html
            )
            mail.send(msg)
            flash('Recovery link has been sent on email.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid email', 'error')
            return render_template('forgot_password.html', form=form, form_title='Restore password')
    return render_template('forgot_password.html', form=form, form_title='Restore password')


@app.route('/confirm/<token>')
@login_required
def confirm(token):
    email = confirm_token(token)
    user = User.query.filter_by(email=email).first()
    if user.confirmed:
        flash('Email already confirmed. Please log in.', 'success')
    else:
        user.confirmed = 1
        db.session.commit()
        flash('Email confirmed.', 'success')
    return redirect(url_for('login'))


@app.route('/forgot/<token>', methods=['GET', 'POST'])
def forgot(token):
    form = Forgot()
    email = confirm_token(token)
    user = User.query.filter_by(email=email).first()
    if user:
        if request.method == 'POST':
            if form.password.data == form.confirm_password.data:
                user.password = generate_password_hash(form.password.data, salt_length=24)
                db.session.commit()
                flash('Password restored', 'success')
                return redirect(url_for('login'))
            else:
                flash("Password doesn't match", 'error')
                return render_template('restore_password.html', form_title='Restore Password', form=form, token=token)
        return render_template('restore_password.html', form_title='Restore Password', form=form, token=token)
    else:
        return redirect(url_for('index'))


def generate_confirm_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


def confirm_token(token):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'])
    except:
        return False
    return email


if __name__ == '__main__':
    app.run()
