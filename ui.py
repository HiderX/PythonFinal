from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.text import Text
import time

console = Console()

def clear_screen():
    console.clear()

def display_menu():
    console.print(Panel.fit(
        "[1] 查看自选股行情 (My Watchlist)\n"
        "[2] 添加自选股 (Add Stock)\n"
        "[3] 删除自选股 (Remove Stock)\n"
        "[4] 查看个股详情 (Stock Detail)\n"
        "[5] 生成今日行情总结 (AI Summary)\n"
        "[6] 查看市场列表 (Market Overview)\n"
        "\[q] 退出 (Quit)",
        title="股票行情追踪器 (Stock Tracker)",
        border_style="bold blue"
    ))

def display_watchlist(stocks_data):
    table = Table(title="自选股行情")
    table.add_column("代码", style="cyan")
    table.add_column("名称", style="magenta")
    table.add_column("市场", style="white")
    table.add_column("最新价", justify="right")
    table.add_column("涨跌额", justify="right")
    table.add_column("涨跌幅", justify="right")
    table.add_column("成交量", justify="right")

    for stock in stocks_data:
        if "error" in stock:
            table.add_row(stock['symbol'], "Error", stock.get('market', '-'), "-", "-", "-", stock['error'], style="red")
            continue
        
        # Color for change
        change = stock.get('change', 0)
        c_percent = stock.get('change_percent', 0)
        
        if c_percent > 0:
            color = "green"
            sign = "+"
        elif c_percent < 0:
            color = "red"
            sign = ""
        else:
            color = "white"
            sign = ""
            
        price_str = f"{stock['price']:.2f}"
        change_str = f"{sign}{change:.2f}"
        percent_str = f"{sign}{c_percent:.2f}%"
        
        table.add_row(
            stock['symbol'],
            stock['name'],
            stock['market'],
            price_str,
            f"[{color}]{change_str}[/{color}]",
            f"[{color}]{percent_str}[/{color}]",
            str(stock['volume'])
        )

    console.print(table)

def display_stock_detail(stock_info, history_df):
    console.print(Panel(f"股票: {stock_info['name']} ({stock_info['symbol']})", style="bold green"))
    
    # Basic Info
    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify="right")
    grid.add_row(f"最新价: {stock_info['price']}", f"涨跌幅: {stock_info['change_percent']:.2f}%")
    console.print(grid)
    
    # History Table
    if history_df is not None and not history_df.empty:
        table = Table(title="历史行情 (最近 10 天)")
        table.add_column("日期")
        table.add_column("开盘", justify="right")
        table.add_column("收盘", justify="right")
        table.add_column("最高", justify="right")
        table.add_column("最低", justify="right")
        table.add_column("成交量", justify="right")
        
        # Take last 10 rows
        recent = history_df.tail(10)
        # Sort desc
        recent = recent.iloc[::-1]
        
        for date, row in recent.iterrows():
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
            # Compare close vs open for color
            c_color = "green" if row['Close'] >= row['Open'] else "red"
            
            table.add_row(
                date_str,
                f"{row['Open']:.2f}",
                f"[{c_color}]{row['Close']:.2f}[/{c_color}]",
                f"{row['High']:.2f}",
                f"{row['Low']:.2f}",
                str(int(row['Volume']))
            )
        console.print(table)
    else:
        console.print("[yellow]无法获取历史数据[/yellow]")

def display_summary(text):
    console.print(Panel(text, title="AI 市场总结", border_style="bold magenta"))

def get_user_input(prompt_text):
    return Prompt.ask(prompt_text)

def display_stock_list(stocks, page=1, page_size=20):
    total = len(stocks)
    start = (page - 1) * page_size
    end = start + page_size
    current_page_stocks = stocks[start:end]
    
    total_pages = (total + page_size - 1) // page_size
    
    table = Table(title=f"市场概览 (第 {page}/{total_pages} 页 - 共 {total} 只)")
    table.add_column("代码", style="cyan")
    table.add_column("名称", style="magenta")
    table.add_column("最新价", justify="right")
    table.add_column("涨跌幅", justify="right")
    table.add_column("成交量", justify="right")

    for stock in current_page_stocks:
        price = stock.get('price')
        # Handle nan/dirty data
        try:
            price = float(price)
            price_str = f"{price:.2f}"
        except:
            price_str = str(price)
            
        c_percent = stock.get('change_percent')
        try:
            c_percent = float(c_percent)
        except:
            c_percent = 0.0

        if c_percent > 0:
            color = "green"
            sign = "+"
        elif c_percent < 0:
            color = "red"
            sign = ""
        else:
            color = "white"
            sign = ""

        table.add_row(
            str(stock.get('symbol')),
            str(stock.get('name')),
            price_str,
            f"[{color}]{sign}{c_percent:.2f}%[/{color}]",
            str(stock.get('volume'))
        )
    
    console.print(table)
    console.print(f"[bold]操作提示[/bold]: \[n] 下一页, \[p] 上一页, \[q] 返回菜单")

def display_stock_list_page(stocks, page, total_pages, total_items):
    """
    Display a pre-sliced page of stock data.
    """
    table = Table(title=f"市场概览 (第 {page}/{total_pages} 页 - 共 {total_items} 只)")
    table.add_column("代码", style="cyan")
    table.add_column("名称", style="magenta")
    table.add_column("最新价", justify="right")
    table.add_column("涨跌幅", justify="right")
    table.add_column("成交量", justify="right")

    for stock in stocks:
        price = stock.get('price')
        # Handle nan/dirty data
        try:
            price = float(price)
            price_str = f"{price:.2f}"
        except:
            price_str = str(price)
            
        c_percent = stock.get('change_percent')
        try:
            c_percent = float(c_percent)
            c_str = f"{c_percent:.2f}%"
        except:
            c_percent = 0.0
            c_str = "-"

        if c_percent > 0:
            color = "green"
            sign = "+"
        elif c_percent < 0:
            color = "red"
            sign = ""
        else:
            color = "white"
            sign = ""

        table.add_row(
            str(stock.get('symbol')),
            str(stock.get('name')),
            price_str,
            f"[{color}]{sign}{c_str}[/{color}]",
            str(stock.get('volume'))
        )
    
    console.print(table)
    console.print(f"[bold]操作提示[/bold]: \[n] 下一页, \[p] 上一页, \[j] 跳转页码, \[q] 返回菜单")

def display_search_results(results):
    """
    Display search results for selection.
    """
    if not results:
        console.print("[yellow]未找到匹配的股票。[/yellow]")
        return

    table = Table(title=f"搜索结果 (共 {len(results)} 条)")
    table.add_column("序号", justify="right", style="cyan")
    table.add_column("代码", style="bold")
    table.add_column("名称", style="magenta")
    table.add_column("市场", style="white")

    for i, stock in enumerate(results):
        table.add_row(
            str(i + 1),
            stock['symbol'],
            stock['name'],
            stock['market']
        )
    
    console.print(table)
