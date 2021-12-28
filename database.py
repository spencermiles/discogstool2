import sqlite3
import util
import pickle
import os
import datetime
import multiprocessing

db_lock = multiprocessing.Lock()

def data2blob(data):
    return sqlite3.Binary(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))

def blob2data(blob):
    return pickle.loads(blob)

def get_ts():
    return str(datetime.date.today())

def ts_age(ts):
    d = datetime.date(*[int(i) for i in ts.split("-")])
    return (datetime.date.today() - d).days

class DiscogsDatabase:
    def __init__(self, max_age=7):
        with db_lock:
            db_file = util.userfile("discogs.db")
            create_flag = not os.path.exists(db_file)
            self.conn = sqlite3.connect(db_file)
            # fetch rows as dictionaries
            self.conn.row_factory = sqlite3.Row

            # maximum data age
            self.max_age = max_age

            if create_flag:
                print("Creating new database.")
                c = self.conn.cursor()
                c.execute('''CREATE TABLE responses (key TEXT PRIMARY KEY,
                                                    last_update TEXT,
                                                    data BLOB)''')
                c.execute('''CREATE TABLE posted (id INTEGER PRIMARY KEY,
                                                price REAL,
                                                count INTEGER,
                                                sales_hi REAL,
                                                sales_lo REAL,
                                                sales_avg REAL,
                                                sales_mdn REAL,
                                                date TEXT)''')
                self.conn.commit()

    def get(self, key):
        c = self.conn.cursor()
        c.execute("SELECT * FROM responses where key=?", (repr(key),))
        r = c.fetchone()
        if not r:
            return None
        return blob2data(r["data"])

    def delete(self, key):
        c = self.conn.cursor()
        c.execute("DELETE FROM responses where key=?", (repr(key),))
        self.conn.commit()

    def put(self, key, value):
        c = self.conn.cursor()
        key = repr(key)
        b = data2blob(value)
        ts = get_ts()
        c.execute("INSERT INTO responses VALUES (?,?,?)",
                (key, ts, b))
        self.conn.commit()

    def get_posted(self, releaseid):
        c = self.conn.cursor()
        c.execute("SELECT * FROM posted WHERE id=? ORDER BY date DESC", (releaseid,))
        return c.fetchall()

    def get_last_posted(self, releaseid, max_age=0):
        results = self.get_posted(releaseid)
        if not results:
            return None
        recent = results[0]
        if max_age and ts_age(recent["date"]) <= max_age:
            return recent
        return None

    def put_posted(self, releaseid, price, count, sales_hi,
                sales_lo, sales_avg, sales_mdn):
        c = self.conn.cursor()
        ts = get_ts()
        c.execute("INSERT INTO posted VALUES (?,?,?,?,?,?,?,?)",
                (releaseid, price, count, sales_hi, sales_lo,
                    sales_avg, sales_mdn, ts))
        self.conn.commit()
