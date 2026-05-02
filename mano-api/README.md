# mano_api

1. python3 -m venv venv
2. source venv/bin/activate
3. pip install packages
4. pip freeze > requirements.txt

-----------------------------------------------------------------
first go to the your project directroy 

# Create new venv
python3 -m venv venv

# Activate it
source venv/bin/activate
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

pip install fastapi uvicorn pandas numpy scikit-learn tensorflow joblib sqlalchemy python-dotenv pymysql

python -m uvicorn main:app --reload
-------------------------------------------------------------------

swagger doc 

http://localhost:8000/docs

drop table in the Server

./venv/bin/python drop_tables.py

./venv/bin/python question_add.py
