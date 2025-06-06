#!/usr/bin/env python3
"""
Email Notifier Module for Options Trading
Handles email notifications for options trade entries and exits
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime

class OptionsEmailNotifier:
    def __init__(self):
        self.enabled = False
        self.sender = None
        self.password = None
        self.recipients = []
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
        self._load_credentials()
    
    def _load_credentials(self):
        """Load email credentials from environment file"""
        try:
            env_file = "email_credentials.env"
            if not os.path.exists(env_file):
                print("📧 Email credentials file not found, email notifications disabled")
                return
            
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "EMAIL_ALERTS_ENABLED":
                            self.enabled = value.lower() == 'true'
                        elif key == "SENDER_EMAIL":
                            self.sender = value
                        elif key == "SENDER_PASSWORD":
                            self.password = value
                        elif key == "TO_EMAILS":
                            self.recipients = [email.strip() for email in value.split(',')]
                        elif key == "SMTP_SERVER":
                            self.smtp_server = value
                        elif key == "SMTP_PORT":
                            self.smtp_port = int(value)
            
            if self.enabled:
                print(f"📧 Email notifications enabled for {len(self.recipients)} recipients")
            else:
                print("📧 Email notifications disabled in configuration")
                
        except Exception as e:
            print(f"❌ Error loading email credentials: {e}")
            self.enabled = False
    
    def test_configuration(self) -> bool:
        """
        Test email configuration
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.enabled:
            print("📧 Email notifications are disabled")
            return False
        
        if not all([self.sender, self.password, self.recipients]):
            print("❌ Email configuration incomplete")
            return False
        
        try:
            # Test SMTP connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender, self.password)
            server.quit()
            print("✅ Email configuration test successful")
            return True
        except Exception as e:
            print(f"❌ Email configuration test failed: {e}")
            return False
    
    def send_trade_notification(self, option_symbol: str, timeframe: str, action: str, 
                               price: float, signal_details: Optional[Dict] = None, 
                               pnl_info: Optional[Dict] = None) -> bool:
        """
        Send email notification for options trade entry/exit
        
        Args:
            option_symbol: Options symbol (e.g., SPY241220C00580000)
            timeframe: Trading timeframe (1min, 5min, 10min)
            action: 'ENTRY' or 'EXIT'
            price: Entry or exit price
            signal_details: Dictionary with signal information
            pnl_info: P&L information (for EXIT actions)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            return True  # Not an error if disabled
        
        try:
            # Parse option symbol for readable info
            option_info = self._parse_option_symbol(option_symbol)
            
            # Create subject
            if action == 'ENTRY':
                subject_emoji = "🟢"
                action_text = "ENTRY"
                price_info = f"${price:.4f}"
            else:  # EXIT
                if pnl_info and pnl_info.get('profit_loss', 0) >= 0:
                    subject_emoji = "📈"
                    pnl = pnl_info['profit_loss']
                    price_info = f"${price:.4f} 📈${pnl:.4f}"
                else:
                    subject_emoji = "📉"
                    pnl = pnl_info['profit_loss'] if pnl_info else 0
                    price_info = f"${price:.4f} 📉${abs(pnl):.4f}"
                action_text = "EXIT"
            
            subject = f"{subject_emoji} {option_info['symbol']} {option_info['type']} - {action_text} ({timeframe})"
            
            # Create email body
            body = f"""🚨 OPTIONS TRADE {action_text} - {option_info['symbol']} {option_info['type']}

Trade Details:
- Option Symbol: {option_symbol}
- Underlying: {option_info['symbol']}
- Option Type: {option_info['type']} (Strike: ${option_info['strike']})
- Expiry: {option_info['expiry']}
- Timeframe: {timeframe}
- Action: {action_text}
- Price: ${price:.4f}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Add signal details for ENTRY
            if action == 'ENTRY' and signal_details:
                body += f"""
Entry Signal Analysis:
- EMA(7) > VWMA(17): ✅
- ROC(8) > 0: ✅  
- MACD Line > MACD Signal: ✅
- All 3 conditions met for entry
"""
            
            # Add exit details and P&L for EXIT
            if action == 'EXIT':
                if signal_details:
                    conditions = signal_details.get('conditions_met', 0)
                    body += f"""
Exit Signal Analysis:
- Conditions triggering exit: {conditions}/3
- At least 2 exit conditions were met
"""
                
                if pnl_info:
                    entry_price = pnl_info.get('entry_price', 0)
                    exit_price = pnl_info.get('exit_price', 0)
                    profit_loss = pnl_info.get('profit_loss', 0)
                    
                    pnl_emoji = "📈" if profit_loss >= 0 else "📉"
                    pnl_status = "PROFIT" if profit_loss >= 0 else "LOSS"
                    
                    body += f"""
P&L Analysis:
- Entry Price: ${entry_price:.4f}
- Exit Price: ${exit_price:.4f}
- Profit/Loss: {pnl_emoji} ${profit_loss:.4f} ({pnl_status})
"""
            
            body += f"""
Technical Strategy:
- Entry: ALL 3 conditions (EMA>VWMA, ROC>0, MACD>Signal)
- Exit: At least 2/3 opposite conditions
- Multi-timeframe analysis (1min, 5min, 10min)

Options Portfolio:
- ATM Call/Put at current SPY price
- OTM Call/Put at SPY-$1 price
- All positions tracked independently per timeframe
"""
            
            # Send email
            return self._send_email(subject, body)
            
        except Exception as e:
            print(f"❌ Error creating trade notification: {e}")
            return False
    
    def _parse_option_symbol(self, option_symbol: str) -> Dict:
        """
        Parse option symbol to extract readable information
        
        Args:
            option_symbol: Standard option symbol (e.g., SPY241220C00580000)
            
        Returns:
            Dictionary with parsed option information
        """
        try:
            # Format: SYMBOL + YYMMDD + C/P + 8-digit strike
            symbol = option_symbol[:3]  # SPY
            date_str = option_symbol[3:9]  # 241220
            option_type = option_symbol[9]  # C or P
            strike_str = option_symbol[10:]  # 00580000
            
            # Parse date
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            expiry_date = f"{year}-{month:02d}-{day:02d}"
            
            # Parse strike price
            strike_price = int(strike_str) / 1000
            
            # Format option type
            type_full = "CALL" if option_type == "C" else "PUT"
            
            return {
                'symbol': symbol,
                'expiry': expiry_date,
                'type': type_full,
                'strike': strike_price
            }
            
        except Exception as e:
            print(f"❌ Error parsing option symbol {option_symbol}: {e}")
            return {
                'symbol': 'UNKNOWN',
                'expiry': 'UNKNOWN',
                'type': 'UNKNOWN',
                'strike': 0
            }
    
    def _send_email(self, subject: str, body: str) -> bool:
        """
        Send email with given subject and body
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender, self.password)
            text = msg.as_string()
            server.sendmail(self.sender, self.recipients, text)
            server.quit()
            
            print(f"📧 Email sent successfully to {len(self.recipients)} recipients")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def send_test_email(self) -> bool:
        """
        Send a test email to verify configuration
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            print("📧 Email notifications are disabled")
            return False
        
        subject = "🧪 Options Tracker - Email Test"
        body = """This is a test email from the Options Trading Tracker.

If you receive this email, your email notification configuration is working correctly.

System Features:
- SPY Options Tracking (Calls & Puts)
- Multi-timeframe Analysis (1min, 5min, 10min)
- Technical Indicator Signals (EMA, VWMA, MACD, ROC)
- Real-time Trade Entry/Exit Notifications
- P&L Tracking per trade

Options Strategy:
- ATM Calls/Puts at current SPY price
- OTM Calls/Puts at SPY-$1 price
- Entry: ALL 3 technical conditions must be met
- Exit: At least 2/3 opposite conditions must be met

You will receive notifications when:
- Options positions are opened (ENTRY)
- Options positions are closed (EXIT)
- P&L analysis for all closed trades

Happy options trading! 📈📉
"""
        
        return self._send_email(subject, body) 