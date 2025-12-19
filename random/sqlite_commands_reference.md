# SQLite CLI Commands Reference

## Essential Commands

**.help** - Shows all available commands
```
.help
```

**.tables** - List all tables
```
.tables
```

**.schema [table]** - Show table structure
```
.schema                    # All table schemas
.schema users             # Just the users table schema
```

**.dump [table]** - Export data as SQL statements
```
.dump                     # Entire database
.dump users              # Just users table
.dump > backup.sql       # Save to file
```

## Display & Formatting

**.mode** - Change output format
```
.mode column             # Nice columns (default)
.mode csv               # CSV format
.mode json              # JSON format  
.mode table             # Pretty table with borders
```

**.headers on/off** - Show/hide column headers
```
.headers on             # Show column names
.headers off            # Hide column names
```

**.width** - Set column widths for better display
```
.width 10 20 15         # Set widths for first 3 columns
```

## File Operations

**.read filename** - Execute SQL from a file
```
.read my_queries.sql
```

**.output filename** - Redirect output to file
```
.output results.txt
SELECT * FROM users;
.output stdout          # Back to screen
```

**.backup filename** - Create database backup
```
.backup my_backup.db
```

## Debugging & Analysis

**.explain on** - Show query execution plan
```
.explain on
SELECT * FROM users WHERE id = 1;
```

**.timer on** - Show query execution time
```
.timer on
SELECT * FROM big_table;
```

**.databases** - Show attached databases
```
.databases
```

## Quick Examples for Your Workout App

```bash
# Open your database
sqlite3 exercises.db

# Quick overview
.tables
.schema workout_sessions

# Check your data
.mode table
.headers on
SELECT * FROM users;

# Export a backup
.dump > workout_backup.sql

# Check query performance
.timer on
.explain on
SELECT * FROM workout_sets WHERE workout_log_id = 1;
```

## Pro Tips

- Use `.mode table` and `.headers on` for the best readable output
- Always backup your database with `.dump > backup.sql` before making major changes
- Use `.timer on` to identify slow queries in your app
- `.explain on` helps you understand if your queries are using indexes efficiently
- Commands starting with `.` are SQLite CLI commands, not SQL statements