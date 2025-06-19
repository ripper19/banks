import sqlite3
import random
import datetime
from tkinter import *
import tkinter as tk
from tkinter import ttk
 #
CHECKING  = "checking account"
SAVINGS = "savings account"
class createAccountError(Exception):
    pass
class accountexistserror(Exception):
    pass
class Connection:
    _instance = None
    def __new__(cls, db_name = "accounts.db"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = sqlite3.connect(db_name)
            cls._instance.cursor = cls._instance.conn.cursor()
            cls._instance._initialize_db()
            return cls._instance
    
    def _initialize_db(self):
        query = """CREATE TABLE IF NOT EXISTS accounts(
        account_number INTEGER PRIMARY KEY,
        Oname TEXT NOT NULL,
        O_ID VARCHAR(20) UNIQUE NOT NULL,
        account_type VARCHAR NOT NULL CHECK(account_type IN('Checking account', 'Savings account')),
        balance REAL DEFAULT 0.0)"""
        self.cursor.execute(query)
        self.conn.commit()
    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
#
class Owner:
    def __init__(self, Fname, PiD):
        self.Fname =Fname
        self.PiD = PiD
#
class Account:
    def __init__(self, owner, acc_num, acc_type, balance =0):
        self.connection = Connection()
        self.cursor = self.connection.cursor
        self.owner = owner
        self.acc_type = acc_type
        self.acc_num =acc_num    
        self.balance = balance
    
    def Withdraw(self,to_acc_num, amount):
        self.cursor.execute(
            "SELECT 1 FROM accounts WHERE acc_number =", (to_acc_num)
        )
        if self.execute.fetchone():
            return False
        try:
            self.cursor.execute(
                "UPDATE acco8unts SET acc_balance - ? WHERE acc_number = ?", (amount, to_acc_num)
            )
            self.connection.commit()
        except sqlite3.Error as e:
            raise Exception(str(e))

        
    def Deposit(self,amount):
        self.balance+= amount
        return True
    
    def Transfer(self,amount, rec_acc_num):
        if amount > self.balance:
            return False
        self.cursor.execute(
            "SELECT 1 FROM accounts where account_number =? LIMIT 1",(rec_acc_num,)
        )
        if not self.execute.fetchone():
            return False
        try:
            self.cursor.execute(
                "UPDATE accounts SET balance = balance - ? WHERE account_number = ?",(amount, self.acc_num)
            )
            self.cursor.execute(
                "UPDATE accounts SET balance = balance + ? WHERE account_number =?",(amount, rec_acc_num)
            )
            self.connection.commit()
            return True 
        except sqlite3.Error:
            self.connection.rollback()
            return False

class Bank:
    def __init__(self):
        self.connection = Connection()
        self.cursor = self.connection.cursor

    def generate(self):
        while True:
            acc_num = random.randint(100000, 999999)
            self.cursor.execute("SELECT 1 FROM accounts WHERE account_number = ? LIMIT 1",(acc_num,))
            if not self.cursor.fetchone():
                return acc_num
        

    def check_double(self, owner, acc_type):
        self.cursor.execute(
            "SELECT 1 from accounts WHERE O_ID = ? AND account_type = ? LIMIT 1",(owner.PiD, acc_type)
        )
        return self.cursor.fetchone() is not None
    
    def create_account(self, owner, acc_type, balance = 0):
        if self.check_double(owner, acc_type):
            raise accountexistserror(str("Account for user exists"))
        
        try:
            acc_num = self.generate()
            self.cursor.execute(
                "INSERT INTO accounts VALUES (?,?,?,?,?)",(acc_num,owner.Fname,owner.PiD,acc_type,balance)
            )
            self.connection.conn.commit()
            return acc_num
        except sqlite3.Error as e:
            self.connection.conn.rollback()
            raise createAccountError(str(e))
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
        
        ttk.Button(self.form, command=self.submit, text="Submit").grid(column=0, row=7)

        self.status_bar = ttk.Label(self.form, text="")
        self.status_bar.grid(column=0, row=10, columnspan=2)

    def submit(self):
        Fname = self.name_entry.get()
        PiD = self.id_entry.get()
        acc_type = self.acc_type.get()
        first_depo = self.first_depo.get()

        if not all([Fname, PiD, acc_type]):
            self.status_show("Enter all details", "red")
            return False
        try :
            owner = Owner(Fname, PiD)
            acc_num = self.bank.create_account(owner, acc_type, first_depo)
            self.status_show(f"Account{acc_num}created for{Fname} account balance is {first_depo}", "green")
            self.clearForm()

        except accountexistserror:
            self.status_show("Account exists", "red")
        except createAccountError as e:
            self.status_show(f"Account creation failed!!: {e}", "red")

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