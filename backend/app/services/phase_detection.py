from app.schemas.phase import DetectedPhase
from app.schemas.pose import PoseFrame

SPORT_PHASES = {
    "Running": ("Foot Strike", "Mid Stance", "Toe Off"),
    "Jumping": ("Preparation", "Take Off", "Flight", "Landing"),
    "Bowling": (
        "Run Up",
        "Back Foot Contact",
        "Front Foot Contact",
        "Ball Release",
        "Follow Through",
    ),
}


class PhaseDetectionError(ValueError):
    pass


class PhaseDetectionService:
    def detect(self, frames: list[PoseFrame], sport: str) -> list[DetectedPhase]:
        phases = SPORT_PHASES.get(sport)
        if phases is None:
            raise PhaseDetectionError(f"Unsupported sport: {sport}")
        if len(frames) < len(phases):
            raise PhaseDetectionError(
                f"At least {len(phases)} pose frames are required for {sport}"
            )

        if sport == "Running":
            candidates = self._running_boundaries(frames)
        elif sport == "Jumping":
            candidates = self._jumping_boundaries(frames)
        else:
            candidates = self._bowling_boundaries(frames)
        boundaries = self._normalize_boundaries(
            candidates, len(frames), len(phases)
        )
        return [
            DetectedPhase(
                name=phase,
                start_frame=frames[boundaries[index]].frame_index,
                end_frame=frames[boundaries[index + 1] - 1].frame_index,
                frame_indexes=[
                    frame.frame_index
                    for frame in frames[
                        boundaries[index] : boundaries[index + 1]
                    ]
                ],
            )
            for index, phase in enumerate(phases)
        ]

    def _running_boundaries(self, frames: list[PoseFrame]) -> list[int]:
        hip_centers = [self._center_x(frame, "left_hip", "right_hip") for frame in frames]
        ankle_maps = [self._landmarks(frame) for frame in frames]
        support_distance = [
            min(
                abs(points["left_ankle"].x - hip_x),
                abs(points["right_ankle"].x - hip_x),
            )
            for points, hip_x in zip(ankle_maps, hip_centers, strict=True)
        ]
        middle_start = max(1, len(frames) // 5)
        middle_end = max(middle_start + 1, len(frames) * 4 // 5)
        mid_stance = min(
            range(middle_start, middle_end), key=support_distance.__getitem__
        )
        ankle_height = [
            max(points["left_ankle"].y, points["right_ankle"].y)
            for points in ankle_maps
        ]
        foot_strike = max(
            range(0, max(1, mid_stance + 1)), key=ankle_height.__getitem__
        )
        upward_velocity = [0.0] + [
            ankle_height[index - 1] - ankle_height[index]
            for index in range(1, len(frames))
        ]
        toe_off = max(
            range(min(mid_stance + 1, len(frames) - 1), len(frames)),
            key=upward_velocity.__getitem__,
        )
        return [
            (foot_strike + mid_stance) // 2 + 1,
            (mid_stance + toe_off) // 2 + 1,
        ]

    def _jumping_boundaries(self, frames: list[PoseFrame]) -> list[int]:
        hip_y = [self._center_y(frame, "left_hip", "right_hip") for frame in frames]
        preparation_window = range(0, max(1, len(frames) * 3 // 5))
        lowest_position = max(preparation_window, key=hip_y.__getitem__)
        apex = min(
            range(lowest_position, len(frames)), key=hip_y.__getitem__
        )
        take_off = lowest_position + max(1, (apex - lowest_position) // 2)
        flight_end = apex + max(1, (len(frames) - apex) // 3)
        return [lowest_position + 1, take_off + 1, flight_end]

    def _bowling_boundaries(self, frames: list[PoseFrame]) -> list[int]:
        wrist_name = self._dominant_wrist(frames)
        wrist_points = [self._landmarks(frame)[wrist_name] for frame in frames]
        wrist_speed = [0.0] + [
            self._distance(wrist_points[index - 1], wrist_points[index])
            for index in range(1, len(frames))
        ]
        search_start = max(1, len(frames) // 5)
        release = max(
            range(search_start, len(frames)), key=wrist_speed.__getitem__
        )

        contact_candidates = self._ankle_contact_candidates(frames, release)
        if len(contact_candidates) >= 2:
            back_contact, front_contact = contact_candidates[-2:]
        else:
            back_contact = max(1, release * 2 // 5)
            front_contact = max(back_contact + 1, release * 3 // 4)
        release_end = release + max(1, (len(frames) - release) // 4)
        return [back_contact, front_contact, release, release_end]

    def _ankle_contact_candidates(
        self, frames: list[PoseFrame], release: int
    ) -> list[int]:
        heights = [
            max(
                self._landmarks(frame)["left_ankle"].y,
                self._landmarks(frame)["right_ankle"].y,
            )
            for frame in frames
        ]
        return [
            index
            for index in range(1, min(release, len(frames) - 1))
            if heights[index] >= heights[index - 1]
            and heights[index] >= heights[index + 1]
        ]

    def _dominant_wrist(self, frames: list[PoseFrame]) -> str:
        names = ("left_wrist", "right_wrist")
        travel = {}
        for name in names:
            points = [self._landmarks(frame)[name] for frame in frames]
            travel[name] = sum(
                self._distance(points[index - 1], points[index])
                for index in range(1, len(points))
            )
        return max(names, key=travel.__getitem__)

    @staticmethod
    def _normalize_boundaries(
        candidates: list[int], frame_count: int, phase_count: int
    ) -> list[int]:
        boundaries = [0]
        for index in range(phase_count - 1):
            remaining = phase_count - index - 1
            fallback = round(frame_count * (index + 1) / phase_count)
            candidate = candidates[index] if index < len(candidates) else fallback
            lower = boundaries[-1] + 1
            upper = frame_count - remaining
            boundaries.append(min(max(candidate, lower), upper))
        boundaries.append(frame_count)
        return boundaries

    @staticmethod
    def _landmarks(frame: PoseFrame) -> dict:
        return {landmark.name: landmark for landmark in frame.landmarks}

    def _center_x(self, frame: PoseFrame, left: str, right: str) -> float:
        landmarks = self._landmarks(frame)
        return (landmarks[left].x + landmarks[right].x) / 2

    def _center_y(self, frame: PoseFrame, left: str, right: str) -> float:
        landmarks = self._landmarks(frame)
        return (landmarks[left].y + landmarks[right].y) / 2

    @staticmethod
    def _distance(first, second) -> float:
        return ((first.x - second.x) ** 2 + (first.y - second.y) ** 2) ** 0.5
