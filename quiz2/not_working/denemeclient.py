import socket
import struct
from threading import Thread
import time
import streamlit as st


class Client:
    def __init__(self, name):
        self.name = name
        self.isNameSet = False
        self.tcpClient = None

    def listen_message(self):
        while True:
            try:
                data = self.tcpClient.recv(1024)
                if data:
                    # Gelen mesajı işleyip Streamlit'te gösterilecek şekilde formatla
                    decoded_data = data.decode('utf-8')
                    st.session_state.messages.append(decoded_data)
            except socket.timeout:
                pass  # Zaman aşımında döngü devam eder

    def send_message(self, receiver, message):
        if not self.isNameSet:
            intro = struct.pack("50s50s", self.name.encode('utf-8'), self.name.encode('utf-8'))
            self.tcpClient.send(intro)
            self.isNameSet = True

        packed_data = struct.pack("50s1024s", receiver.encode('utf-8'), message.encode('utf-8'))
        self.tcpClient.send(packed_data)

    def start(self):
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        host = local_ip
        port = 2004

        self.tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcpClient.settimeout(2.0)  # Zaman aşımı ekle
        self.tcpClient.connect((host, port))

        listen_thread = Thread(target=self.listen_message)
        listen_thread.daemon = True
        listen_thread.start()


# Streamlit UI
if "client" not in st.session_state:
    st.session_state.client = None
    st.session_state.messages = []

st.title("Mesajlaşma Uygulaması")

# Kullanıcı adı girişi ve bağlanma
if st.session_state.client is None:
    name = st.text_input("Adınızı girin:", key="name_input")
    if st.button("Bağlan"):
        st.session_state.client = Client(name)
        st.session_state.client.start()
        st.success("Bağlandı!")

# Mesaj gönderme bölümü
if st.session_state.client:
    st.subheader("Mesaj Gönder")
    receiver = st.text_input("Alıcı Adı", key="receiver_input")
    message = st.text_area("Mesajınızı Yazın", key="message_input")

    if st.button("Gönder"):
        if receiver and message:
            st.session_state.client.send_message(receiver, message)
            st.success("Mesaj gönderildi!")

# Dinamik olarak alınan mesajlar bölümü
st.subheader("Alınan Mesajlar")
message_box = st.empty()  # Dinamik bir mesaj kutusu oluştur

while True:
    # Alınan mesajları sürekli olarak kontrol et ve göster
    if st.session_state.messages:
        with message_box.container():
            message_box.empty()  # Önce kutuyu temizle
            for msg in st.session_state.messages:
                try:
                    sender, text = msg.split("-", 1)  # Gönderen adı ve mesajı ayır
                    st.write(f"**{sender.strip()}** - {text.strip()}")
                except ValueError:
                    st.write(f"{msg.strip()}")  # Mesaj doğru formatta değilse direkt yazdır
    time.sleep(2)  # 2 saniyede bir kontrol et
