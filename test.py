import psycopg2

# Set your database URL
DATABASE_URL = "postgresql://sparshmakharia:sparsh_password_1@localhost:5432/sparshmakharia"

def drop_all_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = current_schema()
                ) LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        conn.commit()

def verify_tables_empty(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = current_schema();
        """)
        tables = cur.fetchall()
        if not tables:
            print("✅ All tables deleted successfully.")
        else:
            print("⚠️ Tables still exist:", [row[0] for row in tables])
import psycopg2

DATABASE_URL = "postgresql://sparshmakharia:sparsh_password_1@localhost:5432/sparshmakharia"

def print_all_data(conn):
    with conn.cursor() as cur:
        # Get all table names in the current schema
        cur.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = current_schema();
        """)
        tables = cur.fetchall()

        if not tables:
            print("🚫 No tables found in the database.")
            return

        for table in tables:
            table_name = table[0]
            print(f"\n📄 Data from table: {table_name}")
            cur.execute(f"SELECT * FROM {table_name};")
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    print(row)
            else:
                print("  (No data)")


def main():
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            print_all_data(conn)
            drop_all_tables(conn)
            verify_tables_empty(conn)
            print_all_data(conn)
    except Exception as e:
        print("❌ Error:", e)

if __name__ == "__main__":
    main()
