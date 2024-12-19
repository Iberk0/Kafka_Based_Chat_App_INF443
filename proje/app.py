from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from kafka import KafkaProducer, KafkaConsumer
from pymongo import MongoClient
import threading
import time
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Kafka ve MongoDB ayarları
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC_NAME = 'chat-topic'
producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017/")
client = MongoClient(MONGO_URI)
db = client['chatdb']
messages_collection = db['messages']

# Kafka Consumer Thread'i
def consume_messages():
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='chat-group',
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    for message in consumer:
        msg_data = message.value
        messages_collection.insert_one(msg_data)

consumer_thread = threading.Thread(target=consume_messages, daemon=True)
consumer_thread.start()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['username'] = username
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    users = messages_collection.distinct("sender")  # Veritabanındaki kullanıcıları listele
    return render_template('chat.html', username=session['username'], users=users)

@app.route('/send', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 403

    data = request.json
    message = data.get('message')
    recipient = data.get('recipient', 'all')
    sender = session['username']

    if message:
        # Kullanıcı doğrulaması: Genel sohbet dışında mesaj gönderen ve alıcı kontrolü
        if recipient != "all" and recipient == sender:
            return jsonify({"error": "Cannot send messages to yourself."}), 400

        try:
            msg_data = {
                "sender": sender,
                "recipient": recipient,
                "message": message,
                "timestamp": time.time()
            }
            producer.send(TOPIC_NAME, msg_data)
            producer.flush()
            return jsonify({"status": "Message sent!"})
        except Exception as e:
            return jsonify({"error": f"Message could not be sent: {str(e)}"}), 500
    else:
        return jsonify({"error": "No message found"}), 400


@app.route('/receive', methods=['GET'])
def receive_messages():
    last_timestamp = float(request.args.get('last_timestamp', 0))
    recipient = request.args.get('recipient', 'all')
    sender = session['username']

    # Mesajları filtrele: Genel sohbet veya iki kullanıcı arasındaki özel mesajlar
    filter_query = {"timestamp": {"$gt": last_timestamp}}
    if recipient == "all":
        filter_query["recipient"] = "all"  # Genel sohbet
    else:
        filter_query["$or"] = [
            {"sender": sender, "recipient": recipient},
            {"sender": recipient, "recipient": sender}
        ]

    msgs = list(messages_collection.find(filter_query).sort("timestamp", 1))

    response = []
    for m in msgs:
        response.append({
            "sender": m['sender'],
            "recipient": m['recipient'],
            "message": m['message'],
            "timestamp": m['timestamp']
        })
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
