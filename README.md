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

python manage.py runserver [ip]:[port]

#if run on pythonanywhere for static files in uploads, set following:
#pythonanywhere->Web->Static files->Enter URL with "/uploads/" and Enter Path with "/home/Andrewwwwww/problem_manager/uploads" 
