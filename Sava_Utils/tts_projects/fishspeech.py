from . import TTSProjet
import requests
import gradio as gr
from ..utils import positive_int
from .. import logger
from .. import i18n
import os
import hashlib
import soundfile as sf
import time
import json
import wave
import shutil
import io

current_path = os.environ.get("current_path")

try:
    dict_language: dict = i18n('DICT_LANGUAGE')
    assert type(dict_language) is dict
    cut_method: dict = i18n('CUT_METHOD')
    assert type(cut_method) is dict
except:
    dict_language = {"Chinese": "all_zh", "Cantonese": "all_yue", "English": "en", "Japanese": "all_ja", "Korean": "all_ko", "Chinese-English Mix": "zh", "Cantonese-English Mix": "yue", "Japanese-English Mix": "ja", "Korean-English Mix": "ko", "Multi-Language Mix": "auto", "Multi-Language Mix (Cantonese)": "auto_yue"}
    cut_method = {"No cutting": "cut0", "Slice once every 4 sentences": "cut1", "Slice per 50 characters": "cut2", "Slice by Chinese punct": "cut3", "Slice by English punct": "cut4", "Slice by every punct": "cut5"}
dict_language_rev = {val: key for key, val in dict_language.items()}

class FishSpeech(TTSProjet):
    def __init__(self, config):
        self.server_mode = False
        self.ui = False
        pass

    def api(self, port, artts_name, **kwargs):
        pass

    def save_action(self, *args, text: str = None):
        pass


    def _UI(self):
        self.choose_ar_tts = gr.Radio(label=i18n('Select TTS Project'), choices=["Fish-Speech"],
                                      value="Fish-Speech", interactive=not self.server_mode)
        self.language2 = gr.Dropdown(choices=list(dict_language.keys()), value=list(dict_language.keys())[5], label=i18n('Inference text language'), interactive=True, allow_custom_value=False)
        with gr.Row():
            self.refer_audio = gr.Audio(label=i18n('Main Reference Audio'))
            self.aux_ref_audio = gr.File(label=i18n('Auxiliary Reference Audios'), file_count="multiple", type="binary")
        with gr.Row():
            self.refer_text = gr.Textbox(label=i18n('Transcription of Main Reference Audio'), value="", placeholder=i18n('Transcription | Pretrained Speaker (Cosy)'))
            self.refer_lang = gr.Dropdown(choices=list(dict_language.keys()), value=list(dict_language.keys())[0], label=i18n('Language of Main Reference Audio'), interactive=True, allow_custom_value=False)
        with gr.Accordion(i18n('Switch Models'), open=False, visible=not self.server_mode):
            self.sovits_path = gr.Textbox(value="", label=f"Sovits {i18n('Model Path')}", interactive=True)
            self.gpt_path = gr.Textbox(value="", label=f"GPT {i18n('Model Path')}", interactive=True)
            self.switch_fishmodel_btn = gr.Button(value=i18n('Switch Models'), variant="primary")
        with gr.Row():
            self.api_port2 = gr.Number(label="API Port", value=9880, interactive=not self.server_mode, visible=not self.server_mode)
        with gr.Accordion(i18n('Advanced Parameters'), open=False):
            self.batch_size = gr.Slider(minimum=1, maximum=200, step=1, label="batch_size", value=20, interactive=True)
            self.batch_threshold = gr.Slider(minimum=0, maximum=1, step=0.01, label="batch_threshold", value=0.75, interactive=True)
            self.fragment_interval = gr.Slider(minimum=0.01, maximum=1, step=0.01, label=i18n('Fragment Interval(sec)'), value=0.3, interactive=True)
            self.speed_factor = gr.Slider(minimum=0.25, maximum=4, step=0.05, label="speed_factor", value=1.0, interactive=True)
            self.top_k = gr.Slider(minimum=1, maximum=100, step=1, label="top_k", value=5, interactive=True)
            self.top_p = gr.Slider(minimum=0, maximum=1, step=0.05, label="top_p", value=1, interactive=True)
            self.temperature = gr.Slider(minimum=0, maximum=1, step=0.05, label="temperature", value=1, interactive=True)
            self.repetition_penalty = gr.Slider(minimum=0, maximum=2, step=0.05, label="repetition_penalty", value=1.35, interactive=True)
            self.split_bucket = gr.Checkbox(label="Split_Bucket", value=True, interactive=True, show_label=True)
            self.how_to_cut = gr.Radio(label=i18n('How to cut'), choices=list(cut_method.keys()), value=list(cut_method.keys())[0], interactive=True)
        with gr.Accordion(i18n('Presets'), open=False):
            self.choose_presets = gr.Dropdown(
                label="",
                value="None",
                interactive=True,
                allow_custom_value=True,
            )
            self.desc_presets = gr.Textbox(label="", placeholder=i18n('(Optional) Description'), interactive=True)
            with gr.Row():
                self.save_presets_btn = gr.Button(value="💾", variant="primary", min_width=60)
                self.refresh_presets_btn = gr.Button(value="🔄️", variant="secondary", min_width=60)
                self.del_preset_btn = gr.Button(value="🗑️", variant="stop", min_width=60)
                self.refresh_presets_btn.click(self.refresh_presets_list, outputs=[self.choose_presets])
                self.del_preset_btn.click(self.del_preset, inputs=[self.choose_presets], outputs=[self.choose_presets])
            preset_args = [self.choose_presets, self.choose_ar_tts, self.desc_presets, self.api_port2, self.refer_audio, self.refer_text, self.refer_lang, self.aux_ref_audio, self.sovits_path, self.gpt_path]
            self.save_presets_btn.click(self.save_preset, inputs=preset_args, outputs=[self.choose_presets])
        with gr.Row():
            self.gen_btn2 = gr.Button(value=i18n('Generate Audio'), variant="primary", visible=True)
        self.switch_fishmodel_btn.click(self.switch_fishmodel, inputs=[self.sovits_path, self.gpt_path, self.api_port2], outputs=[])
        self.choose_presets.change(self.load_preset, inputs=[self.choose_presets], outputs=preset_args[1:])
        fish_ARGS = [self.choose_ar_tts, self.language2, self.api_port2, self.refer_audio, self.aux_ref_audio, self.refer_text, self.refer_lang, self.batch_size, self.batch_threshold, self.fragment_interval, self.speed_factor, self.top_k, self.top_p, self.temperature, self.repetition_penalty, self.split_bucket, self.how_to_cut, self.gpt_path, self.sovits_path]
        return fish_ARGS

    def before_gen_action(self, *args, **kwargs):
        pass

    def save_preset(self, name, artts_name, description, port, ra, ara, rt, rl, sovits_path, gpt_path):
        pass

    def load_preset(self, name):
        pass

    def switch_fishmodel(self, sovits_path, gpt_path, port, force=True, notify=True):
        pass

    def del_preset(self, name):
        pass

    def refresh_presets_list(self, reset=True):
        pass

    def arg_filter(self, *args):
        pass
