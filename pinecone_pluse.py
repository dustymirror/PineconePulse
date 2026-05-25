# Pinecone Pulse v0.30
# 修复菜单进入卡死问题，将开机画面移至 main()

from europi import *
from europi_script import EuroPiScript
from time import ticks_us, ticks_diff, sleep_ms

TRIG_TIME = 5
FIB_VALUES = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
FIB_STR = ["01", "1", "2", "3", "5", "8", "13", "21", "34", "55", "89"]

class PineconePulse(EuroPiScript):
    def __init__(self):
        super().__init__()
        self.min_idx = 0
        self.max_idx = 7
        self.bpm = 89
        self.mode_loop = True
        self.int_clock = False
        self.settings_mode = False

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
        self.last_clock = ticks_us()
        self.ext_bpm = 0

        self.phase_cv3 = 0
        self.phase_cv5 = 0
        self.phase_cv6 = 0

        self.trigger_queue = []

        self.display_normal_counter = 0
        self.display_normal_val = 1
        self.display_reverse_counter = 0
        self.display_reverse_val = 1

        self.last_b1 = False
        self.last_b2 = False
        self.b1_hold_start = 0
        self.b2_hold_start = 0

        self.last_min = -1
        self.last_max = -1
        self.last_bpm = -1
        self.last_mode = -1

        self.update_sequences()

        @din.handler
        def din_handler():
            if not self.int_clock:
                self.trigger_queue.append(True)

        self.int_clock_next = ticks_us()

    def show_splash(self):
        oled.fill(0)
        oled.text(">^< Pinecone", 0, 8)
        oled.text("v0.30 D.Mirror", 0, 20)
        oled.show()
        sleep_ms(1500)

    def update_sequences(self):
        self.min_idx = max(0, min(10, self.min_idx))
        self.max_idx = max(0, min(10, self.max_idx))
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
        self.phase_cv3 = 0
        self.phase_cv5 = 0
        self.phase_cv6 = 0
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

            if self.normal_counter == 0:
                self.fire(cv1)
            if self.reverse_counter == 0:
                self.fire(cv4)

            self.fire(cv2)

            self.phase_cv3 += 1
            if self.phase_cv3 >= 2:
                self.fire(cv3)
                self.phase_cv3 -= 2

            self.phase_cv5 += 1
            if self.phase_cv5 >= 3:
                self.fire(cv5)
                self.phase_cv5 -= 3

            self.phase_cv6 += 1
            if self.phase_cv6 >= 5:
                self.fire(cv6)
                self.phase_cv6 -= 5

            self.normal_counter += 1
            if self.normal_counter >= self.normal_seq[self.normal_idx]:
                self.normal_counter = 0
                self.advance_normal_idx()
                if self.reset_request:
                    self.normal_idx = 0
                    self.normal_counter = 0
                    self.reverse_idx = 0
                    self.reverse_counter = 0
                    self.phase_cv3 = 0
                    self.phase_cv5 = 0
                    self.phase_cv6 = 0
                    self.round_dir = 1
                    self.reset_request = False

            self.reverse_counter += 1
            if self.reverse_counter >= self.reverse_seq[self.reverse_idx]:
                self.reverse_counter = 0
                self.reverse_idx = (self.reverse_idx + 1) % self.reverse_len
                if self.reset_request:
                    self.reverse_idx = 0
                    self.reverse_counter = 0
        except Exception as e:
            # 防止内部错误导致无法退出，打印错误但继续运行
            print("Error in process_clock:", e)

    def update_ext_bpm(self):
        now = ticks_us()
        diff = ticks_diff(now, self.last_clock)
        self.last_clock = now
        if 10000 < diff < 1000000:
            self.ext_bpm = int(60000000 / diff)

    def run_internal_clock(self):
        if self.int_clock:
            now = ticks_us()
            if now >= self.int_clock_next:
                self.process_clock()
                interval = 60000000 / max(21, min(233, self.bpm))
                self.int_clock_next = now + int(interval)

    def update_display(self):
        oled.fill(0)
        min_str = FIB_STR[self.min_idx]
        max_str = FIB_STR[self.max_idx]
        oled.text("MIN:{} MAX:{}".format(min_str, max_str), 0, 0)
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
            bpm_val = self.bpm
        else:
            src = "EX"
            bpm_val = self.ext_bpm if self.ext_bpm > 0 else 0
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
                if self.settings_mode and self.ext_bpm > 0:
                    self.bpm = self.ext_bpm
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
                    if self.ext_bpm > 0:
                        self.bpm = self.ext_bpm
                    self.process_clock()
        self.last_b1 = b1_now
        self.last_b2 = b2_now

    def update_knobs(self):
        k1_val = k1.percent()
        k2_val = k2.percent()
        if self.settings_mode:
            new_bpm = int(21 + k1_val * 212)
            if new_bpm != self.last_bpm:
                self.last_bpm = new_bpm
                self.bpm = new_bpm
            new_mode = k2_val > 0.5
            if new_mode != self.last_mode:
                self.last_mode = new_mode
                self.mode_loop = new_mode
        else:
            new_min = int(k1_val * 10)
            if new_min != self.last_min:
                self.last_min = new_min
                self.min_idx = new_min
                self.update_sequences()
            new_max = int(k2_val * 10)
            if new_max != self.last_max:
                self.last_max = new_max
                self.max_idx = new_max
                self.update_sequences()

    def main(self):
        self.should_exit = False
        # 显示开机画面（移到这里）
        self.show_splash()
        # 初始化旋钮缓存
        self.last_min = int(k1.percent() * 10)
        self.last_max = int(k2.percent() * 10)
        self.last_bpm = int(21 + k1.percent() * 212)
        self.last_mode = k2.percent() > 0.5

        while not self.should_exit:
            try:
                self.update_knobs()
                self.check_buttons()
                while self.trigger_queue:
                    self.trigger_queue.pop()
                    self.process_clock()
                self.run_internal_clock()
                self.update_display()
                sleep_ms(10)
            except Exception as e:
                # 捕获任何异常，避免卡死
                print("Main loop error:", e)
                sleep_ms(100)

if __name__ == "__main__":
    PineconePulse().main()