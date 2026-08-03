import logging
import sys
import traceback

from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    
    Supported signals are:
    finished
        No data
    error
        tuple (exctype, value, traceback.format_exc() )
    result
        object data returned from processing, anything
    progress
        int indication of progress
    """
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)
    status = Signal(str)

class WorkerThread(QThread):
    """
    Worker thread that executes a function in a separate thread.
    """
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        try:
            # Check if function accepts 'progress_callback'
            from inspect import signature
            sig = signature(self.fn)
            if 'progress_callback' in sig.parameters:
                # Define callback to emit signals
                def progress_cb(msg, val=None):
                    self.signals.status.emit(msg)
                    if val is not None:
                         self.signals.progress.emit(val)

                self.kwargs['progress_callback'] = progress_cb

            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


