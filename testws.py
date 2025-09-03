import argparse

from websocket import (
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
    create_connection,
)


class WebSocketConnection:
    def __init__(self, url):
        self.url = url
        self.ws = None

    def __enter__(self, timeout=20):
        self.ws = create_connection(self.url)
        self.ws.settimeout(timeout)
        return self.ws

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ws:
            self.ws.close()


def get_ws_response(ws_url, prompt):
    with WebSocketConnection(ws_url) as ws:
        ws.send(prompt)
        try:
            while True:
                part = ws.recv()
                if part == "[END]":
                    break
                print(part, end="")
        except WebSocketTimeoutException:
            print("Operation timed out.")


def parse_args():
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser("test ws client")
    parser.add_argument(
        "--url", default="ws://0.0.0.0:9500/chatstream", type=str, help="URL to connect"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Optional input prompt. Leave empty if you want to use interactively.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.prompt is not None:
        # respond to a single prompt and exit
        try:
            get_ws_response(args.url, args.prompt)
        except Exception as e:
            print(e)
        exit()
    else:
        try:
            while True:
                prompt = input("\nEnter prompt: ")
                get_ws_response(args.url, prompt)
        except KeyboardInterrupt:
            print("\nWebSocket connection closed.")
        except WebSocketConnectionClosedException:
            print("\nConnection to remote host was lost.")
        except Exception as e:
            print("\nAn error occurred:", e)
        finally:
            if "ws" in locals() and ws.connected:
                print("\nClosing ws connection")
                ws.close()
