#!/usr/bin/env python3
"""
Migration script to create/update PostgreSQL schema.
Applies sql/schema.sql to the database.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB


def main():
    """Run schema migration."""
    print("=" * 70)
    print("PostgreSQL Schema Migration")
    print("=" * 70)
    
    try:
        # Initialize database connection
        print("\n[1] Connecting to PostgreSQL...")
        db = PostgresDB()
        print(f"✅ Connected to database")
        print(f"   Schema: {db.schema}")
        
        # Execute schema file
        print("\n[2] Applying schema...")
        schema_path = Path(__file__).parent.parent / "sql" / "schema.sql"
        
        if not schema_path.exists():
            print(f"❌ Schema file not found: {schema_path}")
            return 1
        
        print(f"   Reading: {schema_path}")
        db.execute_sql_file(str(schema_path))
        print("✅ Schema applied successfully")
        
        # Verify tables exist
        print("\n[3] Verifying tables...")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        tables = inspector.get_table_names(schema=db.schema)
        expected_tables = ['users', 'feeds', 'feed_user', 'podcasts']
        
        print(f"   Found {len(tables)} table(s) in schema '{db.schema}':")
        for table in tables:
            print(f"     ✅ {table}")
        
        missing_tables = [t for t in expected_tables if t not in tables]
        if missing_tables:
            print(f"\n⚠️  Missing tables: {missing_tables}")
            return 1
        
        print("\n✅ All tables created successfully")
        
        # Close connection
        db.close()
        
        print("\n" + "=" * 70)
        print("🎉 Migration completed successfully!")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

