import sys

__version__ = "2.0.0"


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--version", "-v"):
            print(f"Video Downloader Pro v{__version__}")
            return
        if sys.argv[1] in ("--help", "-h"):
            print(f"Video Downloader Pro v{__version__}")
            print("Usage: python main.py [--version | -v] [--help | -h]")
            return

    from app import App
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
