from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from kafka import KafkaProducer, KafkaConsumer
from pymongo import MongoClient
import threading
import time
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Session için bir key

# Kafka ayarları
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC_NAME = 'chat-topic'

producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Mongo ayarları
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017/")
client = MongoClient(MONGO_URI)
db = client['chatdb']
messages_collection = db['messages']

# Kafka Consumer'ı ayrı bir thread ile çalıştırarak mesajları MongoDB'ye kaydediyoruz
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
        # Mesajı MongoDB'ye kaydet
        # msg_data = {"username": ..., "message": ..., "timestamp": ...}
        messages_collection.insert_one(msg_data)

# Bu thread uygulama başlarken çalışmaya başlayacak
consumer_thread = threading.Thread(target=consume_messages, daemon=True)
consumer_thread.start()

@app.route('/sound.wav')
def serve_sound():
    return send_from_directory('templates', 'sound.wav')

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
    return render_template('chat.html', username=session['username'])

@app.route('/send', methods=['POST'])
def send_message():
    if 'username' not in session:
        app.logger.error("Kullanıcı oturum açmamış.")
        return jsonify({"error": "Not logged in"}), 403

    data = request.json
    message = data.get('message')
    if message:
        try:
            msg_data = {
                "username": session['username'],
                "message": message,
                "timestamp": time.time()
            }
            producer.send(TOPIC_NAME, msg_data)
            producer.flush()
            return jsonify({"status": "Message sent!"})
        except Exception as e:
            app.logger.error(f"Mesaj Kafka'ya gönderilemedi: {e}")
            return jsonify({"error": "Message could not be sent"}), 500
    else:
        app.logger.error("Gönderilen mesaj boş.")
        return jsonify({"error": "No message found"}), 400

@app.route('/receive', methods=['GET'])
def receive_messages():
    # İstemciden en son alınan mesajın timestamp'ını parametre olarak bekliyoruz
    last_timestamp = request.args.get('last_timestamp', 0)
    last_timestamp = float(last_timestamp)

    # last_timestamp'tan daha yeni olan mesajları getir
    msgs = list(messages_collection.find({"timestamp": {"$gt": last_timestamp}}).sort("timestamp", 1))

    response = []
    for m in msgs:
        response.append({
            "username": m['username'],
            "message": m['message'],
            "timestamp": m['timestamp']
        })
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
