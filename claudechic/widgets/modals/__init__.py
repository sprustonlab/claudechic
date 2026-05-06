"""Modal screen widgets."""

from claudechic.widgets.modals.base import InfoModal, InfoSection
from claudechic.widgets.modals.computer_info import ComputerInfoModal
from claudechic.widgets.modals.process_detail import ProcessDetailModal
from claudechic.widgets.modals.process_modal import ProcessModal
from claudechic.widgets.modals.profile import ProfileModal
from claudechic.widgets.modals.url_confirm import URLConfirmModal

__all__ = [
    "ComputerInfoModal",
    "InfoModal",
    "InfoSection",
    "ProfileModal",
    "ProcessModal",
    "ProcessDetailModal",
    "URLConfirmModal",
]
