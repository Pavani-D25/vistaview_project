"""
Database migration script to add side_views_keys column
Run this if you have an existing database that needs the new column
"""
from sqlalchemy import create_engine, text
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vistaview.db")

def migrate():
    """Add side_views_keys column to products table"""
    engine = create_engine(DATABASE_URL)
    
    print("🔧 Starting database migration...")
    
    with engine.connect() as conn:
        try:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(products)"))
            columns = [row[1] for row in result]
            
            if 'side_views_keys' in columns:
                print("✅ Column 'side_views_keys' already exists. No migration needed.")
                return
            
            # Add the new column
            conn.execute(text("ALTER TABLE products ADD COLUMN side_views_keys TEXT"))
            conn.commit()
            
            print("✅ Migration complete! Added 'side_views_keys' column to products table.")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate()
