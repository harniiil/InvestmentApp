"""External Python Libraries"""
import sqlite3
import socket
import threading
from contextlib import contextmanager
import requests
import csv
import logging
import datetime

# Defining the Host and Port to make connection
HOST = '127.0.0.1'
PORT = 8000

# This fucntion will create databse and the tables when you run the server side of the code


def create_database_and_tables():
    conn = sqlite3.connect('users.db')  # making connecting with user.db
    c = conn.cursor()  # setting the cursor

    # creating a table for user to store username and passsword data
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  balance REAL DEFAULT 0)''')

    # creating a table for user to keep track of the purchases of stock or crypto
    # the table will keep the trak of product name, amount, and the quantity
    c.execute('''CREATE TABLE IF NOT EXISTS portfolios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  market TEXT NOT NULL,
                  quantity INTEGER NOT NULL,
                  amount REAL NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (username) REFERENCES users(username))''')

    # Creating a table for tranection
    # To keep track of buy and sell items
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  transaction_type TEXT NOT NULL,
                  amount REAL NOT NULL,
                  market TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (username) REFERENCES users(username))''')

    conn.close()  # closing the connection with database


# calling the fucntion
create_database_and_tables()


@contextmanager  # allocate and release resources precisely when you want to
# to manage the opening and closing of a connection
def db_connection(database='users.db'):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    try:
        yield conn, cursor
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def handle_client(conn, addr):
    # handel the client side of the requests
    try:
        with conn:
            print(f'Connected with {addr}')
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                request = data.decode().split('|')
                action = request[0]

                if action == 'login':  # perform when user try to login
                    username = request[1]
                    password = request[2]
                    conn.sendall(authenticate(username, password).encode())

                elif action == 'register':  # perform when user try to register
                    username = request[1]
                    password = request[2]
                    conn.sendall(register_user(username, password).encode())

                elif action == 'deposit':  # perform when user try deposit money in the account
                    username = request[1]
                    amount = float(request[2])
                    response = deposit(username, amount)
                    conn.sendall(response.encode())

                elif action == 'get_balance':  # feth the amount from the client side
                    username = request[1]
                    conn.sendall(str(get_balance(username)).encode())

                elif action == 'invest':  # perform when user try to invest
                    username = request[1]
                    market = request[2]
                    quantity = int(request[3])
                    amount = float(request[4])
                    transaction_type = request[5]
                    response = invest(username, market,
                                      quantity, amount, transaction_type)
                    conn.sendall(response.encode())

                elif action == 'withdraw':  # perform when user try to withdraw money from account
                    username = request[1]
                    amount = float(request[2])
                    response = withdraw_money(username, amount)
                    conn.sendall(response.encode())

                elif action == 'sell_stock':  # perform when user make any sell from the portfolio
                    username, stock, amount = request[1], request[2], int(
                        request[3])
                    response = sell_stock(username, stock, amount)
                    conn.sendall(str(response).encode())
    except Exception as e:
        # to print the error if there is any
        print(f"Error handling client {addr}: {e}")
    finally:
        print(f'Disconnected from {addr}')  # disconnects from the client side


def deposit(username, amount):
    # Function to deposit  money
    if amount <= 0:
        return 'Deposit amount must be positive.'
    try:
        with db_connection() as (conn, db):  # make connection, execute and then commit the changes
            db.execute(
                "UPDATE users SET balance = balance + ? WHERE username = ?", (amount, username))
            conn.commit()
            return 'Deposit successful.'
    except Exception as e:
        print(f"An error occurred during the deposit operation: {e}")
        return 'Error processing the deposit.'


def withdraw_money(username, amount):
    # Function to withdraw money
    if amount <= 0:
        return 'Withdrawal amount must be positive'
    try:
        with db_connection() as (conn, db):
            db.execute("SELECT balance FROM users WHERE username = ?", (username,))
            row = db.fetchone()
            if row is None:
                return 'User not found'
            if row[0] < amount:
                return 'Insufficient funds'
            db.execute(
                "UPDATE users SET balance = balance - ? WHERE username = ?", (amount, username))
            db.execute(
                "INSERT INTO transactions (username, transaction_type, amount) VALUES (?, 'withdraw', ?)",
                (username, amount))
            conn.commit()
            return 'Withdrawal successful'
    except sqlite3.Error as e:
        return f'Database error during withdrawal: {e}'


def authenticate(username, password):
    # Function to perform authentication
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT client_id FROM users WHERE username=? AND password=?",
              (username, password))
    result = c.fetchone()  # API to fetch the data and comapre
    conn.close()
    if result:
        client_id = result[0]
        return f'Login successful, Client ID: {client_id}'
    else:
        return 'Login failed'


def register_user(username, password):
    # Function to register a new user
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:  # conditon to check if username is already in db
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (username, password))
        conn.commit()
        c.execute("SELECT client_id FROM users WHERE username=?", (username,))
        client_id = c.fetchone()[0]
        return f'Registration successful, Client ID: {client_id}'
    except sqlite3.IntegrityError:
        return 'Username already exists'
    finally:
        conn.close()


def get_balance(username):
    # Function to get balance from db
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username = ?", (username,))
    balance = c.fetchone()[0]
    conn.close()
    return balance


def invest(username, market, quantity, amount, transaction_type):
    # Function when user try to invest stocks/crypto
    try:
        with db_connection() as (conn, cursor):
            cursor.execute(
                "SELECT balance FROM users WHERE username = ?", (username,))
            balance_result = cursor.fetchone()
            if balance_result and balance_result[0] >= amount:
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE username = ?", (amount, username))
                cursor.execute("INSERT INTO portfolios (username, market, quantity, amount) VALUES (?, ?, ?, ?)",
                               (username, market, quantity, amount))
                cursor.execute("INSERT INTO transactions (username, transaction_type, amount, market) VALUES (?, ?, ?, ?)",
                               (username, transaction_type, amount, market))
                conn.commit()
                return 'Investment successful'
            else:
                return 'Insufficient funds'
    except Exception as e:
        print(f"Error during investment: {e}")
        return f'Error during investment: {e}'


def sell_stock(username, stock, quantity):
    # Function when user try to sell stocks/crypto
    conn = sqlite3.connect('users.db')
    try:
        c = conn.cursor()

        c.execute("SELECT quantity, amount FROM portfolios WHERE username=? AND market=?",
                  (username, stock))
        result = c.fetchone()
        if result and result[0] >= quantity:
            owned_qty, total_paid = result
            price_per_unit = total_paid / owned_qty if owned_qty > 0 else 0
            sale_amount = price_per_unit * quantity
            new_quantity = owned_qty - quantity
            if new_quantity > 0:
                c.execute("UPDATE portfolios SET quantity=? WHERE username=? AND market=?",
                          (new_quantity, username, stock))
            else:
                c.execute("DELETE FROM portfolios WHERE username=? AND market=?",
                          (username, stock))
            c.execute("UPDATE users SET balance = balance + ? WHERE username=?",
                      (sale_amount, username))
            c.execute("INSERT INTO transactions (username, transaction_type, amount, market) "
                      "VALUES (?, 'sell', ?, ?)", (username, sale_amount, stock))
            conn.commit()
            return {"status": "success", "message": "Stock sold successfully."}
        else:
            return {"status": "failure", "message": "Not enough stock to sell."}
    except sqlite3.Error as e:
        return {"status": "failure", "message": str(e)}
    finally:
        conn.close()


class CryptoScraper:
    # Fetches top-10 crypto data from the CoinGecko public API (no key needed)
    def __init__(self, url='https://api.coingecko.com/api/v3/coins/markets'):
        self.url = url
        self.crypto_data = []  # list of (name, price_str, market_cap_str)

    def fetch_data(self):
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 10,
            'page': 1,
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(
            self.url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        coins = response.json()
        self.crypto_data = [
            (
                coin['name'],
                f"${coin['current_price']:,.2f}",
                f"${coin['market_cap']:,}",
            )
            for coin in coins
        ]

    def write_to_csv(self, filepath='cryptocurrencies.csv'):
        # write data into a csv file
        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Name', 'Price', 'Market Cap'])
            for name, price, market_cap in self.crypto_data:
                writer.writerow([name, price, market_cap])
        print(f"Data has been written to {filepath}.")


class StockScraper:
    # Fetches stock data from the Yahoo Finance chart API (no key needed)
    def __init__(self, tick_file, output_file):
        # initialization of the class
        self.base_url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
        self.tick_file = tick_file
        self.output_file = output_file
        logging.basicConfig(filename='webscraping.log',
                            level=logging.DEBUG)  # log file

    def read_ticks(self):
        # read name of the stocks from ticks file
        try:
            with open(self.tick_file, 'r') as f:
                return [t.strip() for t in f.readlines() if t.strip()]
        except FileNotFoundError as e:
            logging.error(f"Could not read {self.tick_file} file: {e}")
            return []

    def scrape_data(self):
        # fetching data from Yahoo Finance JSON API
        tick_list = self.read_ticks()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        with open(self.output_file, 'w', newline='') as csvfile:
            # write data into csv file
            writer = csv.writer(csvfile)
            writer.writerow(['Name', 'Last Trade Time', 'Last Price'])
            for tick in tick_list:
                url = self.base_url + tick + '?interval=1d&range=1d'
                try:
                    response = requests.get(
                        url, headers=headers, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    result = data.get('chart', {}).get('result') or []
                    if not result:
                        logging.error(f"No data returned for {tick}")
                        continue
                    meta = result[0]['meta']
                    name = (meta.get('longName')
                            or meta.get('shortName') or tick)
                    price = meta.get('regularMarketPrice', 'N/A')
                    trade_time = datetime.datetime.now().strftime('%H:%M')
                    writer.writerow([name, trade_time, price])
                except requests.exceptions.RequestException as err:
                    logging.error(f"Request error for {tick}: {err}")
                except Exception as err:
                    logging.error(f"Unexpected error for {tick}: {err}")


def update_crypto_data():
    # calling the function to update crypto data
    scraper = CryptoScraper()
    scraper.fetch_data()
    scraper.write_to_csv()
    print("Cryptocurrency data updated.")


def update_stock_data():
    # calling the function to update stocks data
    scraper = StockScraper('ticks.csv', 'stocks.csv')
    scraper.scrape_data()
    print("Stock data updated.")


def start_server():
    # This Function will start the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}')

        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()


"""Main method to run the code"""
if __name__ == '__main__':
    update_stock_data()  # this process is lenghty to we are calling it first
    update_crypto_data()  # this method will run cryptoscraper
    start_server()  # this will start the server
