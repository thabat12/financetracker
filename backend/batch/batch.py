from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from batch.config import Config

app = Flask(__name__)
database_engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

@app.route('/retrieve_transactions', methods=['POST'])
def retrieve_transactions():
    return None

if __name__ == '__main__':
    app.run()