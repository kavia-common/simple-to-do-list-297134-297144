#!/usr/bin/env python3
"""Initialize SQLite database for database.

This script:
- Ensures the SQLite file exists and is accessible
- Enables PRAGMA foreign_keys=ON for the connection
- Creates base tables (app_info, users) if not present
- Creates todos table with updated_at maintenance via trigger
- Optionally seeds sample todos (if SEED_TODOS env variable is set to '1' or 'true')
- Writes db_connection.txt with correct path and usage notes
- Writes db_visualizer/sqlite.env for the local viewer
"""

import os
import sqlite3
import subprocess

DB_NAME = "myapp.db"
DB_USER = "kaviasqlite"  # Not used for SQLite, but kept for consistency
DB_PASSWORD = "kaviadefaultpassword"  # Not used for SQLite, but kept for consistency
DB_PORT = "5000"  # Not used for SQLite, but kept for consistency

print("Starting SQLite setup...")

# Check if database already exists
db_exists = os.path.exists(DB_NAME)
if db_exists:
    print(f"SQLite database already exists at {DB_NAME}")
    # Verify it's accessible
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("SELECT 1")
        conn.close()
        print("Database is accessible and working.")
    except Exception as e:
        print(f"Warning: Database exists but may be corrupted: {e}")
else:
    print("Creating new SQLite database...")

# Create/connect to database and ensure integrity settings
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Ensure foreign key enforcement is on for this connection
cursor.execute("PRAGMA foreign_keys = ON")

# Create initial schema
cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create a sample users table as an example (kept for future FKs if needed)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create todos table with updated_at, and an update trigger for updated_at
cursor.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        completed INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create trigger to auto-update updated_at on row updates (idempotent creation)
cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_todos_updated_at
    AFTER UPDATE ON todos
    FOR EACH ROW
    BEGIN
        UPDATE todos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
""")

# Insert/Update initial app_info data
cursor.execute(
    "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
    ("project_name", "database")
)
cursor.execute(
    "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
    ("version", "0.1.0")
)
cursor.execute(
    "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
    ("author", "John Doe")
)
cursor.execute(
    "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
    ("description", "")
)

# Optional seed data for todos (controlled by env var)
seed_flag = os.getenv("SEED_TODOS", "").strip().lower() in ("1", "true", "yes", "y")
if seed_flag:
    # Only seed if table is empty
    cursor.execute("SELECT COUNT(*) FROM todos")
    existing_count = cursor.fetchone()[0]
    if existing_count == 0:
        sample_todos = [
            ("Buy groceries", "Milk, eggs, bread", 0),
            ("Finish project", "Complete the todo app backend", 0),
            ("Read a book", "Spend 30 minutes reading", 0),
        ]
        for title, description, completed in sample_todos:
            cursor.execute(
                "INSERT INTO todos (title, description, completed) VALUES (?, ?, ?)",
                (title, description, completed),
            )
        print("Seeded sample todos (SEED_TODOS enabled).")
    else:
        print("Skipping seeding todos: table already has data.")
else:
    print("SEED_TODOS not enabled. Skipping todo seed data.")

conn.commit()

# Get database statistics
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
table_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM app_info")
record_count = cursor.fetchone()[0]

# Count todos
cursor.execute("SELECT COUNT(*) FROM todos")
todos_count = cursor.fetchone()[0]

conn.close()

# Save connection information to a file with usage notes
current_dir = os.getcwd()
db_abs_path = f"{current_dir}/{DB_NAME}"
connection_string = f"sqlite:///{db_abs_path}"

try:
    with open("db_connection.txt", "w") as f:
        f.write("# SQLite connection methods:\n")
        f.write(f"# Python: sqlite3.connect('{DB_NAME}')\n")
        f.write(f"# Connection string: {connection_string}\n")
        f.write(f"# File path: {db_abs_path}\n")
        f.write("# Usage notes:\n")
        f.write("# - Always enable foreign keys after connecting: cursor.execute(\"PRAGMA foreign_keys = ON\")\n")
        f.write("# - updated_at on todos is maintained by trigger 'trg_todos_updated_at'\n")
        f.write("# - Example CLI query: sqlite3 myapp.db \"SELECT * FROM todos;\"\n")
    print("Connection information saved to db_connection.txt")
except Exception as e:
    print(f"Warning: Could not save connection info: {e}")

# Create environment variables file for Node.js viewer
db_path = os.path.abspath(DB_NAME)

# Ensure db_visualizer directory exists
if not os.path.exists("db_visualizer"):
    os.makedirs("db_visualizer", exist_ok=True)
    print("Created db_visualizer directory")

try:
    with open("db_visualizer/sqlite.env", "w") as f:
        f.write(f"export SQLITE_DB=\"{db_path}\"\n")
    print("Environment variables saved to db_visualizer/sqlite.env")
except Exception as e:
    print(f"Warning: Could not save environment variables: {e}")

print("\nSQLite setup complete!")
print(f"Database: {DB_NAME}")
print(f"Location: {db_abs_path}")
print("")
print("To use with Node.js viewer, run: source db_visualizer/sqlite.env")

print("\nTo connect to the database, use one of the following methods:")
print(f"1. Python: sqlite3.connect('{DB_NAME}')  # Remember to enable PRAGMA foreign_keys")
print(f"2. Connection string: {connection_string}")
print(f"3. Direct file access: {db_abs_path}")
print("")

print("Database statistics:")
print(f"  Tables: {table_count}")
print(f"  App info records: {record_count}")
print(f"  Todos records: {todos_count}")

# If sqlite3 CLI is available, show how to use it
try:
    result = subprocess.run(['which', 'sqlite3'], capture_output=True, text=True)
    if result.returncode == 0:
        print("")
        print("SQLite CLI is available. You can also use:")
        print(f"  sqlite3 {DB_NAME}")
except Exception:
    pass

# Exit successfully
print("\nScript completed successfully.")
