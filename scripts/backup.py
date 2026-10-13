import sqlite3
from datetime import date

def progress(status, remaining, total):
    print(f"{status}: Copied {total - remaining} of {total} pages")

def backup():
    src = sqlite3.connect("/home/tealeaves/fitnesslogger/fitnesslogger.db")
    dst = sqlite3.connect(f"/home/tealeaves/db_backup/backup_{date.today()}.db")
    try:
        src.backup(dst, pages=100, progress=progress, sleep=0.25)
    finally:
        dst.close()
        src.close()

if __name__ == "__main__":
    backup()
