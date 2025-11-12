import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import json
import random
import math
from pathlib import Path


class ELOSystem:
    """ELO评分系统核心类"""
    
    def __init__(self, k_factor=16, initial_rating=1400):
        """
        初始化ELO系统
        :param k_factor: K因子，影响评分变化幅度（论文设定值：16）
        :param initial_rating: 初始评分（论文设定值：1400）
        """
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.ratings = {}  # {图像路径: ELO分数}
        self.comparison_counts = {}  # {图像路径: 比对次数}
        
        # 收敛判断相关数据
        self.rating_history = []  # 记录每轮后的分数快照 [{图像路径: 分数}, ...]
        self.rating_changes = []  # 记录每轮的最大/平均分数变化量
    
    def add_image(self, image_path):
        """添加新图像到系统"""
        if image_path not in self.ratings:
            self.ratings[image_path] = self.initial_rating
            self.comparison_counts[image_path] = 0
    
    def update_ratings(self, winner_path, loser_path):
        """
        根据比赛结果更新ELO分数
        :param winner_path: 获胜图像路径
        :param loser_path: 失败图像路径
        """
        winner_rating = self.ratings.get(winner_path, self.initial_rating)
        loser_rating = self.ratings.get(loser_path, self.initial_rating)
        
        # 计算期望得分
        expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
        expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))
        
        # 更新分数
        self.ratings[winner_path] = winner_rating + self.k_factor * (1 - expected_winner)
        self.ratings[loser_path] = loser_rating + self.k_factor * (0 - expected_loser)
        
        # 更新比对次数
        self.comparison_counts[winner_path] = self.comparison_counts.get(winner_path, 0) + 1
        self.comparison_counts[loser_path] = self.comparison_counts.get(loser_path, 0) + 1
    
    def update_ratings_draw(self, path_a, path_b):
        """
        根据平局结果更新ELO分数（S_A = S_B = 0.5）
        :param path_a: 图像A路径
        :param path_b: 图像B路径
        """
        rating_a = self.ratings.get(path_a, self.initial_rating)
        rating_b = self.ratings.get(path_b, self.initial_rating)
        
        # 计算期望得分
        expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))
        
        # 平局时 S_A = S_B = 0.5，对称更新
        self.ratings[path_a] = rating_a + self.k_factor * (0.5 - expected_a)
        self.ratings[path_b] = rating_b + self.k_factor * (0.5 - expected_b)
        
        # 更新比对次数
        self.comparison_counts[path_a] = self.comparison_counts.get(path_a, 0) + 1
        self.comparison_counts[path_b] = self.comparison_counts.get(path_b, 0) + 1
    
    def get_rating(self, image_path):
        """获取图像的ELO分数"""
        return self.ratings.get(image_path, self.initial_rating)
    
    def get_comparison_count(self, image_path):
        """获取图像的比对次数"""
        return self.comparison_counts.get(image_path, 0)
    
    def record_rating_snapshot(self):
        """记录当前分数快照"""
        snapshot = self.ratings.copy()
        self.rating_history.append(snapshot)
        
        # 如果历史记录超过100轮，只保留最近100轮
        if len(self.rating_history) > 100:
            self.rating_history = self.rating_history[-100:]
    
    def calculate_rating_changes(self):
        """计算分数变化量（最大和平均）"""
        if len(self.rating_history) < 2:
            return None, None
        
        # 获取最近两轮的分数
        current_ratings = self.rating_history[-1]
        previous_ratings = self.rating_history[-2]
        
        # 计算所有图像分数变化的绝对值
        changes = []
        all_images = set(current_ratings.keys()) | set(previous_ratings.keys())
        
        for img_path in all_images:
            current = current_ratings.get(img_path, self.initial_rating)
            previous = previous_ratings.get(img_path, self.initial_rating)
            change = abs(current - previous)
            changes.append(change)
        
        if not changes:
            return None, None
        
        max_change = max(changes)
        avg_change = sum(changes) / len(changes)
        
        # 记录变化量
        self.rating_changes.append({'max': max_change, 'avg': avg_change})
        if len(self.rating_changes) > 100:
            self.rating_changes = self.rating_changes[-100:]
        
        return max_change, avg_change
    
    def calculate_rank_stability(self):
        """计算排名稳定性（Spearman相关系数）"""
        if len(self.rating_history) < 2:
            return None
        
        # 获取最近两轮的分数
        current_ratings = self.rating_history[-1]
        previous_ratings = self.rating_history[-2]
        
        # 获取所有图像
        all_images = list(set(current_ratings.keys()) | set(previous_ratings.keys()))
        
        if len(all_images) < 2:
            return None
        
        # 计算当前排名
        current_ranked = sorted(all_images, 
                               key=lambda x: current_ratings.get(x, self.initial_rating), 
                               reverse=True)
        # 计算上一轮排名
        previous_ranked = sorted(all_images, 
                                key=lambda x: previous_ratings.get(x, self.initial_rating), 
                                reverse=True)
        
        # 计算Spearman相关系数
        # 创建排名字典
        current_ranks = {img: i+1 for i, img in enumerate(current_ranked)}
        previous_ranks = {img: i+1 for i, img in enumerate(previous_ranked)}
        
        # 计算排名差
        rank_diffs = []
        for img in all_images:
            current_rank = current_ranks.get(img, len(all_images))
            previous_rank = previous_ranks.get(img, len(all_images))
            rank_diffs.append((current_rank - previous_rank) ** 2)
        
        # Spearman相关系数公式: 1 - (6 * sum(d^2)) / (n * (n^2 - 1))
        n = len(all_images)
        if n < 2:
            return None
        
        sum_d_squared = sum(rank_diffs)
        spearman_rho = 1 - (6 * sum_d_squared) / (n * (n * n - 1))
        
        return spearman_rho
    
    def set_parameters(self, k_factor, initial_rating):
        """设置ELO参数"""
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        # 更新所有已有图像的初始分数（如果它们还是初始值）
        for path in self.ratings:
            if self.ratings[path] == self.initial_rating:
                self.ratings[path] = initial_rating


class ImageViewerWindow:
    """图像详情查看窗口"""
    
    def __init__(self, parent, image_path):
        self.window = tk.Toplevel(parent)
        self.window.title(f"图像详情 - {os.path.basename(image_path)}")
        
        # 尝试最大化窗口（跨平台兼容）
        try:
            self.window.state('zoomed')  # Windows
        except:
            try:
                self.window.attributes('-zoomed', True)  # Linux
            except:
                # macOS: 设置窗口大小为屏幕大小
                screen_width = self.window.winfo_screenwidth()
                screen_height = self.window.winfo_screenheight()
                self.window.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # 创建画布用于显示图像
        self.canvas = tk.Canvas(self.window, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.image_path = image_path
        self.original_image = None
        self.photo = None
        
        # 绑定窗口大小变化事件
        self.window.bind('<Configure>', lambda e: self.resize_image())
        
        # 延迟加载图像，确保窗口已完全初始化
        self.window.after(100, self.load_image, image_path)
    
    def load_image(self, image_path):
        """加载图像"""
        try:
            self.original_image = Image.open(image_path)
            self.resize_image()
        except Exception as e:
            messagebox.showerror("错误", f"无法加载图像: {str(e)}")
    
    def resize_image(self, event=None):
        """调整图像大小以适应窗口"""
        if self.original_image is None:
            return
        
        # 获取画布大小
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # 如果窗口还没准备好，延迟重试
            self.window.after(50, self.resize_image)
            return
        
        # 计算缩放比例
        img_width, img_height = self.original_image.size
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        scale = min(scale_w, scale_h)
        
        # 缩放图像
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 转换为PhotoImage并显示
        self.photo = ImageTk.PhotoImage(resized_image)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, 
                                image=self.photo, anchor=tk.CENTER)


class MatchWindow:
    """匹配界面窗口"""
    
    def __init__(self, parent, elo_system, image_list, update_callback, gui_instance):
        self.window = tk.Toplevel(parent)
        self.window.title("图像匹配")
        self.window.geometry("1200x800")
        
        self.elo_system = elo_system
        self.image_list = image_list
        self.update_callback = update_callback
        self.gui_instance = gui_instance  # 主界面实例，用于更新比较计数
        
        # 当前匹配的图像对
        self.current_pair = None
        
        # 覆盖功能相关
        self.overlay_canvas = None  # 覆盖层canvas
        self.left_photo = None  # 左图的photo引用
        self.is_overlaying = False  # 是否正在覆盖
        
        # 创建界面
        self.create_widgets()
        
        # 绑定窗口大小变化事件
        self.window.bind('<Configure>', lambda e: self.on_window_resize())
        
        # 绑定键盘事件（空格键覆盖功能）
        self.window.bind('<KeyPress-space>', self.on_overlay_key_press)
        self.window.bind('<KeyRelease-space>', self.on_overlay_key_release)
        self.window.focus_set()  # 确保窗口可以接收键盘事件
        
        # 延迟开始第一次匹配，确保窗口已完全初始化
        self.window.after(200, self.next_match)
        
        # 绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title_label = tk.Label(self.window, text="选择你更喜欢的图像（或选择平局）", 
                              font=("Arial", 20, "bold"))
        title_label.pack(pady=10)
        
        # 提示信息
        hint_label = tk.Label(self.window, text="💡 提示：按住空格键可以让左图覆盖右图，方便比对", 
                             font=("Arial", 11), fg='gray')
        hint_label.pack(pady=5)
        
        # 图像显示区域
        image_frame = tk.Frame(self.window)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 确保窗口大小变化时左右对称
        image_frame.grid_rowconfigure(0, weight=1)
        
        # 使用grid布局确保左右对称
        image_frame.grid_columnconfigure(0, weight=1)
        image_frame.grid_columnconfigure(1, weight=1)
        
        # 左侧图像
        self.left_frame = tk.Frame(image_frame, relief=tk.RAISED, borderwidth=2)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10)
        
        # 使用grid布局确保左右canvas大小一致
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        self.left_label = tk.Label(self.left_frame, text="图像1", font=("Arial", 14))
        self.left_label.grid(row=0, column=0, pady=10)
        
        self.left_canvas = tk.Canvas(self.left_frame, bg='white')
        self.left_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.left_button = tk.Button(self.left_frame, text="选择这个", 
                                     font=("Arial", 16), bg='#4CAF50', fg='white',
                                     command=lambda: self.select_winner(0))
        self.left_button.grid(row=2, column=0, pady=10)
        
        # 右侧图像
        self.right_frame = tk.Frame(image_frame, relief=tk.RAISED, borderwidth=2)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10)
        
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        
        self.right_label = tk.Label(self.right_frame, text="图像2", font=("Arial", 14))
        self.right_label.grid(row=0, column=0, pady=10)
        
        self.right_canvas = tk.Canvas(self.right_frame, bg='white')
        self.right_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # 创建覆盖层canvas（用于显示左图覆盖右图），使用place布局覆盖在右侧canvas上
        # 使用in_参数指定父widget为right_frame，确保坐标系统一致
        self.overlay_canvas = tk.Canvas(self.right_frame, bg='white', highlightthickness=0)
        # 初始时隐藏覆盖层
        self.overlay_canvas.place_forget()
        
        self.right_button = tk.Button(self.right_frame, text="选择这个", 
                                      font=("Arial", 16), bg='#4CAF50', fg='white',
                                      command=lambda: self.select_winner(1))
        self.right_button.grid(row=2, column=0, pady=10)
        
        # 按钮区域（平局和跳过）
        button_area = tk.Frame(self.window)
        button_area.pack(pady=20)
        
        # 平局按钮
        draw_button = tk.Button(button_area, text="平局（两者一样好）", 
                                font=("Arial", 14), bg='#FF9800', fg='white',
                                command=self.select_draw, width=20)
        draw_button.pack(side=tk.LEFT, padx=10)
        
        # 跳过按钮
        skip_button = tk.Button(button_area, text="跳过这一对", 
                                font=("Arial", 12), command=self.next_match)
        skip_button.pack(side=tk.LEFT, padx=10)
    
    def prepare_overlay_image(self, left_img, canvas_width, canvas_height):
        """准备覆盖层图像，使用与右侧canvas相同的缩放和位置逻辑"""
        if not self.overlay_canvas or not left_img:
            return
        
        try:
            # 使用传入的canvas尺寸（应该与右侧canvas相同）
            overlay_width = canvas_width
            overlay_height = canvas_height
            
            if overlay_width <= 1 or overlay_height <= 1:
                return
            
            # 使用与右侧canvas完全相同的缩放逻辑
            margin = 20
            available_width = overlay_width - margin
            available_height = overlay_height - margin
            
            img_width, img_height = left_img.size
            scale_w = available_width / img_width
            scale_h = available_height / img_height
            scale = min(scale_w, scale_h)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            resized_overlay = left_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            overlay_photo = ImageTk.PhotoImage(resized_overlay)
            self.overlay_canvas.delete("all")
            self.overlay_canvas.image = overlay_photo  # 保持引用
            # 使用与右侧canvas完全相同的位置（居中显示）
            self.overlay_canvas.create_image(overlay_width // 2, overlay_height // 2,
                                            image=overlay_photo, anchor=tk.CENTER)
        except Exception as e:
            pass  # 忽略覆盖层准备错误
    
    def on_overlay_key_press(self, event):
        """按下空格键时显示覆盖"""
        if not self.is_overlaying and self.overlay_canvas and self.left_photo and self.right_canvas:
            self.is_overlaying = True
            # 确保布局更新完成
            self.right_frame.update_idletasks()
            # 获取右侧canvas相对于right_frame的位置和大小
            self.right_canvas.update_idletasks()
            # 使用winfo_x和winfo_y获取相对于父窗口的位置
            x = self.right_canvas.winfo_x()
            y = self.right_canvas.winfo_y()
            width = self.right_canvas.winfo_width()
            height = self.right_canvas.winfo_height()
            # 使用place布局覆盖在右侧canvas上，in_参数指定父widget
            self.overlay_canvas.place(in_=self.right_frame, x=x, y=y, width=width, height=height)
            # 确保覆盖层大小正确
            self.window.after(10, self.update_overlay_size)
    
    def on_overlay_key_release(self, event):
        """松开空格键时隐藏覆盖"""
        if self.is_overlaying and self.overlay_canvas:
            self.is_overlaying = False
            self.overlay_canvas.place_forget()  # 隐藏覆盖层
    
    def update_overlay_size(self):
        """更新覆盖层大小"""
        if not self.current_pair or not self.overlay_canvas or not self.right_canvas:
            return
        
        try:
            # 确保布局更新完成
            self.right_frame.update_idletasks()
            # 获取右侧canvas相对于right_frame的位置和大小
            self.right_canvas.update_idletasks()
            x = self.right_canvas.winfo_x()
            y = self.right_canvas.winfo_y()
            width = self.right_canvas.winfo_width()
            height = self.right_canvas.winfo_height()
            
            if width > 1 and height > 1:
                # 更新覆盖层位置和大小，使用in_参数确保坐标系统一致
                self.overlay_canvas.place(in_=self.right_frame, x=x, y=y, width=width, height=height)
                # 重新准备覆盖图像
                left_path = self.current_pair[0]
                img = Image.open(left_path)
                self.prepare_overlay_image(img, width, height)
        except:
            pass
    
    def on_window_resize(self):
        """窗口大小变化时重新显示图像"""
        if self.current_pair:
            self.display_images()
            # 如果正在覆盖，更新覆盖层
            if self.is_overlaying:
                self.window.after(50, self.update_overlay_size)
    
    def next_match(self):
        """开始下一场匹配"""
        if len(self.image_list) < 2:
            messagebox.showwarning("警告", "至少需要2张图像才能进行匹配")
            return
        
        # 隐藏覆盖层（如果正在显示）
        if self.is_overlaying and self.overlay_canvas:
            self.is_overlaying = False
            self.overlay_canvas.place_forget()
        
        # 随机选择两张不同的图像
        self.current_pair = random.sample(self.image_list, 2)
        self.display_images()
    
    def display_images(self):
        """显示当前匹配的图像对，自适应布满整个框架"""
        if not self.current_pair:
            return
        
        for idx, (canvas, path) in enumerate([(self.left_canvas, self.current_pair[0]),
                                               (self.right_canvas, self.current_pair[1])]):
            try:
                # 确保canvas已更新
                canvas.update_idletasks()
                canvas_width = canvas.winfo_width()
                canvas_height = canvas.winfo_height()
                
                # 如果canvas还没准备好，延迟重试
                if canvas_width <= 1 or canvas_height <= 1:
                    self.window.after(50, self.display_images)
                    return
                
                # 加载原始图像
                img = Image.open(path)
                img_width, img_height = img.size
                
                # 计算缩放比例以适应canvas，留出一些边距
                margin = 20
                available_width = canvas_width - margin
                available_height = canvas_height - margin
                
                scale_w = available_width / img_width
                scale_h = available_height / img_height
                scale = min(scale_w, scale_h)
                
                # 缩放图像
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 转换为PhotoImage
                photo = ImageTk.PhotoImage(resized_img)
                
                canvas.delete("all")
                canvas.image = photo  # 保持引用，防止被垃圾回收
                
                # 居中显示图像
                canvas.create_image(canvas_width // 2, canvas_height // 2, 
                                   image=photo, anchor=tk.CENTER)
                
                # 如果是左图，保存photo引用用于覆盖功能
                if idx == 0:
                    self.left_photo = photo
                    # 同时准备覆盖层的图像（使用原始图像对象）
                    self.prepare_overlay_image(img, canvas_width, canvas_height)
                
                # 更新标签显示文件名和当前分数
                filename = os.path.basename(path)
                rating = self.elo_system.get_rating(path)
                if idx == 0:
                    self.left_label.config(text=f"{filename}\nELO分数: {rating:.1f}")
                else:
                    self.right_label.config(text=f"{filename}\nELO分数: {rating:.1f}")
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图像: {str(e)}")
    
    def select_winner(self, winner_idx):
        """选择获胜者并更新ELO分数"""
        if self.current_pair is None:
            return
        
        winner_path = self.current_pair[winner_idx]
        loser_path = self.current_pair[1 - winner_idx]
        
        # 更新ELO分数
        self.elo_system.update_ratings(winner_path, loser_path)
        
        # 增加比较计数
        if self.gui_instance:
            self.gui_instance.comparison_count += 1
            # 每10次比较记录一次分数快照（用于收敛判断）
            if self.gui_instance.comparison_count % 10 == 0:
                self.elo_system.record_rating_snapshot()
        
        # 更新主界面
        if self.update_callback:
            self.update_callback()
        
        # 更新当前显示的分数（实时更新）
        filename_winner = os.path.basename(winner_path)
        filename_loser = os.path.basename(loser_path)
        rating_winner = self.elo_system.get_rating(winner_path)
        rating_loser = self.elo_system.get_rating(loser_path)
        
        if winner_idx == 0:
            self.left_label.config(text=f"{filename_winner}\nELO分数: {rating_winner:.1f}")
            self.right_label.config(text=f"{filename_loser}\nELO分数: {rating_loser:.1f}")
        else:
            self.left_label.config(text=f"{filename_loser}\nELO分数: {rating_loser:.1f}")
            self.right_label.config(text=f"{filename_winner}\nELO分数: {rating_winner:.1f}")
        
        # 延迟开始下一场匹配，让用户看到分数更新
        self.window.after(300, self.next_match)
    
    def select_draw(self):
        """选择平局并更新ELO分数"""
        if self.current_pair is None:
            return
        
        path_a = self.current_pair[0]
        path_b = self.current_pair[1]
        
        # 更新ELO分数（平局：S_A = S_B = 0.5）
        self.elo_system.update_ratings_draw(path_a, path_b)
        
        # 增加比较计数
        if self.gui_instance:
            self.gui_instance.comparison_count += 1
            # 每10次比较记录一次分数快照（用于收敛判断）
            if self.gui_instance.comparison_count % 10 == 0:
                self.elo_system.record_rating_snapshot()
        
        # 更新主界面
        if self.update_callback:
            self.update_callback()
        
        # 更新当前显示的分数（实时更新）
        filename_a = os.path.basename(path_a)
        filename_b = os.path.basename(path_b)
        rating_a = self.elo_system.get_rating(path_a)
        rating_b = self.elo_system.get_rating(path_b)
        
        self.left_label.config(text=f"{filename_a}\nELO分数: {rating_a:.1f}")
        self.right_label.config(text=f"{filename_b}\nELO分数: {rating_b:.1f}")
        
        # 延迟开始下一场匹配，让用户看到分数更新
        self.window.after(300, self.next_match)
    
    def on_closing(self):
        """窗口关闭事件"""
        self.window.destroy()


class ELOSystemGUI:
    """ELO系统主界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ELO图像评分系统")
        self.root.geometry("1400x900")
        
        # 初始化ELO系统
        self.elo_system = ELOSystem()
        
        # 图像列表
        self.image_list = []
        self.sorted_image_list = []  # 排序后的图像列表，用于显示
        self.current_directory = ""
        
        # 比较计数
        self.comparison_count = 0  # 已标记的对数
        
        # 参数文件路径
        self.config_file = "elo_config.json"
        self.scores_file = None  # 将根据图像目录动态设置
        
        # 创建界面
        self.create_widgets()
        
        # 加载配置
        self.load_config()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置主容器使用grid布局，让左右各占50%
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # 左侧面板 - 图像列表（占50%）
        left_panel = tk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_panel.grid_rowconfigure(1, weight=1)  # 让列表区域可扩展
        
        # 右侧面板 - 参数设置和操作（占50%）
        right_panel = tk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # 图像列表标题
        list_title = tk.Label(left_panel, text="图像列表（按ELO分数从高到低排序）", font=("Arial", 14, "bold"))
        list_title.pack(pady=10)
        
        # 图像列表和滚动条容器
        list_frame = tk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 使用grid布局来避免滚动条重叠
        # 创建内部容器
        inner_frame = tk.Frame(list_frame)
        inner_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 纵向滚动条
        v_scrollbar = tk.Scrollbar(inner_frame, orient=tk.VERTICAL)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 横向滚动条
        h_scrollbar = tk.Scrollbar(inner_frame, orient=tk.HORIZONTAL)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 图像列表
        self.image_listbox = tk.Listbox(inner_frame, 
                                       yscrollcommand=v_scrollbar.set,
                                       xscrollcommand=h_scrollbar.set,
                                       font=("Arial", 10), 
                                       width=70)
        self.image_listbox.grid(row=0, column=0, sticky="nsew")
        self.image_listbox.bind('<Double-Button-1>', self.on_image_select)
        
        # 配置grid权重
        inner_frame.grid_rowconfigure(0, weight=1)
        inner_frame.grid_columnconfigure(0, weight=1)
        
        # 配置滚动条
        v_scrollbar.config(command=self.image_listbox.yview)
        h_scrollbar.config(command=self.image_listbox.xview)
        
        
        # 操作按钮区域
        button_frame = tk.Frame(right_panel)
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="选择图像目录", font=("Arial", 12),
                 command=self.select_directory, bg='#2196F3', fg='white',
                 width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="进入匹配界面", font=("Arial", 12),
                 command=self.open_match_window, bg='#FF9800', fg='white',
                 width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="保存分数", font=("Arial", 12),
                 command=self.save_scores, bg='#4CAF50', fg='white',
                 width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="加载分数", font=("Arial", 12),
                 command=self.load_scores, bg='#9C27B0', fg='white',
                 width=15).pack(side=tk.LEFT, padx=5)
        
        # 参数设置区域
        params_frame = tk.LabelFrame(right_panel, text="ELO参数设置", 
                                    font=("Arial", 12, "bold"), padx=20, pady=20)
        params_frame.pack(fill=tk.X, pady=20)
        
        # K因子
        k_frame = tk.Frame(params_frame)
        k_frame.pack(fill=tk.X, pady=10)
        tk.Label(k_frame, text="K因子（影响评分变化幅度）:", 
                font=("Arial", 11)).pack(side=tk.LEFT, padx=10)
        self.k_factor_var = tk.DoubleVar(value=16.0)
        k_spinbox = tk.Spinbox(k_frame, from_=1, to=100, textvariable=self.k_factor_var,
                              width=10, font=("Arial", 11))
        k_spinbox.pack(side=tk.LEFT, padx=10)
        k_spinbox.bind('<FocusOut>', lambda e: self.update_parameters())
        
        # 初始评分
        init_frame = tk.Frame(params_frame)
        init_frame.pack(fill=tk.X, pady=10)
        tk.Label(init_frame, text="初始评分:", 
                font=("Arial", 11)).pack(side=tk.LEFT, padx=10)
        self.initial_rating_var = tk.DoubleVar(value=1400.0)
        init_spinbox = tk.Spinbox(init_frame, from_=0, to=10000, 
                                 textvariable=self.initial_rating_var,
                                 width=10, font=("Arial", 11))
        init_spinbox.pack(side=tk.LEFT, padx=10)
        init_spinbox.bind('<FocusOut>', lambda e: self.update_parameters())
        
        # 保存参数按钮
        tk.Button(params_frame, text="保存参数", font=("Arial", 11),
                 command=self.save_config, bg='#607D8B', fg='white').pack(pady=10)
        
        # 信息显示区域（可扩展）
        info_frame = tk.LabelFrame(right_panel, text="系统信息", 
                                  font=("Arial", 12, "bold"), padx=10, pady=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.info_text = tk.Text(info_frame, wrap=tk.WORD, font=("Arial", 9),
                                height=15, width=50)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加纵向滚动条
        scrollbar_info_v = tk.Scrollbar(info_frame, orient=tk.VERTICAL)
        scrollbar_info_v.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_info_h = tk.Scrollbar(info_frame, orient=tk.HORIZONTAL)
        scrollbar_info_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.info_text.config(yscrollcommand=scrollbar_info_v.set, xscrollcommand=scrollbar_info_h.set)
        scrollbar_info_v.config(command=self.info_text.yview)
        scrollbar_info_h.config(command=self.info_text.xview)
        
        self.update_info()
    
    def select_directory(self):
        """选择图像目录"""
        directory = filedialog.askdirectory(title="选择包含图像的目录")
        if directory:
            self.current_directory = directory
            self.load_images_from_directory(directory)
    
    def load_images_from_directory(self, directory):
        """从目录加载所有图像"""
        # 支持的图像格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
        
        self.image_list = []
        try:
            for file_path in Path(directory).rglob('*'):
                if file_path.suffix.lower() in image_extensions:
                    self.image_list.append(str(file_path))
                    # 添加到ELO系统
                    self.elo_system.add_image(str(file_path))
            
            # 设置分数文件路径为图像目录
            self.scores_file = os.path.join(directory, "elo_scores.json")
            
            # 尝试自动加载已有的分数文件（如果存在）
            if os.path.exists(self.scores_file):
                try:
                    with open(self.scores_file, 'r', encoding='utf-8') as f:
                        scores_data = json.load(f)
                    if 'comparison_count' in scores_data:
                        self.comparison_count = int(scores_data['comparison_count'])
                    # 加载ELO配置参数
                    if 'k_factor' in scores_data:
                        self.k_factor_var.set(float(scores_data['k_factor']))
                    if 'initial_rating' in scores_data:
                        self.initial_rating_var.set(float(scores_data['initial_rating']))
                    # 更新ELO系统参数
                    self.update_parameters()
                    # 加载分数和比对次数
                    if 'scores' in scores_data:
                        for img_path, score in scores_data['scores'].items():
                            if os.path.exists(img_path) and img_path in self.image_list:
                                self.elo_system.ratings[img_path] = float(score)
                                # 加载比对次数
                                if 'image_comparison_counts' in scores_data and img_path in scores_data['image_comparison_counts']:
                                    self.elo_system.comparison_counts[img_path] = int(scores_data['image_comparison_counts'][img_path])
                except:
                    # 如果加载失败，重置计数
                    self.comparison_count = 0
            else:
                # 如果没有分数文件，重置计数
                self.comparison_count = 0
            
            # 记录初始分数快照
            if self.image_list:
                self.elo_system.record_rating_snapshot()
            
            # 更新列表显示
            self.update_image_list()
            self.update_info()
            
            messagebox.showinfo("成功", f"已加载 {len(self.image_list)} 张图像")
        except Exception as e:
            messagebox.showerror("错误", f"加载图像时出错: {str(e)}")
    
    def update_image_list(self):
        """更新图像列表显示，按ELO分数从高到低排序"""
        self.image_listbox.delete(0, tk.END)
        
        # 按ELO分数从高到低排序
        self.sorted_image_list = sorted(self.image_list, 
                                       key=lambda x: self.elo_system.get_rating(x), 
                                       reverse=True)
        
        for img_path in self.sorted_image_list:
            filename = os.path.basename(img_path)
            # 获取相对目录路径
            if self.current_directory:
                try:
                    rel_path = os.path.relpath(img_path, self.current_directory)
                    dir_path = os.path.dirname(rel_path)
                    if dir_path:
                        dir_display = f"[{dir_path}]"
                    else:
                        dir_display = "[根目录]"
                except:
                    dir_display = os.path.dirname(img_path)
            else:
                dir_display = os.path.dirname(img_path)
            
            rating = self.elo_system.get_rating(img_path)
            comparison_count = self.elo_system.get_comparison_count(img_path)
            # 格式化显示文本，确保完整显示
            display_text = f"{dir_display} {filename} | ELO: {rating:.1f} | 比对: {comparison_count}次"
            self.image_listbox.insert(tk.END, display_text)
    
    def on_image_select(self, event):
        """双击图像名称时查看详情"""
        selection = self.image_listbox.curselection()
        if selection and self.sorted_image_list:
            idx = selection[0]
            if idx < len(self.sorted_image_list):
                image_path = self.sorted_image_list[idx]
                ImageViewerWindow(self.root, image_path)
    
    def update_parameters(self):
        """更新ELO参数"""
        k_factor = self.k_factor_var.get()
        initial_rating = self.initial_rating_var.get()
        self.elo_system.set_parameters(k_factor, initial_rating)
        self.update_image_list()
    
    def save_config(self):
        """保存配置参数"""
        try:
            config = {
                'k_factor': self.k_factor_var.get(),
                'initial_rating': self.initial_rating_var.get()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("成功", "参数已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存参数失败: {str(e)}")
    
    def load_config(self):
        """加载配置参数"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.k_factor_var.set(config.get('k_factor', 16.0))
                self.initial_rating_var.set(config.get('initial_rating', 1400.0))
                self.update_parameters()
        except Exception as e:
            messagebox.showwarning("警告", f"加载配置失败: {str(e)}")
    
    def save_scores(self):
        """保存分数到JSON文件"""
        if not self.image_list:
            messagebox.showwarning("警告", "没有图像数据可保存")
            return
        
        if not self.current_directory:
            messagebox.showwarning("警告", "请先选择图像目录")
            return
        
        try:
            # 确保分数文件路径已设置
            if not self.scores_file:
                self.scores_file = os.path.join(self.current_directory, "elo_scores.json")
            
            scores_data = {
                'directory': self.current_directory,
                'comparison_count': self.comparison_count,
                'k_factor': float(self.k_factor_var.get()),
                'initial_rating': float(self.initial_rating_var.get()),
                'scores': {},
                'image_comparison_counts': {}
            }
            for img_path in self.image_list:
                scores_data['scores'][img_path] = float(self.elo_system.get_rating(img_path))
                scores_data['image_comparison_counts'][img_path] = self.elo_system.get_comparison_count(img_path)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.scores_file) or '.', exist_ok=True)
            
            with open(self.scores_file, 'w', encoding='utf-8') as f:
                json.dump(scores_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("成功", f"分数已保存到 {self.scores_file}")
        except Exception as e:
            import traceback
            error_msg = f"保存分数失败: {str(e)}\n{traceback.format_exc()}"
            messagebox.showerror("错误", error_msg)
    
    def load_scores(self):
        """从JSON文件加载分数"""
        if not self.current_directory:
            messagebox.showwarning("警告", "请先选择图像目录")
            return
        
        try:
            # 确定分数文件路径
            if not self.scores_file:
                self.scores_file = os.path.join(self.current_directory, "elo_scores.json")
            
            if not os.path.exists(self.scores_file):
                messagebox.showwarning("警告", f"文件 {self.scores_file} 不存在")
                return
            
            with open(self.scores_file, 'r', encoding='utf-8') as f:
                scores_data = json.load(f)
            
            # 检查数据格式
            if 'scores' not in scores_data:
                messagebox.showerror("错误", "JSON文件格式不正确：缺少'scores'字段")
                return
            
            # 加载比较计数
            if 'comparison_count' in scores_data:
                self.comparison_count = int(scores_data['comparison_count'])
            else:
                self.comparison_count = 0
            
            # 加载ELO配置参数
            if 'k_factor' in scores_data:
                self.k_factor_var.set(float(scores_data['k_factor']))
            if 'initial_rating' in scores_data:
                self.initial_rating_var.set(float(scores_data['initial_rating']))
            
            # 更新ELO系统参数
            self.update_parameters()
            
            # 加载分数和比对次数
            loaded_count = 0
            for img_path, score in scores_data['scores'].items():
                if os.path.exists(img_path):
                    self.elo_system.ratings[img_path] = float(score)
                    # 加载比对次数
                    if 'image_comparison_counts' in scores_data and img_path in scores_data['image_comparison_counts']:
                        self.elo_system.comparison_counts[img_path] = int(scores_data['image_comparison_counts'][img_path])
                    loaded_count += 1
            
            # 更新显示
            self.update_image_list()
            self.update_info()
            
            messagebox.showinfo("成功", f"已加载 {loaded_count} 个图像的分数，已标记 {self.comparison_count} 对")
        except json.JSONDecodeError:
            messagebox.showerror("错误", "JSON文件格式错误，无法解析")
        except Exception as e:
            messagebox.showerror("错误", f"加载分数失败: {str(e)}")
    
    def open_match_window(self):
        """打开匹配界面"""
        if len(self.image_list) < 2:
            messagebox.showwarning("警告", "至少需要2张图像才能进行匹配")
            return
        
        MatchWindow(self.root, self.elo_system, self.image_list, 
                   lambda: (self.update_image_list(), self.update_info()),
                   self)
    
    def update_info(self):
        """更新信息显示"""
        self.info_text.delete(1.0, tk.END)
        info = f"当前目录: {self.current_directory if self.current_directory else '未选择'}\n"
        info += f"图像数量: {len(self.image_list)}\n"
        info += f"已标记对数: {self.comparison_count}\n"
        info += f"K因子: {self.k_factor_var.get()}\n"
        info += f"初始评分: {self.initial_rating_var.get()}\n\n"
        
        # 收敛判断信息
        if len(self.elo_system.rating_history) >= 2:
            max_change, avg_change = self.elo_system.calculate_rating_changes()
            spearman_rho = self.elo_system.calculate_rank_stability()
            
            info += "=== 收敛判断 ===\n"
            
            # 1. 最大/平均单轮分数变化量
            if max_change is not None and avg_change is not None:
                info += f"最大分数变化量 (Δmax): {max_change:.3f}\n"
                info += f"平均分数变化量 (Δavg): {avg_change:.3f}\n"
                
                # 检查是否连续T轮都小于阈值
                if len(self.elo_system.rating_changes) >= 5:
                    recent_changes = self.elo_system.rating_changes[-5:]
                    threshold = 1.0  # ε = 1分
                    all_below_threshold = all(c['max'] < threshold for c in recent_changes)
                    if all_below_threshold:
                        info += f"✓ 连续5轮 Δmax < {threshold}，可能已收敛\n"
                    else:
                        info += f"  连续5轮 Δmax < {threshold}: 否\n"
                info += "\n"
            
            # 2. 排名稳定性
            if spearman_rho is not None:
                info += f"排名稳定性 (Spearman ρ): {spearman_rho:.4f}\n"
                
                # 检查是否连续T轮都大于阈值
                if len(self.elo_system.rating_history) >= 5:
                    recent_rhos = []
                    for i in range(max(1, len(self.elo_system.rating_history) - 4), len(self.elo_system.rating_history)):
                        if i >= 1:
                            # 临时计算每轮的rho
                            current = self.elo_system.rating_history[i]
                            previous = self.elo_system.rating_history[i-1]
                            all_images = list(set(current.keys()) | set(previous.keys()))
                            if len(all_images) >= 2:
                                current_ranked = sorted(all_images, 
                                                       key=lambda x: current.get(x, self.elo_system.initial_rating), 
                                                       reverse=True)
                                previous_ranked = sorted(all_images, 
                                                         key=lambda x: previous.get(x, self.elo_system.initial_rating), 
                                                         reverse=True)
                                current_ranks = {img: j+1 for j, img in enumerate(current_ranked)}
                                previous_ranks = {img: j+1 for j, img in enumerate(previous_ranked)}
                                rank_diffs = [(current_ranks.get(img, len(all_images)) - previous_ranks.get(img, len(all_images))) ** 2 
                                             for img in all_images]
                                n = len(all_images)
                                rho = 1 - (6 * sum(rank_diffs)) / (n * (n * n - 1))
                                recent_rhos.append(rho)
                    
                    if recent_rhos:
                        threshold_rho = 0.99
                        all_above_threshold = all(rho > threshold_rho for rho in recent_rhos)
                        if all_above_threshold:
                            info += f"✓ 连续5轮 ρ > {threshold_rho}，排名已稳定\n"
                        else:
                            info += f"  连续5轮 ρ > {threshold_rho}: 否\n"
                info += "\n"
        
        if self.image_list:
            info += "图像分数排名（前10名）:\n"
            sorted_images = sorted(self.image_list, 
                                  key=lambda x: self.elo_system.get_rating(x), 
                                  reverse=True)
            for i, img_path in enumerate(sorted_images[:10], 1):
                filename = os.path.basename(img_path)
                rating = self.elo_system.get_rating(img_path)
                info += f"{i}. {filename}: {rating:.1f}\n"
        
        self.info_text.insert(1.0, info)


def main():
    """主函数"""
    root = tk.Tk()
    app = ELOSystemGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

