"""Initialize and seed the cinema database.

Usage:
    python main.py init
    python main.py seed --admin-email you@example.com --admin-password 'your-long-password'
"""

import argparse
import os

from app import create_app
from models import db
from seed import seed_cinema


def main():
    parser = argparse.ArgumentParser(description="Screenlane database tools")
    parser.add_argument("command", nargs="?", choices=["init", "seed"], default="init")
    parser.add_argument("--admin-email", default=os.environ.get("ADMIN_EMAIL"))
    parser.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD"))
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        db.create_all()
        if args.command == "seed":
            seed_cinema(admin_email=args.admin_email, admin_password=args.admin_password)
        else:
            print("Created database tables (or kept existing tables). Use 'python main.py seed' for sample content.")


if __name__ == "__main__":
    main()
