"""
WSGI Entry Point for Production
"""
import os
from app_production import create_app

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

app = create_app('production')

if __name__ == "__main__":
    app.run()
