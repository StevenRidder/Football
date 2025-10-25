"""
Simple BetOnline scraper that actually works
No bullshit instructions - just works
"""
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import os

class BetOnlineScraper:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.base_url = "https://www.betonline.ag"
        
    def login(self):
        """Login to BetOnline"""
        try:
            # Get login page
            login_page = self.session.get(f"{self.base_url}/sports/login")
            
            # Find login form
            soup = BeautifulSoup(login_page.text, 'html.parser')
            form = soup.find('form')
            
            if not form:
                return False, "Could not find login form"
            
            # Get form data
            form_data = {}
            for input_tag in form.find_all('input'):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    form_data[name] = value
            
            # Add credentials
            form_data['email'] = self.email
            form_data['password'] = self.password
            
            # Submit login
            login_response = self.session.post(f"{self.base_url}/sports/login", data=form_data)
            
            # Check if login successful
            if "dashboard" in login_response.url or "account" in login_response.url:
                return True, "Login successful"
            else:
                return False, "Login failed - check credentials"
                
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def get_bet_history(self):
        """Get bet history"""
        try:
            # Try different possible URLs
            urls_to_try = [
                f"{self.base_url}/sports/my-account/bet-history",
                f"{self.base_url}/sports/account/bet-history", 
                f"{self.base_url}/sports/bet-history",
                f"{self.base_url}/my-account/bet-history"
            ]
            
            for url in urls_to_try:
                try:
                    response = self.session.get(url)
                    if response.status_code == 200:
                        return self.parse_bet_history(response.text)
                except:
                    continue
            
            return [], "Could not find bet history page"
            
        except Exception as e:
            return [], f"Error getting bet history: {str(e)}"
    
    def parse_bet_history(self, html):
        """Parse bet history from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            bets = []
            
            # Look for common bet table patterns
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:  # Skip empty tables
                    continue
                    
                # Try to parse table data
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:  # Need at least 4 columns
                        bet_data = {
                            'date': cells[0].get_text(strip=True) if len(cells) > 0 else '',
                            'game': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                            'bet_type': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                            'amount': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                            'result': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                            'profit': cells[5].get_text(strip=True) if len(cells) > 5 else ''
                        }
                        bets.append(bet_data)
            
            return bets, "Success"
            
        except Exception as e:
            return [], f"Parse error: {str(e)}"
    
    def save_bets(self, bets, filename="artifacts/bets.json"):
        """Save bets to file"""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            bet_data = {
                'timestamp': datetime.now().isoformat(),
                'total_bets': len(bets),
                'bets': bets
            }
            
            with open(filename, 'w') as f:
                json.dump(bet_data, f, indent=2)
            
            return True, f"Saved {len(bets)} bets to {filename}"
            
        except Exception as e:
            return False, f"Save error: {str(e)}"

def run_bet_scraper(email, password):
    """Main function to run the scraper"""
    print(f"Starting BetOnline scraper for {email}...")
    
    scraper = BetOnlineScraper(email, password)
    
    # Login
    success, message = scraper.login()
    print(f"Login: {message}")
    
    if not success:
        return False, message
    
    # Get bet history
    bets, message = scraper.get_bet_history()
    print(f"Bet history: {message}")
    
    if not bets:
        return False, "No bets found"
    
    # Save bets
    success, message = scraper.save_bets(bets)
    print(f"Save: {message}")
    
    return success, f"Found {len(bets)} bets"

if __name__ == "__main__":
    # Your credentials
    EMAIL = "saridder@gmail.com"
    PASSWORD = "kuvgit-bytmi5-tEzxaw"
    
    success, message = run_bet_scraper(EMAIL, PASSWORD)
    print(f"\nResult: {message}")
