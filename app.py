from datetime import date

from flask_mobility.decorators import mobile_template
from flask_mobility.mobility import Mobility
from flask import Flask, render_template, redirect, abort
from flask_login import logout_user, login_required, LoginManager, login_user, current_user
from flask_ngrok import run_with_ngrok

from data import db_session
from data.classes import Class
from data.db_functions import repair_dependencies_students_and_groups
from data.epos import EPOS
from data.groups import Group
from data.homeworks import Homework
from data.projects_8_class import Project
from data.schools import School
from data.students import Student
from data.users import User
from forms.login import LoginForm
from forms.profile import ProfileForm
from forms.register import RegisterForm

SCOPES = ['https://www.googleapis.com/auth/classroom.coursework.me.readonly']

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
Mobility(app)
login_manager = LoginManager()
login_manager.init_app(app)
db_session.global_init('db/database.sqlite')
epos = EPOS()

run_with_ngrok(app)


def main():
    app.run()


@app.route('/')
@app.route('/index')
@app.route('/main')
@mobile_template('{mobile/}index.html')
def index(template):
    return render_template(template,
                           title='Главная')


@app.route('/login', methods=['GET', 'POST'])
@mobile_template('{mobile/}login.html')
def login(template):
    if current_user.is_authenticated:
        redirect('/profile')

    form = LoginForm()

    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user: User
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if not user:
            return render_template(template,
                                   title='Авторизация',
                                   message="Вы не зарегистрированы в системе",
                                   form=form)
        if user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/index")
        return render_template(template,
                               title='Авторизация',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template(template,
                           title='Авторизация',
                           form=form)


@app.route('/register', methods=['GET', 'POST'])
@mobile_template('{mobile/}register.html')
def register(template):
    if current_user.is_authenticated:
        redirect('/homework')

    form = RegisterForm()

    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template(template,
                                   title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают",
                                   btn_label='Войти')

        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template(template,
                                   title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть",
                                   btn_label='Войти')

        # noinspection PyArgumentList
        user = User(
            surname=form.surname.data,
            name=form.name.data,
            patronymic=form.last_name.data,
            date_of_birth=form.date_of_birth.data,
            email=form.email.data,
            epos_login=form.epos_login.data,
            epos_password=form.epos_password.data,
            school_id=int(db_sess.query(School.id).
                          filter(School.title == form.school.data).first()[0]),
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        login_user(user)
        return redirect('/profile')

    return render_template(template,
                           title='Регистрация',
                           form=form,
                           btn_label='Войти')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
@mobile_template('{mobile/}profile.html')
def profile(template):
    form = ProfileForm()
    db_sess = db_session.create_session()
    user = current_user

    if form.validate_on_submit():
        user.surname = form.surname.data
        user.name = form.name.data
        user.patronymic = form.patronymic.data
        user.email = form.email.data
        user.school_id = int(db_sess.query(School.id).filter(
            School.title == form.school.data).first()[0])
        user.role = form.role.data
        user.date_of_birth = form.date_of_birth.data
        user.about = form.about.data

        user.epos_login = form.epos_login.data
        if form.epos_password.data:
            user.epos_password = form.epos_password.data

        if form.old_password.data or form.password.data or form.password_again.data:
            if not form.old_password.data:
                return render_template(template,
                                       title='Профиль',
                                       form=form,
                                       school=db_sess.query(School.title).filter(
                                           School.id == user.school_id).first()[0],
                                       message="Введите старый пароль",
                                       date=current_user.date_of_birth.strftime('%d.%m.%Y'),
                                       btn_label='Сохранить')
            elif not form.password.data:
                return render_template(template,
                                       title='Профиль',
                                       form=form,
                                       school=db_sess.query(School.title).filter(
                                           School.id == user.school_id).first()[0],
                                       message="Введите новый пароль",
                                       date=current_user.date_of_birth.strftime('%d.%m.%Y'),
                                       btn_label='Сохранить')
            elif not form.password_again.data:
                return render_template(template,
                                       title='Профиль',
                                       form=form,
                                       school=db_sess.query(School.title).filter(
                                           School.id == user.school_id).first()[0],
                                       message="Повторите новый пароль",
                                       date=current_user.date_of_birth.strftime('%d.%m.%Y'),
                                       btn_label='Сохранить')
            elif not user.check_password(form.old_password.data):
                return render_template(template,
                                       title='Профиль',
                                       form=form,
                                       school=db_sess.query(School.title).filter(
                                           School.id == user.school_id).first()[0],
                                       message="Неверный старый пароль",
                                       date=current_user.date_of_birth.strftime('%d.%m.%Y'),
                                       btn_label='Сохранить')
            elif form.password.data != form.password_again.data:
                return render_template(template,
                                       title='Профиль',
                                       form=form,
                                       school=db_sess.query(School.title).filter(
                                           School.id == user.school_id).first()[0],
                                       message="Пароли не совпадают",
                                       date=current_user.date_of_birth.strftime('%d.%m.%Y'),
                                       btn_label='Сохранить')
            else:
                user.set_password(form.password.data)

        db_sess.merge(user)
        db_sess.commit()
        return render_template(template,
                               title='Профиль',
                               form=form,
                               school=db_sess.query(School.title).filter(
                                   School.id == user.school_id).first()[0],
                               message="Сохранено",
                               date=current_user.date_of_birth.strftime('%d.%m.%Y'),
                               btn_label='Сохранить')

    return render_template(template,
                           title='Профиль',
                           form=form,
                           school=db_sess.query(School.title).filter(
                               School.id == user.school_id).first()[0],
                           date=current_user.date_of_birth.strftime('%d.%m.%Y'),
                           btn_label='Сохранить')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/login")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/area-diary')
@login_required
@mobile_template('{mobile/}area-diary.html')
def area_diary(template):
    repair_dependencies_students_and_groups()
    db_sess = db_session.create_session()
    days = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб']
    schedule = dict()
    for day in days:
        schedule[day] = [['-', -1] for _ in range(8)]

    # Получаем группы ученика и составляем по ним расписание
    group_ids = list(db_sess.query(Student.group_id).filter(Student.user_id == current_user.id))
    for group_id in group_ids:
        group = db_sess.query(Group).get(group_id)
        for day_n, lesson_n in list(map(lambda x: (int(x[0]), int(x[1])),
                                        str(group.schedule).split(','))):
            schedule[days[day_n - 1]][lesson_n - 1][0] = group.subject
            schedule[days[day_n - 1]][lesson_n - 1][1] = group_id[0]

    # Убираем пустые уроки с конца
    for key in schedule.keys():
        while schedule[key][-1][0] == '-':
            schedule[key] = schedule[key][:-1]

    begin_date = date(2021, 5, 3)
    homework = dict()
    for day in days:
        homework[day] = [[] for _ in range(8)]
    for day_n in range(6):
        for lesson_n in range(len(schedule[days[day_n - 1]])):
            homeworks = list(map(lambda x: str(x[0]).capitalize(),
                                 db_sess.query(Homework.homework).filter(
                                     Homework.date == date(begin_date.year,
                                                           begin_date.month,
                                                           begin_date.day + day_n),
                                     Homework.lesson_number == lesson_n,
                                     Homework.group_id == schedule[days[day_n]][lesson_n - 1][1]
                                 )))
            if homeworks:
                homework[days[day_n]][lesson_n - 1] = homeworks
    dates = [str(begin_date.day + i).rjust(2, '0') for i in range(6)]
    return render_template(template,
                           title='Дневник AREA',
                           schedule=schedule,
                           homework=homework,
                           dates=dates,
                           days=days)


@app.route('/epos-diary')
@login_required
@mobile_template('{mobile/}epos-diary.html')
def epos_diary(template):
    if not current_user.is_authenticated:
        return abort(401)

    epos_login = current_user.epos_login
    epos_password = current_user.epos_password
    epos.run(epos_login, epos_password)
    response = epos.get_schedule()
    response: list
    schedule = []

    if response == 'bad password':
        abort(403)
    elif response == 'timeout':
        abort(408)
    else:
        schedule = response

    return render_template(template,
                           title='Дневник ЭПОСа',
                           schedule=schedule)


@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(408)
@mobile_template('{mobile/}error-page.html')
def page_not_found(error, template):
    messages = {
        401: ['Вы не авторизованы',
              'Через несколько секунд Вы будете направлены на страницу авторизации'],
        403: ['Ошибка при авторизации в ЭПОС.Школа',
              'Попробуйте ещё раз. При повторном возникновении ошибки проверьте пароль от '
              'ЭПОС.Школа и обновите его в профиле'],
        404: ['Страница не найдена',
              'Проверьте правильность введённого адреса'],
        408: ['Превышено время ожидания',
              'Попробуйте сделать запрос еще раз. Если проблема повторится, обратитесь в '
              'техподдержку']
    }

    return render_template(template,
                           code=error.code,
                           title=messages[error.code][0],
                           message=messages[error.code][1])


@app.route('/privacy-policy')
@mobile_template('{mobile/}privacy-policy.html')
def privacy_policy(template):
    return render_template(template,
                           title='Политика конфиденциальности')


@app.route('/8-classes-projects-result')
@mobile_template('{mobile/}8-classes-projects-result.html')
def projects_8_class(template):
    db_sess = db_session.create_session()
    project = db_sess.query(Project.title, Project.points). \
        filter(Project.authors_ids.contains(current_user.id)).first()
    projects = dict()
    sections = sorted(list(map(lambda x: x[0], set(list(db_sess.query(Project.section))))))
    for section in sections:
        data = list(db_sess.query(Project.title, Project.points).filter(Project.section == section))
        data.sort(key=lambda x: x[-1])
        projects[section] = data
    return render_template(template,
                           project=project,
                           projects=projects,
                           sections=sections)


if __name__ == '__main__':
    main()
