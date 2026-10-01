import io
import json
import logging
import math
import os
import re
import wave
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import onnxruntime as ort
import soundfile as sf
from scipy.signal import resample_poly

from backend.app.core.config import settings

logger = logging.getLogger("dsp_analyzer")

TARGET_SR = 16000
VAD_FRAME_SIZE = 512  # 32 ms at 16 kHz
VOWELS_RU = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")


@dataclass
class PauseSegment:
    start: float
    end: float
    duration: float
    is_justified: bool
    type_label: str  # "Обоснованная пауза (знак препинания)" или "Запинка / неоправданная пауза"


@dataclass
class OrthoepyWordInfo:
    word: str
    stressed: str
    wrong: str
    rule: str


@dataclass
class DSPMetrics:
    total_duration_sec: float
    speech_duration_sec: float
    pause_duration_sec: float
    speech_ratio_pct: float
    wpm: float
    spm: float
    tempo_status: str
    tempo_score: int
    pauses_count: int
    justified_pauses_count: int
    unjustified_pauses_count: int
    justified_pauses_pct: float
    pause_segments: List[Dict[str, Any]]
    pitch_contour: List[float]
    pitch_mean_hz: float
    intonation_status: str
    orthoepy_matches: List[Dict[str, Any]]
    summary: str


class DSPAnalyzer:
    """Модуль цифровой обработки сигналов: VAD, WPM, паузы, F0 и орфоэпия ФИПИ"""

    def __init__(self, model_path: Optional[str] = None, orthoepy_path: Optional[str] = None):
        self.root_dir = settings.root_dir
        self.model_path = model_path or str(self.root_dir / "data" / "models" / "silero_vad.onnx")
        self.orthoepy_path = orthoepy_path or str(self.root_dir / "data" / "orthoepy.json")

        self.vad_session: Optional[ort.InferenceSession] = None
        self.orthoepy_dict: List[Dict[str, Any]] = []
        self._init_vad()
        self._load_orthoepy()

    def _init_vad(self):
        try:
            if os.path.exists(self.model_path):
                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                self.vad_session = ort.InferenceSession(self.model_path, sess_options=opts)
                logger.info(f"Silero VAD ONNX успешно загружен из {self.model_path}")
            else:
                logger.warning(f"Файл Silero VAD не найден по пути {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка инициализации Silero VAD ONNX: {e}")
            self.vad_session = None

    def _load_orthoepy(self):
        try:
            if os.path.exists(self.orthoepy_path):
                with open(self.orthoepy_path, "r", encoding="utf-8-sig") as f:
                    self.orthoepy_dict = json.load(f)
                logger.info(f"Орфоэпический словник загружен ({len(self.orthoepy_dict)} слов)")
        except Exception as e:
            logger.error(f"Ошибка загрузки орфоэпического словника: {e}")
            self.orthoepy_dict = []

    def analyze(
        self,
        audio_bytes: bytes,
        task_content: str = "",
        mime_type: str = "audio/webm",
    ) -> DSPMetrics:
        """Полный акустический и просодический анализ аудиозаписи"""
        audio, sr = self._decode_audio(audio_bytes, mime_type)
        total_duration = len(audio) / sr if sr > 0 else 0.0

        if len(audio) == 0 or total_duration < 0.2:
            return self._empty_metrics()

        # 1. Silero VAD: детекция речи и пауз
        speech_dur, pause_dur, raw_pauses = self._detect_vad(audio, sr)

        # 2. Анализ текста и подсчет темпа (WPM / SPM)
        word_count = max(1, len(re.findall(r"[а-яА-ЯёЁa-zA-Z0-9]+", task_content)))
        syllables_count = sum(1 for ch in task_content if ch in VOWELS_RU)

        effective_speech_sec = max(0.5, speech_dur)
        wpm = round((word_count / effective_speech_sec) * 60, 1)
        spm = round((syllables_count / effective_speech_sec) * 60, 1) if syllables_count > 0 else 0.0

        tempo_status, tempo_score, tempo_msg = self._evaluate_tempo(wpm)

        # 3. Анализ обоснованности пауз (сопоставление с пунктуацией)
        punct_count = len(re.findall(r"[,.!?:;—–-]", task_content))
        classified_pauses, just_cnt, unjust_cnt, just_pct = self._classify_pauses(raw_pauses, punct_count)

        # 4. Анализ интонационного контура (F0 Pitch)
        pitch_contour, mean_f0, intonation_status = self._extract_pitch(audio, sr)

        # 5. Сверка с орфоэпическим словарем ФИПИ
        orthoepy_matches = self._match_orthoepy(task_content)

        speech_ratio = round((speech_dur / max(0.001, total_duration)) * 100, 1)

        summary = (
            f"Темп речи: {wpm} сл/мин ({tempo_status}). Чистая речь: {round(speech_dur, 1)} сек из {round(total_duration, 1)} сек. "
            f"Паузы: {len(classified_pauses)} (обоснованных: {just_pct}%). "
            f"{tempo_msg}"
        )

        return DSPMetrics(
            total_duration_sec=round(total_duration, 2),
            speech_duration_sec=round(speech_dur, 2),
            pause_duration_sec=round(pause_dur, 2),
            speech_ratio_pct=speech_ratio,
            wpm=wpm,
            spm=spm,
            tempo_status=tempo_status,
            tempo_score=tempo_score,
            pauses_count=len(classified_pauses),
            justified_pauses_count=just_cnt,
            unjustified_pauses_count=unjust_cnt,
            justified_pauses_pct=just_pct,
            pause_segments=[asdict(p) for p in classified_pauses],
            pitch_contour=pitch_contour,
            pitch_mean_hz=round(mean_f0, 1),
            intonation_status=intonation_status,
            orthoepy_matches=orthoepy_matches,
            summary=summary,
        )

    def _decode_audio(self, audio_bytes: bytes, mime_type: str) -> Tuple[np.ndarray, int]:
        """Универсальное декодирование аудио в 16 кГц моно float32"""
        # Сначала пробуем soundfile
        try:
            bio = io.BytesIO(audio_bytes)
            data, sr = sf.read(bio, dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != TARGET_SR and sr > 0:
                data = self._resample(data, sr, TARGET_SR)
                sr = TARGET_SR
            return data, sr
        except Exception:
            pass

        # Пробуем стандартный wave
        try:
            bio = io.BytesIO(audio_bytes)
            with wave.open(bio, "rb") as wf:
                n_ch = wf.getnchannels()
                sw = wf.getsampwidth()
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)

            if sw == 2:
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            elif sw == 1:
                samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            else:
                samples = np.frombuffer(raw, dtype=np.float32)

            if n_ch > 1:
                samples = samples.reshape(-1, n_ch).mean(axis=1)

            if sr != TARGET_SR and sr > 0:
                samples = self._resample(samples, sr, TARGET_SR)
                sr = TARGET_SR

            return samples, sr
        except Exception as e:
            logger.warning(f"Не удалось декодировать аудио стандартными средствами: {e}")

        # Fallback: эвристическая попытка интерпретации как 16-битный PCM
        try:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            return samples, TARGET_SR
        except Exception:
            return np.array([], dtype=np.float32), TARGET_SR

    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        gcd = math.gcd(orig_sr, target_sr)
        up = target_sr // gcd
        down = orig_sr // gcd
        return resample_poly(audio, up, down).astype(np.float32)

    def _detect_vad(self, audio: np.ndarray, sr: int) -> Tuple[float, float, List[Dict[str, float]]]:
        """Обработка через Silero VAD для определения сегментов речи и пауз"""
        if self.vad_session is None:
            return self._energy_vad_fallback(audio, sr)

        n_samples = len(audio)
        frame_size = VAD_FRAME_SIZE
        state = np.zeros((2, 1, 128), dtype=np.float32)
        sr_tensor = np.array(sr, dtype=np.int64)

        speech_probs = []
        for i in range(0, n_samples, frame_size):
            chunk = audio[i : i + frame_size]
            if len(chunk) < frame_size:
                chunk = np.pad(chunk, (0, frame_size - len(chunk)))
            inp = chunk[np.newaxis, :].astype(np.float32)

            out, state = self.vad_session.run(None, {"input": inp, "state": state, "sr": sr_tensor})
            prob = float(out[0][0])
            speech_probs.append(prob)

        frame_dur = frame_size / sr
        is_speech = np.array(speech_probs) > 0.45
        speech_frames = int(np.sum(is_speech))

        if speech_frames == 0 and np.mean(np.abs(audio)) > 0.008:
            return self._energy_vad_fallback(audio, sr)

        speech_duration = speech_frames * frame_dur
        pause_duration = max(0.0, (n_samples / sr) - speech_duration)

        pauses = []
        in_pause = False
        pause_start = 0.0

        for idx, sp in enumerate(is_speech):
            t = idx * frame_dur
            if not sp and not in_pause:
                in_pause = True
                pause_start = t
            elif sp and in_pause:
                in_pause = False
                p_len = t - pause_start
                if p_len >= 0.35:
                    pauses.append({"start": round(pause_start, 2), "end": round(t, 2), "duration": round(p_len, 2)})

        if in_pause:
            p_len = (len(is_speech) * frame_dur) - pause_start
            if p_len >= 0.35:
                pauses.append({"start": round(pause_start, 2), "end": round(len(is_speech) * frame_dur, 2), "duration": round(p_len, 2)})

        return speech_duration, pause_duration, pauses

    def _energy_vad_fallback(self, audio: np.ndarray, sr: int) -> Tuple[float, float, List[Dict[str, float]]]:
        """Резервный VAD на основе энергии (RMS), если ONNX модель недоступна"""
        frame_len = int(sr * 0.03)  # 30 ms
        energies = [np.sqrt(np.mean(audio[i : i + frame_len] ** 2)) for i in range(0, len(audio), frame_len)]
        threshold = max(0.015, np.mean(energies) * 0.4)
        is_speech = np.array(energies) > threshold

        speech_dur = float(np.sum(is_speech)) * 0.03
        total_dur = len(audio) / sr
        pause_dur = max(0.0, total_dur - speech_dur)
        return speech_dur, pause_dur, []

    def _evaluate_tempo(self, wpm: float) -> Tuple[str, int, str]:
        """Критериальная оценка темпа речи по нормам ФИПИ (критерий ТК)"""
        if 95 <= wpm <= 130:
            return "норма", 1, "Темп чтения соответствует нормам ФИПИ (100–120 слов в минуту). Речь звучит естественно и разборчиво."
        elif wpm < 95:
            return "замедленный", 0, "Темп чтения замедленный (<95 сл/мин). Постарайтесь читать с меньшим количеством задержек."
        else:
            return "ускоренный", 0, "Темп чтения ускорен (>130 сл/мин). Спешка может привести к смазыванию окончаний и несоблюдению пауз."

    def _classify_pauses(
        self, raw_pauses: List[Dict[str, float]], punctuation_count: int
    ) -> Tuple[List[PauseSegment], int, int, float]:
        """Классификация пауз на обоснованные (логические знаки) и неоправданные запинки"""
        classified = []
        justified_count = 0
        unjustified_count = 0

        # Ожидаемое количество пауз коррелирует с пунктуацией
        expected_pauses = max(2, punctuation_count)
        
        for idx, p in enumerate(raw_pauses):
            dur = p["duration"]
            # Нормальная пауза между синтагмами: 0.35 - 1.6 сек
            if dur <= 1.6 and idx < (expected_pauses + 3):
                is_just = True
                label = "Обоснованная пауза (синтагма / знак препинания)"
                justified_count += 1
            else:
                is_just = False
                label = f"Запинка / неоправданная пауза ({dur}с)"
                unjustified_count += 1

            classified.append(
                PauseSegment(
                    start=p["start"],
                    end=p["end"],
                    duration=dur,
                    is_justified=is_just,
                    type_label=label,
                )
            )

        total = len(classified)
        pct = round((justified_count / total) * 100, 1) if total > 0 else 100.0
        return classified, justified_count, unjustified_count, pct

    def _extract_pitch(self, audio: np.ndarray, sr: int) -> Tuple[List[float], float, str]:
        """Извлечение интонационного контура речи (F0 в Гц) методом нормализованной автокорреляции"""
        win_size = int(sr * 0.04)  # 40 ms
        hop_size = int(sr * 0.02)  # 20 ms
        f_min, f_max = 75, 400
        tau_min = int(sr / f_max)
        tau_max = int(sr / f_min)

        f0_points = []
        for i in range(0, len(audio) - win_size, hop_size):
            frame = audio[i : i + win_size]
            rms = np.sqrt(np.mean(frame**2))
            if rms < 0.02:
                f0_points.append(0.0)
                continue

            autocorr = np.correlate(frame, frame, mode="full")
            autocorr = autocorr[len(frame) - 1 :]
            if len(autocorr) <= tau_max:
                f0_points.append(0.0)
                continue

            search_region = autocorr[tau_min:tau_max]
            peak_idx = int(np.argmax(search_region))
            max_val = search_region[peak_idx]

            if autocorr[0] > 0 and (max_val / autocorr[0]) > 0.35:
                pitch_hz = float(sr / (tau_min + peak_idx))
                f0_points.append(pitch_hz)
            else:
                f0_points.append(0.0)

        voiced = [p for p in f0_points if p > 0]
        mean_f0 = float(np.mean(voiced)) if voiced else 180.0

        # Сжимаем кривую до 60 точек для аккуратного SVG-графика на фронтенде
        target_pts = 60
        if len(f0_points) > target_pts:
            step = len(f0_points) / target_pts
            downsampled = [round(float(np.mean(f0_points[int(j * step) : int((j + 1) * step)])), 1) for j in range(target_pts)]
        else:
            downsampled = [round(p, 1) for p in f0_points]

        # Анализ интонации: смотрим спад на конце фраз
        non_zero = [p for p in downsampled if p > 0]
        if len(non_zero) >= 4:
            end_trend = non_zero[-1] - non_zero[-3]
            intonation_status = "Нисходящая интонация в конце фразы (повествовательная норма ФИПИ)" if end_trend <= 0 else "Вопросительная / незавершённая интонация"
        else:
            intonation_status = "Естественная ровная интонация"

        return downsampled, mean_f0, intonation_status

    def _match_orthoepy(self, text: str) -> List[Dict[str, Any]]:
        """Поиск слов из эталонного словника ФИПИ в тексте задания"""
        if not text or not self.orthoepy_dict:
            return []

        text_lower = text.lower()
        matches = []
        seen = set()

        for item in self.orthoepy_dict:
            base_word = item["word"].lower()
            if re.search(rf"\b{base_word}\b", text_lower):
                if base_word not in seen:
                    seen.add(base_word)
                    matches.append(item)

        return matches

    def _empty_metrics(self) -> DSPMetrics:
        return DSPMetrics(
            total_duration_sec=0.0,
            speech_duration_sec=0.0,
            pause_duration_sec=0.0,
            speech_ratio_pct=0.0,
            wpm=0.0,
            spm=0.0,
            tempo_status="не определен",
            tempo_score=0,
            pauses_count=0,
            justified_pauses_count=0,
            unjustified_pauses_count=0,
            justified_pauses_pct=100.0,
            pause_segments=[],
            pitch_contour=[],
            pitch_mean_hz=0.0,
            intonation_status="не определена",
            orthoepy_matches=[],
            summary="Аудиозапись слишком короткая или пустая.",
        )
