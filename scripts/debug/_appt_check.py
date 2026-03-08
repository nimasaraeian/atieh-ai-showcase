import sqlite3
c = sqlite3.connect('atieh_clinic.db')
idxs = c.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='appointments'").fetchall()
for i in idxs:
    print(i)
r = c.execute("SELECT COUNT(1) FROM appointments").fetchone()[0]
print("total appointments:", r)
c.close()
