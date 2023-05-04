import sqlite3
import streamlit as st
import datetime
import random
import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pymongo.mongo_client import MongoClient

#url link here for mongoDB
mongo_client = MongoClient(uri)
mongo_db = mongo_client['ClinicApp']
doctors_coll = mongo_db['doctors']
doctors_mongo = doctors_coll.find({})

# doctors.insert_many([
#     {"_id": 0, "role": "Admin", "login": "admin", "password": "1234"},
#     {"_id": 1, "role": "Doctor", "login": "albert", "password": "1234", "experience": 10, "education": "Первый Московский государственный медицинский университет имени И. М. Сеченова"},
#     {"_id": 2, "role": "Doctor", "login": "pozdnyakov", "password": "1234", "experience": 5, "education": "Российская медицинская академия непрерывного профессионального образования"},
#     {"_id": 3, "role": "Doctor", "login": "maxim", "password": "1234", "experience": 6, "education": "Российский национальный исследовательский медицинский университет имени Н. И. Пирогова"},
#     {"_id": 4, "role": "Doctor", "login": "alex", "password": "1234", "experience": 20, "education": "Первый Московский государственный медицинский университет имени И. М. Сеченова"},
#     {"_id": 5, "role": "Doctor", "login": "evg", "password": "1234", "experience": 15, "education": "Российская медицинская академия непрерывного профессионального образования"},
#     {"_id": 6, "role": "Doctor", "login": "katz", "password": "1234", "experience": 6, "education": "Российский национальный исследовательский медицинский университет имени Н. И. Пирогова"},
#     {"_id": 7, "role": "Doctor", "login": "elena", "password": "1234", "experience": 12, "education": "Первый Московский государственный медицинский университет имени И. М. Сеченова"}
# ])

try:
    conn = sqlite3.connect('ClinicApp.sqlite')
    c = conn.cursor()
except sqlite3.Error as e:
    print(e)


def main():
    st.sidebar.header('Вход для работников')
    login = st.sidebar.text_input('Логин')
    password = st.sidebar.text_input('Пароль', type='password')
    entry_btn = st.sidebar.checkbox('Войти')
    if entry_btn:
        doctor_entry = doctors_coll.find_one({"login": login, "password": password})
        if doctor_entry and doctor_entry["role"] == "Admin":
            menu_choice = st.selectbox('Выбор меню', ['Управление врачами', 'Добавление сеансов'])
            if menu_choice == 'Управление врачами':
                doctor_types = [x[0] for x in c.execute("SELECT type_name FROM Doctor_type").fetchall()]
                with st.form(key='register', clear_on_submit=True):
                    doctor_type_choice = st.selectbox('Выберите специальность врача', doctor_types)
                    for type_id, doctor_type in enumerate(doctor_types):
                        if doctor_type_choice == doctor_type:
                            selected_type_id = type_id + 1
                    doctor_name = st.text_input("Имя")
                    doctor_email = st.text_input('Почта')
                    doctor_login = st.text_input('Логин')
                    doctor_password = st.text_input('Пароль')
                    doctor_experience = st.slider('Опыт работы', min_value=0, max_value=50)
                    doctor_education = st.text_area('Образование')
                    reg_btn = st.form_submit_button('Зарегистрироваться')
                    if reg_btn:
                        c.execute("INSERT INTO Doctor (name, type_id) "
                                  "VALUES (?,?)", (doctor_name, selected_type_id,))
                        conn.commit()
                        new_doctor_id = c.execute("SELECT id FROM Doctor WHERE name = ? AND type_id = ?",
                                                  (doctor_name, selected_type_id,)).fetchone()[0]
                        doctors_coll.insert_one({
                            "_id": new_doctor_id,
                            "role": "Doctor",
                            "login": doctor_login,
                            "password": doctor_password,
                            "experience": doctor_experience,
                            "education": doctor_education,
                            "mail": doctor_email
                        })
                        message = f'Здравствуйте, {doctor_name}\n' \
                                  f'Поздравляем, c принятием на работу в нашу клинику\n' \
                                  f'В дальнейшем вам понадобятся логин и пароль для работы с приложением, сохраните их и не теряйте!\n' \
                                  f'ВАШ ЛОГИН: {doctor_login}\n' \
                                  f'ВАШ ПАРОЛЬ: {doctor_password}'
                        send_mail(receiver=doctor_email,message=message)
            elif menu_choice == 'Добавление сеансов':
                doctors = c.execute("SELECT * FROM Doctor").fetchall()
                doctor_names = [x[1] for x in doctors]
                selected_doctor = st.selectbox('Выберите врача для создания записей', doctor_names)
                session_date = st.date_input('Дата приема', min_value=datetime.date.today(),
                                             max_value=datetime.date.today() + datetime.timedelta(weeks=4))
                session_time = st.time_input('Время приема', datetime.time(9, 0), step=1800)
                for doctor in doctors:
                    if selected_doctor == doctor[1]:
                        doctor_id = doctor[0]
                if st.button('Добавить сеанс'):
                    session = c.execute("SELECT * FROM Session WHERE doctor_id = ? AND date = ? AND time = ?",
                                        (doctor_id, session_date, str(session_time),)).fetchone()
                    if not session:
                        c.execute("INSERT INTO Session (status_id, doctor_id, date, time) "
                                  "VALUES (?,?,?,?)", (1, doctor_id, session_date, str(session_time),))
                        conn.commit()
                    else:
                        st.error('Запись с таким временем и датой уже существует')
                doctor_sessions = c.execute("SELECT * FROM Session WHERE doctor_id = ? AND date = ?",
                                            (doctor_id, session_date,)).fetchall()
                for session in doctor_sessions:
                    if session:
                        year, month, day = list(map(int, session[3].split('-')))
                        end_date = datetime.date(year=year, month=month, day=day)
                        diff_dates = end_date - datetime.date.today()
                        if diff_dates.days >= 0:
                            with st.container():
                                session_id = session[0]
                                status = 'Свободно' if session[1] == 1 else 'Занято'
                                st.markdown(f'Дата приема: {session[3]}')
                                st.markdown(f'Время приема: {session[4]}')
                                st.markdown(f'Статус прием: {status}')
                                col1, col2 = st.columns(2)
                                with col1:
                                    cancel_btn_key = 'cancel' + session[3] + session[4]
                                    if st.button('Отменить запись', key=cancel_btn_key,
                                                 disabled=True if status == 'Свободно' else False):
                                        cancel_appointment(session_id)
                                        st._rerun()
                                with col2:
                                    delete_btn_key = 'delete' + session[3] + session[4]
                                    if st.button('Удалить запись', key=delete_btn_key):
                                        delete_session(session_id)
                                        st._rerun()
        elif doctor_entry and doctor_entry["role"] == "Doctor":
            doctor_id = doctor_entry["_id"]
            doctor_sessions = c.execute("SELECT * FROM Session WHERE doctor_id = ? AND date = ?",
                                        (doctor_id, datetime.date.today(),)).fetchall()
            session_times = [x[4] for x in doctor_sessions]
            time_choice = st.selectbox('Время приема', session_times)
            for ind, session_time in enumerate(session_times):
                if session_time == time_choice:
                    session_id = doctor_sessions[ind][0]
                    if doctor_sessions[ind][1] == 1:
                        st.subheader('Нет активной записи пользователя')
                    else:
                        appointment = c.execute("SELECT * FROM Appointment WHERE session_id = ?",
                                                (session_id,)).fetchone()
                        appointment_id = appointment[0]
                        appointment_status = appointment[1]
                        if appointment_status == 1 or appointment_status == 2:
                            user_id = appointment[3]
                            user = c.execute("SELECT * FROM User WHERE id = ?", (user_id,)).fetchone()
                            st.markdown(f'Имя пациента: {user[1]}')
                            st.markdown(f'Дата рождения {user[3]}')
                            medications = c.execute("SELECT * FROM Medication")
                            medication_names = [x[1] for x in medications]
                            medication_choice = st.selectbox('Препараты', medication_names)
                            for ind, med_name in enumerate(medication_names):
                                if med_name == medication_choice:
                                    selected_medication_id = ind + 1
                            if st.button('Назначить препарат'):
                                if c.execute("SELECT * FROM Prescript_medication WHERE user_id = ? AND medication_id = ?",
                                             (user_id, selected_medication_id,)).fetchone():
                                    st.error('Данный препарат уже был назначен')
                                else:
                                    c.execute("INSERT INTO Prescript_medication (doctor_id, medication_id, user_id, "
                                              "prescription_date) VALUES (?,?,?,?)",
                                              (doctor_id, selected_medication_id, user_id, datetime.date.today(),))
                                    conn.commit()
                                    st.success('Препарат был успешно назначен')
                            st.subheader('Назначенные препараты')
                            prescript_medication = c.execute("SELECT * FROM Prescript_medication "
                                                             "WHERE user_id = ?", (user_id,)).fetchall()
                            for pr_med in prescript_medication:
                                prescription_id = pr_med[0]
                                medication_id = pr_med[2]
                                medication = c.execute("SELECT * FROM Medication WHERE id = ?",
                                                       (medication_id,)).fetchone()
                                prescript_doctor = c.execute("SELECT name FROM Doctor WHERE id = ?",
                                                             (pr_med[1],)).fetchone()
                                with st.container():
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown(f'Название препарата: {medication[1]}')
                                        st.markdown(f'Описание: {medication[2]}')
                                        st.markdown(f'Дозировка: {medication[3]}')
                                    with col2:
                                        st.markdown(f'Дата назначения: {pr_med[4]}')
                                        st.markdown(f'Назначавший врач: {prescript_doctor[0]}')
                                        revoke_med_key = 'revoke_med' + str(prescription_id)
                                        if st.button('Отозвать назначение', key=revoke_med_key):
                                            c.execute("DELETE FROM Prescript_medication WHERE id = ?", (prescription_id,))
                                            conn.commit()
                            input_data = st.text_area('Информация о приеме')
                            if st.button('Завершить прием'):
                                c.execute("UPDATE Appointment SET status_id = ?, text = ? "
                                          "WHERE id = ?", (3, input_data, appointment_id,))
                                conn.commit()
                                st._rerun()
                        elif appointment_status == 3:
                            st.subheader('Пациент был обслужен')
                        elif appointment_status == 4:
                            st.subheader('Прием был отменен')
        else:
            st.error('Вы ввели неправильные данные')
    else:
        st.subheader('Для записи к врачу необходимо заристрироваться в системе клиники')
        is_registered = st.checkbox('Имеется код для записи')
        if not is_registered:
            with st.form(key='register', clear_on_submit=True):
                user_name = st.text_input("Имя")
                user_sex = st.radio('Пол', ['Мужчина', 'Женщина'])
                user_birth_date = st.date_input('Дата рождения', min_value=datetime.date(year=1930, month=1, day=1))
                user_email = st.text_input('Почта')
                reg_btn = st.form_submit_button('Зарегистрироваться')
                if reg_btn:
                    user_code = ''.join(str(random.randint(0, 9)) for _ in range(8))
                    c.execute("INSERT INTO User (name, sex, birth_date, user_code, user_email) VALUES (?,?,?,?,?)",
                              (user_name, user_sex, user_birth_date, user_code, user_email,))
                    conn.commit()
                    message = f'Здравствуйте, {user_name}\n' \
                              f'Поздравляем, вы успешно зарегистрировались в приложении клиники\n' \
                              f'В дальнейшем вам понадобится код для записи на прием к врачам, сохраните его и не теряйте!\n' \
                              f'ВАШ КОД: {user_code}'
                    send_mail(receiver=user_email, message=message)
                    st.success('Аккаунт успешно создан')
        else:
            user_code = st.text_input('Введите ваш код')
            doctor_types = [x[0] for x in c.execute("SELECT type_name FROM Doctor_type").fetchall()]
            if st.button('Проверить код'):
                if find_user_code(user_code):
                    st.success('Код для для записи найден')
                else:
                    st.error('Код для записи не найден')
            menu_choice = st.selectbox('Выберите меню', ['Записаться к врачу', 'Мои записи', 'Назначенные препараты'])
            if menu_choice == 'Записаться к врачу':
                doctor_type_choice = st.selectbox('Выберите специальность врача', doctor_types)
                doctors = c.execute("SELECT * FROM Doctor")
                selected_doctors = pd.DataFrame(doctors, columns=['id', 'name', 'type_id'])
                for type_id, doctor_type in enumerate(doctor_types):
                    if doctor_type_choice == doctor_type:
                        selected_doctors = selected_doctors[selected_doctors['type_id'] == (type_id + 1)]
                for ind, doctor in selected_doctors.iterrows():
                    with st.container():
                        print(doctor)
                        doctor_id = int(doctor[0])
                        doctor_name = doctor[1]
                        col1, col2 = st.columns(2)
                        doctor_info = doctors_coll.find_one({"_id": doctor_id})
                        with col1:
                            print(doctor_info)
                            st.subheader(doctor_name)
                            st.markdown(f'Опыт работы: {doctor_info["experience"]}')
                            st.markdown(f'Образование: {doctor_info["education"]}')
                        with col2:
                            session_date_key = 'date' + str(doctor_id)
                            session_date = st.date_input('Дата приема', min_value=datetime.date.today(),
                                                         max_value=datetime.date.today() + datetime.timedelta(days=7),
                                                         key=session_date_key)
                            free_sessions = c.execute("SELECT * FROM Session WHERE doctor_id = ? AND date = ?",
                                                      (doctor_id, session_date,)).fetchall()
                            for session in free_sessions:
                                session_id = session[0]
                                st.markdown(f'Время приема: {session[4]}')
                                app_btn_key = 'appl' + str(session[2]) + session[3] + session[4]
                                if st.button('Записаться', key=app_btn_key,
                                             disabled=True if session[1] == 2 else False):
                                    user_id = find_user_code(user_code)
                                    if user_id:
                                        enroll_appointment(user_id, session_id)
                                        user = c.execute("SELECT name, user_email FROM User WHERE id = ?",
                                                         (user_id,)).fetchone()
                                        message = f'Здравствуйте, {user[0]}\n' \
                                                  f'Поздравляем, вы успешно записались на прием к врачу. ' \
                                                  f'Информация о приеме:\n' \
                                                  f'Врач: {doctor_name}, специализация: {doctor_type_choice}\n' \
                                                  f'Дата приема: {session[3]}, Время: {session[4]}\n'
                                        send_mail(receiver=user[1], message=message)
                                        st.success('Вы успешно записались на прием')
                                        st._rerun()
                                    else:
                                        st.error('Вы неправильно ввели код для записи')
            elif menu_choice == 'Мои записи':
                user_id = c.execute("SELECT id FROM User WHERE user_code = ?",
                                    (user_code,)).fetchone()[0]
                if user_id:
                    user_appointments = c.execute("SELECT * FROM Appointment WHERE user_id = ?", (user_id,)).fetchall()
                    for app in user_appointments:
                        appointment_id = app[0]
                        app_status = app[1]
                        app_statuses = [x[0] for x in c.execute("SELECT status_name FROM Appointment_status").fetchall()]
                        session = c.execute("SELECT * From Session where id = ?", (app[2],)).fetchone()
                        session_id = session[0]
                        doctor = c.execute("SELECT * FROM Doctor where id = ?", (session[2],)).fetchone()
                        st.subheader(f'Специализация: {doctor_types[doctor[2] - 1]}')
                        st.markdown(f'Врач: {doctor[1]}')
                        st.markdown(f'Статус записи: {app_statuses[app[1] - 1]}')
                        st.markdown(f'Дата: {session[3]}')
                        st.markdown(f'Время: {session[4]}')
                        confirm_app_key = 'confirmapp' + str(appointment_id) + session[3] + session[4]
                        cancel_app_key = 'dellapp' + str(appointment_id) + session[3] + session[4]
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button('Подтвердить запись', key=confirm_app_key,
                                         disabled=True if app_status != 1 else False):
                                confirm_appointment(appointment_id)
                                st._rerun()
                                st.success('Запись успешно подтверждена')
                        with col2:
                            if st.button('Отменить запись', key=cancel_app_key):
                                cancel_appointment(session_id)
                                st._rerun()
            elif menu_choice == 'Назначенные препараты':
                user_id = c.execute("SELECT id FROM User WHERE user_code = ?",
                                    (user_code,)).fetchone()[0]
                if user_id:
                    st.subheader('Назначенные препараты')
                    prescript_medication = c.execute("SELECT * FROM Prescript_medication "
                                                     "WHERE user_id = ?", (user_id,)).fetchall()
                    for pr_med in prescript_medication:
                        prescription_id = pr_med[0]
                        medication_id = pr_med[2]
                        medication = c.execute("SELECT * FROM Medication WHERE id = ?",
                                               (medication_id,)).fetchone()
                        prescript_doctor = c.execute("SELECT name FROM Doctor WHERE id = ?",
                                                     (pr_med[1],)).fetchone()
                        with st.container():
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f'Название препарата: {medication[1]}')
                                st.markdown(f'Описание: {medication[2]}')
                                st.markdown(f'Дозировка: {medication[3]}')
                            with col2:
                                st.markdown(f'Дата назначения: {pr_med[4]}')
                                st.markdown(f'Назначавший врач: {prescript_doctor[0]}')


def enroll_appointment(user_id, session_id):
    c.execute("UPDATE Session SET status_id = ? WHERE id = ?",
              (2, session_id,))
    c.execute("INSERT INTO Appointment (status_id, session_id, user_id) "
              "VALUES (?,?,?)", (1, session_id, user_id,))
    conn.commit()


def find_user_code(user_code):
    if user_code == '':
        return False

    try:
        user_id = c.execute("SELECT id FROM User WHERE user_code = ?",
                            (user_code,)).fetchone()[0]
        print(user_id)
        return user_id
    except Exception as e:
        print(e)
        return False


def confirm_appointment(appointment_id):
    c.execute("UPDATE Appointment SET status_id = ? WHERE id = ?", (2, appointment_id))
    conn.commit()


def delete_session(session_id):
    c.execute("DELETE FROM Session WHERE id = ?", (session_id,))
    c.execute("DELETE FROM Appointment WHERE session_id = ?", (session_id,))
    conn.commit()


def cancel_appointment(session_id):
    c.execute("UPDATE Session SET status_id = ? WHERE id = ?", (1, session_id,))
    c.execute("DELETE FROM Appointment WHERE session_id = ?", (session_id,))
    conn.commit()


def send_mail(receiver, message):
    # ваши учетные данные для входа в почту
    email = '------------'
    password = '-----------'
    # информация о письме
    from_address = email
    to_address = receiver
    subject = 'Ваш код для записи'
    print(message)

    # создаем объект сообщения
    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['To'] = to_address
    msg['Subject'] = subject

    # добавляем текст сообщения
    msg.attach(MIMEText(message, 'plain'))

    # создаем SMTP объект и отправляем письмо
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email, password)
    text = msg.as_string()
    server.sendmail(from_address, to_address, text)
    server.quit()
    print('Письмо отправлено!')


if __name__ == '__main__':
    main()
