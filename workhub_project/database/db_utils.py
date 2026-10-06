import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "company_database.sqlite")
MOCK_JS_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "mockData.js")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def sync_sqlite_to_mockdata():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        
        tables = ["employees", "expenses", "tasks", "leaves", "documents", "emails", "benefits"]
        db_dict = {}
        
        for table in tables:
            try:
                c.execute(f"SELECT * FROM {table}")
                rows = c.fetchall()
                db_dict[table] = [dict(row) for row in rows]
            except:
                db_dict[table] = []
    finally:
        conn.close()
    
    # Write to mockData.js
    output = "// Mock Data for WorkHub Simulation Environment\n\nconst mockData = " + json.dumps(db_dict, indent=4) + ";\n"
    with open(MOCK_JS_PATH, "w", encoding="utf-8") as f:
        f.write(output)

def _read_mock_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    tables = ["employees", "expenses", "tasks", "leaves", "documents", "emails", "benefits"]
    db_dict = {}
    
    for table in tables:
        try:
            c.execute(f"SELECT * FROM {table}")
            rows = c.fetchall()
            db_dict[table] = [dict(row) for row in rows]
        except:
            db_dict[table] = []
            
    conn.close()
    return db_dict

def _write_mock_db(db):
    conn = get_db_connection()
    c = conn.cursor()
    
    tables = ["employees", "expenses", "tasks", "leaves", "documents", "emails", "benefits"]
    for table in tables:
        # Clear existing
        try:
            c.execute(f"DELETE FROM {table}")
        except:
            pass
            
        records = db.get(table, [])
        for record in records:
            keys = list(record.keys())
            values = [record[k] for k in keys]
            placeholders = ",".join(["?"] * len(keys))
            columns = ",".join(keys)
            
            try:
                c.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)
            except sqlite3.Error as e:
                # If there's an error (like a new key not in schema), we can skip or alter
                print(f"Error inserting into {table}: {e}")
                
    conn.commit()
    conn.close()
    
    sync_sqlite_to_mockdata()

