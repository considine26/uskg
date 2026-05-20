import asyncio
import sys
from src.menu import interactive_menu

if __name__ == "__main__":
    try:
        asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        print("\n👋 用户中止程序。")
        sys.exit(0)
