#!/usr/bin/env python3
"""
Instagram Live MP3保存・文字起こしアプリ (GUI版 - Liquid Glass Design)
Mac / Windows 対応 - 初心者向け
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import sys
import os
from pathlib import Path
from datetime import datetime

from downloader import InstagramDownloader
from audio_converter import AudioConverter
from transcriber import AudioTranscriber


class GlassCard(tk.Canvas):
    """Liquid Glass card - 正確なCSS仕様実装"""
    def __init__(self, parent, width=800, height=200, **kwargs):
        # 紺色の背景に合わせる
        super().__init__(parent, highlightthickness=0, bg='#1a1f3a', **kwargs)
        self.card_width = width
        self.card_height = height
        self.configure(width=width, height=height)

        self.create_glass_card()

    def create_glass_card(self):
        """
        CSS仕様:
        background: rgba(6, 78, 59, 0.18);
        border-radius: 12px;
        border: 1px solid rgba(110, 231, 183, 0.2);
        box-shadow: 0px 10px 30px 0 rgba(2, 44, 34, 0.25),
                    inset 0 0 0px rgba(255, 255, 255, 0),
                    inset 0px 0px 4px 2px rgba(255, 255, 255, 0.05);
        """
        w = self.card_width
        h = self.card_height

        # Outer shadow: 0px 10px 30px 0 rgba(2, 44, 34, 0.25)
        # 複数の影のレイヤーで30pxのぼかしを再現
        for i in range(5, 0, -1):
            offset = i * 6  # 合計30pxまで
            shadow_color = '#021614' if i == 5 else '#02221c'
            self.create_rounded_rect(
                0, 10 + i, w, h + 10 + i,
                radius=12,
                fill=shadow_color,
                outline=''
            )

        # Card background: rgba(6, 78, 59, 0.18)
        # RGB(6, 78, 59)をtkinterで不透明色に変換
        self.create_rounded_rect(
            0, 0, w, h,
            radius=12,
            fill='#0a2b22',  # rgba(6, 78, 59, 0.18) の近似値
            outline=''
        )

        # Inner glow (最も微妙): inset 0px 0px 4px 2px rgba(255, 255, 255, 0.05)
        # 内側の微妙な白いハイライト
        self.create_rounded_rect(
            2, 2, w - 2, h - 2,
            radius=10,
            fill='',
            outline='#1a2e2a',  # 非常に暗い白のハイライト
            width=0.5
        )

        # Border: 1px solid rgba(110, 231, 183, 0.2)
        # RGB(110, 231, 183) with 20% opacity
        self.create_rounded_rect(
            0, 0, w, h,
            radius=12,
            fill='',
            outline='#2d5a4d',  # rgba(110, 231, 183, 0.2) の近似値
            width=1
        )

    def create_rounded_rect(self, x1, y1, x2, y2, radius=12, **kwargs):
        """Create a rounded rectangle"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class GlassButton(tk.Canvas):
    """Glass button with hover effects"""
    def __init__(self, parent, text, command, width=160, height=44,
                 color='#6ee7b7', text_color='#FFFFFF',
                 font=("Helvetica", 11, "bold"), state='normal'):
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, bg='#1a1f3a', cursor='hand2')

        self.command = command
        self.text = text
        self.btn_color = color
        self.text_color = text_color
        self.font_config = font
        self.button_state = state
        self.is_disabled = state == 'disabled'
        self.is_hovered = False
        self.is_pressed = False

        self.draw_button()
        self.bind('<Button-1>', self.on_press)
        self.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)

    def draw_button(self):
        """Draw glass button"""
        self.delete('all')
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        if self.is_disabled:
            self.create_rounded_rect(0, 0, w, h, radius=12,
                                    fill='#1a2e2a', outline='#2d5a4d', width=1)
            text_col = '#4a5a54'
        elif self.is_pressed:
            # Pressed: darker
            self.create_rounded_rect(0, 0, w, h, radius=12,
                                    fill='#0d362a', outline='#2d5a4d', width=1)
            text_col = self.text_color
        elif self.is_hovered:
            # Hover: brighter
            self.create_rounded_rect(0, 0, w, h, radius=12,
                                    fill='#0f4a37', outline='#3d6a5d', width=1.5)
            text_col = self.text_color
        else:
            # Normal
            self.create_rounded_rect(0, 0, w, h, radius=12,
                                    fill='#0a2b22', outline='#2d5a4d', width=1)
            text_col = self.text_color

        # Draw text
        self.create_text(w//2, h//2, text=self.text, fill=text_col,
                        font=self.font_config)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=12, **kwargs):
        """Create a rounded rectangle"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def on_press(self, event):
        if not self.is_disabled:
            self.is_pressed = True
            self.draw_button()

    def on_release(self, event):
        if not self.is_disabled:
            self.is_pressed = False
            self.draw_button()
            if self.command:
                self.command()

    def on_enter(self, event):
        if not self.is_disabled:
            self.is_hovered = True
            self.draw_button()

    def on_leave(self, event):
        if not self.is_disabled:
            self.is_hovered = False
            self.is_pressed = False
            self.draw_button()

    def configure_state(self, state):
        """Change button state"""
        self.is_disabled = (state == 'disabled')
        self.button_state = state
        self.configure(cursor='arrow' if self.is_disabled else 'hand2')
        self.draw_button()


class GlassEntry(tk.Canvas):
    """Glass entry field"""
    def __init__(self, parent, width=500, height=44, **kwargs):
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, bg='#1a1f3a')

        # Glass background
        self.create_rounded_rect(0, 0, width, height, radius=12,
                                fill='#0a2b22', outline='#2d5a4d', width=1)

        # Entry widget
        self.entry = tk.Entry(
            self,
            font=("Helvetica", 10),
            relief=tk.FLAT,
            bg='#0d1f1a',
            fg='#e0f2f1',
            insertbackground='#6ee7b7',
            bd=0,
            **kwargs
        )

        self.create_window(18, height//2, anchor='w', window=self.entry,
                          width=width-36)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=12, **kwargs):
        """Create a rounded rectangle"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def get(self):
        """Get entry value"""
        return self.entry.get()


class URLInputRow(tk.Frame):
    """URL input row with glass styling"""
    def __init__(self, parent, on_remove=None, **kwargs):
        super().__init__(parent, bg='#1a1f3a', **kwargs)
        self.on_remove = on_remove

        # URL input field
        self.url_entry_canvas = GlassEntry(self, width=680, height=42)
        self.url_entry_canvas.pack(side=tk.LEFT, padx=(0, 8))

        # Remove button
        self.remove_btn = GlassButton(
            self,
            text="×",
            command=self.remove,
            width=42,
            height=42,
            color='#ef4444',
            text_color='#FFFFFF',
            font=("Helvetica", 16, "bold")
        )
        self.remove_btn.pack(side=tk.RIGHT)

    def get_url(self):
        """Get URL value"""
        return self.url_entry_canvas.get().strip()

    def remove(self):
        """Remove this row"""
        if self.on_remove:
            self.on_remove(self)


class InstagramLiveApp:
    """Instagram Live/Reel MP3保存・文字起こし GUIアプリケーション (Liquid Glass Design)"""

    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Live Transcription")
        self.root.geometry("980x900")
        self.root.minsize(950, 850)

        # Output queue
        self.log_queue = queue.Queue()

        # Default settings
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

        # Whisper model set to "large" for maximum accuracy
        self.whisper_model = "large"
        self.language = tk.StringVar(value="ja")

        # Liquid Glass color scheme - 紺色ベース
        self.colors = {
            # 背景: 紺色
            'bg': '#0f1729',              # Deep navy blue

            # Glass elements
            'glass_bg': '#0a2b22',        # rgba(6, 78, 59, 0.18) approximation
            'glass_border': '#2d5a4d',    # rgba(110, 231, 183, 0.2) approximation

            # Text colors
            'text_primary': '#e0f2f1',    # Light cyan text
            'text_secondary': '#b0c4c3',  # Medium cyan text
            'text_light': '#809998',      # Dark cyan text

            # Accent colors
            'accent_green': '#6ee7b7',    # Mint green
            'accent_teal': '#5ba3a3',     # Teal
            'accent_blue': '#60a5fa',     # Blue
            'accent_amber': '#fbbf24',    # Amber
            'accent_red': '#ef4444',      # Red
        }

        # URL input rows
        self.url_rows = []

        self.setup_ui()
        self.check_log_queue()
        self.show_welcome_message()

        self.processing = False

    def setup_ui(self):
        """Setup UI with liquid glass design"""
        # 紺色の背景
        self.root.configure(bg=self.colors['bg'])

        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.place(relx=0.5, rely=0.5, anchor='center',
                            width=900, height=860)

        # ========== HEADER ==========
        header_frame = tk.Frame(main_container, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 20))

        # Title
        title_label = tk.Label(
            header_frame,
            text="Instagram Live Transcription",
            font=("Helvetica", 24, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['accent_green']
        )
        title_label.pack()

        # Subtitle
        subtitle_label = tk.Label(
            header_frame,
            text="Instagram Live & Reel MP3保存・文字起こし（最高精度）",
            font=("Helvetica", 10),
            bg=self.colors['bg'],
            fg=self.colors['text_secondary']
        )
        subtitle_label.pack(pady=(4, 0))

        # ========== STEP 1: URL INPUT (Glass Card) ==========
        step1_container = tk.Frame(main_container, bg=self.colors['bg'])
        step1_container.pack(fill=tk.X, pady=(0, 16))

        step1_card = GlassCard(step1_container, width=900, height=230)
        step1_card.pack()

        # Card content frame - カード内には不要なCSSを付けない
        step1_content = tk.Frame(step1_card, bg='#0a2b22')
        step1_card.create_window(22, 22, anchor='nw', window=step1_content,
                                 width=856, height=186)

        # Header with badge
        step1_header = tk.Frame(step1_content, bg='#0a2b22')
        step1_header.pack(fill=tk.X, pady=(0, 14))

        step1_title = tk.Label(
            step1_header,
            text="STEP 1: Instagram URL を入力",
            font=("Helvetica", 13, "bold"),
            bg='#0a2b22',
            fg=self.colors['text_primary']
        )
        step1_title.pack(side=tk.LEFT)

        # URL count badge
        badge_canvas = tk.Canvas(step1_header, width=70, height=28,
                                highlightthickness=0, bg='#0a2b22')
        badge_canvas.pack(side=tk.RIGHT)

        badge_canvas.create_rounded_rect = lambda x1, y1, x2, y2, r=14, **kw: badge_canvas.create_polygon(
            [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2,
             x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1],
            smooth=True, **kw
        )

        badge_canvas.create_rounded_rect(0, 0, 70, 28, r=14,
                                         fill='#0d362a', outline='#2d5a4d', width=1)

        self.url_count_badge = badge_canvas.create_text(35, 14, text="0 URLs",
                                                         font=("Helvetica", 9, "bold"),
                                                         fill=self.colors['accent_green'])
        self.badge_canvas = badge_canvas

        # URL container
        self.url_container = tk.Frame(step1_content, bg='#0a2b22')
        self.url_container.pack(fill=tk.BOTH, expand=True)

        # Add first URL row
        self.add_url_row()

        # Example text
        example_label = tk.Label(
            step1_content,
            text="例: https://www.instagram.com/reel/...",
            font=("Helvetica", 9),
            bg='#0a2b22',
            fg=self.colors['text_light']
        )
        example_label.pack(anchor=tk.W, pady=(10, 8))

        # Add URL button
        add_url_btn = GlassButton(
            step1_content,
            text="+ URL を追加",
            command=self.add_url_row,
            width=140,
            height=34,
            color=self.colors['accent_green'],
            text_color='#ffffff',
            font=("Helvetica", 10, "bold")
        )
        add_url_btn.pack(anchor=tk.W, pady=(4, 0))

        # ========== STEP 2: SETTINGS (Glass Card) ==========
        step2_container = tk.Frame(main_container, bg=self.colors['bg'])
        step2_container.pack(fill=tk.X, pady=(0, 16))

        step2_card = GlassCard(step2_container, width=900, height=120)
        step2_card.pack()

        step2_content = tk.Frame(step2_card, bg='#0a2b22')
        step2_card.create_window(22, 22, anchor='nw', window=step2_content,
                                 width=856, height=76)

        step2_title = tk.Label(
            step2_content,
            text="STEP 2: 設定（そのままでもOK）",
            font=("Helvetica", 13, "bold"),
            bg='#0a2b22',
            fg=self.colors['text_primary']
        )
        step2_title.pack(anchor=tk.W, pady=(0, 14))

        # Settings row
        settings_row = tk.Frame(step2_content, bg='#0a2b22')
        settings_row.pack(fill=tk.X)

        # Language selection
        lang_frame = tk.Frame(settings_row, bg='#0a2b22')
        lang_frame.pack(side=tk.LEFT, padx=(0, 24))

        lang_label = tk.Label(
            lang_frame,
            text="言語:",
            font=("Helvetica", 10),
            bg='#0a2b22',
            fg=self.colors['text_secondary']
        )
        lang_label.pack(side=tk.LEFT, padx=(0, 10))

        # Combobox styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Glass.TCombobox',
                       fieldbackground='#0d362a',
                       background='#0f4a37',
                       foreground=self.colors['text_primary'],
                       borderwidth=1,
                       relief=tk.FLAT,
                       arrowcolor=self.colors['text_primary'])

        lang_options = [
            ("🇯🇵 日本語", "ja"),
            ("🇺🇸 English", "en"),
            ("🇨🇳 中文", "zh"),
            ("🇰🇷 한국어", "ko")
        ]

        self.lang_menu = ttk.Combobox(
            lang_frame,
            textvariable=self.language,
            values=[opt[1] for opt in lang_options],
            state="readonly",
            font=("Helvetica", 10),
            width=18,
            style='Glass.TCombobox'
        )
        self.lang_menu.pack(side=tk.LEFT)

        def update_lang_display(*args):
            lang = self.language.get()
            for opt_text, opt_value in lang_options:
                if opt_value == lang:
                    self.lang_menu.set(opt_text)
                    break

        self.language.trace_add('write', update_lang_display)
        update_lang_display()

        # Output directory
        output_frame = tk.Frame(settings_row, bg='#0a2b22')
        output_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        output_label = tk.Label(
            output_frame,
            text="保存先:",
            font=("Helvetica", 10),
            bg='#0a2b22',
            fg=self.colors['text_secondary']
        )
        output_label.pack(side=tk.LEFT, padx=(0, 10))

        self.output_label = tk.Label(
            output_frame,
            text=str(self.output_dir),
            font=("Helvetica", 9),
            bg='#0a2b22',
            fg=self.colors['text_light']
        )
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        change_dir_btn = GlassButton(
            output_frame,
            text="📁 変更",
            command=self.change_output_dir,
            width=90,
            height=32,
            color=self.colors['accent_teal'],
            text_color='#ffffff',
            font=("Helvetica", 9, "bold")
        )
        change_dir_btn.pack(side=tk.RIGHT)

        # ========== STEP 3: EXECUTION (Glass Card) ==========
        step3_container = tk.Frame(main_container, bg=self.colors['bg'])
        step3_container.pack(fill=tk.X, pady=(0, 16))

        step3_card = GlassCard(step3_container, width=900, height=140)
        step3_card.pack()

        step3_content = tk.Frame(step3_card, bg='#0a2b22')
        step3_card.create_window(22, 22, anchor='nw', window=step3_content,
                                 width=856, height=96)

        step3_title = tk.Label(
            step3_content,
            text="STEP 3: 実行",
            font=("Helvetica", 13, "bold"),
            bg='#0a2b22',
            fg=self.colors['text_primary']
        )
        step3_title.pack(anchor=tk.W, pady=(0, 14))

        # Buttons row
        button_row = tk.Frame(step3_content, bg='#0a2b22')
        button_row.pack(fill=tk.X, pady=(0, 12))

        # Start button
        self.start_btn = GlassButton(
            button_row,
            text="▶  処理開始",
            command=self.start_processing,
            width=150,
            height=46,
            color=self.colors['accent_green'],
            text_color='#ffffff',
            font=("Helvetica", 12, "bold")
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 12))

        # Stop button
        self.stop_btn = GlassButton(
            button_row,
            text="■  停止",
            command=self.stop_processing,
            width=110,
            height=46,
            color=self.colors['accent_red'],
            text_color='#ffffff',
            font=("Helvetica", 11, "bold"),
            state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 12))

        # Open folder button
        open_btn = GlassButton(
            button_row,
            text="📂  保存フォルダを開く",
            command=self.open_output_folder,
            width=190,
            height=46,
            color=self.colors['accent_blue'],
            text_color='#ffffff',
            font=("Helvetica", 10, "bold")
        )
        open_btn.pack(side=tk.RIGHT)

        # Progress bar
        style.configure('Glass.Horizontal.TProgressbar',
                       troughcolor='#0d1f1a',
                       background=self.colors['accent_amber'],
                       borderwidth=0,
                       thickness=8)

        self.progress = ttk.Progressbar(
            step3_content,
            mode='indeterminate',
            length=856,
            style='Glass.Horizontal.TProgressbar'
        )
        self.progress.pack(fill=tk.X, pady=(0, 8))

        self.status_label = tk.Label(
            step3_content,
            text="",
            font=("Helvetica", 9),
            bg='#0a2b22',
            fg=self.colors['accent_amber']
        )
        self.status_label.pack(pady=(0, 0))

        # ========== LOG DISPLAY (Glass Card) ==========
        log_container = tk.Frame(main_container, bg=self.colors['bg'])
        log_container.pack(fill=tk.BOTH, expand=True)

        log_card = GlassCard(log_container, width=900, height=260)
        log_card.pack()

        log_content = tk.Frame(log_card, bg='#0a2b22')
        log_card.create_window(22, 22, anchor='nw', window=log_content,
                              width=856, height=216)

        log_title = tk.Label(
            log_content,
            text="処理ログ",
            font=("Helvetica", 12, "bold"),
            bg='#0a2b22',
            fg=self.colors['text_primary']
        )
        log_title.pack(anchor=tk.W, pady=(0, 10))

        # Log text area
        log_frame = tk.Frame(log_content, bg='#0a2b22')
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=("Menlo", 9),
            bg='#0d1f1a',
            fg=self.colors['text_primary'],
            state=tk.DISABLED,
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=12,
            pady=12,
            borderwidth=0,
            highlightthickness=0,
            insertbackground=self.colors['accent_green']
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Log color tags
        self.log_text.tag_config("success", foreground=self.colors['accent_green'],
                                font=("Menlo", 9, "bold"))
        self.log_text.tag_config("error", foreground=self.colors['accent_red'],
                                font=("Menlo", 9, "bold"))
        self.log_text.tag_config("warning", foreground=self.colors['accent_amber'],
                                font=("Menlo", 9, "bold"))
        self.log_text.tag_config("info", foreground=self.colors['accent_teal'],
                                font=("Menlo", 9, "bold"))

    def add_url_row(self):
        """Add URL input row"""
        row = URLInputRow(self.url_container, on_remove=self.remove_url_row)
        row.pack(fill=tk.X, pady=(0, 10))
        self.url_rows.append(row)
        self.update_url_count()

    def remove_url_row(self, row):
        """Remove URL input row"""
        if len(self.url_rows) > 1:
            row.destroy()
            self.url_rows.remove(row)
            self.update_url_count()
        else:
            messagebox.showinfo(
                "削除不可",
                "最低1つのURL入力欄は必要です。"
            )

    def update_url_count(self):
        """Update URL count badge"""
        count = len(self.url_rows)
        self.badge_canvas.itemconfig(self.url_count_badge,
                                     text=f"{count} URL{'s' if count != 1 else ''}")

    def get_all_urls(self):
        """Get all URLs"""
        urls = []
        for row in self.url_rows:
            url = row.get_url()
            if url and 'instagram.com' in url:
                urls.append(url)
        return urls

    def show_welcome_message(self):
        """Show welcome message"""
        welcome = """
╔═══════════════════════════════════════════════════════════════╗
║     インスタライブ文字起こしツールへようこそ！                ║
╚═══════════════════════════════════════════════════════════════╝

📝 使い方:
  1. Instagram Live/Reel の URL をコピー
  2. 上の入力欄に貼り付け（複数URL対応）
  3. 「処理開始」ボタンをクリック

💡 ヒント:
  • 複数のURLを一度に処理できます（「+ URLを追加」で追加）
  • 初回起動時はモデルのダウンロードに時間がかかります
  • 最高精度モデル（large）を使用しています
  • 処理には数分かかる場合があります

準備ができたら URL を入力して「処理開始」してください！
"""
        self.log(welcome)

    def log(self, message, tag=None):
        """Add log message"""
        self.log_queue.put((message, tag))

    def check_log_queue(self):
        """Check and display log queue"""
        try:
            while True:
                message, tag = self.log_queue.get_nowait()
                self.log_text.configure(state=tk.NORMAL)

                if tag:
                    self.log_text.insert(tk.END, message + "\n", tag)
                else:
                    # Auto-tagging
                    if "✓" in message or "完了" in message:
                        self.log_text.insert(tk.END, message + "\n", "success")
                    elif "✗" in message or "エラー" in message or "失敗" in message:
                        self.log_text.insert(tk.END, message + "\n", "error")
                    elif "⚠" in message or "警告" in message:
                        self.log_text.insert(tk.END, message + "\n", "warning")
                    elif "【" in message or "STEP" in message:
                        self.log_text.insert(tk.END, message + "\n", "info")
                    else:
                        self.log_text.insert(tk.END, message + "\n")

                self.log_text.see(tk.END)
                self.log_text.configure(state=tk.DISABLED)
        except queue.Empty:
            pass

        self.root.after(100, self.check_log_queue)

    def change_output_dir(self):
        """Change output directory"""
        directory = filedialog.askdirectory(
            initialdir=self.output_dir,
            title="保存先フォルダを選択"
        )
        if directory:
            self.output_dir = Path(directory)
            self.output_label.config(text=str(self.output_dir))
            self.log(f"✓ 保存先を変更: {self.output_dir}")

    def open_output_folder(self):
        """Open output folder"""
        import platform
        import subprocess

        if not self.output_dir.exists():
            self.output_dir.mkdir(exist_ok=True)

        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', str(self.output_dir)])
        elif platform.system() == 'Windows':
            os.startfile(str(self.output_dir))
        else:  # Linux
            subprocess.run(['xdg-open', str(self.output_dir)])

        self.log(f"📂 フォルダを開きました: {self.output_dir}")

    def start_processing(self):
        """Start processing"""
        urls = self.get_all_urls()

        if not urls:
            messagebox.showwarning(
                "URLが入力されていません",
                "Instagram Live/Reel の URL を入力してください。\n\n"
                "例: https://www.instagram.com/reel/..."
            )
            return

        self.processing = True
        self.start_btn.configure_state('disabled')
        self.stop_btn.configure_state('normal')
        self.progress.start()
        self.status_label.config(text="処理中...")

        # Clear log
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

        # Run in separate thread
        thread = threading.Thread(target=self.process_urls, args=(urls,))
        thread.daemon = True
        thread.start()

    def stop_processing(self):
        """Stop processing"""
        self.processing = False
        self.start_btn.configure_state('normal')
        self.stop_btn.configure_state('disabled')
        self.progress.stop()
        self.status_label.config(text="処理を停止しました")
        self.log("✗ ユーザーによって処理が停止されました")

    def process_urls(self, urls):
        """Process URLs (runs in separate thread)"""
        try:
            self.log("╔═══════════════════════════════════════════════════════════════╗")
            self.log(f"║            処理を開始します（{len(urls)} 個のURL）              ║")
            self.log("╚═══════════════════════════════════════════════════════════════╝\n")

            success_count = 0
            fail_count = 0

            for idx, url in enumerate(urls, 1):
                if not self.processing:
                    self.log("\n✗ 処理が中断されました")
                    break

                self.log(f"\n{'='*60}")
                self.log(f"【URL {idx}/{len(urls)}】処理開始")
                self.log(f"{'='*60}\n")

                if self.process_single_url(url):
                    success_count += 1
                else:
                    fail_count += 1

            # Final results
            self.log("\n\n╔═══════════════════════════════════════════════════════════════╗")
            self.log("║                   すべての処理が完了しました                  ║")
            self.log("╚═══════════════════════════════════════════════════════════════╝\n")
            self.log(f"📊 結果サマリー:")
            self.log(f"  • 成功: {success_count} 件")
            if fail_count > 0:
                self.log(f"  • 失敗: {fail_count} 件")
            self.log(f"\n📂 保存先: {self.output_dir}")

            self.finish_processing(success_count > 0)

        except Exception as e:
            self.log(f"\n✗ エラーが発生しました: {e}")
            import traceback
            self.log(f"\n{traceback.format_exc()}")
            self.finish_processing(False)

    def process_single_url(self, url):
        """Process single URL"""
        try:
            # Download
            self.log("【ステップ 1/3】📥 Instagram動画をダウンロード中...")
            self.log(f"URL: {url}\n")
            self.update_status("動画をダウンロード中...")

            downloader = InstagramDownloader(str(self.output_dir))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_file = downloader.download(url, f"instagram_{timestamp}")

            if not video_file or not self.processing:
                self.log("✗ ダウンロードに失敗しました")
                return False

            self.log(f"✓ ダウンロード完了！\n")

            # Extract audio
            self.log("【ステップ 2/3】🎵 MP3音声を抽出中...")
            self.update_status("MP3音声を抽出中...")

            converter = AudioConverter()
            mp3_file = converter.extract_audio(video_file)

            if not mp3_file or not self.processing:
                self.log("✗ 音声抽出に失敗しました")
                return False

            self.log(f"✓ MP3音声の抽出完了！\n")

            # Delete video file
            if video_file != mp3_file and os.path.exists(video_file):
                os.remove(video_file)

            # Transcribe
            self.log("【ステップ 3/3】📝 文字起こし中（最高精度モデル）...")
            self.log("⏳ Whisper 最高精度モデルを読み込んでいます...")
            self.update_status("文字起こし中（最高精度・数分かかります）...")

            transcriber = AudioTranscriber(
                self.whisper_model,
                self.language.get()
            )

            if not self.processing:
                return False

            self.log("⏳ 音声を解析しています... しばらくお待ちください\n")
            result = transcriber.transcribe(mp3_file, str(self.output_dir))

            if not result or not self.processing:
                self.log("✗ 文字起こしに失敗しました")
                return False

            self.log("\n✓ 文字起こし完了！")
            self.log(f"  • 文字数: {len(result['text']):,} 文字")
            self.log(f"  • セグメント数: {len(result['segments']):,} 個")
            self.log(f"  • 保存ファイル: {Path(mp3_file).stem}_transcript.*")

            return True

        except Exception as e:
            self.log(f"✗ エラー: {e}")
            return False

    def update_status(self, text):
        """Update status label"""
        self.root.after(0, lambda: self.status_label.config(text=text))

    def finish_processing(self, success):
        """Finish processing"""
        self.processing = False
        self.root.after(0, self._finish_ui_update, success)

    def _finish_ui_update(self, success):
        """Update UI (runs in main thread)"""
        self.start_btn.configure_state('normal')
        self.stop_btn.configure_state('disabled')
        self.progress.stop()

        if success:
            self.status_label.config(text="✓ 処理完了！")
            result = messagebox.askyesno(
                "処理完了",
                "すべての処理が完了しました！\n\n"
                "保存フォルダを開きますか？",
                icon='info'
            )
            if result:
                self.open_output_folder()
        else:
            self.status_label.config(text="✗ 処理失敗")


def main():
    """Main function"""
    root = tk.Tk()

    # Icon setup (optional)
    try:
        if sys.platform == 'darwin':
            # macOS
            pass
        elif sys.platform == 'win32':
            # Windows
            pass
    except:
        pass

    app = InstagramLiveApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
