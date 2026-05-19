import sys
from pathlib import Path
from ui.main_window import MainWindow
from core.assembler import load_state


def main():
    cache_dir = Path("_cachedata")
    if not cache_dir.exists():
        cache_dir.mkdir()

    cached_data = load_state()

    app = MainWindow(cached_data)
    app.mainloop()


if __name__ == "__main__":
    main()
