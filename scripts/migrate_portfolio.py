import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import setup_logger
logger = setup_logger("migrate_portfolio")


from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        logger.info("Migrating Portfolio table...")
        try:
            # Check if columns exist and add if not
            with db.engine.connect() as conn:
                # detail column
                try:
                    conn.execute(text("ALTER TABLE portfolio ADD COLUMN details TEXT"))
                    logger.info("Added 'details' column.")
                except Exception as e:
                    logger.info(f"'details' column might already exist: {e}")
                
                # features column
                try:
                    conn.execute(text("ALTER TABLE portfolio ADD COLUMN features TEXT"))
                    logger.info("Added 'features' column.")
                except Exception as e:
                    logger.info(f"'features' column might already exist: {e}")
                
                conn.commit()
            logger.info("Migration completed successfully.")
        except Exception as e:
            logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
