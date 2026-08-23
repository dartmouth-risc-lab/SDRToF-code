#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: USRP ToF Vibrometry - Clean Audio DSP + Record Demo
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import uhd
import time
import os, time
import sip
import threading



class test0_usrp_audio_demo(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "USRP ToF Vibrometry - Clean Audio DSP + Record Demo", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("USRP ToF Vibrometry - Clean Audio DSP + Record Demo")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test0_usrp_audio_demo")

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
        self.samp_rate = samp_rate = 10000000.0
        self.decim1 = decim1 = 10
        self.fs1 = fs1 = samp_rate/decim1
        self.decim2 = decim2 = 5
        self.record_dir = record_dir = '/home/risc/ram/USRP/usrp_software/gnuradio_software'
        self.record_basename = record_basename = 'tof_audio'
        self.fs2 = fs2 = fs1/decim2
        self.decim3 = decim3 = 5
        self.tx_gain = tx_gain = 28
        self.tx_amp = tx_amp = 0.1
        self.rx_gain = rx_gain = 10
        self.resamp_interp = resamp_interp = 6
        self.resamp_decim = resamp_decim = 5
        self.record_filename = record_filename = os.path.join(record_dir, record_basename + '_' + time.strftime('%Y%m%d_%H%M%S') + '.wav')
        self.record_enable = record_enable = False
        self.fs3 = fs3 = fs2/decim3
        self.fc = fc = 900000000.0
        self.fb = fb = 10e3
        self.audio_trans_width = audio_trans_width = 150
        self.audio_rate = audio_rate = 48000
        self.audio_lp_cutoff = audio_lp_cutoff = 8000
        self.audio_hp_cutoff = audio_hp_cutoff = 1
        self.agc_ref = agc_ref = 0.5
        self.agc_rate = agc_rate = 0.001
        self.agc_max_gain = agc_max_gain = 2000

        ##################################################
        # Blocks
        ##################################################

        self._tx_gain_range = qtgui.Range(0, 31.5, 0.5, 28, 200)
        self._tx_gain_win = qtgui.RangeWidget(self._tx_gain_range, self.set_tx_gain, "TX Gain (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._tx_gain_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._rx_gain_range = qtgui.Range(0, 31.5, 0.5, 10, 200)
        self._rx_gain_win = qtgui.RangeWidget(self._rx_gain_range, self.set_rx_gain, "RX Gain (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._rx_gain_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._record_enable_choices = {'Pressed': bool(True), 'Released': bool(False)}

        _record_enable_toggle_button = qtgui.ToggleButton(self.set_record_enable, 'Record', self._record_enable_choices, False, 'value')
        _record_enable_toggle_button.setColors("default", "default", "red", "default")
        self.record_enable = _record_enable_toggle_button

        self.top_grid_layout.addWidget(_record_enable_toggle_button, 0, 4, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._fb_range = qtgui.Range(1e3, 20e3, 100, 10e3, 200)
        self._fb_win = qtgui.RangeWidget(self._fb_range, self.set_fb, "Probe Tone (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._fb_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(('addr=192.168.10.3', '')),
            uhd.stream_args(
                cpu_format="fc32",
                otw_format="sc16",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_now(uhd.time_spec(time.time()), uhd.ALL_MBOARDS)

        self.uhd_usrp_source_0.set_center_freq(fc, 0)
        self.uhd_usrp_source_0.set_antenna("RX2", 0)
        self.uhd_usrp_source_0.set_gain(rx_gain, 0)
        self.uhd_usrp_sink_0 = uhd.usrp_sink(
            ",".join(('addr=192.168.10.3', '')),
            uhd.stream_args(
                cpu_format="fc32",
                otw_format="sc16",
                args='',
                channels=list(range(0,1)),
            ),
            "",
        )
        self.uhd_usrp_sink_0.set_samp_rate(samp_rate)
        self.uhd_usrp_sink_0.set_time_now(uhd.time_spec(time.time()), uhd.ALL_MBOARDS)

        self.uhd_usrp_sink_0.set_center_freq(fc, 0)
        self.uhd_usrp_sink_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0.set_gain(tx_gain, 0)
        self._record_basename_tool_bar = Qt.QToolBar(self)
        self._record_basename_tool_bar.addWidget(Qt.QLabel("Recording Name" + ": "))
        self._record_basename_line_edit = Qt.QLineEdit(str(self.record_basename))
        self._record_basename_tool_bar.addWidget(self._record_basename_line_edit)
        self._record_basename_line_edit.editingFinished.connect(
            lambda: self.set_record_basename(str(str(self._record_basename_line_edit.text()))))
        self.top_grid_layout.addWidget(self._record_basename_tool_bar, 0, 3, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rational_resampler_xxx_0 = filter.rational_resampler_fff(
                interpolation=resamp_interp,
                decimation=resamp_decim,
                taps=[],
                fractional_bw=0)
        self.qtgui_waterfall_sink_x_1 = qtgui.waterfall_sink_f(
            2048, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            fs3, #bw
            "Phase Spectrogram (Notes Being Played)", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_1.set_update_time(0.1)
        self.qtgui_waterfall_sink_x_1.enable_grid(True)
        self.qtgui_waterfall_sink_x_1.enable_axis_labels(True)


        self.qtgui_waterfall_sink_x_1.set_plot_pos_half(not True)

        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_1.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_1.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_1.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_1.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_1_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_1.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._qtgui_waterfall_sink_x_1_win, 2, 0, 1, 4)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_time_sink_x_1 = qtgui.time_sink_f(
            4096, #size
            fs3, #samp_rate
            "Phase (Notes Being Played)", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_1.set_update_time(0.05)
        self.qtgui_time_sink_x_1.set_y_axis(-3.2, 3.2)

        self.qtgui_time_sink_x_1.set_y_label('Phase', 'rad')

        self.qtgui_time_sink_x_1.enable_tags(True)
        self.qtgui_time_sink_x_1.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_1.enable_autoscale(True)
        self.qtgui_time_sink_x_1.enable_grid(True)
        self.qtgui_time_sink_x_1.enable_axis_labels(True)
        self.qtgui_time_sink_x_1.enable_control_panel(False)
        self.qtgui_time_sink_x_1.enable_stem_plot(False)


        labels = ['Phase (Notes Being Played)', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
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
                self.qtgui_time_sink_x_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_1.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_1.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_1.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_1.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_1.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_1.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_1_win = sip.wrapinstance(self.qtgui_time_sink_x_1.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_time_sink_x_1_win, 1, 0, 1, 4)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.low_pass_filter_2 = filter.fir_filter_ccf(
            decim3,
            firdes.low_pass(
                1,
                fs2,
                (0.45*fs3),
                (0.1*fs3),
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_1 = filter.fir_filter_ccf(
            decim2,
            firdes.low_pass(
                1,
                fs1,
                (0.45*fs2),
                (0.1*fs2),
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0 = filter.fir_filter_ccf(
            decim1,
            firdes.low_pass(
                1,
                samp_rate,
                (0.45*fs1),
                (0.1*fs1),
                window.WIN_HAMMING,
                6.76))
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink(
            record_filename,
            1,
            audio_rate,
            blocks.FORMAT_WAV,
            blocks.FORMAT_PCM_16,
            False
            )
        self.blocks_multiply_conjugate_cc_0 = blocks.multiply_conjugate_cc(1)
        self.blocks_copy_0 = blocks.copy(gr.sizeof_float*1)
        self.blocks_copy_0.set_enabled(record_enable)
        self.blocks_complex_to_arg_0 = blocks.complex_to_arg(1)
        self.audio_sink_0 = audio.sink(audio_rate, '', True)
        self.analog_sig_source_x_0 = analog.sig_source_c(samp_rate, analog.GR_SIN_WAVE, fb, tx_amp, 0, 0)
        self.analog_agc_xx_0 = analog.agc_ff(agc_rate, agc_ref, 1.0, agc_max_gain)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_agc_xx_0, 0), (self.qtgui_time_sink_x_1, 0))
        self.connect((self.analog_agc_xx_0, 0), (self.qtgui_waterfall_sink_x_1, 0))
        self.connect((self.analog_agc_xx_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_multiply_conjugate_cc_0, 0))
        self.connect((self.analog_sig_source_x_0, 0), (self.uhd_usrp_sink_0, 0))
        self.connect((self.blocks_complex_to_arg_0, 0), (self.analog_agc_xx_0, 0))
        self.connect((self.blocks_copy_0, 0), (self.audio_sink_0, 0))
        self.connect((self.blocks_copy_0, 0), (self.blocks_wavfile_sink_0, 0))
        self.connect((self.blocks_multiply_conjugate_cc_0, 0), (self.low_pass_filter_0, 0))
        self.connect((self.low_pass_filter_0, 0), (self.low_pass_filter_1, 0))
        self.connect((self.low_pass_filter_1, 0), (self.low_pass_filter_2, 0))
        self.connect((self.low_pass_filter_2, 0), (self.blocks_complex_to_arg_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.blocks_copy_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_multiply_conjugate_cc_0, 1))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test0_usrp_audio_demo")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_fs1(self.samp_rate/self.decim1)
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, (0.45*self.fs1), (0.1*self.fs1), window.WIN_HAMMING, 6.76))
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_decim1(self):
        return self.decim1

    def set_decim1(self, decim1):
        self.decim1 = decim1
        self.set_fs1(self.samp_rate/self.decim1)

    def get_fs1(self):
        return self.fs1

    def set_fs1(self, fs1):
        self.fs1 = fs1
        self.set_fs2(self.fs1/self.decim2)
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, (0.45*self.fs1), (0.1*self.fs1), window.WIN_HAMMING, 6.76))
        self.low_pass_filter_1.set_taps(firdes.low_pass(1, self.fs1, (0.45*self.fs2), (0.1*self.fs2), window.WIN_HAMMING, 6.76))

    def get_decim2(self):
        return self.decim2

    def set_decim2(self, decim2):
        self.decim2 = decim2
        self.set_fs2(self.fs1/self.decim2)

    def get_record_dir(self):
        return self.record_dir

    def set_record_dir(self, record_dir):
        self.record_dir = record_dir
        self.set_record_filename(os.path.join(self.record_dir, self.record_basename + '_' + time.strftime('%Y%m%d_%H%M%S') + '.wav'))

    def get_record_basename(self):
        return self.record_basename

    def set_record_basename(self, record_basename):
        self.record_basename = record_basename
        Qt.QMetaObject.invokeMethod(self._record_basename_line_edit, "setText", Qt.Q_ARG("QString", str(self.record_basename)))
        self.set_record_filename(os.path.join(self.record_dir, self.record_basename + '_' + time.strftime('%Y%m%d_%H%M%S') + '.wav'))

    def get_fs2(self):
        return self.fs2

    def set_fs2(self, fs2):
        self.fs2 = fs2
        self.set_fs3(self.fs2/self.decim3)
        self.low_pass_filter_1.set_taps(firdes.low_pass(1, self.fs1, (0.45*self.fs2), (0.1*self.fs2), window.WIN_HAMMING, 6.76))
        self.low_pass_filter_2.set_taps(firdes.low_pass(1, self.fs2, (0.45*self.fs3), (0.1*self.fs3), window.WIN_HAMMING, 6.76))

    def get_decim3(self):
        return self.decim3

    def set_decim3(self, decim3):
        self.decim3 = decim3
        self.set_fs3(self.fs2/self.decim3)

    def get_tx_gain(self):
        return self.tx_gain

    def set_tx_gain(self, tx_gain):
        self.tx_gain = tx_gain
        self.uhd_usrp_sink_0.set_gain(self.tx_gain, 0)

    def get_tx_amp(self):
        return self.tx_amp

    def set_tx_amp(self, tx_amp):
        self.tx_amp = tx_amp
        self.analog_sig_source_x_0.set_amplitude(self.tx_amp)

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.uhd_usrp_source_0.set_gain(self.rx_gain, 0)

    def get_resamp_interp(self):
        return self.resamp_interp

    def set_resamp_interp(self, resamp_interp):
        self.resamp_interp = resamp_interp

    def get_resamp_decim(self):
        return self.resamp_decim

    def set_resamp_decim(self, resamp_decim):
        self.resamp_decim = resamp_decim

    def get_record_filename(self):
        return self.record_filename

    def set_record_filename(self, record_filename):
        self.record_filename = record_filename
        self.blocks_wavfile_sink_0.open(self.record_filename)

    def get_record_enable(self):
        return self.record_enable

    def set_record_enable(self, record_enable):
        self.record_enable = record_enable
        self.blocks_copy_0.set_enabled(self.record_enable)

    def get_fs3(self):
        return self.fs3

    def set_fs3(self, fs3):
        self.fs3 = fs3
        self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.fs3, self.audio_hp_cutoff, self.audio_lp_cutoff, self.audio_trans_width, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_2.set_taps(firdes.low_pass(1, self.fs2, (0.45*self.fs3), (0.1*self.fs3), window.WIN_HAMMING, 6.76))
        self.qtgui_time_sink_x_1.set_samp_rate(self.fs3)
        self.qtgui_waterfall_sink_x_1.set_frequency_range(0, self.fs3)

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

    def get_audio_trans_width(self):
        return self.audio_trans_width

    def set_audio_trans_width(self, audio_trans_width):
        self.audio_trans_width = audio_trans_width
        self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.fs3, self.audio_hp_cutoff, self.audio_lp_cutoff, self.audio_trans_width, window.WIN_HAMMING, 6.76))

    def get_audio_rate(self):
        return self.audio_rate

    def set_audio_rate(self, audio_rate):
        self.audio_rate = audio_rate

    def get_audio_lp_cutoff(self):
        return self.audio_lp_cutoff

    def set_audio_lp_cutoff(self, audio_lp_cutoff):
        self.audio_lp_cutoff = audio_lp_cutoff
        self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.fs3, self.audio_hp_cutoff, self.audio_lp_cutoff, self.audio_trans_width, window.WIN_HAMMING, 6.76))

    def get_audio_hp_cutoff(self):
        return self.audio_hp_cutoff

    def set_audio_hp_cutoff(self, audio_hp_cutoff):
        self.audio_hp_cutoff = audio_hp_cutoff
        self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.fs3, self.audio_hp_cutoff, self.audio_lp_cutoff, self.audio_trans_width, window.WIN_HAMMING, 6.76))

    def get_agc_ref(self):
        return self.agc_ref

    def set_agc_ref(self, agc_ref):
        self.agc_ref = agc_ref
        self.analog_agc_xx_0.set_reference(self.agc_ref)

    def get_agc_rate(self):
        return self.agc_rate

    def set_agc_rate(self, agc_rate):
        self.agc_rate = agc_rate
        self.analog_agc_xx_0.set_rate(self.agc_rate)

    def get_agc_max_gain(self):
        return self.agc_max_gain

    def set_agc_max_gain(self, agc_max_gain):
        self.agc_max_gain = agc_max_gain
        self.analog_agc_xx_0.set_max_gain(self.agc_max_gain)




def main(top_block_cls=test0_usrp_audio_demo, options=None):

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
