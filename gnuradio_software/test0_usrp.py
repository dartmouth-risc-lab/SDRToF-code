#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: USRP loopback
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import analog
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
import sip
import threading



class test0_usrp(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "USRP loopback", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("USRP loopback")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test0_usrp")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 2e6
        self.factors = factors = [8,4,2]
        self.fs_stage1 = fs_stage1 = samp_rate/factors[0]
        self.fs_stage2 = fs_stage2 = fs_stage1/factors[1]
        self.fs_stage3 = fs_stage3 = fs_stage2/factors[2]
        self.fc = fc = 900e6
        self.fb = fb = 10e3
        self.collection_time_sec = collection_time_sec = 10

        ##################################################
        # Blocks
        ##################################################

        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(('addr=192.168.10.3', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_now(uhd.time_spec(time.time()), uhd.ALL_MBOARDS)

        self.uhd_usrp_source_0.set_center_freq(fc, 0)
        self.uhd_usrp_source_0.set_antenna("RX2", 0)
        self.uhd_usrp_source_0.set_gain(10, 0)
        self.uhd_usrp_sink_0 = uhd.usrp_sink(
            ",".join(('addr=192.168.10.3', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
            "",
        )
        self.uhd_usrp_sink_0.set_samp_rate(samp_rate)
        self.uhd_usrp_sink_0.set_time_now(uhd.time_spec(time.time()), uhd.ALL_MBOARDS)

        self.uhd_usrp_sink_0.set_center_freq(fc, 0)
        self.uhd_usrp_sink_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0.set_gain(28, 0)
        self.qtgui_waterfall_sink_x_0 = qtgui.waterfall_sink_f(
            4096, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            3200, #bw
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0.set_update_time(0.1)
        self.qtgui_waterfall_sink_x_0.enable_grid(True)
        self.qtgui_waterfall_sink_x_0.enable_axis_labels(True)


        self.qtgui_waterfall_sink_x_0.set_plot_pos_half(not True)

        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0.qwidget(), Qt.QWidget)

        self.top_layout.addWidget(self._qtgui_waterfall_sink_x_0_win)
        self.qtgui_time_sink_x_0_0_0 = qtgui.time_sink_f(
            4096, #size
            fs_stage3, #samp_rate
            'Phase (arg(I + jQ))', #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0_0_0.set_update_time(0.05)
        self.qtgui_time_sink_x_0_0_0.set_y_axis(-2, 2)

        self.qtgui_time_sink_x_0_0_0.set_y_label('Phase', 'rad')

        self.qtgui_time_sink_x_0_0_0.enable_tags(True)
        self.qtgui_time_sink_x_0_0_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0_0_0.enable_autoscale(True)
        self.qtgui_time_sink_x_0_0_0.enable_grid(True)
        self.qtgui_time_sink_x_0_0_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0_0_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0_0_0.enable_stem_plot(False)


        labels = ['Phase', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_0_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0_0_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0_0_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0_0_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0_0_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0_0_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_0_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0_0_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_time_sink_x_0_0_0_win)
        self.low_pass_filter_0_1_0_0 = filter.fir_filter_ccf(
            factors[2],
            firdes.low_pass(
                1,
                fs_stage2,
                (0.4*fs_stage3),
                (0.05*fs_stage3),
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_1_0 = filter.fir_filter_ccf(
            factors[1],
            firdes.low_pass(
                1,
                fs_stage1,
                (0.5*fs_stage2),
                (0.1*fs_stage2),
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_1 = filter.fir_filter_ccf(
            factors[0],
            firdes.low_pass(
                1,
                samp_rate,
                (0.5*fs_stage1),
                (0.1*fs_stage1),
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0_0_0_0 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                4,
                fs_stage3,
                7000,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.dc_blocker_xx_0 = filter.dc_blocker_ff(128, True)
        self.blocks_multiply_conjugate_cc_1 = blocks.multiply_conjugate_cc(1)
        self.blocks_complex_to_arg_0_0 = blocks.complex_to_arg(1)
        self.analog_sig_source_x_0 = analog.sig_source_c(samp_rate, analog.GR_SIN_WAVE, fb, 0.1, 0, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_multiply_conjugate_cc_1, 0))
        self.connect((self.analog_sig_source_x_0, 0), (self.uhd_usrp_sink_0, 0))
        self.connect((self.blocks_complex_to_arg_0_0, 0), (self.dc_blocker_xx_0, 0))
        self.connect((self.blocks_complex_to_arg_0_0, 0), (self.qtgui_time_sink_x_0_0_0, 0))
        self.connect((self.blocks_multiply_conjugate_cc_1, 0), (self.low_pass_filter_0_1, 0))
        self.connect((self.dc_blocker_xx_0, 0), (self.qtgui_waterfall_sink_x_0, 0))
        self.connect((self.low_pass_filter_0_0_0_0_0, 0), (self.blocks_complex_to_arg_0_0, 0))
        self.connect((self.low_pass_filter_0_1, 0), (self.low_pass_filter_0_1_0, 0))
        self.connect((self.low_pass_filter_0_1_0, 0), (self.low_pass_filter_0_1_0_0, 0))
        self.connect((self.low_pass_filter_0_1_0_0, 0), (self.low_pass_filter_0_0_0_0_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_multiply_conjugate_cc_1, 1))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test0_usrp")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_fs_stage1(self.samp_rate/self.factors[0])
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.low_pass_filter_0_1.set_taps(firdes.low_pass(1, self.samp_rate, (0.5*self.fs_stage1), (0.1*self.fs_stage1), window.WIN_HAMMING, 6.76))
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_factors(self):
        return self.factors

    def set_factors(self, factors):
        self.factors = factors
        self.set_fs_stage1(self.samp_rate/self.factors[0])
        self.set_fs_stage2(self.fs_stage1/self.factors[1])
        self.set_fs_stage3(self.fs_stage2/self.factors[2])

    def get_fs_stage1(self):
        return self.fs_stage1

    def set_fs_stage1(self, fs_stage1):
        self.fs_stage1 = fs_stage1
        self.set_fs_stage2(self.fs_stage1/self.factors[1])
        self.low_pass_filter_0_1.set_taps(firdes.low_pass(1, self.samp_rate, (0.5*self.fs_stage1), (0.1*self.fs_stage1), window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_1_0.set_taps(firdes.low_pass(1, self.fs_stage1, (0.5*self.fs_stage2), (0.1*self.fs_stage2), window.WIN_HAMMING, 6.76))

    def get_fs_stage2(self):
        return self.fs_stage2

    def set_fs_stage2(self, fs_stage2):
        self.fs_stage2 = fs_stage2
        self.set_fs_stage3(self.fs_stage2/self.factors[2])
        self.low_pass_filter_0_1_0.set_taps(firdes.low_pass(1, self.fs_stage1, (0.5*self.fs_stage2), (0.1*self.fs_stage2), window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_1_0_0.set_taps(firdes.low_pass(1, self.fs_stage2, (0.4*self.fs_stage3), (0.05*self.fs_stage3), window.WIN_HAMMING, 6.76))

    def get_fs_stage3(self):
        return self.fs_stage3

    def set_fs_stage3(self, fs_stage3):
        self.fs_stage3 = fs_stage3
        self.high_pass_filter_0.set_taps(firdes.high_pass(1, (self.fs_stage3/2), 30, 60, window.WIN_HANN, 6.76))
        self.low_pass_filter_0_0_0_0_0.set_taps(firdes.low_pass(4, self.fs_stage3, 7000, 2000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_1_0_0.set_taps(firdes.low_pass(1, self.fs_stage2, (0.4*self.fs_stage3), (0.05*self.fs_stage3), window.WIN_HAMMING, 6.76))
        self.qtgui_time_sink_x_0_0_0.set_samp_rate(self.fs_stage3)

    def get_fc(self):
        return self.fc

    def set_fc(self, fc):
        self.fc = fc
        self.uhd_usrp_sink_0.set_center_freq(self.fc, 0)
        self.uhd_usrp_source_0.set_center_freq(self.fc, 0)

    def get_fb(self):
        return self.fb

    def set_fb(self, fb):
        self.fb = fb
        self.analog_sig_source_x_0.set_frequency(self.fb)

    def get_collection_time_sec(self):
        return self.collection_time_sec

    def set_collection_time_sec(self, collection_time_sec):
        self.collection_time_sec = collection_time_sec




def main(top_block_cls=test0_usrp, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
