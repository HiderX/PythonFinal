import sys
import os
from dotenv import load_dotenv
from rich.console import Console
import time

# Load env before imports if needed, though most classes load on init
load_dotenv()

from ui import display_menu, display_watchlist, display_stock_detail, display_summary, get_user_input, clear_screen, console
from stock_data import StockDataProvider
from watchlist import WatchlistManager
from ai_summarizer import MarketSummarizer

def main():
    # Initialize components
    watchlist_mgr = WatchlistManager()
    
    # Check if PROXIES is set, if so enable proxy
    use_proxy = os.getenv("PROXIES") is not None
    stock_provider = StockDataProvider(use_proxy=use_proxy)
    
    summarizer = MarketSummarizer()

    while True:
        clear_screen()
        display_menu()
        choice = get_user_input("[bold green]请输入选项[/bold green]")

        if choice == '1':
            # View Watchlist
            stocks = watchlist_mgr.get_watchlist()
            if not stocks:
                console.print("[yellow]自选股列表为空，请先添加股票。[/yellow]")
            else:
                with console.status("[bold green]正在加载自选股数据...[/bold green]"):
                    # Use batch fetching
                    stocks_data = stock_provider.get_prices_batch(stocks)
                display_watchlist(stocks_data)
            get_user_input("\n按回车键返回...")

        elif choice == '2':
            # Add Stock
            symbol = get_user_input("请输入股票代码 (例如 AAPL 或 600519): ")
            market = get_user_input("请输入市场 (US 或 CN): ").upper()
            if market not in ['US', 'CN']:
                console.print("[red]无效的市场。请输入 US 或 CN。[/red]")
            else:
                watchlist_mgr.add_stock(symbol, market)
                console.print(f"[green]已添加 {symbol} 到自选股。[/green]")
            get_user_input("\n按回车键返回...")

        elif choice == '3':
            # Remove Stock
            symbol = get_user_input("请输入要删除的股票代码: ")
            watchlist_mgr.remove_stock(symbol)
            console.print(f"[green]已从自选股删除 {symbol}。[/green]")
            get_user_input("\n按回车键返回...")

        elif choice == '4':
            # Detail
            symbol = get_user_input("请输入股票代码: ")
            market = get_user_input("请输入市场 (US 或 CN): ").upper()
            
            with console.status(f"[bold green]正在获取 {symbol} 详情...[/bold green]"):
                price_data = stock_provider.get_price(symbol, market)
                
                if price_data and "error" not in price_data:
                    history = stock_provider.get_history(symbol, market, period="1mo")
                    display_stock_detail(price_data, history)
                else:
                    err = price_data.get('error') if price_data else "Unknown error"
                    console.print(f"[red]获取数据失败: {err}[/red]")
            
            get_user_input("\n按回车键返回...")

        elif choice == '5':
            # AI Summary
            stocks = watchlist_mgr.get_watchlist()
            if not stocks:
                console.print("[yellow]自选股为空，无法生成总结。[/yellow]")
            else:
                with console.status("[bold green]正在获取数据并生成 AI 总结...[/bold green]"):
                    stocks_data = stock_provider.get_prices_batch(stocks)
                    summary = summarizer.summarize_market(stocks_data)
                display_summary(summary)
            get_user_input("\n按回车键返回...")

        elif choice == '6':
            # Stock List & Pagination
            market = get_user_input("请输入市场 (US 或 CN): ").upper()
            if market not in ['US', 'CN']:
                console.print("[red]无效的市场。请输入 US 或 CN。[/red]")
                time.sleep(1)
                continue

            with console.status(f"[bold green]正在加载 {market} 市场列表...[/bold green]"):
                full_list = stock_provider.get_stock_list(market)
            
            if not full_list:
                console.print("[red]列表为空或加载失败。[/red]")
                get_user_input("\n按回车键返回...")
                continue
                
            page = 1
            page_size = 20
            
            from ui import display_stock_list # Local import to ensure it picks up new function if module reload issues
            
            while True:
                clear_screen()
                display_stock_list(full_list, page, page_size)
                
                nav = get_user_input("请输入指令: ").lower()
                
                if nav == 'n':
                    # Next
                    total_pages = (len(full_list) + page_size - 1) // page_size
                    if page < total_pages:
                        page += 1
                elif nav == 'p':
                    # Prev
                    if page > 1:
                        page -= 1
                elif nav == 'q':
                    break
                else:
                    # Refresh or check if user entered page number? For now just refresh
                    pass

        elif choice.lower() == 'q':
            console.print("再见！")
            break
        else:
            console.print("[red]无效选项，请重试。[/red]")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]程序已终止。[/yellow]")
        sys.exit(0)
