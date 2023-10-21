import os
import time
import threading
import psycopg2
from psycopg2 import extras
from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import GiftEvent, ConnectEvent, DisconnectEvent
from queue import Queue
import socket

PORT = int(os.environ.get("PORT", "8080"))
# Define a rate limiter class
connection = connect_to_database()
cursor = connection.cursor(cursor_factory=extras.RealDictCursor)
class RateLimiter:
    def __init__(self, rate_limit, interval):
        self.rate_limit = rate_limit
        self.interval = interval
        self.lock = threading.Lock()
        self.tokens = rate_limit
        self.last_refill_time = time.time()

    def _refill_tokens(self):
        now = time.time()
        time_elapsed = now - self.last_refill_time
        tokens_to_add = time_elapsed / self.interval
        self.tokens = min(self.rate_limit, self.tokens + tokens_to_add)
        self.last_refill_time = now

    def acquire(self):
        with self.lock:
            self._refill_tokens()
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                return False
def handle_client(client_socket):
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        # You can add logic to handle incoming data here if needed
        # For example, you can trigger actions based on the received data
        # client_socket.send(b"Received: " + data)
    client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", PORT))
    server.listen(5)
    print(f"Server listening on port {PORT}")

    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr[0]}:{addr[1]}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()
def connect_to_database():
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_user = os.environ.get("DB_USER", "")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_name = os.environ.get("DB_NAME", "tiktoklivestalker")
    try:
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name,
            sslmode='require'
        )
        return connection
    except psycopg2.Error as e:
        print("Error connecting to the database:", e)
        return None
def fetch_unique_ids():
    
    if connection is None:
        return []

    try:
        cursor.execute("SELECT unique_id FROM subjects")
        unique_ids = [row['unique_id'] for row in cursor.fetchall()]
        return unique_ids
    except psycopg2.Error as e:
        print("Error fetching unique_ids from the database:", e)
        return []

def attach_to_live(unique_id, rate_limiter):
    if rate_limiter.acquire():
        client: TikTokLiveClient = TikTokLiveClient(unique_id=f"@{unique_id}")
        @client.on("connect")
        async def on_connect(_: ConnectEvent):
                print("Connected to Room ID: ", client.room_id)
                with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                    cursor.execute('INSERT INTO live_history (room_id, unique_id, time, oper) VALUES (%s, %s, now(), %s)', (client.room_id, unique_id, 0))
                    connection.commit()
                    cursor.close()
        @client.on("gift")
        async def on_gift(event: GiftEvent):
            if event.gift.streakable and not event.gift.streaking:
                with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                    cursor.execute('INSERT INTO gifts(gift_id, count, diamond_count, room_id, streakable) VALUES (%s, %s, %s, %s, %s)', (event.gift.id,
                                                                                                                                        event.gift.count,
                                                                                                                                        event.gift.info.diamond_count,
                                                                                                                                        client.room_id,
                                                                                                                                        event.gift.streakable
                                                                                                                                        )
                                                                                                                                        )
                    connection.commit()
                    cursor.close()
            elif not event.gift.streakable:
                with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                    cursor.execute('INSERT INTO gifts(gift_id, count, diamond_count, room_id, streakable) VALUES (%s, %s, %s, %s, %s)', (event.gift.id,
                                                                                                                                        event.gift.count,
                                                                                                                                        event.gift.info.diamond_count,
                                                                                                                                        client.room_id,
                                                                                                                                        event.gift.streakable
                                                                                                                                        )
                                                                                                                                        )
                    connection.commit()
                    cursor.close()
        @client.on("disconnect")
        async def on_disconnect(event: DisconnectEvent):
            with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute('INSERT INTO live_history (room_id, unique_id, time, oper) VALUES (%s, %s, now(), %s)', (client.room_id, unique_id, 1))
                connection.commit()
                cursor.close()
            return event
        try:
            
            client.run()
        except Exception as e:
            #if e has retry_after attribute then it's a RateLimitError
            if hasattr(e, 'retry_after'):
                print(f"[Error] Rate limited: {e.retry_after} seconds")
                #retry after e.retry_after seconds
                time.sleep(int(e.retry_after))
            else:
                print(f"[Error] Can't connect to @{unique_id} room: ", e)
            return False
        return True

def subjects_attach_to_live(unique_ids, rate_limiter):
    while True:
        for unique_id in unique_ids:
            attach_to_live(unique_id, rate_limiter)

def main():

    unique_ids = fetch_unique_ids()

    # Create a rate limiter with a rate limit of 5 requests per minute (adjust as needed)
    rate_limiter = RateLimiter(1, 7)

    # Split unique_ids into groups (adjust the group size as needed)
    group_size = 3  # Number of unique_ids to process in each batch
    unique_id_groups = [unique_ids[i:i + group_size] for i in range(0, len(unique_ids), group_size)]

    threads = []
    for group in unique_id_groups:
        thread = threading.Thread(target=subjects_attach_to_live, args=(group, rate_limiter))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
if __name__ == "__main__":
    start_server()
    main()
