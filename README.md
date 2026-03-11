# lore_keeper
knowlege and experience keeper

new_run_steps:

cd lore_keeper

python3 -m venv venv

source venv/bin/activate   # Windows 用 venv\Scripts\activate

pip3 install -r requirements.txt

python3 manage.py makemigrations

python3 manage.py makemigrations problems

python3 manage.py migrate

python3 manage.py collectstatic --noinput

python3 manage.py createsuperuser

python3 manage.py runserver [ip]:[port]

#if run on pythonanywhere for static files in uploads, set following:

#pythonanywhere->Web->Static files->Enter URL with "/uploads/" and Enter Path with "/home/user/problem_manager/uploads"
