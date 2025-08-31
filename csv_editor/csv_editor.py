import csv
import tkinter as tk
from tkinter import ttk, messagebox
import os
import numpy as np
from scipy.interpolate import splprep, splev
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

try:
    import sv_ttk
except ImportError:
    sv_ttk = None

# ========== 設定エリア ==========
# ファイルパス設定
INPUT_FILE = "input.csv"  # 入力CSVファイルのパス
OUTPUT_FILE = "output.csv"  # 出力CSVファイルのパス
BACKGROUND_FILE = "background.csv" # 新しく追加する背景CSVファイルのパス

class CsvCurveEditor(tk.Tk):
    def __init__(self, input_file, output_file, background_file=None): # background_fileを追加
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.background_file = background_file # 新しいプロパティ

        if sv_ttk:
            sv_ttk.set_theme("dark")
            self.dark_mode = True
        else:
            self.dark_mode = False

        self.data = []
        self.inner_lane_data = []
        self.outer_lane_data = []
        self.background_data = [] # 背景データを保持するリストを追加
        self.fieldnames = []
        self._last_edited_index = None
        self._epsilon = 5

        self.selected_indices = set()
        self.drag_mode = None
        self.rect_start_pos = None
        self.drag_start_pos = None
        self.selection_rect = None
        self.original_data_on_drag = None

        self.history = []
        self.redo_stack = []
        self.max_history = 20

        self.smoothing_factor = 3

        self.load_csv()
        self.load_lane_boundaries()
        self.load_background_data() # 背景データの読み込みを追加
        if not self.data:
            self.destroy()
            return
            
        self.create_widgets()
        self.plot_data()
        self.connect_events()

    def save_history_state(self):
        self.redo_stack.clear()
        if len(self.history) >= self.max_history:
            self.history.pop(0)
        self.history.append([row.copy() for row in self.data])

    def undo(self, event=None):
        if not self.history:
            messagebox.showinfo("元に戻す", "元に戻す操作はありません。")
            return
        self.redo_stack.append([row.copy() for row in self.data])
        self.data = self.history.pop()
        self.plot_data()

    def redo(self, event=None):
        if not self.redo_stack:
            messagebox.showinfo("やり直し", "やり直す操作はありません。")
            return
        self.history.append([row.copy() for row in self.data])
        self.data = self.redo_stack.pop()
        self.plot_data()

    def _load_lane_csv(self, file_path):
        data = []
        try:
            with open(file_path, mode='r', newline='', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                if 'x' not in reader.fieldnames or 'y' not in reader.fieldnames:
                    return []
                
                temp_data = list(reader)
                for row in temp_data:
                    try:
                        data.append({'x': float(row['x']), 'y': float(row['y'])})
                    except (ValueError, TypeError):
                        pass
        except FileNotFoundError:
            pass
        except Exception as e:
            messagebox.showwarning("警告", f"{os.path.basename(file_path)} の読み込み中にエラーが発生しました: {e}")
        return data

    def load_lane_boundaries(self):
        try:
            __cd__ = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            __cd__ = os.path.dirname(os.path.abspath('__main__'))
        
        inner_lane_file = os.path.join(__cd__, "lane/inner_lane_bound.csv")
        outer_lane_file = os.path.join(__cd__, "lane/out_lane_bound.csv")
        
        self.inner_lane_data = self._load_lane_csv(inner_lane_file)
        self.outer_lane_data = self._load_lane_csv(outer_lane_file)

    def load_background_data(self):
        """第三のCSVファイルから背景データを読み込む"""
        if not self.background_file:
            return

        try:
            try:
                 __cd__ = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                 __cd__ = os.path.dirname(os.path.abspath('__main__'))

            background_path = os.path.join(__cd__, self.background_file)
            
            with open(background_path, mode='r', newline='', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                if not reader.fieldnames:
                    messagebox.showwarning("警告", f"背景CSVファイル {self.background_file} にヘッダーがありません。")
                    return
                if 'x' not in reader.fieldnames or 'y' not in reader.fieldnames:
                    messagebox.showwarning("警告", f"背景CSVファイル {self.background_file} には 'x' と 'y' の列が必要です。")
                    return

                temp_data = list(reader)
                self.background_data = []
                for row in temp_data:
                    try:
                        self.background_data.append({'x': float(row['x']), 'y': float(row['y'])})
                    except (ValueError, TypeError):
                        pass

        except FileNotFoundError:
            messagebox.showwarning("警告", f"背景ファイルが見つかりません: {self.background_file}")
        except Exception as e:
            messagebox.showwarning("警告", f"背景CSV読み込み中にエラーが発生しました: {e}")

    def load_csv(self):
        try:
            try:
                 __cd__ = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                 __cd__ = os.path.dirname(os.path.abspath('__main__'))

            self.input_file = os.path.join(__cd__, self.input_file)
            self.output_file = os.path.join(__cd__, self.output_file)
            
            with open(self.input_file, mode='r', newline='', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                if not reader.fieldnames:
                    messagebox.showerror("エラー", "CSVファイルにヘッダーがありません。")
                    return
                self.fieldnames = reader.fieldnames
                if 'x' not in self.fieldnames or 'y' not in self.fieldnames:
                    messagebox.showerror("エラー", "CSVには 'x' と 'y' の列が必要です。")
                    return
                if 'speed' not in self.fieldnames:
                    messagebox.showwarning("警告", "CSVに 'speed' 列がありません。速度による色分けは無効になります。")

                temp_data = list(reader)
                self.data = []
                for row in temp_data:
                    try:
                        row['x'] = float(row['x'])
                        row['y'] = float(row['y'])
                        if 'speed' in row:
                            row['speed'] = float(row['speed'])
                        self.data.append(row)
                    except (ValueError, TypeError):
                        pass

        except FileNotFoundError:
            messagebox.showerror("エラー", f"入力ファイルが見つかりません: {self.input_file}")
        except Exception as e:
            messagebox.showerror("エラー", f"CSV読み込み中にエラーが発生しました: {e}")

    def create_widgets(self):
        bg_color = "#2b2b2b" if self.dark_mode else "white"
        fg_color = "white" if self.dark_mode else "black"
        plot_bg_color = "#3c3c3c" if self.dark_mode else "white"
        grid_color = '#555555' if self.dark_mode else '#cccccc'

        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor=bg_color)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(plot_bg_color)

        self.ax.set_xlabel("X", color=fg_color)
        self.ax.set_ylabel("Y", color=fg_color)
        self.ax.grid(True, color=grid_color)
        self.ax.axis('equal')

        self.ax.tick_params(axis='x', colors=fg_color)
        self.ax.tick_params(axis='y', colors=fg_color)
        for spine in self.ax.spines.values():
            spine.set_edgecolor(fg_color)

        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(control_frame, text="スムージング:").pack(side=tk.LEFT, padx=(0, 5))
        self.smoothing_slider = ttk.Scale(control_frame, from_=0, to=10, orient=tk.HORIZONTAL, command=self.on_smoothing_change)
        self.smoothing_slider.set(self.smoothing_factor)
        self.smoothing_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        resample_button = ttk.Button(control_frame, text="範囲リサンプリング", command=self.resample_range)
        resample_button.pack(side=tk.LEFT, padx=(5, 0))

        resample_all_button = ttk.Button(control_frame, text="全体リサンプリング", command=self.resample_points)
        resample_all_button.pack(side=tk.LEFT, padx=(5, 0))

        sample_curve_button = ttk.Button(control_frame, text="曲線上サンプリング(100点)", command=self.sample_curve_points)
        sample_curve_button.pack(side=tk.LEFT, padx=(5, 0))

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        save_button = ttk.Button(self, text="編集内容を保存", command=self.save_csv)
        save_button.pack(pady=10)

    def sample_curve_points(self, num_points=100):
        if len(self.data) < 4:
            messagebox.showwarning("警告", "サンプリングするには点が少なすぎます。")
            return
        try:
            from scipy.spatial import KDTree
            old_data = [row.copy() for row in self.data]
            points = np.array([[row['x'] for row in old_data], [row['y'] for row in old_data]])
            tck, u = splprep(points, s=0, per=True)
            u_new = np.linspace(u.min(), u.max(), num_points)
            new_points = splev(u_new, tck, der=0)
            original_points = np.column_stack((points[0], points[1]))
            tree = KDTree(original_points)
            new_data = []
            for i in range(num_points):
                x_new, y_new = new_points[0][i], new_points[1][i]
                _, idx = tree.query([x_new, y_new])
                base_row = old_data[idx].copy()
                base_row['x'] = x_new
                base_row['y'] = y_new
                new_data.append(base_row)
            self.data = new_data
            self.save_history_state()
            self.plot_data()
            messagebox.showinfo("成功", f"曲線上を{num_points}点でサンプリングしました。")
        except Exception as e:
            print(f"曲線サンプリングエラー: {e}")
            messagebox.showerror("エラー", f"曲線サンプリング中にエラーが発生しました: {e}")

    def on_smoothing_change(self, value):
        self.smoothing_factor = float(value)
        self.plot_data()

    def plot_data(self):
        self.ax.clear() # 既存の描画を全てクリア

        bg_color = "#2b2b2b" if self.dark_mode else "white"
        fg_color = "white" if self.dark_mode else "black"
        plot_bg_color = "#3c3c3c" if self.dark_mode else "white"
        grid_color = '#555555' if self.dark_mode else '#cccccc'

        self.ax.set_facecolor(plot_bg_color)
        self.ax.set_xlabel("X", color=fg_color)
        self.ax.set_ylabel("Y", color=fg_color)
        self.ax.grid(True, color=grid_color)
        self.ax.axis('equal')

        self.ax.tick_params(axis='x', colors=fg_color)
        self.ax.tick_params(axis='y', colors=fg_color)
        for spine in self.ax.spines.values():
            spine.set_edgecolor(fg_color)

        # --- 新機能: 背景データの描画 (最背面) ---
        if self.background_data:
            bg_points = np.array([[row['x'] for row in self.background_data], [row['y'] for row in self.background_data]])
            # 背景なので、目立たない色で、点ではなく線のみを描画
            self.ax.plot(bg_points[0], bg_points[1], '-', color="#FF0000", linewidth=1, alpha=0.7, zorder=0)
            self.ax.scatter(bg_points[0], bg_points[1], color="#FF0000", s=5, zorder=0)


        # レーン境界の描画
        lane_color = '#777777' if self.dark_mode else 'k'
        if self.inner_lane_data:
            inner_points = np.array([[row['x'] for row in self.inner_lane_data], [row['y'] for row in self.inner_lane_data]])
            self.ax.plot(inner_points[0], inner_points[1], '--', color=lane_color, linewidth=0.5, zorder=1)

        if self.outer_lane_data:
            outer_points = np.array([[row['x'] for row in self.outer_lane_data], [row['y'] for row in self.outer_lane_data]])
            self.ax.plot(outer_points[0], outer_points[1], '--', color=lane_color, linewidth=0.5, zorder=1)

        if not self.data:
            self.canvas.draw()
            return

        points = np.array([[row['x'] for row in self.data], [row['y'] for row in self.data]])
        speeds = np.array([row.get('speed', 0) for row in self.data])

        # メインデータの点と線の描画 (中間のレイヤー)
        if 'speed' in self.fieldnames and len(speeds) > 0:
            cmap = plt.get_cmap('jet')
            norm = plt.Normalize(vmin=speeds.min(), vmax=speeds.max())
            colors = cmap(norm(speeds))
            self.ax.scatter(points[0], points[1], c=colors, s=25, zorder=5)
        else:
            point_color = 'red'
            self.ax.scatter(points[0], points[1], color=point_color, s=25, zorder=5)

        # 選択された点をハイライト表示 (最前面)
        if self.selected_indices:
            selected_points = np.array([[self.data[i]['x'] for i in self.selected_indices],
                                        [self.data[i]['y'] for i in self.selected_indices]])
            self.ax.scatter(selected_points[0], selected_points[1],
                            facecolors='none', edgecolors='yellow', s=80, linewidth=2, zorder=6)

        line_color = '#00A0FF' if self.dark_mode else 'b'
        label_color = 'white' if self.dark_mode else 'black'
        try:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            dx = (xlim[1] - xlim[0]) * 0.01
            dy = (ylim[1] - ylim[0]) * 0.01
        except Exception:
            dx = dy = 0.5

        for idx in range(points.shape[1]):
            self.ax.text(points[0][idx] + dx, points[1][idx] + dy, str(idx), color=label_color, fontsize=8, zorder=7)

        if len(self.data) > 3:
            try:
                tck, u = splprep(points, s=0, per=True)
                unew = np.linspace(u.min(), u.max(), 1000)
                xnew, ynew = splev(unew, tck, der=0)
                self.ax.plot(xnew, ynew, '-', color=line_color, zorder=4)
            except Exception:
                self.ax.plot(np.append(points[0], points[0][0]), np.append(points[1], points[1][0]), '-', color=line_color, zorder=4)
        else:
            self.ax.plot(np.append(points[0], points[0][0]), np.append(points[1], points[1][0]), '-', color=line_color, zorder=4)
        
        # 描画後に選択矩形があれば追加し直す (クリアされるため)
        if self.drag_mode == 'selection' and self.selection_rect:
            self.ax.add_patch(self.selection_rect)

        self.canvas.draw()

    def connect_events(self):
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-y>", self.redo)

    def on_press(self, event):
        if event.inaxes != self.ax:
            return

        points = np.array([[row['x'] for row in self.data], [row['y'] for row in self.data]])
        d = np.sqrt((points[0] - event.xdata)**2 + (points[1] - event.ydata)**2)
        
        clicked_on_point = d.min() < self._epsilon
        if clicked_on_point:
            clicked_index = d.argmin()
            
            if clicked_index in self.selected_indices:
                self.drag_mode = 'move'
            else:
                self.selected_indices.clear()
                self.selected_indices.add(clicked_index)
                self.drag_mode = 'move'

            if self.drag_mode == 'move':
                self.save_history_state()
                self.original_data_on_drag = [row.copy() for row in self.data]
                self.drag_start_pos = (event.xdata, event.ydata)

        else:
            self.drag_mode = 'selection'
            self.selected_indices.clear()
            self.rect_start_pos = (event.xdata, event.ydata)
            self.selection_rect = Rectangle(self.rect_start_pos, 0, 0,
                                            facecolor='blue', alpha=0.2,
                                            edgecolor='blue', linestyle='--', zorder=8) # zorderを高く設定
            self.ax.add_patch(self.selection_rect)

        self.plot_data()

    def on_release(self, event):
        if self.drag_mode == 'selection' and self.selection_rect:
            x0, y0 = self.rect_start_pos
            x1, y1 = event.xdata, event.ydata
            
            min_x, max_x = min(x0, x1), max(x0, x1)
            min_y, max_y = min(y0, y1), max(y0, y1)

            self.selected_indices.clear()
            for i, row in enumerate(self.data):
                if min_x <= row['x'] <= max_x and min_y <= row['y'] <= max_y:
                    self.selected_indices.add(i)

            self.selection_rect.remove()
            self.selection_rect = None
            self.plot_data()

        elif self.drag_mode == 'move':
            if self.selected_indices:
                 self._last_edited_index = list(self.selected_indices)[0]

        self.drag_mode = None
        self.original_data_on_drag = None
        self.drag_start_pos = None

    def on_motion(self, event):
        if event.inaxes != self.ax:
            return

        if self.drag_mode == 'selection' and self.selection_rect:
            x0, y0 = self.rect_start_pos
            width = event.xdata - x0
            height = event.ydata - y0
            self.selection_rect.set_width(width)
            self.selection_rect.set_height(height)
            self.canvas.draw_idle()

        elif self.drag_mode == 'move' and self.selected_indices and self.original_data_on_drag:
            dx = event.xdata - self.drag_start_pos[0]
            dy = event.ydata - self.drag_start_pos[1]
            
            for index in self.selected_indices:
                original_row = self.original_data_on_drag[index]
                self.data[index]['x'] = original_row['x'] + dx
                self.data[index]['y'] = original_row['y'] + dy
            
            self.plot_data()

    def resample_range(self):
        if self._last_edited_index is None:
            messagebox.showinfo("情報", "まだ点が編集されていません。点をドラッグしてから実行してください。")
            return

        if len(self.data) < 4:
            return

        self.save_history_state()
        
        range_size = 10 
        num_points = len(self.data)

        start_index = (self._last_edited_index - range_size + num_points) % num_points
        end_index = (self._last_edited_index + range_size + 1 + num_points) % num_points

        indices = []
        if start_index < end_index:
            indices = list(range(start_index, end_index))
        else:
            indices = list(range(start_index, num_points)) + list(range(0, end_index))

        if len(indices) < 4:
            messagebox.showwarning("警告", "リサンプリングするには範囲内の点が少なすぎます。")
            return

        range_points_orig = [self.data[i] for i in indices]
        range_points = np.array([[p['x'] for p in range_points_orig], [p['y'] for p in range_points_orig]])

        try:
            tck, u = splprep(range_points, s=self.smoothing_factor, per=False)
            u_new = np.linspace(u.min(), u.max(), len(indices))
            new_points = splev(u_new, tck, der=0)
            
            for i, idx in enumerate(indices):
                self.data[idx]['x'] = new_points[0][i]
                self.data[idx]['y'] = new_points[1][i]

            self.save_history_state()
            self.plot_data()
            messagebox.showinfo("成功", "選択範囲のリサンプリングが完了しました。")

        except Exception as e:
            print(f"範囲リサンプリングエラー: {e}")
            messagebox.showerror("エラー", f"範囲リサンプリング中にエラーが発生しました: {e}")

    def resample_points(self):
        if messagebox.askokcancel("確認", "すべての点を再配置しますか？この操作は元に戻せません。"):
            if len(self.data) < 4:
                return

            self.save_history_state()

            points = np.array([[row['x'] for row in self.data], [row['y'] for row in self.data]])
            try:
                tck, u = splprep(points, s=self.smoothing_factor, per=True)
                u_new = np.linspace(u.min(), u.max(), len(self.data))
                new_points = splev(u_new, tck, der=0)

                from scipy.spatial import KDTree
                original_points = np.array([[row['x'], row['y']] for row in self.data])
                tree = KDTree(original_points)

                new_data_list = []
                for i in range(len(self.data)):
                    new_x, new_y = new_points[0][i], new_points[1][i]
                    _, nearest_idx = tree.query([new_x, new_y])
                    new_row = self.data[nearest_idx].copy()
                    new_row['x'] = new_x
                    new_row['y'] = new_y
                    new_data_list.append(new_row)
                
                self.data = new_data_list

                self.save_history_state()
                self.plot_data()
                messagebox.showinfo("成功", "全体の再サンプリングが完了しました。")

            except Exception as e:
                print(f"リサンプリングエラー: {e}")
                messagebox.showerror("エラー", f"リサンプリング中にエラーが発生しました: {e}")

    def save_csv(self):
        try:
            with open(self.output_file, mode='w', newline='', encoding='utf-8') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=self.fieldnames)
                writer.writeheader()
                data_to_write = []
                for row in self.data:
                    new_row = row.copy()
                    for key, value in new_row.items():
                        new_row[key] = str(value)
                    data_to_write.append(new_row)
                writer.writerows(data_to_write)
            messagebox.showinfo("成功", f"データが {self.output_file} に保存されました")
        except Exception as e:
            messagebox.showerror("エラー", f"CSV保存中にエラーが発生しました: {e}")

if __name__ == "__main__":
    # BACKGROUND_FILE を CsvCurveEditor の初期化時に渡す
    app = CsvCurveEditor(INPUT_FILE, OUTPUT_FILE, BACKGROUND_FILE)
    app.mainloop()