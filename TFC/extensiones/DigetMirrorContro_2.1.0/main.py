import sys

current_version = int("{0}{1}".format(sys.version_info[0], sys.version_info[1]))
if current_version == 37:
    from DigetMirrorControl.__hybrid__.digetMirrorControl37 import DigetMirrorControlUi
if current_version == 39:
    from DigetMirrorControl.__hybrid__.digetMirrorControl39 import DigetMirrorControlUi
if current_version == 310:
    from DigetMirrorControl.__hybrid__.digetMirrorControl310 import DigetMirrorControlUi
if current_version == 311:
    from DigetMirrorControl.__hybrid__.digetMirrorControl311 import DigetMirrorControlUi


def create_gui():
    DigetMirrorControlUi.show_dialog()


def main():
    create_gui()
