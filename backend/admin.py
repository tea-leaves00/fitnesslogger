import sqlite3
import csv

def main_menu():
    print("\nWorkout App CLI")
    print('-' * 15)
    print("1. List all data from a table")
    print("2. Find exercises by muscle group")
    print("3. Update an exercise")
    print("4. Add a table")
    print("5. Drop a table")
    print("6. List all tables")
    print("7. List all columns for a table")
    print("8. Export to a CSV")
    print("9. Import from a CSV")
    print("10. Exit")
    choice = input("Enter your choice: ")
    return choice


def list_exercises():
    conn = sqlite3.connect("exercises.db")
    c = conn.cursor()
    log_date = '2025-02-27'
    c.execute("SELECT * FROM muscle_groups")


    rows = c.fetchall()
    for row in rows:
      print(row)

    conn.commit()
    conn.close()

def get_exercises_by_muscle_group(muscle_group_name):
    conn = sqlite3.connect("exercises.db")
    try:
        c = conn.cursor()

        # Query to find the muscle_group_id based on the provided name
        c.execute("SELECT muscle_group_id FROM muscle_groups WHERE muscle_group_name = ?", (muscle_group_name,))
        muscle_group = c.fetchone()
        
        if muscle_group is None:
            print(f"No muscle group found with the name '{muscle_group_name}'.")
            return

        muscle_group_id = muscle_group[0]

        # Query to find exercises based on the muscle_group_id
        query = """
            SELECT e.exercise_name AS exercise_name
            FROM exercise_muscle_groups emg
            JOIN exercises e ON emg.exercise_id = e.exercise_id
            WHERE emg.muscle_group_id = ?;
        """
        c.execute(query, (muscle_group_id,))
        results = c.fetchall()

        if results:
            print(f"Exercises for muscle group '{muscle_group_name}':")
            print("-" * 40)
            for row in results:
                print(row[0])
        else:
            print(f"No exercises found for muscle group '{muscle_group_name}'.")

    finally:
        conn.close()

def update_exercise_name(old_name, new_name):
    try:
        conn = sqlite3.connect("exercises.db")
        c = conn.cursor()

        # Update the exercise name
        c.execute("""
            UPDATE exercises
            SET exercise_name = ?
            WHERE exercise_name = ?;
        """, (new_name, old_name))

        conn.commit()

        if c.rowcount == 0:
            print(f"No exercise found with the name '{old_name}'.")
            return False
        else:
             print(f"Updated '{old_name}' to '{new_name}' successfully.")
             return True

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False

    finally:
        conn.close()

def create_table():
    conn = sqlite3.connect("exercises.db")
    c = conn.cursor()

    # Get the table name
    table_name = input("Enter the name of the table: ").strip()

    # Get column definitions
    print("Enter column definitions in the format 'column_name column_type'.")
    print("Type 'done' when finished.")
    columns = []
    while True:
        column = input("Column definition: ").strip()
        if column.lower() == "done":
            break
        columns.append(column)

    # Construct the CREATE TABLE query
    columns_query = ", ".join(columns)
    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_query});"

    # Execute the query
    try:
        c.execute(query)
        conn.commit()
        print(f"Table '{table_name}' created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

def drop_table(table_name):
    conn = sqlite3.connect('exercises.db')
    c = conn.cursor()

    # Only allow dropping specific tables
    valid_tables = {"exercises", "muscle_groups", "workout_sessions", "workout_logs", "workout_sets"}  # Set of allowed tables

    if table_name not in valid_tables:
        print("Invalid table name. Operation not allowed.")
        conn.close()
        return

    try:
        c.execute(f"DROP TABLE IF EXISTS {table_name}")  # Now safe
        conn.commit()
        print(f"Table '{table_name}' successfully dropped.")
    
    except sqlite3.Error as e:
        print(f"Error dropping table: {e}")

    finally:
        conn.close()

def list_tables():
    conn = sqlite3.connect("exercises.db")
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()

    conn.close()
    return [table[0] for table in tables]

def check_table_columns(table_name):
    conn = sqlite3.connect("exercises.db")
    c = conn.cursor()

    # Only allow valid table names
    
    valid_tables = list_tables()

    if table_name not in valid_tables:
        print(f"Invalid table name: '{table_name}'.")
        conn.close()
        return []

    try:
        c.execute(f"PRAGMA table_info({table_name})")
        columns = c.fetchall()
        return columns

    except sqlite3.Error as e:
        print(f"Error retrieving columns: {e}")
        return []

    finally:
        conn.close()

def export_to_csv(db_name, table_name, output_file):
    try:
        # Connect to the specified database
        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        # Fetch data from the specified table
        query = f"SELECT * FROM {table_name}"
        c.execute(query)
        rows = c.fetchall()

        # Ensure the table exists before writing to a file
        if not rows:
            print(f"Warning: Table '{table_name}' is empty or does not exist in '{db_name}'.")
            return

        # Open CSV file for writing
        with open(output_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([desc[0] for desc in c.description])  # Write headers
            writer.writerows(rows)

        print(f"Data exported from '{table_name}' in '{db_name}' to '{output_file}' successfully.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except FileNotFoundError:
        print("Error: Database file not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        conn.close()
 
def import_from_csv():
    # Prompt user for database, table, and CSV file
    db_name = input("Enter the database file (e.g., 'exercises.db'): ").strip()
    table_name = input("Enter the table name to import into: ").strip()
    csv_file = input("Enter the CSV file name (e.g., 'data.csv'): ").strip()

    try:
        # Connect to the user-specified database
        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        # Check if the table exists
        c.execute(f"PRAGMA table_info({table_name});")
        columns = c.fetchall()

        if not columns:
            print(f"Error: Table '{table_name}' does not exist in '{db_name}'.")
            return

        column_names = [col[1] for col in columns]  # Extract column names

        # Ask user how many rows they want to import (or all)
        row_limit = input("How many rows would you like to import? (Enter a number or 'all'): ").strip()
        if row_limit.lower() != "all":
            try:
                row_limit = int(row_limit)
            except ValueError:
                print("Invalid row limit. Defaulting to 'all'.")
                row_limit = "all"

        with open(csv_file, "r", newline="") as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the first row as the header

            # Ensure CSV headers match table columns
            if len(header) != len(column_names):
                print(f"Error: CSV has {len(header)} columns, but table '{table_name}' expects {len(column_names)}.")
                return

            # Build the INSERT query dynamically based on table columns
            placeholders = ", ".join("?" for _ in column_names)
            insert_query = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"

            # Insert data row-by-row, up to the limit specified
            row_count = 0
            for row in reader:
                if row_limit != "all" and row_count >= row_limit:
                    break
                c.execute(insert_query, row)
                row_count += 1

        conn.commit()
        print(f"Successfully imported {row_count} rows into '{table_name}' in '{db_name}'.")

    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        conn.close()



def run_cli():
    while True:
        choice = main_menu()

        if choice == "1":
            list_exercises()
        elif choice == "2":
            muscle_group_name = input("Enter muscle group name: ")
            get_exercises_by_muscle_group(muscle_group_name)
        elif choice == "3":
            old_exercise_name = input("Enter the curent exercise name: ")
            new_exercise_name = input("What would you like to re-name it?: ")
            update_exercise_name(old_exercise_name, new_exercise_name)
        elif choice == "4":
            create_table()
        elif choice == "5":
            table_name = input("Enter the table you'd like to drop: ").strip().lower()
            drop_table(table_name)
        elif choice == "6":
            print(list_tables())
        elif choice == "7":
            table_name = input("Enter the table name: ").strip()
            print(check_table_columns(table_name))
        elif choice == "8":
            db_name = input("Enter the database file (e.g., 'exercises.db'): ").strip()
            table_name = input("Enter the table name: ").strip()
            output_file = input("What would you like to name the file? (e.g., 'backup.csv'): ").strip()
            export_to_csv(db_name, table_name, output_file)
        elif choice == "9":
            import_from_csv()
        elif choice == "10":
            break
        else:
            print("Invalid choice. Please try again.")


run_cli()



















