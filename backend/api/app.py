from flask import Flask
from api.config import Config
from sqlalchemy import create_engine
from api.routes.sandbox import sandbox_bp

app = Flask(__name__)
app.config.from_object(Config)

# Register the blueprint
app.register_blueprint(sandbox_bp, url_prefix='/api')

if __name__ == "__main__":
    app.run(debug=True)
