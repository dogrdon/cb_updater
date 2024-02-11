import os
import gspread
import requests
import hmac
import hashlib
import time
from requests.auth import AuthBase


class CoinbaseAuth(AuthBase):
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def __call__(self, request):
        timestamp = str(int(time.time()))
        message = timestamp + request.method + request.path_url + (request.body or '')
        signature = hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()


        request.headers.update({
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
        })
        return request

def get_spot_price(currency_pair):
    response = requests.get(f"{api_url}prices/{currency_pair}/spot")
    if response.ok:
        return response.json()
    else:
        print("Error:", response.text)
        return None


sa_path = os.path.abspath("./service_account.json")
print(f"using: {sa_path}")
# connect to Google Sheets - service account key json file needs to be at ~/.config/gspread/service_account.json
gspread_client = gspread.service_account(filename=sa_path)
#gspread_client = gspread.service_account()
# list all available spreadsheets
spreadsheets = gspread_client.openall()
if spreadsheets:
    print("Available spreadsheets:")
    for spreadsheet in spreadsheets:
        print(f"Title: {spreadsheet.title} URL: {spreadsheet.url}")
else:
    print("No spreadsheets available")
    print("Please share the spreadsheet with Service Account email")
    print(gspread_client.auth.signer_email)

budget = gspread_client.open("Upcoming Bills and Budgeting").sheet1


# Before implementation, set environmental variables with the names API_KEY and API_SECRET
coinbase_API_key = os.environ.get('coinbase_API_key')
coinbase_API_secret = os.environ.get('coinbase_API_secret')

# API Url
api_url = 'https://api.coinbase.com/v2/'

# Create auth object

def main(coinbase_API_key, coinbase_API_secret):
    auth = CoinbaseAuth(coinbase_API_key, coinbase_API_secret)

    # Get Balances
    response = requests.get(api_url + 'accounts', auth=auth)
    if response.ok:
        accounts = response.json()
    else:
        print("Error:", response.text)
        accounts = None
    total = 0

    if accounts:
        for wallet in accounts['data']:
            wallet_abbrv = wallet['name'].split()[0]
            account_type = wallet['type']
            current_wallet_amount = float(wallet['balance']['amount'])
            if account_type == "wallet" and current_wallet_amount > 0:
                wallet_spot_price_id = str(f"{wallet_abbrv}-USD")
                wallet_spot_price = float(get_spot_price(currency_pair=wallet_spot_price_id)['data']['amount'])
                print(
                    f"Getting values for {wallet['name']}. Balance = {current_wallet_amount}. Price = {wallet_spot_price}"
                )
                total += float(current_wallet_amount * wallet_spot_price)
                if wallet_abbrv == "XTZ":
                    budget.update_cell(3, 7, wallet_spot_price)

            elif account_type == "fiat":
                print(
                    f"Getting values for fiat (Cash) {wallet['name']}. Balance = {current_wallet_amount}."
                )
                total += float(current_wallet_amount)
        print(f"Total balance for portfolio = {total}")
        print("Writing Portfolio Balance to Sheet Cell.")
        budget.update_cell(2, 7, total)
    else:
        print("No accounts data.")


if __name__ == '__main__':
    main(coinbase_API_key, coinbase_API_secret)