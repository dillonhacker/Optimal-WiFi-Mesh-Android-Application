"""
app/widgets/heatmap_widget.py

HeatmapWidget:
- Pure PySide6 (no matplotlib)
- Displays channel overlap using QColor intensity.
- Blue = very low overlap
- Dark red = high overlap

We draw a horizontal bar with one segment per distinct channel.
"""

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtCore import Qt


class HeatmapWidget(QLabel):
    """
    A simple PySide6-drawn heatmap.

    Usage:
        heatmap.update_heatmap([[1,6], [6,11], [1,11]])
    """

    def update_heatmap(self, channel_lists: list[list[int]]) -> None:
        """
        Convert a list of best-channel lists into a colored overlap bar.

        Args:
            channel_lists:
                Example:
                    [
                      [1, 6],
                      [6, 11],
                      [1, 11],
                    ]
        """
        # Count how often each channel appears.
        counts: dict[int, int] = {}
        for ch_list in channel_lists:
            for ch in ch_list:
                counts[ch] = counts.get(ch, 0) + 1

        # If no channels exist yet, show text.
        if not counts:
            self.setText("No channel data available for heatmap.")
            return

        channels = sorted(counts.keys())
        max_count = max(counts.values())

        # Size of the heatmap bar.
        width, height = 500, 80

        pix = QPixmap(width, height)
        pix.fill(Qt.white)

        painter = QPainter(pix)

        # Each channel gets a segment.
        step = width / len(channels)

        for i, ch in enumerate(channels):
            ratio = counts[ch] / max_count  # 0..1

            # Interpolate between blue (low) and red (high).
            # Red intensity grows with overlap ratio.
            color = QColor(
                int(255 * ratio),         # red
                0,                        # green
                int(255 * (1 - ratio))    # blue
            )

            painter.fillRect(int(i * step), 0, int(step), height, color)

        painter.end()
        self.setPixmap(pix)
