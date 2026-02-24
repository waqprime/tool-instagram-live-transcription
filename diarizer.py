#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
話者分離モジュール
SpeechBrain ECAPA-TDNN + SpectralClustering を使用して
音声中の話者を識別し、文字起こしセグメントに話者情報を付与
"""

import os
import sys
from typing import List, Dict

import numpy as np

# Windows環境での文字化け対策
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class SpeakerDiarizer:
    """SpeechBrain ECAPA-TDNN による話者分離クラス（トークン不要）"""

    def __init__(self):
        self.model = None

    def _load_model(self):
        """SpeechBrain ECAPA-TDNNモデルを初期化"""
        if self.model is not None:
            return

        print("[INFO] SpeechBrain話者分離モデルを読み込み中...", flush=True)
        print("[INFO] 初回実行時はモデルの自動ダウンロードが行われます", flush=True)

        from speechbrain.inference.speaker import EncoderClassifier

        self.model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=os.path.join(os.path.expanduser("~"), ".cache", "speechbrain", "spkrec-ecapa-voxceleb"),
        )

        print("[OK] SpeechBrain話者分離モデル読み込み完了", flush=True)

    def diarize(self, audio_path: str) -> List[Dict]:
        """
        音声ファイルの話者分離を実行

        1. torchaudioで音声読み込み（16kHzモノラル）
        2. 1.5秒ウィンドウ（0.75秒ストライド）でスライス
        3. 各ウィンドウのECAPA-TDNN埋め込みを抽出
        4. SpectralClusteringで話者クラスタリング（silhouetteスコアで話者数自動推定、2〜8）
        5. 連続する同一話者セグメントをマージ

        Args:
            audio_path: 音声ファイルのパス

        Returns:
            話者セグメントのリスト: [{'start': float, 'end': float, 'speaker': str}, ...]
        """
        try:
            self._load_model()

            print(f"[INFO] 話者分離を実行中: {audio_path}", flush=True)
            print("[PROGRESS] 話者分離: 0%", flush=True)

            import torch
            import torchaudio

            # 音声読み込み（16kHzモノラル）
            waveform, sample_rate = torchaudio.load(audio_path)

            # モノラルに変換
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            # 16kHzにリサンプリング
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
                waveform = resampler(waveform)
                sample_rate = 16000

            duration = waveform.shape[1] / sample_rate

            # ウィンドウパラメータ
            window_sec = 1.5
            stride_sec = 0.75
            window_samples = int(window_sec * sample_rate)
            stride_samples = int(stride_sec * sample_rate)

            # ウィンドウごとに埋め込みを抽出
            embeddings = []
            timestamps = []
            total_windows = max(1, (waveform.shape[1] - window_samples) // stride_samples + 1)

            for i, start_sample in enumerate(range(0, waveform.shape[1] - window_samples + 1, stride_samples)):
                end_sample = start_sample + window_samples
                segment = waveform[:, start_sample:end_sample]

                with torch.no_grad():
                    embedding = self.model.encode_batch(segment)
                    embeddings.append(embedding.squeeze().cpu().numpy())

                start_time = start_sample / sample_rate
                end_time = end_sample / sample_rate
                timestamps.append((start_time, end_time))

                # 進捗表示（埋め込み抽出: 0-60%）
                progress = int((i + 1) / total_windows * 60)
                if (i + 1) % max(1, total_windows // 10) == 0 or i == total_windows - 1:
                    print(f"[PROGRESS] 話者分離: {progress}%", flush=True)

            if len(embeddings) < 2:
                print("[WARNING] セグメント数が不足しています。話者分離をスキップします。", flush=True)
                return []

            embeddings_array = np.array(embeddings)

            # SpectralClusteringで話者数を自動推定（2〜8話者）
            from sklearn.cluster import SpectralClustering
            from sklearn.metrics import silhouette_score

            print("[PROGRESS] 話者分離: 65%", flush=True)

            best_n = 2
            best_score = -1
            best_labels = None
            max_speakers = min(8, len(embeddings_array) - 1)

            for n in range(2, max_speakers + 1):
                try:
                    sc = SpectralClustering(
                        n_clusters=n,
                        affinity='rbf',
                        assign_labels='kmeans',
                        random_state=42,
                    )
                    labels = sc.fit_predict(embeddings_array)
                    score = silhouette_score(embeddings_array, labels)

                    if score > best_score:
                        best_score = score
                        best_n = n
                        best_labels = labels
                except Exception:
                    continue

            if best_labels is None:
                sc = SpectralClustering(n_clusters=2, affinity='rbf', random_state=42)
                best_labels = sc.fit_predict(embeddings_array)
                best_n = 2

            print(f"[INFO] 推定話者数: {best_n} (silhouetteスコア: {best_score:.3f})", flush=True)
            print("[PROGRESS] 話者分離: 80%", flush=True)

            # セグメントを構築
            raw_segments = []
            for idx, (start_time, end_time) in enumerate(timestamps):
                speaker_id = int(best_labels[idx])
                raw_segments.append({
                    'start': start_time,
                    'end': end_time,
                    'speaker': f"話者{speaker_id + 1}",
                })

            # 連続する同一話者セグメントをマージ
            segments = []
            if raw_segments:
                current = dict(raw_segments[0])
                for seg in raw_segments[1:]:
                    if seg['speaker'] == current['speaker']:
                        current['end'] = seg['end']
                    else:
                        segments.append(current)
                        current = dict(seg)
                segments.append(current)

            print(f"[PROGRESS] 話者分離: 100%", flush=True)
            print(f"[OK] 話者分離完了: {len(segments)}セグメント, {best_n}話者", flush=True)

            return segments

        except Exception as e:
            print(f"[ERROR] 話者分離エラー: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return []

    def merge_with_transcription(
        self,
        transcription_segments: List[Dict],
        diarization_segments: List[Dict],
    ) -> List[Dict]:
        """
        文字起こしセグメントに話者情報をマージ

        各文字起こしセグメントの中間点がどの話者セグメントに含まれるかで判定

        Args:
            transcription_segments: 文字起こしセグメント [{'start', 'end', 'text'}, ...]
            diarization_segments: 話者分離セグメント [{'start', 'end', 'speaker'}, ...]

        Returns:
            話者情報が付与された文字起こしセグメント [{'start', 'end', 'text', 'speaker'}, ...]
        """
        if not diarization_segments:
            return transcription_segments

        merged = []
        for t_seg in transcription_segments:
            mid_point = (t_seg['start'] + t_seg['end']) / 2.0

            # 中間点がどの話者セグメントに含まれるか探索
            speaker = ''
            for d_seg in diarization_segments:
                if d_seg['start'] <= mid_point <= d_seg['end']:
                    speaker = d_seg['speaker']
                    break

            merged_seg = {
                'start': t_seg['start'],
                'end': t_seg['end'],
                'text': t_seg['text'],
                'speaker': speaker,
            }
            merged.append(merged_seg)

        assigned = sum(1 for s in merged if s['speaker'])
        print(f"[OK] 話者マージ完了: {assigned}/{len(merged)}セグメントに話者を割当", flush=True)

        return merged
