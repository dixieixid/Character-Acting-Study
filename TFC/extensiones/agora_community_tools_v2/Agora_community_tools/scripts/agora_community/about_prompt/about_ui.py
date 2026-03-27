"""
This module provides a simple About dialog for the Agora Community tools.
The dialog displays information about the tool, its license, and links to the community.
"""
import os
import webbrowser

from agora_community import (
    qtui,
    mayaui,
)
from agora_community.constants import (
    ROOT_PATH,
    ICONS_PATH,
    AGORA_COMMUNITY_ASSETS_URL,
    AGORA_COMMUNITY_HOME_URL,
    AGORA_COMMUNITY_DISCORD_URL,
    AGORA_STUDIO_URL,
    TOOLS_VERSION
)


TOOL_TITLE = 'About Agora Community tools'


def launch():
    """Launch the About dialog."""
    AboutWindow(parent=mayaui.mayaMainWindow()).exec()


class AboutWindow(qtui.QDialog):
    """Dialog window displaying information about the Agora Community tools."""

    def __init__(self, parent=None):
        super(AboutWindow, self).__init__(parent)
        self.setWindowTitle(f"{TOOL_TITLE} - v.{TOOLS_VERSION}")

        mayaui.addBaseStyleSheet(self)

        self.clickable_links_color = '#25A8DF'

        self.setWindowModality(qtui.Qt.ApplicationModal)
        self.setFixedWidth(450 * qtui.SCALE_FACTOR)
        self.setFixedHeight(400 * qtui.SCALE_FACTOR)
        self._create_ui()

    def open_license_file(self):
        """Open the LICENSE file with the default application."""
        license_file_path = os.path.join(ROOT_PATH, 'License.txt')
        if os.path.exists(license_file_path):
            os.startfile(license_file_path)  # Use os.startfile to open the file with the default application
        else:
            print(f"License file not found at: {license_file_path}")

    def _create_ui(self):
        """Create the UI layout and populate it with content."""
        # Define the logo path as a local variable
        agora_community_logo_path = os.path.join(ICONS_PATH, 'Agora_Community_Logo.png')
        discord_icon_path = os.path.join(ICONS_PATH, 'Discord-Symbol-Light Blurple.svg')

        # Main layout for the dialog
        main_layout = qtui.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Vertical layout for content
        vbox = qtui.QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(2 * qtui.SCALE_FACTOR)

        # Header
        header = qtui.QHBoxLayout()
        header.setContentsMargins(0, 10, 0, 10)

        header_icon = qtui.QLabel()
        header_icon.setPixmap(qtui.QPixmap(agora_community_logo_path).scaledToHeight(30 * qtui.SCALE_FACTOR))
        header_icon.setContentsMargins(10, 0, 10 * qtui.SCALE_FACTOR, 0)
        header_icon.setCursor(qtui.Qt.PointingHandCursor)
        header_icon.setToolTip("Click to visit Agora Community website")
        # Make the icon clickable
        header_icon.mousePressEvent = lambda *_: webbrowser.open(AGORA_COMMUNITY_HOME_URL)

        header.addWidget(header_icon)

        header.addStretch(1)

        label_layout = qtui.QVBoxLayout()
        label_layout.setContentsMargins(0, 0, 10, 0)
        header_label = qtui.QLabel('Agora Community Tools')
        header_label.setAlignment(qtui.Qt.AlignRight)
        header_label.setStyleSheet('font-size: 20px; font-weight: bold;')
        label_layout.addWidget(header_label)

        # Add a small description below the header
        header_description = qtui.QLabel(
            'By <a href="{}" style="color: {}; text-decoration: none;">Agora.Studio</a>'.format(
            AGORA_STUDIO_URL,
            self.clickable_links_color)
        )
        header_description.setToolTip('Click to visit Agora Studio website')
        header_description.setAlignment(qtui.Qt.AlignRight)
        header_description.setStyleSheet('font-size: 12px;')
        header_description.setWordWrap(True)
        header_description.setOpenExternalLinks(True)
        label_layout.addWidget(header_description)

        header.addLayout(label_layout)

        vbox.addLayout(header)

        separator = qtui.QFrame()
        separator.setFrameShape(qtui.QFrame.HLine)
        separator.setFrameShadow(qtui.QFrame.Sunken)
        separator.setLineWidth(1)
        separator.setStyleSheet('color: #000;')
        vbox.addWidget(separator)

        # Description
        description = qtui.QLabel(
            "A free set of animation tools for Maya, developed "
            "by Agora Studio and packaged for the Agora Community.\n"
            "These tools are currently in beta phase and may contain bugs.\n"
            "Please report any issues you encounter to the Agora Community Discord server.\n\n"
            "We appreciate your feedback and support!"
        )
        description.setContentsMargins(10 * qtui.SCALE_FACTOR, 10 * qtui.SCALE_FACTOR, 10 * qtui.SCALE_FACTOR, 0)
        description.setAlignment(qtui.Qt.AlignLeft)
        description.setWordWrap(True)
        vbox.addWidget(description)

        # Add spacing between description and license info
        spacer = qtui.QSpacerItem(0, 20 * qtui.SCALE_FACTOR, qtui.QSizePolicy.Minimum, qtui.QSizePolicy.Fixed)
        vbox.addSpacerItem(spacer)

        # License
        license_label = qtui.QLabel('License info:')
        license_label.setStyleSheet('font-weight: bold;')
        vbox.addWidget(license_label)

        license_layout = qtui.QVBoxLayout()
        license_layout.setContentsMargins(10 * qtui.SCALE_FACTOR, 0, 10 * qtui.SCALE_FACTOR, 0)
        vbox.addLayout(license_layout)

        # Add the main license text
        license_text_start = qtui.QLabel(
            "You're welcome to use this tool for either personal or commercial work."
        )
        license_text_start.setWordWrap(True)
        license_layout.addWidget(license_text_start)

        # Add the clickable "License File" link
        license_link = qtui.QLabel(
            f'<span style="color: {self.clickable_links_color}; font-weight: bold;">'
            'Read License for more info'
            '</span>'
        )
        license_link.setTextFormat(qtui.Qt.RichText)
        license_link.setCursor(qtui.Qt.PointingHandCursor)
        license_link.setToolTip('Click to open the License file')
        license_link.setAlignment(qtui.Qt.AlignLeft)

        # Connect the license link click to the open_license_file method
        license_link.mousePressEvent = lambda event: self.open_license_file()
        license_layout.addWidget(license_link)

        # Add spacer to separate the license section from the description
        vbox.addStretch(1)

        # Horizontal layout for icons
        icon_layout = qtui.QHBoxLayout()
        icon_layout.setSpacing(10 * qtui.SCALE_FACTOR)

        # Add a spacer to push content to the top
        vbox.addStretch(1)

        # Tool page link
        self.add_clickable_text_with_icon(
            vbox,
            "Tools documentation and download page",
            agora_community_logo_path,
            AGORA_COMMUNITY_ASSETS_URL,
            "Click to visit the Agora Community tools page"
        )

        # Agora Community link
        self.add_clickable_text_with_icon(
            vbox,
            "Agora Community",
            agora_community_logo_path,
            AGORA_COMMUNITY_HOME_URL,
            "Click to visit the Agora Community home page"
        )

        # Discord link
        self.add_clickable_text_with_icon(
            vbox,
            "Join our Discord",
            discord_icon_path,
            AGORA_COMMUNITY_DISCORD_URL,
            "Click to join the Agora Community Discord server"
        )

        vbox.addLayout(icon_layout)

        # Add version information at the bottom of the window
        version_layout = qtui.QHBoxLayout()
        version_layout.setContentsMargins(5 * qtui.SCALE_FACTOR, 10 * qtui.SCALE_FACTOR, 5 * qtui.SCALE_FACTOR, 5 * qtui.SCALE_FACTOR)

        version_label = qtui.QLabel('Version: {}. Copyright (c) 2025 Agora VFX inc.'.format(TOOLS_VERSION))
        version_label.setAlignment(qtui.Qt.AlignCenter)
        version_label.setStyleSheet('font-size: 10px; color: #888888;')

        version_layout.addStretch(1)
        version_layout.addWidget(version_label)

        vbox.addLayout(version_layout)

        # Add the vertical layout to the main layout
        main_layout.addLayout(vbox)

    def add_clickable_text_with_icon(self, layout, text, icon_path, url, tooltip):
        """
        Add a clickable text with an icon to the given layout.

        Args:
            layout: The layout to add the clickable text to
            text: The text to display
            icon_path: Path to the icon image
            url: URL to open when clicked
            tooltip: Tooltip text to display on hover
        """
        # Create a horizontal layout
        hbox = qtui.QHBoxLayout()
        hbox.setContentsMargins(0, 5, 0, 5)

        # Add the icon
        icon_label = qtui.QLabel()
        icon_label.setPixmap(qtui.QPixmap(icon_path).scaledToWidth(20 * qtui.SCALE_FACTOR))
        icon_label.setToolTip(tooltip)
        icon_label.setContentsMargins(10, 0, 10 * qtui.SCALE_FACTOR, 0)
        hbox.addWidget(icon_label)

        # Create the clickable text
        text_label = qtui.QLabel(
            '<a href="{}" style="color: {}; text-decoration: none;">{}</a>'.format(
                url,
                self.clickable_links_color,
                text
            )
        )
        text_label.setStyleSheet('font-size: 14px;')
        text_label.setOpenExternalLinks(True)
        text_label.setToolTip(tooltip)
        hbox.addWidget(text_label)

        # Add a stretchable space to push the content to the left
        hbox.addStretch(1)

        # Add the horizontal layout to the parent layout
        layout.addLayout(hbox)
