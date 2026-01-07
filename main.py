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
    
    # Initialize provider (uses system proxy if configured in env)
    stock_provider = StockDataProvider()
    
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
            # Add Stock with Fuzzy Search
            from ui import display_search_results
            
            keyword = get_user_input("请输入股票名称或代码 (直接添加请按 D)").strip()
            
            if keyword.upper() == 'D':
                # Direct Entry Mode
                symbol = get_user_input("请输入股票代码 (例如 AAPL 或 600519)")
                market = get_user_input("请输入市场 (US 或 CN)").upper()
                if market not in ['US', 'CN']:
                    console.print("[red]无效的市场。[/red]")
                else:
                    watchlist_mgr.add_stock(symbol, market)
                    console.print(f"[green]已添加 {symbol} 到自选股。[/green]")
            else:
                # Search Mode
                with console.status(f"[bold green]正在搜索 '{keyword}'... (首次搜索可能较慢)[/bold green]"):
                    matches = stock_provider.search_stocks(keyword)
                
                if matches:
                    display_search_results(matches)
                    idx_str = get_user_input("请输入序号进行添加 (或输入 0 取消)")
                    if idx_str.isdigit():
                        idx = int(idx_str)
                        if 1 <= idx <= len(matches):
                            selected = matches[idx-1]
                            watchlist_mgr.add_stock(selected['symbol'], selected['market'])
                            console.print(f"[green]已添加 {selected['name']} ({selected['symbol']}) 到自选股。[/green]")
                        elif idx == 0:
                            console.print("[yellow]已取消。[/yellow]")
                        else:
                             console.print("[red]无效的序号。[/red]")
                    else:
                        console.print("[red]无效的输入。[/red]")
                else:
                    console.print("[red]未找到相关股票。[/red]")
                    if get_user_input("是否尝试直接添加代码? (y/n)").lower() == 'y':  # Fixed colon here
                        symbol = get_user_input("请输入股票代码")
                        market = get_user_input("请输入市场 (US 或 CN)").upper()
                        if market in ['US', 'CN']:
                             watchlist_mgr.add_stock(symbol, market)
                             console.print(f"[green]已添加 {symbol} 到自选股。[/green]")

            get_user_input("\n按回车键返回...")

        elif choice == '3':
            # Remove Stock
            symbol = get_user_input("请输入要删除的股票代码")
            watchlist_mgr.remove_stock(symbol)
            console.print(f"[green]已从自选股删除 {symbol}。[/green]")
            get_user_input("\n按回车键返回...")

        elif choice == '4':
            # Detail
            symbol = get_user_input("请输入股票代码")
            market = get_user_input("请输入市场 (US 或 CN)").upper()
            
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
            while True:
                market = get_user_input("请输入市场 (US 或 CN)").upper()
                if market in ['US', 'CN', 'Q']:
                    break
                console.print("[red]无效的市场。请输入 US 或 CN (输入 Q 返回)。[/red]")
            
            if market == 'Q':
                continue

            with console.status(f"[bold green]正在加载 {market} 市场代码列表...[/bold green]"):
                all_tickers = stock_provider.get_market_tickers(market)
            
            if not all_tickers:
                 console.print(f"[red]无法获取 {market} 市场列表或列表为空。[/red]")
                 get_user_input("\n按回车键返回...")
                 continue
                 


            page = 1
            page_size = 20
            
            from ui import display_stock_list 
            
            while True:
                clear_screen()
                # Pagination Logic: Slice first, then fetch prices
                total_pages = (len(all_tickers) + page_size - 1) // page_size
                start = (page - 1) * page_size
                end = start + page_size
                page_tickers = all_tickers[start:end]
                
                with console.status(f"[bold blue]正在获取第 {page}/{total_pages} 页行情...[/bold blue]"):
                    page_data = stock_provider.get_prices_batch(page_tickers)
                
                # Display the page
                from ui import display_stock_list_page
                display_stock_list_page(page_data, page, total_pages, len(all_tickers))
                
                nav = get_user_input("请输入指令").lower()
                
                if nav == 'n':
                    if page < total_pages:
                        page += 1
                elif nav == 'p':
                    if page > 1:
                        page -= 1
                elif nav == 'j':
                    target = get_user_input(f"请输入跳转页码 (1-{total_pages})")
                    if target.isdigit():
                        p = int(target)
                        if 1 <= p <= total_pages:
                            page = p
                        else:
                            console.print(f"[red]页码超出范围 (1-{total_pages})[/red]")
                            time.sleep(1)
                    else:
                         console.print("[red]无效的页码[/red]")
                         time.sleep(1)
                elif nav == 'q':
                    break
                else:
                    pass

                    pass

        elif choice == '7':
            # Market Analysis (Overall)
            from ui import display_market_analysis
            
            with console.status("[bold green]正在获取主要指数数据并生成市场综述...[/bold green]"):
                indices_data = stock_provider.get_market_indices()
                summary = summarizer.summarize_overall_market(indices_data)
                
            display_market_analysis(indices_data, summary)
            get_user_input("\n按回车键返回...")

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
