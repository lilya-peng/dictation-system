from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1 style="color: red;">Hello, World!</h1>'

if __name__ == '__main__':
    app.run(debug=True, port=5001)