from flask import Flask
import lottosumoclicker
import lottowunderclicker

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello!"

@app.route("/lottosumo")
def lottosumo():
    lottosumoclicker.init()
    played_tickets = lottosumoclicker.harvest()
    return "Played " + str(played_tickets) + " tickets."

@app.route("/lottowunder")
def lottowunder():
    lottowunderclicker.init()
    played_tickets = lottowunderclicker.harvest()
    return "Played " + str(played_tickets) + " tickets."