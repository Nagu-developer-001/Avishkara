from statistics import mean

from app.schemas.biomechanics import (
    RunningBiomechanicsMetrics,
    RunningFootStrike,
    RunningGaitEvents,
    RunningStepInterval,
    RunningStrideAnalysis,
    RunningStrideInterval,
)
from app.schemas.pose import PoseFrame, PoseLandmark


class RunningGaitAnalysisService:
    def analyze(self, frames: list[PoseFrame]) -> RunningBiomechanicsMetrics:
        if len(frames) < 3:
            return RunningBiomechanicsMetrics()

        left_strikes, left_toe_offs = self._foot_events(frames, "left")
        right_strikes, right_toe_offs = self._foot_events(frames, "right")
        left_strikes, right_strikes = self._alternating_strikes(
            frames, left_strikes, right_strikes
        )
        left_toe_offs = self._toe_offs_after_strikes(left_strikes, left_toe_offs)
        right_toe_offs = self._toe_offs_after_strikes(right_strikes, right_toe_offs)
        events = RunningGaitEvents(
            left_foot_strikes=left_strikes,
            left_toe_offs=left_toe_offs,
            right_foot_strikes=right_strikes,
            right_toe_offs=right_toe_offs,
        )

        all_strikes = sorted(left_strikes + right_strikes)
        duration_seconds = self._duration_seconds(frames)
        if not self._has_reliable_gait_events(
            frames=frames,
            left_strikes=left_strikes,
            right_strikes=right_strikes,
            all_strikes=all_strikes,
            duration_seconds=duration_seconds,
        ):
            return RunningBiomechanicsMetrics(
                duration_seconds=round(duration_seconds, 3),
            )

        left_stride_times = self._stride_times_ms(frames, left_strikes)
        right_stride_times = self._stride_times_ms(frames, right_strikes)
        all_stride_times = left_stride_times + right_stride_times
        left_contact_times = self._contact_times_ms(frames, left_strikes, left_toe_offs)
        right_contact_times = self._contact_times_ms(frames, right_strikes, right_toe_offs)
        all_contact_times = left_contact_times + right_contact_times
        stride_analysis = self._stride_analysis(frames, left_strikes, right_strikes)

        mean_stride_time_ms = self._safe_mean(all_stride_times)
        contact_time_ms = self._safe_mean(all_contact_times)
        flight_time_ms = (
            max((mean_stride_time_ms / 2) - contact_time_ms, 0)
            if mean_stride_time_ms is not None and contact_time_ms is not None
            else None
        )
        duty_factor_pct = (
            contact_time_ms / (mean_stride_time_ms / 2) * 100
            if mean_stride_time_ms and contact_time_ms is not None
            else None
        )

        return RunningBiomechanicsMetrics(
            gait_events=events,
            stride_analysis=stride_analysis,
            step_count=len(all_strikes),
            left_step_count=len(left_strikes),
            right_step_count=len(right_strikes),
            duration_seconds=round(duration_seconds, 3),
            cadence_spm=(
                round(len(all_strikes) / duration_seconds * 60, 2)
                if duration_seconds > 0
                else None
            ),
            mean_stride_time_ms=self._round_optional(mean_stride_time_ms),
            contact_time_ms=self._round_optional(contact_time_ms),
            flight_time_ms=self._round_optional(flight_time_ms),
            duty_factor_pct=self._round_optional(duty_factor_pct),
            stride_length_norm=self._round_optional(
                self._normalized_stride_length(frames, left_strikes, right_strikes)
            ),
            vertical_oscillation_ratio_pct=self._round_optional(
                self._vertical_oscillation_ratio(frames)
            ),
            overstriding_index_pct=self._round_optional(
                self._overstriding_index(frames, left_strikes, right_strikes)
            ),
            stride_time_symmetry_pct=self._round_optional(
                self._symmetry_pct(self._safe_mean(left_stride_times), self._safe_mean(right_stride_times))
            ),
            contact_time_symmetry_pct=self._round_optional(
                self._symmetry_pct(self._safe_mean(left_contact_times), self._safe_mean(right_contact_times))
            ),
        )

    def _foot_events(
        self, frames: list[PoseFrame], side: str
    ) -> tuple[list[int], list[int]]:
        raw_signal = [
            self._average_y(frame, f"{side}_ankle", f"{side}_heel")
            for frame in frames
        ]
        signal = self._smooth_signal(
            raw_signal,
            window=max(3, self._minimum_strike_gap_frames(frames) // 2),
        )
        min_gap = self._minimum_strike_gap_frames(frames)
        strike_indexes = self._local_maxima(
            signal,
            min_gap=min_gap,
            prominence=self._signal_prominence(signal),
        )
        toe_off_indexes = []
        velocity = [0.0] + [
            signal[index - 1] - signal[index] for index in range(1, len(signal))
        ]

        for current, following in zip(strike_indexes, strike_indexes[1:]):
            if following - current < 3:
                continue
            search_indexes = range(current + 1, following)
            toe_off_indexes.append(max(search_indexes, key=velocity.__getitem__))

        return (
            [frames[index].frame_index for index in strike_indexes],
            [frames[index].frame_index for index in toe_off_indexes],
        )

    @staticmethod
    def _alternating_strikes(
        frames: list[PoseFrame], left_strikes: list[int], right_strikes: list[int]
    ) -> tuple[list[int], list[int]]:
        min_gap = RunningGaitAnalysisService._minimum_strike_gap_frames(frames)
        candidates = sorted(
            [(frame, "left") for frame in left_strikes]
            + [(frame, "right") for frame in right_strikes]
        )
        if not candidates:
            return [], []

        selected: list[tuple[int, str]] = []
        for frame, side in candidates:
            if not selected:
                selected.append((frame, side))
                continue

            previous_frame, previous_side = selected[-1]
            if frame - previous_frame < min_gap:
                continue
            if side == previous_side:
                replacement = next(
                    (
                        candidate
                        for candidate in candidates
                        if candidate[0] > previous_frame
                        and candidate[1] != previous_side
                        and candidate[0] - previous_frame >= min_gap
                    ),
                    None,
                )
                if replacement is None or replacement[0] != frame:
                    continue
            selected.append((frame, side))

        return (
            [frame for frame, side in selected if side == "left"],
            [frame for frame, side in selected if side == "right"],
        )

    @staticmethod
    def _toe_offs_after_strikes(strikes: list[int], toe_offs: list[int]) -> list[int]:
        filtered = []
        for current, following in zip(strikes, strikes[1:]):
            toe_off = next(
                (frame for frame in toe_offs if current < frame < following),
                None,
            )
            if toe_off is not None:
                filtered.append(toe_off)
        return filtered

    @staticmethod
    def _has_reliable_gait_events(
        *,
        frames: list[PoseFrame],
        left_strikes: list[int],
        right_strikes: list[int],
        all_strikes: list[int],
        duration_seconds: float,
    ) -> bool:
        if duration_seconds <= 0 or len(all_strikes) < 6:
            return False

        cadence_spm = len(all_strikes) / duration_seconds * 60
        if cadence_spm < 60 or cadence_spm > 260:
            return False

        if abs(len(left_strikes) - len(right_strikes)) > 2:
            return False

        frame_times = RunningGaitAnalysisService._timestamps_by_frame(frames)
        step_intervals = [
            frame_times[following] - frame_times[current]
            for current, following in zip(all_strikes, all_strikes[1:])
            if current in frame_times and following in frame_times
        ]
        if len(step_intervals) < 5:
            return False
        if min(step_intervals) < 150 or max(step_intervals) > 1200:
            return False

        sides_by_frame = {
            **{frame: "left" for frame in left_strikes},
            **{frame: "right" for frame in right_strikes},
        }
        ordered_sides = [sides_by_frame[frame] for frame in all_strikes]
        same_side_pairs = sum(
            current == following
            for current, following in zip(ordered_sides, ordered_sides[1:])
        )
        return same_side_pairs <= 1

    @staticmethod
    def _minimum_strike_gap_frames(frames: list[PoseFrame]) -> int:
        if len(frames) < 2:
            return 2
        duration_ms = max(frames[-1].timestamp_ms - frames[0].timestamp_ms, 1)
        fps = (len(frames) - 1) / (duration_ms / 1000)
        return max(3, round(fps * 0.18))

    @staticmethod
    def _smooth_signal(values: list[float], *, window: int) -> list[float]:
        if len(values) < 3:
            return values
        if window % 2 == 0:
            window += 1
        radius = window // 2
        smoothed = []
        for index in range(len(values)):
            start = max(0, index - radius)
            end = min(len(values), index + radius + 1)
            smoothed.append(mean(values[start:end]))
        return smoothed

    @staticmethod
    def _signal_prominence(values: list[float]) -> float:
        if len(values) < 3:
            return 0
        amplitude = max(values) - min(values)
        return amplitude * 0.18

    @staticmethod
    def _local_maxima(
        values: list[float], *, min_gap: int, prominence: float = 0
    ) -> list[int]:
        candidates = [
            index
            for index in range(1, len(values) - 1)
            if values[index] >= values[index - 1]
            and values[index] >= values[index + 1]
            and (values[index] > values[index - 1] or values[index] > values[index + 1])
            and values[index] - min(values[max(0, index - min_gap): index + min_gap + 1])
            >= prominence
        ]
        selected: list[int] = []
        for index in candidates:
            if not selected or index - selected[-1] >= min_gap:
                selected.append(index)
            elif values[index] > values[selected[-1]]:
                selected[-1] = index
        return selected

    @staticmethod
    def _duration_seconds(frames: list[PoseFrame]) -> float:
        return max((frames[-1].timestamp_ms - frames[0].timestamp_ms) / 1000, 0)

    @staticmethod
    def _stride_times_ms(frames: list[PoseFrame], strikes: list[int]) -> list[float]:
        timestamps = RunningGaitAnalysisService._timestamps_by_frame(frames)
        return [
            timestamps[next_frame] - timestamps[current_frame]
            for current_frame, next_frame in zip(strikes, strikes[1:])
            if current_frame in timestamps and next_frame in timestamps
        ]

    @staticmethod
    def _contact_times_ms(
        frames: list[PoseFrame], strikes: list[int], toe_offs: list[int]
    ) -> list[float]:
        timestamps = RunningGaitAnalysisService._timestamps_by_frame(frames)
        contact_times = []
        for strike in strikes:
            toe_off = next((frame for frame in toe_offs if frame > strike), None)
            if toe_off is None or strike not in timestamps or toe_off not in timestamps:
                continue
            contact_times.append(timestamps[toe_off] - timestamps[strike])
        return contact_times

    @staticmethod
    def _timestamps_by_frame(frames: list[PoseFrame]) -> dict[int, int]:
        return {frame.frame_index: frame.timestamp_ms for frame in frames}

    @staticmethod
    def _stride_analysis(
        frames: list[PoseFrame], left_strikes: list[int], right_strikes: list[int]
    ) -> RunningStrideAnalysis:
        frame_map = {frame.frame_index: frame for frame in frames}
        timestamps = RunningGaitAnalysisService._timestamps_by_frame(frames)
        leg_length = RunningGaitAnalysisService._estimated_leg_length(frames)

        foot_strikes = sorted(
            [
                *RunningGaitAnalysisService._foot_strike_points(
                    frame_map, left_strikes, "left", leg_length
                ),
                *RunningGaitAnalysisService._foot_strike_points(
                    frame_map, right_strikes, "right", leg_length
                ),
            ],
            key=lambda strike: strike.frame_index,
        )

        stride_intervals = [
            *RunningGaitAnalysisService._stride_intervals(
                frames, left_strikes, "left", leg_length
            ),
            *RunningGaitAnalysisService._stride_intervals(
                frames, right_strikes, "right", leg_length
            ),
        ]
        stride_intervals.sort(key=lambda interval: interval.start_frame)

        step_intervals = []
        for current, following in zip(foot_strikes, foot_strikes[1:]):
            if current.side == following.side:
                continue
            step_intervals.append(
                RunningStepInterval(
                    from_side=current.side,
                    to_side=following.side,
                    start_frame=current.frame_index,
                    end_frame=following.frame_index,
                    duration_ms=round(
                        timestamps[following.frame_index]
                        - timestamps[current.frame_index],
                        2,
                    ),
                )
            )

        return RunningStrideAnalysis(
            foot_strikes=foot_strikes,
            stride_intervals=stride_intervals,
            step_intervals=step_intervals,
        )

    @staticmethod
    def _foot_strike_points(
        frame_map: dict[int, PoseFrame],
        strikes: list[int],
        side: str,
        leg_length: float | None,
    ) -> list[RunningFootStrike]:
        points = []
        for strike in strikes:
            frame = frame_map.get(strike)
            if frame is None:
                continue
            landmarks = RunningGaitAnalysisService._landmarks(frame)
            ankle = landmarks[f"{side}_ankle"]
            heel = landmarks[f"{side}_heel"]
            foot_x = (ankle.x + heel.x) / 2
            foot_y = (ankle.y + heel.y) / 2
            hip = RunningGaitAnalysisService._midpoint(frame, "left_hip", "right_hip")
            overstride_pct = (
                (foot_x - hip.x) / leg_length * 100 if leg_length else None
            )
            points.append(
                RunningFootStrike(
                    frame_index=frame.frame_index,
                    timestamp_ms=frame.timestamp_ms,
                    side=side,
                    foot_x=round(foot_x, 4),
                    foot_y=round(foot_y, 4),
                    hip_x=round(hip.x, 4),
                    overstride_pct=RunningGaitAnalysisService._round_optional(
                        overstride_pct
                    ),
                )
            )
        return points

    @staticmethod
    def _stride_intervals(
        frames: list[PoseFrame],
        strikes: list[int],
        side: str,
        leg_length: float | None,
    ) -> list[RunningStrideInterval]:
        frame_map = {frame.frame_index: frame for frame in frames}
        timestamps = RunningGaitAnalysisService._timestamps_by_frame(frames)
        intervals = []
        for current, following in zip(strikes, strikes[1:]):
            current_frame = frame_map.get(current)
            following_frame = frame_map.get(following)
            if current_frame is None or following_frame is None:
                continue
            current_hip = RunningGaitAnalysisService._midpoint(current_frame, "left_hip", "right_hip")
            following_hip = RunningGaitAnalysisService._midpoint(following_frame, "left_hip", "right_hip")
            stride_length_norm = (
                abs(following_hip.x - current_hip.x) / leg_length
                if leg_length
                else None
            )
            intervals.append(
                RunningStrideInterval(
                    side=side,
                    start_frame=current,
                    end_frame=following,
                    duration_ms=round(timestamps[following] - timestamps[current], 2),
                    stride_length_norm=RunningGaitAnalysisService._round_optional(
                        stride_length_norm
                    ),
                )
            )
        return intervals

    @staticmethod
    def _normalized_stride_length(
        frames: list[PoseFrame], left_strikes: list[int], right_strikes: list[int]
    ) -> float | None:
        frame_map = {frame.frame_index: frame for frame in frames}
        leg_length = RunningGaitAnalysisService._estimated_leg_length(frames)
        if not leg_length:
            return None

        lengths = []
        for strikes in (left_strikes, right_strikes):
            for current, following in zip(strikes, strikes[1:]):
                current_frame = frame_map.get(current)
                following_frame = frame_map.get(following)
                if not current_frame or not following_frame:
                    continue
                current_hip = RunningGaitAnalysisService._midpoint(current_frame, "left_hip", "right_hip")
                following_hip = RunningGaitAnalysisService._midpoint(following_frame, "left_hip", "right_hip")
                lengths.append(abs(following_hip.x - current_hip.x) / leg_length)
        return RunningGaitAnalysisService._safe_mean(lengths)

    @staticmethod
    def _vertical_oscillation_ratio(frames: list[PoseFrame]) -> float | None:
        leg_length = RunningGaitAnalysisService._estimated_leg_length(frames)
        if not leg_length:
            return None
        hip_y = [
            RunningGaitAnalysisService._midpoint(frame, "left_hip", "right_hip").y
            for frame in frames
        ]
        return (max(hip_y) - min(hip_y)) / leg_length * 100

    @staticmethod
    def _overstriding_index(
        frames: list[PoseFrame], left_strikes: list[int], right_strikes: list[int]
    ) -> float | None:
        leg_length = RunningGaitAnalysisService._estimated_leg_length(frames)
        if not leg_length:
            return None
        frame_map = {frame.frame_index: frame for frame in frames}
        values = []
        for side, strikes in (("left", left_strikes), ("right", right_strikes)):
            for strike in strikes:
                frame = frame_map.get(strike)
                if frame is None:
                    continue
                hip = RunningGaitAnalysisService._midpoint(frame, "left_hip", "right_hip")
                ankle = RunningGaitAnalysisService._landmarks(frame)[f"{side}_ankle"]
                values.append((ankle.x - hip.x) / leg_length * 100)
        return RunningGaitAnalysisService._safe_mean(values)

    @staticmethod
    def _estimated_leg_length(frames: list[PoseFrame]) -> float | None:
        lengths = []
        for frame in frames:
            landmarks = RunningGaitAnalysisService._landmarks(frame)
            for side in ("left", "right"):
                hip = landmarks[f"{side}_hip"]
                knee = landmarks[f"{side}_knee"]
                ankle = landmarks[f"{side}_ankle"]
                lengths.append(
                    RunningGaitAnalysisService._distance(hip, knee)
                    + RunningGaitAnalysisService._distance(knee, ankle)
                )
        return RunningGaitAnalysisService._safe_mean(lengths)

    @staticmethod
    def _average_y(frame: PoseFrame, first: str, second: str) -> float:
        landmarks = RunningGaitAnalysisService._landmarks(frame)
        return (landmarks[first].y + landmarks[second].y) / 2

    @staticmethod
    def _midpoint(frame: PoseFrame, first: str, second: str) -> PoseLandmark:
        landmarks = RunningGaitAnalysisService._landmarks(frame)
        first_point = landmarks[first]
        second_point = landmarks[second]
        return PoseLandmark(
            index=first_point.index,
            name=f"{first}_{second}_midpoint",
            x=(first_point.x + second_point.x) / 2,
            y=(first_point.y + second_point.y) / 2,
            z=(first_point.z + second_point.z) / 2,
            visibility=None,
            presence=None,
        )

    @staticmethod
    def _landmarks(frame: PoseFrame) -> dict[str, PoseLandmark]:
        return {landmark.name: landmark for landmark in frame.landmarks}

    @staticmethod
    def _distance(first: PoseLandmark, second: PoseLandmark) -> float:
        return ((first.x - second.x) ** 2 + (first.y - second.y) ** 2) ** 0.5

    @staticmethod
    def _safe_mean(values: list[float | None]) -> float | None:
        available = [value for value in values if value is not None]
        if not available:
            return None
        return mean(available)

    @staticmethod
    def _symmetry_pct(left: float | None, right: float | None) -> float | None:
        if left is None or right is None or left + right == 0:
            return None
        return abs(left - right) / ((left + right) / 2) * 100

    @staticmethod
    def _round_optional(value: float | None) -> float | None:
        return round(value, 2) if value is not None else None
