# lore_keeper
knowlege and experience keeper

new_run_steps:

cd lore_keeper

python -m venv venv

source venv/bin/activate   # Windows 用 venv\Scripts\activate

pip install django==4.2

python manage.py makemigrations

python manage.py makemigrations problems

python manage.py migrate

python manage.py createsuperuser

python manage.py runserver

