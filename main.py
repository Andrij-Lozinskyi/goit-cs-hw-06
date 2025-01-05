import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.parse import parse_qs
import pymongo
from threading import Thread

MONGO_HOST = 'mongodb'
MONGO_PORT = 27017
mongo_client = pymongo.MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
db = mongo_client["messages_db"]
collection = db["messages"]

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = self.path
        print(f"Отримано GET запит: {pr_url}")
        
        if pr_url == '/':
            self.send_html_file('index.html')
        elif pr_url == '/message.html':
            self.send_html_file('message.html')
        elif pr_url == '/style.css':
            self.send_static('style.css', 'text/css')
        elif pr_url == '/logo.png':
            self.send_static('logo.png', 'image/png')
        else:
            self.send_html_file('error.html', 404)

    def do_POST(self):
        print("Отримано POST запит")
        
        content_length = int(self.headers['Content-Length'])
        print(f"Довжина даних: {content_length}")
        
        post_data = self.rfile.read(content_length)
        print(f"Отримані сирі дані: {post_data}")
        print(f"Отримані декодовані дані: {post_data.decode()}")
        
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.sendto(post_data, ('127.0.0.1', 5000))
            client.close()
            print("Дані успішно відправлені на сокет-сервер")
            
            self.send_response(303)  
            self.send_header('Location', '/')
            self.end_headers()
            
        except Exception as e:
            print(f"Помилка при відправці даних: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self, filename, content_type):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()
        with open(f"static/{filename}", 'rb') as fd:
            self.wfile.write(fd.read())

def socket_server():
    print("Запуск socket сервера")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('', 5000)
    
    try:
        sock.bind(server_address)
        print("Socket сервер успішно запущено на порту 5000")
        
        while True:
            print("Очікування даних на socket сервері...")
            data, address = sock.recvfrom(1024)
            print(f"Отримано дані від {address}")
            
            try:
                data_str = data.decode()
                print(f"Декодовані дані: {data_str}")
                
                data_parse = parse_qs(data_str)
                print(f"Розібрані дані: {data_parse}")
                
                if 'username' in data_parse and 'message' in data_parse:
                    message = {
                        "date": datetime.now().isoformat(),
                        "username": data_parse['username'][0],
                        "message": data_parse['message'][0]
                    }
                    
                    result = collection.insert_one(message)
                    
                    if result.acknowledged:
                        print(f"Повідомлення успішно збережено з id: {result.inserted_id}")
                        saved_message = collection.find_one({"_id": result.inserted_id})
                        if saved_message:
                            print("Збережене повідомлення:")
                            print(f"Username: {saved_message['username']}")
                            print(f"Message: {saved_message['message']}")
                            print(f"Date: {saved_message['date']}")
                    else:
                        print("Помилка: Повідомлення не було збережено")
                else:
                    print("Помилка: Відсутні обов'язкові поля в даних")
                    
            except Exception as e:
                print(f"Помилка при обробці даних: {e}")
                
    except Exception as e:
        print(f"Помилка при запуску socket сервера: {e}")
    finally:
        sock.close()
        
        try:
            message = {
                "date": datetime.now().isoformat(),
                "username": data_parse['username'][0],
                "message": data_parse['message'][0]
            }
            
            result = collection.insert_one(message)
            
            if result.acknowledged:
                print(f"Повідомлення успішно збережено з id: {result.inserted_id}")
                
                saved_message = collection.find_one({"_id": result.inserted_id})
                if saved_message:
                    print("Зміст збереженого повідомлення:")
                    print(f"Username: {saved_message['username']}")
                    print(f"Message: {saved_message['message']}")
                    print(f"Date: {saved_message['date']}")
                else:
                    print("Помилка: Не вдалося прочитати збережене повідомлення")
            else:
                print("Помилка: Повідомлення не було збережено")
                
        except Exception as e:
            print(f"Помилка при збереженні повідомлення: {e}")

def run_http_server():
    server_address = ('', 3000)
    http = HTTPServer(server_address, HttpHandler)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()

def show_all_messages():
    try:
        messages = collection.find()
        print("\nВсі повідомлення в базі даних:")
        for msg in messages:
            print(f"\nID: {msg['_id']}")
            print(f"Username: {msg['username']}")
            print(f"Message: {msg['message']}")
            print(f"Date: {msg['date']}")
        print("\nЗагальна кількість повідомлень:", collection.count_documents({}))
    except Exception as e:
        print(f"Помилка при читанні повідомлень: {e}")

def main():
    show_all_messages()
    
    socket_thread = Thread(target=socket_server)
    http_thread = Thread(target=run_http_server)
    
    socket_thread.start()
    http_thread.start()

if __name__ == '__main__':
    main()
    