import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import json
import threading
import time

# 配置参数
CONFIG = {
    "background": "#000080",       # 深蓝色背景
    "font_color": "yellow",        # 默认字体颜色
    "status_colors": {
        "waiting": "yellow",       # 候车状态
        "boarding": "#00FF00",     # 检票状态（亮绿色）
        "closed": "#FF0000"        # 停止检票（红色）
    },
    "refresh_interval": 10,        # 刷新频率（秒）
    "column_width": 150,           # 表格列宽
    "row_height": 40,              # 表格行高
    "max_rows": 17,                 # 表格最大显示行数
    "table_bg": "#0000FF"
}

class RealTimeScheduleSystem:
    def __init__(self, master):
        self.master = master
        self.master.title("列车状态")
        self.master.geometry("1400x781")
        self.master.configure(bg=CONFIG["background"])
        
	# 禁止用户调整窗口大小
        self.master.resizable(False, False)

        # 初始化数据
        self.schedule_data = self.load_schedule_data()
        self.current_page = 0  # 当前页码
        self.total_pages = self.calculate_total_pages()  # 总页数
        self.create_ui()
        self.start_update_thread()

    def load_schedule_data(self):
        """程序启动时自动加载数据"""
        try:
            with open("train_schedule.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"数据加载失败: {str(e)}")
            return []

    def calculate_total_pages(self):
        """计算总页数，确保每页显示完整行数"""
        total_trains = len(self.schedule_data)
        if total_trains <= CONFIG["max_rows"]:
            return 1
        # 计算总页数，确保最后一页也显示完整行数
        return (total_trains + CONFIG["max_rows"] - 1) // CONFIG["max_rows"]

    def create_ui(self):
        """创建界面组件"""
        # 主容器
        main_frame = tk.Frame(self.master, bg=CONFIG["background"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 系统标题
        title_label = tk.Label(
            main_frame,
            text="实时列车状态监控系统",
            font=("黑体", 28, "bold"),
            fg=CONFIG["font_color"],
            bg=CONFIG["background"]
        )
        title_label.pack(pady=15)

        # 状态表格
        self.create_schedule_table(main_frame)

        # 状态栏
        self.status_label = tk.Label(
            main_frame,
            text=f"最后更新时间：{datetime.now().strftime('%H:%M:%S')} | 当前页：{self.current_page + 1}/{self.total_pages}",
            font=("宋体", 12),
            fg=CONFIG["font_color"],
            bg=CONFIG["background"]
        )
        self.status_label.pack(fill=tk.X, pady=10)

    def create_schedule_table(self, parent):
        """创建带状态显示的时间表"""
        style = ttk.Style()
        style.configure("Status.Treeview",
                        rowheight=CONFIG["row_height"],
                        font=("宋体", 22),
                        foreground=CONFIG["font_color"],
                        background=CONFIG["table_bg"])
        
        # 表格列配置
        columns = ("车次", "始发站", "终到站", "计划发车时间", "开始检票时间", "停止检票时间", "当前状态")
        self.schedule_table = ttk.Treeview(
            parent,
            style="Status.Treeview",
            columns=columns,
            show="headings",
            selectmode="none"
        )

        # 配置列标题
        col_widths = [120, 180, 180, 120, 120, 120, 150]
        for idx, col in enumerate(columns):
            self.schedule_table.heading(col, text=col)
            self.schedule_table.column(col, width=col_widths[idx], anchor=tk.CENTER)

        # 状态标签配置
        self.schedule_table.tag_configure("waiting", foreground=CONFIG["status_colors"]["waiting"])
        self.schedule_table.tag_configure("boarding", foreground=CONFIG["status_colors"]["boarding"])
        self.schedule_table.tag_configure("closed", foreground=CONFIG["status_colors"]["closed"])

        self.schedule_table.pack(fill=tk.BOTH, expand=True)

    def calculate_time_status(self, departure_str):
        """计算时间相关状态"""
        now = datetime.now()
        try:
            # 解析发车时间（假设当天）
            departure_time = datetime.strptime(departure_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            
            # 计算时间节点
            time_data = {
                "start_boarding": departure_time - timedelta(minutes=20),
                "stop_boarding": departure_time - timedelta(minutes=3),
                "departure": departure_time
            }
            
            # 判断当前状态
            if now < time_data["start_boarding"]:
                status = ("waiting", "正在候车")
            elif time_data["start_boarding"] <= now < time_data["stop_boarding"]:
                status = ("boarding", "正在检票")
            elif time_data["stop_boarding"] <= now < departure_time:
                status = ("closed", "停止检票")
            else:
                status = ("closed", "已发车")
                
            return {
                "schedule_time": departure_time.strftime("%H:%M"),
                "start_boarding": time_data["start_boarding"].strftime("%H:%M"),
                "stop_boarding": time_data["stop_boarding"].strftime("%H:%M"),
                "status": status
            }
        except ValueError:
            return None

    def refresh_display(self):
        """刷新界面显示"""
        # 清空现有数据
        self.schedule_table.delete(*self.schedule_table.get_children())
        
        # 计算当前页的数据范围
        start_idx = self.current_page * CONFIG["max_rows"]
        end_idx = start_idx + CONFIG["max_rows"]
        page_data = self.schedule_data[start_idx:end_idx]
        
        # 如果当前页数据不足，补充空行
        while len(page_data) < CONFIG["max_rows"]:
            page_data.append({"车次": "", "始发站": "", "终到站": "", "发车时间": ""})
        
        # 更新每趟列车信息
        for train in page_data:
            if train["车次"]:  # 仅处理有效数据
                time_info = self.calculate_time_status(train["发车时间"])
                if not time_info:
                    continue
                    
                # 获取状态标签和显示文本
                status_tag, status_text = time_info["status"]
                
                # 插入表格数据
                self.schedule_table.insert("", "end", values=(
                    train["车次"],
                    train["始发站"],
                    train["终到站"],
                    time_info["schedule_time"],
                    time_info["start_boarding"],
                    time_info["stop_boarding"],
                    status_text
                ), tags=(status_tag,))
            else:
                # 插入空行
                self.schedule_table.insert("", "end", values=("", "", "", "", "", "", ""))
            
        # 更新状态栏
        self.status_label.config(
            text=f"上一次更新时间：{datetime.now().strftime('%H:%M:%S')} | 当前页：{self.current_page + 1}/{self.total_pages}"
        )

    def next_page(self):
        """翻到下一页"""
        self.current_page = (self.current_page + 1) % self.total_pages
        self.refresh_display()

    def start_update_thread(self):
        """启动自动更新线程"""
        def update_loop():
            while True:
                try:
                    self.refresh_display()
                    self.next_page()
                except Exception as e:
                    print(f"更新失败：{str(e)}")
                time.sleep(CONFIG["refresh_interval"])
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = RealTimeScheduleSystem(root)
    root.mainloop()