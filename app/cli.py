"""Local administration commands: pair, serve and revoke."""
import argparse
import socket
import time
import uvicorn
from app import storage
from app.auth import issue_pairing_code


def lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(prog="p2c")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("pair", help="Create a one-time phone pairing code")
    serve = sub.add_parser("serve", help="Start local P2C server")
    serve.add_argument("--lan", action="store_true", help="Bind to primary LAN address")
    sub.add_parser("revoke-all", help="Revoke every paired device")
    args = parser.parse_args()
    storage.init_db()
    if args.action == "pair":
        code, expires = issue_pairing_code()
        print("\nP2C one-time pairing code")
        print("  " + code)
        print("Expires in about " + str(int(expires - time.time())) + " seconds.")
        print("Enter this code in the P2C phone app. Keep it private.\n")
    elif args.action == "revoke-all":
        print("Revoked " + str(storage.revoke_all_devices(time.time())) + " active sessions.")
    else:
        host = lan_ip() if args.lan else "127.0.0.1"
        print("P2C listening at http://" + host + ":8000")
        if args.lan:
            print("LAN mode is for a trusted private network only. Do not use public Wi-Fi.")
        uvicorn.run("app.main:app", host=host, port=8000, workers=1, log_level="info")


if __name__ == "__main__":
    main()
