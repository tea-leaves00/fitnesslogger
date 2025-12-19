import sqlite3
from datetime import datetime

conn = sqlite3.connect("exercises.db")
c = conn.cursor()

# c.execute("""CREATE TABLE IF NOT EXISTS workout_sessions (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     session_date TEXT NOT NULL,
#     session_notes TEXT
# )""")

# c.execute("""CREATE TABLE IF NOT EXISTS workout_logs (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     session_id INTEGER NOT NULL,
#     exercise_id INTEGER NOT NULL,
#     exercise_notes TEXT,
#     FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
#     FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
# )""")



# c.execute("""CREATE TABLE IF NOT EXISTS workout_sets (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     workout_log_id INTEGER NOT NULL,
#     set_number INTEGER NOT NULL,
#     reps INTEGER NOT NULL,
#     weight REAL,  -- NULL for bodyweight exercises
#     FOREIGN KEY (workout_log_id) REFERENCES workout_logs(id) ON DELETE CASCADE
# )""")


# c.execute("""CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         first_name TEXT NOT NULL,
#         last_name TEXT NOT NULL,
#         username TEXT NOT NULL UNIQUE,
#         password TEXT NOT NULL,
#         email TEXT NOT NULL UNIQUE,
#         date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)


# c.execute("""
#     INSERT INTO users (first_name, last_name, username, password, email)
#     VALUES (?, ?, ?, ?, ?)
# """, ("Key", "Panzarella", "k_panzarella", "Monkeys123!", "test@gmail.com"))


# c.execute("UPDATE workout_sessions SET user_id = ? WHERE user_id IS NULL", (1,))


conn.commit()
conn.close()


    
# def list_muscle_groups():
#     conn = sqlite3.connect("exercises.db")
#     c = conn.cursor()
#     c.execute("SELECT * FROM muscle_groups")


#     rows = c.fetchall()
#     for row in rows:
#       print(row)

#     conn.commit()
#     conn.close()






            






















        
   











