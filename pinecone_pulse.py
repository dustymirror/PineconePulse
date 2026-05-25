# Pinecone Pulse v0.38
# AIN 控制 MAX 值（优化版 - 只在值变化时更新序列）

from europi import *
from europi_script import EuroPiScript
from time import ticks_us, ticks_diff, sleep_ms

TRIG_TIME = 5
FIB_VALUES = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
FIB_STR = ["01", "1", "2", "3", "5", "8", "13", "21", "34", "55", "89"]
BPM_SCALE = 4
AIN_SMOOTH = 0.2

class PineconePulse(EuroPiScript):
    def __init__(self):
        super().__init__()
        
        # 参数
        self.min_idx = 0
        self.max_idx = 7
        self.bpm_display = 89
        self.mode_loop = True
        self.int_clock = False
        self.settings_mode = False

        # 节奏位置
        self.normal_seq = [1]
        self.normal_idx = 0
        self.normal_counter = 0
        self.normal_len = 1
        self.round_dir = 1

        self.reverse_seq = [1]
        self.reverse_idx = 0
        self.reverse_counter = 0
        self.reverse_len = 1

        self.reset_request = False
        
        # 外部时钟
        self.last_clock = ticks_us()
        self.ext_bpm_real = 0
        self.ext_bpm_display = 0
        self.bpm_samples = []
        
        # AIN 平滑滤波
        self.ain_filtered = 0.0
        self.ain_last_max = -1      # 上次 AIN 控制的 MAX 值
        self.ain_active = False     # AIN 是否有有效信号
        
        # 计数器
        self.cv3_counter = 0
        self.cv5_counter = 0
        self.cv6_counter = 0

        self.trigger_queue = []

        # 显示缓存
        self.display_normal_counter = 0
        self.display_normal_val = 1
        self.display_reverse_counter = 0
        self.display_reverse_val = 1

        # 按钮状态
        self.last_b1 = False
        self.last_b2 = False
        self.b1_hold_start = 0
        self.b2_hold_start = 0

        # 旋钮缓存
        self.k1_min = 0
        self.k2_max = 7
        self.k1_bpm = 89
        self.k2_mode = True
        
        self.last_k1_raw = 0.0
        self.last_k2_raw = 0.0

        self.update_sequences()

        @din.handler
        def din_handler():
            if not self.int_clock:
                self.trigger_queue.append(True)

        self.int_clock_next = ticks_us()

    def show_splash(self):
        oled.fill(0)
        oled.text(">^< Pinecone", 0, 8)
        oled.text("v0.38 D.Mirror", 0, 20)
        oled.show()
        sleep_ms(1500)

    def get_ain_voltage(self):
        try:
            return ain.read_voltage()
        except AttributeError:
            try:
                return ain.percent() * 5.0
            except AttributeError:
                return ain.value() / 65535 * 5.0

    def update_ain(self):
        """读取 AIN，返回是否需要更新序列"""
        ain_voltage = self.get_ain_voltage()
        
        # 检测 AIN 是否有有效信号
        self.ain_active = ain_voltage > 0.1
        
        if not self.ain_active:
            return False
        
        # 平滑滤波
        self.ain_filtered = self.ain_filtered * (1 - AIN_SMOOTH) + ain_voltage * AIN_SMOOTH
        
        # 映射到 0-10 索引
        max_idx = int((self.ain_filtered / 5.0) * 10)
        max_idx = max(0, min(10, max_idx))
        
        # 只有变化时才更新
        if max_idx != self.ain_last_max and max_idx >= self.min_idx:
            self.ain_last_max = max_idx
            self.max_idx = max_idx
            return True
        
        return False

    def update_sequences(self):
        self.min_idx = max(0, min(10, self.k1_min))
        
        # 如果 AIN 激活，MAX 由 AIN 控制；否则由 K2 控制
        if self.ain_active:
            # MAX 已经在 update_ain() 中设置
            pass
        else:
            self.max_idx = max(0, min(10, self.k2_max))
            self.ain_last_max = -1  # 重置 AIN 缓存
        
        if self.min_idx <= self.max_idx:
            self.normal_seq = FIB_VALUES[self.min_idx:self.max_idx+1]
            self.reverse_seq = list(reversed(self.normal_seq))
        else:
            self.normal_seq = FIB_VALUES[self.max_idx:self.min_idx+1]
            self.normal_seq.reverse()
            self.reverse_seq = list(reversed(self.normal_seq))
            
        if not self.normal_seq:
            self.normal_seq = [1]
        if not self.reverse_seq:
            self.reverse_seq = [1]
            
        self.normal_len = len(self.normal_seq)
        self.reverse_len = len(self.reverse_seq)
        self.normal_idx = 0
        self.normal_counter = 0
        self.reverse_idx = 0
        self.reverse_counter = 0
        self.round_dir = 1
        self.reset_request = False
        
        # 重置计数器（序列改变时重置）
        self.cv3_counter = 0
        self.cv5_counter = 0
        self.cv6_counter = 0
        
        self.update_display_cache()

    def update_display_cache(self):
        self.display_normal_counter = self.normal_counter
        self.display_normal_val = self.normal_seq[self.normal_idx] if self.normal_seq else 1
        self.display_reverse_counter = self.reverse_counter
        self.display_reverse_val = self.reverse_seq[self.reverse_idx] if self.reverse_seq else 1

    def advance_normal_idx(self):
        if self.normal_len <= 1:
            return
        if self.mode_loop:
            self.normal_idx = (self.normal_idx + 1) % self.normal_len
        else:
            next_idx = self.normal_idx + self.round_dir
            if next_idx >= self.normal_len:
                next_idx = self.normal_len - 2
                self.round_dir = -1
            elif next_idx < 0:
                next_idx = 1
                self.round_dir = 1
            self.normal_idx = next_idx

    def fire(self, pin):
        pin.on()
        sleep_ms(TRIG_TIME)
        pin.off()

    def process_clock(self):
        try:
            if not self.normal_seq or self.normal_idx >= self.normal_len:
                return
            if not self.reverse_seq or self.reverse_idx >= self.reverse_len:
                return

            self.update_display_cache()
            
            # CV1 - 模块第一拍
            if self.normal_counter == 0:
                self.fire(cv1)
            
            # CV4 - 逆行模块第一拍
            if self.reverse_counter == 0:
                self.fire(cv4)
            
            # CV2 - 每拍
            self.fire(cv2)
            
            # CV3 - 每2拍
            self.cv3_counter += 1
            if self.cv3_counter >= 2:
                self.fire(cv3)
                self.cv3_counter = 0
            
            # CV5 - 每3拍
            self.cv5_counter += 1
            if self.cv5_counter >= 3:
                self.fire(cv5)
                self.cv5_counter = 0
            
            # CV6 - 每5拍
            self.cv6_counter += 1
            if self.cv6_counter >= 5:
                self.fire(cv6)
                self.cv6_counter = 0

            # 更新正常序列计数器
            self.normal_counter += 1
            if self.normal_counter >= self.normal_seq[self.normal_idx]:
                self.normal_counter = 0
                self.advance_normal_idx()
                if self.reset_request:
                    self.normal_idx = 0
                    self.normal_counter = 0
                    self.reverse_idx = 0
                    self.reverse_counter = 0
                    self.cv3_counter = 0
                    self.cv5_counter = 0
                    self.cv6_counter = 0
                    self.round_dir = 1
                    self.reset_request = False

            # 更新逆行序列计数器
            self.reverse_counter += 1
            if self.reverse_counter >= self.reverse_seq[self.reverse_idx]:
                self.reverse_counter = 0
                self.reverse_idx = (self.reverse_idx + 1) % self.reverse_len
                if self.reset_request:
                    self.reverse_idx = 0
                    self.reverse_counter = 0
                    
        except Exception as e:
            print("Clock error:", e)

    def update_ext_bpm(self):
        now = ticks_us()
        diff = ticks_diff(now, self.last_clock)
        self.last_clock = now
        if 10000 < diff < 2000000:
            bpm_real = 60000000 / diff
            self.bpm_samples.append(bpm_real)
            if len(self.bpm_samples) > 4:
                self.bpm_samples.pop(0)
            self.ext_bpm_real = int(sum(self.bpm_samples) / len(self.bpm_samples))
            self.ext_bpm_display = self.ext_bpm_real // BPM_SCALE
            self.ext_bpm_display = max(5, min(233, self.ext_bpm_display))

    def run_internal_clock(self):
        if self.int_clock:
            now = ticks_us()
            if now >= self.int_clock_next:
                self.process_clock()
                real_bpm = self.bpm_display * BPM_SCALE
                real_bpm = max(20, min(400, real_bpm))
                interval = 60000000 // real_bpm
                self.int_clock_next = now + interval

    def update_display(self):
        oled.fill(0)
        min_str = FIB_STR[self.min_idx]
        max_str = FIB_STR[self.max_idx]
        max_display = max_str + ("*" if self.ain_active else "")
        oled.text("MIN:{} MAX:{}".format(min_str, max_display), 0, 0)
        cv1_beat = self.display_normal_counter + 1
        cv1_total = self.display_normal_val
        cv4_beat = self.display_reverse_counter + 1
        cv4_total = self.display_reverse_val
        oled.text("1 {}/{} 4 {}/{}".format(cv1_beat, cv1_total, cv4_beat, cv4_total), 0, 12)
        if self.settings_mode:
            prefix = "@"
        else:
            prefix = ""
        if self.int_clock:
            src = "IN"
            bpm_val = self.bpm_display
        else:
            src = "EX"
            bpm_val = self.ext_bpm_display if self.ext_bpm_display > 0 else 0
        if bpm_val > 0:
            bpm_text = "{}{}:{}BPM".format(prefix, src, bpm_val)
        else:
            bpm_text = "{}{}:---BPM".format(prefix, src)
        mode_text = "LOOP" if self.mode_loop else "RND"
        oled.text("{} {}".format(bpm_text, mode_text), 0, 24)
        oled.show()

    def check_buttons(self):
        b1_now = b1.value()
        b2_now = b2.value()
        if b1_now and b2_now:
            if self.b1_hold_start == 0:
                self.b1_hold_start = ticks_us()
            elif ticks_diff(ticks_us(), self.b1_hold_start) > 500000:
                self.should_exit = True
                return
        else:
            self.b1_hold_start = 0
        if b1_now:
            if self.b2_hold_start == 0:
                self.b2_hold_start = ticks_us()
            elif ticks_diff(ticks_us(), self.b2_hold_start) > 500000:
                self.settings_mode = not self.settings_mode
                if self.settings_mode:
                    self.k1_bpm = self.bpm_display
                    self.k2_mode = self.mode_loop
                else:
                    self.bpm_display = self.k1_bpm
                    self.mode_loop = self.k2_mode
                sleep_ms(200)
                self.b2_hold_start = 0
                self.last_b1 = b1.value()
                return
        else:
            if self.last_b1 and not b1_now:
                self.reset_request = True
            self.b2_hold_start = 0
        if not self.settings_mode:
            if self.last_b2 and not b2_now:
                self.int_clock = not self.int_clock
                if self.int_clock:
                    if self.ext_bpm_display > 0:
                        self.bpm_display = self.ext_bpm_display
                    self.process_clock()
        self.last_b1 = b1_now
        self.last_b2 = b2_now

    def update_knobs(self):
        k1_raw = k1.percent()
        k2_raw = k2.percent()
        k1_changed = abs(k1_raw - self.last_k1_raw) > 0.01
        k2_changed = abs(k2_raw - self.last_k2_raw) > 0.01
        if k1_changed:
            self.last_k1_raw = k1_raw
        if k2_changed:
            self.last_k2_raw = k2_raw
        if self.settings_mode:
            if k1_changed:
                new_bpm = int(21 + k1_raw * 212)
                if new_bpm != self.k1_bpm:
                    self.k1_bpm = new_bpm
                    self.bpm_display = new_bpm
            if k2_changed:
                new_mode = k2_raw > 0.5
                if new_mode != self.k2_mode:
                    self.k2_mode = new_mode
                    self.mode_loop = new_mode
        else:
            need_update = False
            if k1_changed:
                new_min = int(k1_raw * 10)
                if new_min != self.k1_min:
                    self.k1_min = new_min
                    need_update = True
            # K2 只在 AIN 无信号时使用
            if k2_changed and not self.ain_active:
                new_max = int(k2_raw * 10)
                if new_max != self.k2_max:
                    self.k2_max = new_max
                    need_update = True
            
            if need_update:
                self.update_sequences()

    def main(self):
        self.should_exit = False
        self.show_splash()
        
        # 初始化
        self.ain_filtered = self.get_ain_voltage()
        self.ain_last_max = -1
        self.k1_min = int(k1.percent() * 10)
        self.k2_max = int(k2.percent() * 10)
        self.k1_bpm = 89
        self.k2_mode = True
        self.last_k1_raw = k1.percent()
        self.last_k2_raw = k2.percent()
        
        self.update_sequences()
        
        while not self.should_exit:
            try:
                # 更新旋钮
                self.update_knobs()
                
                # 更新 AIN（仅在值变化时触发序列更新）
                if self.update_ain():
                    self.update_sequences()
                
                self.check_buttons()
                
                while self.trigger_queue:
                    self.trigger_queue.pop()
                    self.process_clock()
                    self.update_ext_bpm()
                
                self.run_internal_clock()
                self.update_display()
                sleep_ms(10)
                
            except Exception as e:
                print("Main error:", e)
                sleep_ms(100)

if __name__ == "__main__":
    PineconePulse().main()
