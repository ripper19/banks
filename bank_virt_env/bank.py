import psycopg2
from psycopg2 import sql, OperationalError
import threading
from dotenv import load_dotenv
import os
from threading import RLock

import random
import datetime
from tkinter import *
import tkinter as tk
from tkinter import ttk
import logging
 #
CHECKING  = "Checking account"
SAVINGS = "Savings account"
class createAccountError(Exception):
    pass
class accountexistserror(Exception):
    pass
class DatabaseError(Exception):
    pass
load_dotenv()

class PostConnection:
    _instance = None
    def __new__(cls, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        try:
            cls._instance.conn = psycopg2.connect(
                host = DB_HOST, 
                port = DB_PORT,
                dbname = DB_NAME,
                user = DB_USER,
                password = DB_PASSWORD
            )
            cls._instance.conn.autocommit = False
        except OperationalError as e:
            raise ConnectionError(str(e))
        return cls._instance
    def get_cursor(self):
        return self.conn.cursor()
    
    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()
#
class Owner:
    def __init__(self, Fname, PiD):
        self.Fname =Fname
        self.PiD = PiD
#
class Account:
    def __init__(self, owner, acc_num, acc_type, balance =0):
        self.post = PostConnection()
        self.cursor = self.post.get_cursor()
        self.owner = owner
        self.acc_type = acc_type
        self.acc_num =acc_num    
        self.balance = balance
        
    
    def Withdraw(self,to_acc_num, amount):
        with self.bank.gen_lock:
            try:    
                self.cursor.execute(
                "SELECT 1 FROM accounts WHERE account_number = %s", (to_acc_num,)
                )
                if self.cursor.fetchone():
                    return False
            
                self.cursor.execute(
                    "UPDATE accounts SET account_balance =account_balance - %s WHERE account_number = %s AND account_balance >= %s" "RETURNING account_balance", (amount, to_acc_num, amount,)
                )
                result = self.cursor.fetchone()

                if not result:
                    raise ValueError(f"insufficient funds {result[0]}")
                self.post.commit()
                return result[0]

            except psycopg2.Error as e:
                self.post.rollback()
                raise Exception(f"Cant connect: {e.pgerror}")

        
    def Deposit(self,amount):
        self.balance+= amount
        return True
    
    def Transfer(self,amount,account_num, rec_acc_num):
        with self.bank.gen_lock:
            try:
                self.cursor.execute(
                "SELECT 1 FROM accounts where account_number =%s",(rec_acc_num,)
                )
                if self.cursor.fetchone() is None:
                    return False
                self.cursor.execute(
                    "UPDATE accounts SET account_balance = account_balance - %s WHERE account_number = %s AND account_balance >= %s",(amount,account_num,amount,)
                )
                self.cursor.execute(
                    "UPDATE accounts SET account_balance = account_balance + %s WHERE account_number = %s",(amount,account_num,)
                )
            except psycopg2.Error as e:
                self.connection.rollback()
                raise Exception(f"cant put {e.pgerror}")

class Bank:
    def __init__(self):
        self.post = PostConnection( 
        DB_HOST=os.getenv('DB_HOST'),
        DB_PORT=int(os.getenv('DB_PORT')),
        DB_NAME=os.getenv('DB_NAME'),
        DB_USER=os.getenv('DB_USER'),
        DB_PASSWORD=os.getenv('DB_PASSWORD'))

        self.cursor = self.post.get_cursor()
        self.gen_lock = RLock()
        logging.basicConfig(
            filename = "bank_errors.log",
            level = logging.ERROR,
            format = '%(acstime)s - %(levelname)s, %(message)s'
        )

    def generate(self):
        print("[DEBUG] Entered create_account")
        with self.gen_lock:
            print("[DEBUG] Acquired lock") 
            while True:
                acc_num = str(random.randint(100000,999999))
                self.cursor.execute ("SELECT 1 FROM accounts WHERE account_number = %s LIMIT 1",(acc_num,))

                if not self.cursor.fetchone():
                    return acc_num
    
    def log_error(self, err_mess):
        logging.error(err_mess)

    def check_double(self, owner, acc_type):
        try:
            self.cursor.execute(
            "SELECT 1 from accounts WHERE owner_ID = %s AND account_type = %s LIMIT 1",(owner.PiD, acc_type)
            )
            return self.cursor.fetchone() is not None
        except psycopg2.Error as e:
            self.post.rollback()
            raise DatabaseError (f"Failed to check {e.pgerror}")
        
    
    def create_account(self, owner, acc_type, balance = 0):
        with self.gen_lock:
            try:
                if self.check_double(owner, acc_type):
                    raise accountexistserror(f"Account for user{owner.Fname}, {acc_type} exists")
        
                acc_num = self.generate()
                self.cursor.execute(
    "INSERT INTO accounts (account_number, owner_name, owner_id, account_type, balance) "
    "VALUES (%s, %s, %s, %s, %s) RETURNING account_number",
    (str(acc_num), owner.Fname, owner.PiD, acc_type, float(balance))
)


                result = self.cursor.fetchone()
                self.post.commit()
                return result[0]
        
            except psycopg2.Error as e:
                self.post.rollback()
                raise createAccountError(f"Cant perform action {e.pgcode}: {e.pgerror}")
#
class checking_Account(Account):
    def __init__(self, owner, acc_num, CHECKING, balance=0):
        super().__init__(owner, acc_num, balance)

class savings_Account(Account):
    def __init__(self, owner, acc_num, balance=0, interest_rate = 0.3, waiting_period = 3):
        super().__init__(owner, acc_num,SAVINGS, balance)
        self.pending_withdrawal is None
        self.interest_rate = interest_rate
        self.waiting_period = waiting_period

    def earn_interest(self):
        interest = self.balance*self.interest_rate
        self.balance +=interest

    def request_withdraw(self,amount):
        if self.pending_withdrawal is not None:
            return False
        if amount > self.balance:
            return False
        release_date = datetime.date.today() + datetime.timedelta(days=self.waiting_period)
        self.pending_withdrawal = (amount, release_date)

    def process_request(self):
        if self.pending_withdrawal is None:
            return False
        amount, release_date = self.pending_withdrawal
        if  datetime.date.today() >= release_date:
            self.balance -= amount
            self.pending_withdrawal is None
            return True
    def interest_rate(self):
        interest = self.balance * self.interest_rate
        self.balance +=interest

#mainpage
class mainpage:
    def __init__(self):
        self.root =tk.Tk()
        self.root.title("Bankbank")
        self.setInterface()

    def setInterface(self):

        frm = ttk.Frame(self.root, padding=20)
        frm.grid()
        
        self.main_select = tk.StringVar()
        ttk.Label(frm, text="Welcome to bankbank!!What would you like to do today").grid(column=0, row=1)
        ttk.Radiobutton(frm, variable=self.main_select, value="Create account", text="Create account").grid(column=0, row=2)
        ttk.Radiobutton(frm, variable=self.main_select, value="Withdraw", text="Withdraw").grid(column=0, row=3)


        ttk.Button(text="Confirm", command=self.go_next).grid(column=0, row=5)
    
    def go_next(self):
        choice = self.main_select.get()
        self.root.destroy()

        if choice == "Create account":
            AccountFormHandler()
        else:
            mainpage()

#formtotake intodb
class AccountFormHandler():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Create Account")
        self.bank = Bank()
        print("[DEBUG] Bank initialized")
        self.setupinfo()
        self.root.mainloop()

    def setupinfo(self):
        self.form = ttk.Frame(self.root, padding=20)
        self.form.grid()
#nameentry
        ttk.Label(self.form, text="Full Name:").grid(column=0, row=1)
        self.name_entry = ttk.Entry(self.form)
        self.name_entry.grid(column=1, row=1)
#id
        ttk.Label(self.form, text="ID number").grid(column=0, row=2)
        self.id_entry = ttk.Entry(self.form)
        self.id_entry.grid(column=1, row=2)

#accttype
        self.acc_type = tk.StringVar()
        ttk.Label(self.form, text="Choose Account : ").grid(column=0, row=3)
        ttk.Radiobutton(self.form, variable=self.acc_type, value="Checking account", text="Checking Account").grid(column=0, row=4)
        ttk.Radiobutton(self.form, variable=self.acc_type, value="Savings account", text="Savings Account").grid(column=0, row=5)


        ttk.Label(self.form, text="First deposit amount: ").grid(column=0, row=6)
        self.first_depo = ttk.Entry(self.form)
        self.first_depo.grid(column=1, row=6)
        
        self.submit_button = ttk.Button(self.form, command=self.submit, text="Submit")
        self.submit_button.grid(column=0, row=7)

        self.status_bar = ttk.Label(self.form, text="")
        self.status_bar.grid(column=0, row=10, columnspan=2)

    def submit(self):
        def db_task():
            try:
                Fname = self.name_entry.get()
                PiD = self.id_entry.get()
                acc_type = self.acc_type.get()
                first_depo = float(self.first_depo.get())

                if not all([Fname, PiD, acc_type]):
                    self.status_show("Enter all details", "red")
                    return False

                print(f"[DEBUG] Data: {Fname}, {PiD}, {acc_type}, {first_depo}")

            
                owner = Owner(Fname, PiD)
                acc_num = self.bank.create_account(owner, acc_type, first_depo)

                print(f"[DEBUG] Account created: {acc_num}")

                self.root.after(0, lambda: [
                    self.status_show(f"Successfully created account {acc_num}","green"),
                    self.clearForm()
                ])

            except accountexistserror:
                self.root.after(0, lambda: [self.status_show("Account exists")])
            except createAccountError as e:
                self.root.after(0, lambda:[self.status_show("Error!!")])
                self.bank.log_error(f"Unexpected: {e}")
            except Exception as e:
                print(f"[ERROR] {str(e)}")
                self.root.after(0, lambda: [self.status_show(f"try again {str(e)}", "red")])
            finally:
                self.root.after(0, lambda: self.submit_button.config(state=tk.NORMAL))
        threading.Thread(target=db_task, daemon=True).start()
        print(f"[Thread Info] Active threads: {threading.active_count()}")

    def status_show(self, message, color):
        self.status_bar.config(text=message, foreground=color)

    def clearForm(self):
        self.name_entry.delete(0, 'end')
        self.id_entry.delete(0, 'end')
        self.acc_type.set('')
        self.first_depo.delete(0, 'end')
        self.form.after(3000, lambda: self.status_bar.config(text=""))

class WithdrawFormHandler():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Withdrawals")
        self.account = Account
        self.withdrawal_info()
        self.root.mainloop()

    def withdrawal_info(self):
        self.form = ttk.Frame(self.root, padding=20)
        self.form.grid()

        ttk.Label(self.form, text="Withdrawals").grid(column=0, row=1)

        ttk.Label(self.form, text="Account to withdraw from :")
        self.with_from_account = ttk.Entry(self.form)
        self.with_from_account.grid(column=0, row=2)

        ttk.Label(self.form, text="Amount to withdraw : ")
        self.with_amount = ttk.Entry(self.form)
        self.with_amount.grid(column=0, row=3)

        ttk.Button(self.form, text="withdraw").grid(column=0, row=4)

        self.show_status = ttk.Label(self.form, text="")
        self.show_status.grid(column=0, row= 6, columnspan=2)

    def with_dr(self):
        account_number = self.with_from_account.get()
        amount = self.with_amount.get()

        if not all([account_number, amount]):
            self.show_withdraw_status("Fill the dets","red")
            

if __name__ == "__main__":
    main = mainpage()
    main.root.mainloop()