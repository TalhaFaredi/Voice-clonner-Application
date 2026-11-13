import os
from app import create_app

app = create_app()
if __name__=='__main__':
    from waitress import serve
    serve(app,host='127.0.0.1',port=int(os.getenv('PORT','8010')),threads=8)
