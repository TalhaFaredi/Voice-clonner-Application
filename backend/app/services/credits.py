import time
import uuid
from flask import abort


def change(db, user_id, amount, reason, reference):
    if db.execute('SELECT 1 FROM ledger WHERE reference=?',(reference,)).fetchone():
        return False
    if db.execute('UPDATE users SET credits=credits+? WHERE id=? AND credits+?>=0',
                  (amount,user_id,amount)).rowcount != 1:
        abort(402, 'Not enough credits. Choose a plan or use less text.')
    db.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',
               (uuid.uuid4().hex,user_id,amount,reason,reference,time.time()))
    return True
